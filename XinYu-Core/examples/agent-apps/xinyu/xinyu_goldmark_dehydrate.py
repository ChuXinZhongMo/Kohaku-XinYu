from __future__ import annotations

import json
import os
import re
import sqlite3
import time
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

from stores.persona_runtime_overlay import write_goldmark_overlay
from xinyu_dialogue_archive import dialogue_archive_path
from xinyu_goldmark import read_goldmark_overlay
from xinyu_llm_api import (
    anthropic_headers,
    anthropic_messages_endpoint,
    anthropic_payload_from_messages,
    extract_anthropic_text,
    extract_openai_text,
    is_anthropic_messages_provider,
    openai_headers,
)
from xinyu_sent_reply_index import normalize_visible_text


PROMPT_VERSION = "goldmark_dehydration_v1"
DEFAULT_BATCH_SIZE = 5
MAX_ERROR_LOG_CHARS = 500
MAX_OWNER_NOTE_CHARS = 500
MAX_VISIBLE_TEXT_CHARS = 1200
PROCESSING_STALE_SECONDS = 15 * 60
SKIP_TOO_SHORT = "SKIP_TOO_SHORT"

VALID_STATUSES = {"pending", "processing", "done", "failed"}
PROVIDER_CHOICES = {"auto", "local", "llm"}
FORBIDDEN_OUTPUT_MARKERS = (
    "turn-",
    "adapter_msg_id",
    "adapter_message_id",
    "archive_assistant_message_id",
    "message_id",
    "http://",
    "https://",
    "[CQ:",
    "```",
)
_CODE_FENCE_RE = re.compile(r"```[\s\S]*?```", re.M)
_TRACEBACK_RE = re.compile(r"(?i)^\s*(traceback|file \".+\", line \d+|at .+\(.+\)|[a-z_]*error:|exception:)")


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _parse_iso(value: Any) -> datetime | None:
    text = _safe_str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _entry_identity(entry: dict[str, Any]) -> str:
    return "|".join(
        (
            _safe_str(entry.get("adapter")).strip(),
            _safe_str(entry.get("adapter_msg_id") or entry.get("adapter_message_id")).strip(),
            _safe_str(entry.get("route")).strip(),
            _safe_str(entry.get("turn_id")).strip(),
        )
    )


def _read_archive_assistant_text(root: Path, archive_message_id: str) -> str:
    if not _safe_str(archive_message_id).strip().isdigit():
        return ""
    path = dialogue_archive_path(root)
    if not path.exists():
        return ""
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=2)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """
            SELECT role, text
            FROM dialogue_messages
            WHERE id = ?
            """,
            (int(archive_message_id),),
        ).fetchone()
    except sqlite3.Error:
        return ""
    finally:
        if conn is not None:
            conn.close()
    if row is None or _safe_str(row["role"]).strip() != "assistant":
        return ""
    return normalize_visible_text(_safe_str(row["text"]))[:MAX_VISIBLE_TEXT_CHARS]


def _visible_text_for_entry(root: Path, entry: dict[str, Any]) -> str:
    archive_text = _read_archive_assistant_text(root, _safe_str(entry.get("archive_assistant_message_id")).strip())
    if archive_text:
        return preprocess_dehydration_source(archive_text)
    return preprocess_dehydration_source(_safe_str(entry.get("visible_text_preview")))


def _code_symbol_ratio(text: str) -> float:
    compact = re.sub(r"\s+", "", _safe_str(text))
    if not compact:
        return 0.0
    code_symbols = sum(1 for char in compact if char in "{}[]();=<>|\\")
    return code_symbols / max(1, len(compact))


def _jsonish_line(text: str) -> bool:
    stripped = text.strip()
    if stripped[0:1] in {"{", "["} and stripped.count(":") >= 3 and stripped.count(",") >= 3:
        return True
    if len(stripped) < 80:
        return False
    return _code_symbol_ratio(stripped) > 0.22 and not re.search(r"[\u4e00-\u9fff]", stripped)


def preprocess_dehydration_source(text: str) -> str:
    """Strip code/traceback-heavy material before extracting reusable voice traits."""
    without_fences = _CODE_FENCE_RE.sub(" ", _safe_str(text))
    kept: list[str] = []
    for raw_line in without_fences.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith(">"):
            continue
        if _TRACEBACK_RE.search(line):
            continue
        if _jsonish_line(line):
            continue
        if len(line) > 240 and _code_symbol_ratio(line) > 0.12:
            continue
        kept.append(line)
    cleaned = normalize_visible_text(" ".join(kept) if kept else without_fences)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:MAX_VISIBLE_TEXT_CHARS]


def build_dehydration_prompt(*, visible_text: str, owner_note: str) -> tuple[str, str]:
    system = (
        "You are XinYu's Goldmark vibe dehydrator. You extract only reusable response-state "
        "and structural traits from a marked assistant reply. You must not preserve facts, names, "
        "project details, jokes, catchphrases, or exact wording. Output one strict JSON object only."
    )
    user = f"""
[Dehydration Protocol v1]
Analyze this assistant reply that the owner marked as good.

Assistant reply:
{visible_text}

Owner note:
{owner_note or "none"}

Hard filters:
- Remove all business facts, code details, project names, people names, IDs, URLs, and specific conclusions.
- Remove catchphrases, memes, recurring wording, quoted wording, and exact sentence shapes.
- Do not teach the model to copy the original sentence.

Extract only:
- tone_tags: 2 to 6 short tags about reusable tone/state, such as concise, non-defensive, emotionally receptive, relaxed, direct, lightly teasing.
- structural_pattern: one concise sentence describing reusable structure only.

Return strict JSON only:
{{"tone_tags":["..."],"structural_pattern":"..."}}
""".strip()
    return system, user


def _load_local_env(root: Path) -> None:
    env_path = root / "xinyu.local.env"
    if not env_path.exists():
        return
    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _llm_configured(root: Path) -> bool:
    _load_local_env(root)
    return bool(os.environ.get("XINYU_BASE_URL", "").strip() and os.environ.get("XINYU_API_KEY", "").strip())


def _choose_provider(root: Path, provider: str) -> str:
    normalized = provider.strip().lower() or "auto"
    if normalized not in PROVIDER_CHOICES:
        normalized = "auto"
    if normalized == "auto":
        return "llm" if _llm_configured(root) and os.environ.get("XINYU_GOLDMARK_DEHYDRATE_PROVIDER", "").lower() == "llm" else "local"
    return normalized


def _call_llm_dehydrator(root: Path, *, visible_text: str, owner_note: str, timeout_seconds: int = 45) -> dict[str, Any]:
    _load_local_env(root)
    base_url = os.environ.get("XINYU_BASE_URL", "").strip()
    api_key = os.environ.get("XINYU_API_KEY", "").strip()
    model = os.environ.get("XINYU_GOLDMARK_DEHYDRATE_MODEL", "").strip() or os.environ.get("XINYU_LLM_MODEL", "").strip()
    model = model or "mimo-v2.5-pro"
    provider = os.environ.get("XINYU_GOLDMARK_DEHYDRATE_LLM_PROVIDER", "").strip() or os.environ.get("XINYU_LLM_PROVIDER", "").strip()
    if not base_url or not api_key:
        raise RuntimeError("llm_not_configured")

    system, user = build_dehydration_prompt(visible_text=visible_text, owner_note=owner_note)
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    if is_anthropic_messages_provider(provider):
        url = anthropic_messages_endpoint(base_url)
        body = anthropic_payload_from_messages(messages, model=model, temperature=0.1, max_tokens=500)
        headers = anthropic_headers(api_key)
        extract_text = extract_anthropic_text
    else:
        url = base_url.rstrip("/") + "/chat/completions"
        body = {
            "model": model,
            "temperature": 0.1,
            "max_tokens": 500,
            "messages": messages,
        }
        headers = openai_headers(api_key)
        extract_text = extract_openai_text
    request = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw_body = response.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"llm_request_failed:{type(exc).__name__}") from exc
    try:
        payload = json.loads(raw_body)
        if not isinstance(payload, dict):
            raise AttributeError("non-object response")
        text = extract_text(payload)
    except (AttributeError, json.JSONDecodeError) as exc:
        raise RuntimeError("llm_invalid_response") from exc
    return _parse_feature_json(text)


def _strip_trailing_commas(text: str) -> str:
    previous = ""
    current = text
    while current != previous:
        previous = current
        current = re.sub(r",(\s*[}\]])", r"\1", current)
    return current


def _balanced_json_object(text: str) -> str:
    start = text.find("{")
    if start < 0:
        return text
    depth = 0
    in_string = False
    escape = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return text[start:]


def extract_json_from_markdown(text: str) -> dict[str, Any]:
    cleaned = _safe_str(text).strip()
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, flags=re.I)
    if fenced:
        cleaned = fenced.group(1).strip()
    cleaned = _balanced_json_object(cleaned)
    cleaned = _strip_trailing_commas(cleaned)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise RuntimeError("feature_json_invalid") from exc
    if not isinstance(data, dict):
        raise RuntimeError("feature_json_not_object")
    return data


def _parse_feature_json(text: str) -> dict[str, Any]:
    return extract_json_from_markdown(text)


def _local_dehydrator(*, visible_text: str, owner_note: str) -> dict[str, Any]:
    text = normalize_visible_text(visible_text)
    note = normalize_visible_text(owner_note)
    compact = re.sub(r"\s+", "", text)
    tags: list[str] = []

    if len(compact) <= 16:
        tags.extend(["极简", "直接收束"])
    elif len(compact) <= 70:
        tags.append("简洁")
    else:
        tags.append("克制展开")

    if not any(marker in text for marker in ("抱歉", "对不起", "我应该", "我会注意")):
        tags.append("非防御性")
    if any(marker in note for marker in ("语气", "自然", "舒服", "像人", "不错", "可以")):
        tags.append("自然")
    if any(marker in note for marker in ("吐槽", "准", "锋利", "直接")):
        tags.append("判断直接")
    if any(marker in text for marker in ("。", "，")) and len(compact) <= 80:
        tags.append("低解释负担")

    tags = list(dict.fromkeys(tags))[:6] or ["简洁", "非防御性"]
    if len(compact) <= 16:
        pattern = "使用极短句直接确认或收束，不展开机制解释，也不追加补偿性说明。"
    elif "？" in text or "?" in text:
        pattern = "先承接当前语境，再用一个轻量问题把话题交回给对方。"
    elif len(compact) <= 70:
        pattern = "用短句给出核心反应，保留一点停顿感，避免模板化前缀和长解释。"
    else:
        pattern = "先承接情绪，再按少量层次展开判断，整体保持克制而不防卫。"
    return {"tone_tags": tags, "structural_pattern": pattern}


def _natural_length(text: str) -> int:
    return len("".join(re.findall(r"[\w\u4e00-\u9fff]", normalize_visible_text(text))))


def _should_skip_too_short(text: str) -> bool:
    compact = re.sub(r"\s+", "", normalize_visible_text(text))
    if _natural_length(compact) < 15:
        return True
    short_instruction_markers = ("删了", "重跑", "别废话", "直接", "不用解释", "知道了", "可以")
    return len(compact) <= 24 and any(marker in compact for marker in short_instruction_markers)


def _source_substrings(text: str, min_len: int = 8) -> set[str]:
    compact = re.sub(r"\s+", "", normalize_visible_text(text))
    if len(compact) < min_len:
        return set()
    return {compact[index : index + min_len] for index in range(0, max(0, len(compact) - min_len + 1))}


def validate_vibe_features(features: dict[str, Any], *, source_text: str) -> dict[str, Any]:
    if not isinstance(features, dict):
        return {"ok": False, "reason": "features_not_object"}
    raw_tags = features.get("tone_tags")
    pattern = normalize_visible_text(_safe_str(features.get("structural_pattern")))
    if not isinstance(raw_tags, list):
        return {"ok": False, "reason": "tone_tags_not_list"}
    tags = [normalize_visible_text(_safe_str(tag)) for tag in raw_tags]
    tags = [tag for tag in tags if tag]
    if not 1 <= len(tags) <= 8:
        return {"ok": False, "reason": "tone_tags_count_invalid"}
    if any(len(tag) > 24 for tag in tags):
        return {"ok": False, "reason": "tone_tag_too_long"}
    if not 8 <= len(pattern) <= 500:
        return {"ok": False, "reason": "structural_pattern_length_invalid"}
    combined = "\n".join([*tags, pattern])
    lowered = combined.lower()
    if any(marker.lower() in lowered for marker in FORBIDDEN_OUTPUT_MARKERS):
        return {"ok": False, "reason": "forbidden_marker"}
    source_parts = _source_substrings(source_text)
    output_compact = re.sub(r"\s+", "", combined)
    if any(part and part in output_compact for part in source_parts):
        return {"ok": False, "reason": "source_text_copied"}
    return {
        "ok": True,
        "features": {
            "tone_tags": tags,
            "structural_pattern": pattern,
        },
    }


def _mark_processing(root: Path, identities: set[str], *, provider: str) -> None:
    entries = read_goldmark_overlay(root)
    now = _now_iso()
    for item in entries:
        if _entry_identity(item) in identities:
            item["dehydration_status"] = "processing"
            item["dehydration_provider"] = provider
            item["processing_started_at"] = now
            item["dehydration_started_at"] = now
            item["processing_stale_after_seconds"] = PROCESSING_STALE_SECONDS
            item["error_log"] = None
    write_goldmark_overlay(root, entries)


def _update_entry(root: Path, identity: str, updates: dict[str, Any]) -> None:
    entries = read_goldmark_overlay(root)
    for item in entries:
        if _entry_identity(item) == identity:
            item.update(updates)
            break
    write_goldmark_overlay(root, entries)


def _processing_is_stale(entry: dict[str, Any]) -> bool:
    started = _parse_iso(entry.get("processing_started_at") or entry.get("dehydration_started_at"))
    if started is None:
        return True
    age = (datetime.now().astimezone() - started).total_seconds()
    return age > PROCESSING_STALE_SECONDS


def _candidate_entries(root: Path, *, limit: int, force: bool) -> tuple[list[dict[str, Any]], int]:
    entries = read_goldmark_overlay(root)
    recovered = 0
    for item in entries:
        status = _safe_str(item.get("dehydration_status") or "pending").strip().lower()
        if status == "processing" and _processing_is_stale(item):
            item["dehydration_status"] = "pending"
            item["stale_processing_recovered_at"] = _now_iso()
            item["error_log"] = "stale_processing_recovered"
            recovered += 1
    if recovered:
        write_goldmark_overlay(root, entries)

    candidates: list[dict[str, Any]] = []
    for item in entries:
        status = _safe_str(item.get("dehydration_status") or "pending").strip().lower()
        if status not in VALID_STATUSES:
            status = "pending"
        if force:
            if status in {"pending", "failed", "done"}:
                candidates.append(dict(item))
        elif status == "pending":
            candidates.append(dict(item))
        if len(candidates) >= limit:
            break
    return candidates, recovered


def dehydrate_one_entry(
    root: Path,
    entry: dict[str, Any],
    *,
    provider: str = "auto",
    timeout_seconds: int = 45,
) -> dict[str, Any] | str:
    selected_provider = _choose_provider(root, provider)
    visible_text = _visible_text_for_entry(root, entry)
    if not visible_text:
        raise RuntimeError("missing_visible_text")
    if _should_skip_too_short(visible_text):
        return SKIP_TOO_SHORT
    owner_note = _safe_str(entry.get("owner_note")).strip()[:MAX_OWNER_NOTE_CHARS]
    if selected_provider == "llm":
        raw_features = _call_llm_dehydrator(
            root,
            visible_text=visible_text,
            owner_note=owner_note,
            timeout_seconds=timeout_seconds,
        )
    else:
        raw_features = _local_dehydrator(visible_text=visible_text, owner_note=owner_note)
    validation = validate_vibe_features(raw_features, source_text=visible_text)
    if not validation.get("ok"):
        raise RuntimeError("invalid_vibe_features:" + _safe_str(validation.get("reason"), "unknown"))
    features = dict(validation["features"])
    features["prompt_version"] = PROMPT_VERSION
    features["provider"] = selected_provider
    return features


def run_goldmark_dehydration_maintenance(
    root: Path,
    *,
    limit: int = DEFAULT_BATCH_SIZE,
    force: bool = False,
    provider: str = "auto",
    timeout_seconds: int = 45,
) -> dict[str, Any]:
    safe_limit = max(1, int(limit))
    selected_provider = _choose_provider(root, provider)
    candidates, recovered = _candidate_entries(root, limit=safe_limit, force=force)
    if not candidates:
        return {
            "status": "idle",
            "processed": 0,
            "succeeded": 0,
            "failed": 0,
            "recovered": recovered,
            "provider": selected_provider,
            "notes": ["goldmark_dehydration_no_pending"],
        }

    identities = {_entry_identity(item) for item in candidates}
    _mark_processing(root, identities, provider=selected_provider)
    processed = 0
    succeeded = 0
    failed = 0
    skipped = 0
    failures: list[str] = []
    for candidate in candidates:
        identity = _entry_identity(candidate)
        processed += 1
        now = _now_iso()
        try:
            features = dehydrate_one_entry(
                root,
                candidate,
                provider=selected_provider,
                timeout_seconds=timeout_seconds,
            )
        except Exception as exc:
            failed += 1
            error = f"{type(exc).__name__}: {exc}"[:MAX_ERROR_LOG_CHARS]
            failures.append(error)
            _update_entry(
                root,
                identity,
                {
                    "dehydration_status": "failed",
                    "dehydration_finished_at": now,
                    "dehydration_provider": selected_provider,
                    "error_log": error,
                },
            )
            continue
        if features == SKIP_TOO_SHORT:
            skipped += 1
            _update_entry(
                root,
                identity,
                {
                    "dehydration_status": "done",
                    "dehydration_finished_at": now,
                    "dehydration_provider": selected_provider,
                    "vibe_features": SKIP_TOO_SHORT,
                    "dehydration_skip_reason": "too_short_or_minimal_instruction",
                    "error_log": None,
                },
            )
            continue
        succeeded += 1
        _update_entry(
            root,
            identity,
            {
                "dehydration_status": "done",
                "dehydration_finished_at": now,
                "dehydration_provider": selected_provider,
                "vibe_features": features,
                "error_log": None,
            },
        )

    return {
        "status": "processed",
        "processed": processed,
        "succeeded": succeeded,
        "failed": failed,
        "skipped": skipped,
        "recovered": recovered,
        "provider": selected_provider,
        "force": force,
        "notes": ["goldmark_dehydration_processed"] + failures[:3],
    }

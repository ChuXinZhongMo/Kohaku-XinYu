from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from state_service import append_jsonl, atomic_write_text


TRACE_REL = Path("runtime/group_shadow/group_shadow_observations.jsonl")
STATE_REL = Path("memory/context/group_shadow_state.md")

STYLE_PRESSURE_MARKERS = (
    "AI味",
    "太AI",
    "像AI",
    "GPT味",
    "机械",
    "模板",
    "模版",
    "客服",
    "接待腔",
    "不像人",
)

COMMAND_PREFIXES = ("/", "!", "！", ".", "#")
URL_RE = re.compile(r"https?://|www\.", re.IGNORECASE)


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _hash_id(value: Any, *, length: int = 16) -> str:
    text = _safe_str(value).strip()
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:length]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _trim(text: Any, limit: int = 260) -> str:
    clean = re.sub(r"\s+", " ", _safe_str(text)).strip()
    if len(clean) <= limit:
        return clean
    return clean[: max(0, limit - 3)].rstrip() + "..."


def _contains_any(text: str, markers: tuple[str, ...]) -> list[str]:
    return [marker for marker in markers if marker and marker in text]


def classify_group_shadow_message(text: str, *, triggered: bool) -> dict[str, Any]:
    clean = _trim(text, limit=1000)
    compact = re.sub(r"\s+", "", clean)
    markers = {
        "style_pressure": _contains_any(clean, STYLE_PRESSURE_MARKERS),
        "url": ["url"] if URL_RE.search(clean) else [],
        "command_like": ["command_prefix"] if compact.startswith(COMMAND_PREFIXES) else [],
        "question": ["question"] if "?" in clean or "？" in clean else [],
    }
    risk_flags: list[str] = []
    if len(clean) <= 2:
        risk_flags.append("too_short_to_learn")
    if markers["command_like"]:
        risk_flags.append("command_like")
    if not triggered and len(clean) < 6:
        risk_flags.append("untriggered_short_chatter")
    if markers["style_pressure"]:
        risk_flags.append("style_pressure_in_group")
    if triggered:
        learning_candidate = "triggered_reply_context"
    elif markers["url"] or markers["question"] or len(clean) >= 18:
        learning_candidate = "ambient_social_context"
    else:
        learning_candidate = "low_signal_chatter"
    return {
        "text_chars": len(clean),
        "markers": markers,
        "risk_flags": risk_flags,
        "learning_candidate": learning_candidate,
    }


def record_group_shadow_observation(
    root: Path,
    *,
    event: dict[str, Any],
    text: str,
    normalized_text: str = "",
    triggered: bool = False,
    trigger_reason: str = "",
    allowed_group: bool = False,
    prepare_reason: str = "",
    max_text_chars: int = 260,
) -> dict[str, Any]:
    root = Path(root)
    raw_group_id = _safe_str(event.get("group_id")).strip()
    raw_user_id = _safe_str(event.get("user_id")).strip()
    raw_message_id = _safe_str(event.get("message_id")).strip()
    observed_at = _now_iso()
    clean_text = _trim(text, limit=max(40, int(max_text_chars)))
    classification = classify_group_shadow_message(normalized_text or text, triggered=triggered)
    trace_path = root / TRACE_REL
    row = {
        "observed_at": observed_at,
        "source": "qq_gateway_group_shadow",
        "reply_policy": "no_reply_shadow_only",
        "stable_memory_write": "blocked",
        "owner_relationship_write": "blocked",
        "group_id_hash": _hash_id(raw_group_id),
        "actor_hash": _hash_id(raw_user_id),
        "message_id_hash": _hash_id(raw_message_id),
        "allowed_group": bool(allowed_group),
        "triggered": bool(triggered),
        "trigger_reason": _safe_str(trigger_reason),
        "prepare_reason": _safe_str(prepare_reason),
        "text_excerpt": clean_text,
        "normalized_text_excerpt": _trim(normalized_text or text, limit=max(40, int(max_text_chars))),
        **classification,
    }
    append_jsonl(trace_path, row)
    _write_state(root, row)
    return {
        "recorded": True,
        "path": str(trace_path),
        "notes": ["group_shadow_observed", "no_reply", "stable_memory_write_blocked"],
        "row": row,
    }


def _write_state(root: Path, row: dict[str, Any]) -> None:
    state_path = root / STATE_REL
    state_path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(
        [
            "---",
            "title: Group Shadow State",
            "memory_type: group_shadow_state",
            "time_scope: short_term",
            "subject_ids: [xinyu]",
            "protected: true",
            "source: xinyu_group_shadow_observer",
            f"updated_at: {_safe_str(row.get('observed_at'))}",
            "status: active",
            "tags: [runtime, group, shadow, no-reply]",
            "---",
            "",
            "# Group Shadow State",
            "",
            "## Latest Observation",
            f"- observed_at: {_safe_str(row.get('observed_at'))}",
            f"- group_id_hash: {_safe_str(row.get('group_id_hash'))}",
            f"- actor_hash: {_safe_str(row.get('actor_hash'))}",
            f"- triggered: {str(bool(row.get('triggered'))).lower()}",
            f"- trigger_reason: {_safe_str(row.get('trigger_reason')) or 'none'}",
            f"- learning_candidate: {_safe_str(row.get('learning_candidate'))}",
            f"- risk_flags: {', '.join(row.get('risk_flags') or []) or 'none'}",
            f"- text_excerpt: {_safe_str(row.get('text_excerpt'))}",
            "",
            "## Boundary",
            "- reply_policy: no_reply_shadow_only",
            "- stable_memory_write: blocked",
            "- owner_relationship_write: blocked",
            "- use: observe group social texture before enabling active replies",
        ]
    )
    atomic_write_text(state_path, content)

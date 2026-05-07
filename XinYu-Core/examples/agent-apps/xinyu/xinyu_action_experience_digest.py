from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_visible_text_sanitizer import (
    sanitize_visible_text,
    visible_action_pressure_label,
    visible_action_result_label,
    visible_action_theme_label,
)


ACTION_RESIDUE_REL = Path("runtime/life_kernel/action_experience_residue.jsonl")
DIGEST_STATE_REL = Path("runtime/life_kernel/action_experience_digest_state.json")
DIGEST_TRACE_REL = Path("runtime/life_kernel/action_experience_digest_trace.jsonl")
DREAM_SEEDS_REL = Path("memory/dreams/dream_seeds.md")
REFLECTION_QUEUE_REL = Path("memory/reflection/reflection_queue.md")


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _compact(value: Any, *, limit: int = 220, default: str = "none") -> str:
    text = re.sub(r"\s+", " ", _safe_str(value).strip())
    if not text:
        return default
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _bounded_float(value: Any, *, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return round(max(0.0, min(1.0, number)), 3)


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig", errors="replace")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def _field_from_block(block: str, key: str, default: str = "none") -> str:
    prefix = f"- {key}:"
    for line in block.splitlines():
        stripped = line.strip()
        if stripped.startswith(prefix):
            value = stripped.removeprefix(prefix).strip()
            return value or default
    return default


def _markdown_block(text: str, heading_id: str) -> str:
    if not heading_id:
        return ""
    pattern = re.compile(rf"(?ms)^## {re.escape(heading_id)}\n(?P<body>.*?)(?=^## |\Z)")
    match = pattern.search(text)
    return match.group("body") if match else ""


def _load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": 1, "digested_ids": []}
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "digested_ids": []}
    if not isinstance(value, dict):
        return {"version": 1, "digested_ids": []}
    ids = value.get("digested_ids")
    if not isinstance(ids, list):
        value["digested_ids"] = []
    return value


def _write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def _hash_id(text: str, length: int = 10) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:length]


def _date_part(produced_at: str) -> str:
    match = re.match(r"\d{4}-\d{2}-\d{2}", produced_at)
    return match.group(0) if match else datetime.now().astimezone().date().isoformat()


def _seed_id(row: dict[str, Any], produced_at: str) -> str:
    exp_id = _safe_str(row.get("experience_id"), "unknown")
    return f"seed-action-{_date_part(produced_at)}-{_hash_id(exp_id)}"


def _pressure_band(row: dict[str, Any]) -> str:
    pressure = row.get("pressure") if isinstance(row.get("pressure"), dict) else {}
    return _safe_str(pressure.get("band"), "unknown") or "unknown"


def _pressure_score(row: dict[str, Any]) -> float:
    pressure = row.get("pressure") if isinstance(row.get("pressure"), dict) else {}
    return _bounded_float(pressure.get("score"), default=0.0)


def _summary_fragments(row: dict[str, Any]) -> list[str]:
    fragments: list[str] = []
    for key in ("memory_candidates", "outcome_summary"):
        values = row.get(key)
        if not isinstance(values, list):
            continue
        for item in values:
            text = _compact(item, limit=150, default="")
            if text and text not in fragments:
                fragments.append(text.replace("\\", "/"))
            if len(fragments) >= 3:
                return fragments
    return fragments


def _theme(row: dict[str, Any]) -> str:
    tool = _safe_str(row.get("tool"), "unknown_tool") or "unknown_tool"
    target = _safe_str(row.get("target_alias"), "none") or "none"
    return _compact(visible_action_theme_label(f"local action pressure after {tool}:{target}"), limit=120)


def _residue(row: dict[str, Any]) -> str:
    result = _safe_str(row.get("result"), "unknown") or "unknown"
    band = _pressure_band(row)
    fragments = [sanitize_visible_text(item) for item in _summary_fragments(row)]
    detail = "；".join(item for item in fragments if item) or "没有保留可见细节"
    return _compact(
        f"{_theme(row)} {visible_action_result_label(result)}；{visible_action_pressure_label(band)}；{detail}",
        limit=300,
    )


def _emotional_weight(row: dict[str, Any]) -> int:
    salience = _bounded_float(row.get("salience"), default=0.0)
    score = _pressure_score(row)
    weight = 45 + round(salience * 34) + round(score * 16)
    if _safe_str(row.get("result")) not in {"", "success"}:
        weight += 6
    return max(45, min(95, weight))


def _reflection_priority(row: dict[str, Any]) -> str:
    salience = _bounded_float(row.get("salience"), default=0.0)
    band = _pressure_band(row)
    result = _safe_str(row.get("result"))
    if salience >= 0.78 or band == "high" or result not in {"", "success"}:
        return "high"
    if salience >= 0.6 or band == "medium":
        return "medium"
    return "low"


def _next_reflection_item_id(text: str, produced_at: str) -> str:
    date_part = _date_part(produced_at)
    pattern = re.compile(rf"(?m)^## item-{re.escape(date_part)}-(\d{{3}})$")
    numbers = [int(match.group(1)) for match in pattern.finditer(text)]
    return f"item-{date_part}-{max(numbers, default=0) + 1:03d}"


def _append_dream_seed(root: Path, row: dict[str, Any], produced_at: str) -> tuple[str, bool]:
    path = root / DREAM_SEEDS_REL
    text = _read_text(path)
    if not text.strip():
        text = "# Dream Seeds\n"

    exp_id = _safe_str(row.get("experience_id"), "unknown")
    seed_id = _seed_id(row, produced_at)
    if seed_id in text or f"action_experience / {exp_id}" in text:
        return seed_id, False

    body = f"""## {seed_id}
- source_event: action_experience / {exp_id}
- theme: {_theme(row)}
- residue: {_residue(row)}
- emotional_weight: {_emotional_weight(row)}
- factual_status: bounded local action residue; stdout and stderr are not stored here
- dream_permission: can_recombine_but_not_rewrite_fact
- consumed_at: none
- dream_count: 0
- last_dreamed_at: none
- decay_after_dream: soft_decay_after_reflection
- action_result: {_safe_str(row.get("result"), "unknown") or "unknown"}
- action_pressure: {_pressure_band(row)}
- target_alias: {_safe_str(row.get("target_alias"), "none") or "none"}
- boundary: experience material only; does not grant future disk access or rewrite facts
"""
    _write_text(path, text.rstrip() + "\n\n" + body.rstrip())
    return seed_id, True


def _append_reflection_queue_item(
    root: Path,
    row: dict[str, Any],
    *,
    seed_id: str,
    produced_at: str,
) -> tuple[str, bool]:
    priority = _reflection_priority(row)
    if priority == "low":
        return "", False

    path = root / REFLECTION_QUEUE_REL
    text = _read_text(path)
    if not text.strip():
        text = "# Reflection Queue\n"

    exp_id = _safe_str(row.get("experience_id"), "unknown")
    source_line = f"action_experience_residue / {exp_id}"
    if source_line in text:
        existing = re.search(r"(?m)^## (item-\d{4}-\d{2}-\d{2}-\d{3})\n(?:(?!^## ).)*" + re.escape(source_line), text, re.S)
        return existing.group(1) if existing else "", False

    item_id = _next_reflection_item_id(text, produced_at)
    body = f"""## {item_id}
- topic: 行动残留来自 {_theme(row)}
- source: {source_line}
- priority: {priority}
- suggested_writer: reflection_writer
- action_source_seed: {seed_id}
- waking_residue: {_residue(row)}
- boundary: use as reflection material only; do not invent facts, permissions, or owner intent
"""
    _write_text(path, text.rstrip() + "\n\n" + body.rstrip())
    return item_id, True


def _trace_digest(root: Path, row: dict[str, Any], result: dict[str, Any]) -> None:
    trace = {
        "created_at": result.get("produced_at"),
        "experience_id": row.get("experience_id"),
        "seed_id": result.get("seed_id"),
        "reflection_item_id": result.get("reflection_item_id"),
        "dream_seed_written": result.get("dream_seed_written"),
        "reflection_item_written": result.get("reflection_item_written"),
        "salience": row.get("salience"),
        "pressure": _pressure_band(row),
        "result": row.get("result"),
    }
    _append_jsonl(root / DIGEST_TRACE_REL, trace)


def digest_action_experience_residue(
    root: Path,
    *,
    produced_at: str | None = None,
    max_items: int = 4,
    salience_threshold: float = 0.6,
) -> dict[str, Any]:
    produced_at = produced_at or datetime.now().astimezone().isoformat(timespec="seconds")
    state_path = root / DIGEST_STATE_REL
    state = _load_state(state_path)
    digested_ids = [_safe_str(item) for item in state.get("digested_ids", []) if _safe_str(item)]
    digested_set = set(digested_ids)

    rows = _load_jsonl(root / ACTION_RESIDUE_REL)
    candidates: list[dict[str, Any]] = []
    for row in rows:
        exp_id = _safe_str(row.get("experience_id"))
        if not exp_id or exp_id in digested_set:
            continue
        if _bounded_float(row.get("salience"), default=0.0) < salience_threshold:
            continue
        candidates.append(row)
        if len(candidates) >= max(1, max_items):
            break

    if not candidates:
        return {
            "digested_count": 0,
            "dream_seed_ids": [],
            "reflection_item_ids": [],
            "notes": ["action_experience_digest_no_candidate"],
        }

    dream_seed_ids: list[str] = []
    reflection_item_ids: list[str] = []
    per_item: list[dict[str, Any]] = []
    notes: list[str] = []

    for row in candidates:
        exp_id = _safe_str(row.get("experience_id"))
        seed_id, seed_written = _append_dream_seed(root, row, produced_at)
        item_id, item_written = _append_reflection_queue_item(root, row, seed_id=seed_id, produced_at=produced_at)
        if seed_id:
            dream_seed_ids.append(seed_id)
        if item_id:
            reflection_item_ids.append(item_id)
        digested_set.add(exp_id)
        per_result = {
            "produced_at": produced_at,
            "experience_id": exp_id,
            "seed_id": seed_id,
            "reflection_item_id": item_id,
            "dream_seed_written": seed_written,
            "reflection_item_written": item_written,
        }
        per_item.append(per_result)
        _trace_digest(root, row, per_result)
        notes.append("action_experience_dream_seed_written" if seed_written else "action_experience_dream_seed_existing")
        if item_written:
            notes.append("action_experience_reflection_item_written")

    new_ids = [exp_id for exp_id in digested_ids if exp_id in digested_set]
    for row in candidates:
        exp_id = _safe_str(row.get("experience_id"))
        if exp_id and exp_id not in new_ids:
            new_ids.append(exp_id)
    state.update(
        {
            "version": 1,
            "updated_at": produced_at,
            "digested_ids": new_ids[-512:],
            "last_digest": {
                "produced_at": produced_at,
                "digested_count": len(candidates),
                "dream_seed_ids": dream_seed_ids,
                "reflection_item_ids": reflection_item_ids,
            },
        }
    )
    _write_state(state_path, state)

    return {
        "produced_at": produced_at,
        "digested_count": len(candidates),
        "dream_seed_ids": dream_seed_ids,
        "reflection_item_ids": reflection_item_ids,
        "items": per_item,
        "notes": notes[:8] or ["action_experience_digest_done"],
    }


def read_recent_action_digest_snapshot(root: Path, *, limit: int = 5) -> dict[str, Any]:
    state = _load_state(root / DIGEST_STATE_REL)
    trace_rows = _load_jsonl(root / DIGEST_TRACE_REL)
    recent: list[dict[str, Any]] = []
    for row in trace_rows[-max(1, limit):]:
        enriched = dict(row)
        detail = _seed_digest_detail(root, _safe_str(row.get("seed_id")))
        if detail:
            enriched["seed_detail"] = detail
        recent.append(enriched)
    return {
        "version": 1,
        "updated_at": _safe_str(state.get("updated_at")),
        "digested_count": len(state.get("digested_ids", []) if isinstance(state.get("digested_ids"), list) else []),
        "last_digest": state.get("last_digest") if isinstance(state.get("last_digest"), dict) else {},
        "recent": recent,
        "notes": ["action_experience_digest_snapshot_v1"],
    }


def _seed_digest_detail(root: Path, seed_id: str) -> dict[str, str]:
    block = _markdown_block(_read_text(root / DREAM_SEEDS_REL), seed_id)
    if not block:
        return {}
    return {
        "theme": _field_from_block(block, "theme"),
        "residue": _field_from_block(block, "residue"),
        "source_event": _field_from_block(block, "source_event"),
        "consumed_at": _field_from_block(block, "consumed_at"),
        "dream_permission": _field_from_block(block, "dream_permission"),
    }


def read_recent_action_digest_context(root: Path, *, limit: int = 3) -> str:
    snapshot = read_recent_action_digest_snapshot(root, limit=limit)
    rows = [row for row in snapshot.get("recent", []) if isinstance(row, dict)]
    if not rows:
        return ""
    lines = [
        "recent action digestion sidecar:",
        (
            "These are local action experiences that have already been converted into "
            "dream/reflection material. If the owner asks whether a recent action entered "
            "dream/reflection, or what residue it left, answer from this sidecar. A dream "
            "seed means material is available for dreams; it does not prove a dream output "
            "has already run unless the seed is marked consumed."
        ),
    ]
    for row in reversed(rows[-max(1, limit):]):
        seed_id = _safe_str(row.get("seed_id"))
        detail = _seed_digest_detail(root, seed_id)
        item_id = _safe_str(row.get("reflection_item_id")) or "none"
        result = visible_action_result_label(row.get("result"))
        pressure = visible_action_pressure_label(row.get("pressure"))
        residue = _compact(detail.get("residue"), limit=180)
        consumed = _safe_str(detail.get("consumed_at"), "none") or "none"
        lines.append(
            (
                f"- experience={_safe_str(row.get('experience_id'), 'unknown')} 结果={result} "
                f"负载={pressure} seed={seed_id or 'none'} consumed_at={consumed} "
                f"reflection_item={item_id}; residue={residue}"
            )
        )
    return "\n".join(lines)


def _action_digest_followup_mode(text: str) -> str:
    compact = re.sub(r"\s+", "", _safe_str(text)).lower()
    if not compact:
        return ""
    asks_dream_reflection = any(
        marker in compact
        for marker in (
            "进梦",
            "梦里",
            "梦境",
            "反思",
            "消化",
            "沉淀",
            "残留",
            "经历",
            "经验",
            "留下什么",
            "留下了什么",
            "有留下",
        )
    )
    recent_markers = ("刚才", "刚刚", "这次", "那次", "上次", "刚扫", "刚跑", "刚做")
    if asks_dream_reflection and any(marker in compact for marker in recent_markers):
        if any(marker in compact for marker in ("留下", "残留", "经历", "经验", "沉淀")):
            return "residue"
        return "route"
    if "有没有" in compact and asks_dream_reflection:
        return "route"
    return ""


def compose_action_digest_followup(
    root: Path,
    text: str,
    *,
    max_age_seconds: int = 24 * 3600,
) -> dict[str, Any] | None:
    mode = _action_digest_followup_mode(text)
    if not mode:
        return None
    rows = _load_jsonl(root / DIGEST_TRACE_REL)
    if not rows:
        return None
    now = datetime.now().astimezone()
    fresh: list[dict[str, Any]] = []
    for row in rows:
        produced_at = _safe_str(row.get("created_at"))
        try:
            created = datetime.fromisoformat(produced_at)
        except ValueError:
            continue
        if created.tzinfo is None:
            created = created.astimezone()
        age = (now - created).total_seconds()
        if age <= max_age_seconds:
            fresh.append(row)
    if not fresh:
        return None
    row = fresh[-1]
    seed_id = _safe_str(row.get("seed_id"))
    item_id = _safe_str(row.get("reflection_item_id")) or "none"
    detail = _seed_digest_detail(root, seed_id)
    residue = _compact(detail.get("residue"), limit=180, default="没有留下可读的残留摘要")
    consumed_at = _safe_str(detail.get("consumed_at"), "none") or "none"
    dream_state = "已经被梦境用过" if consumed_at not in {"", "none", "unknown"} else "还只是梦种，等下一轮梦境输出读取"
    if mode == "residue":
        reply = f"留下的是这段：{residue}。它已经进了梦种 {seed_id}，反思队列也有 {item_id}。"
    else:
        reply = f"进了。它现在是梦种 {seed_id}，{dream_state}；反思队列是 {item_id}。"
    return {
        "reply": reply,
        "mode": mode,
        "row": row,
        "seed_detail": detail,
        "notes": ["action_digest_followup_matched", f"action_digest_followup_mode:{mode}"],
    }

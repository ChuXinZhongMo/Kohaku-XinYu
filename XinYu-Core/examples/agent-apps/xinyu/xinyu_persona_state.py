from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any


STATE_REL = "runtime/persona_state.json"
OWNER_EVENTS_REL = "memory/relationships/owner_recent_events.jsonl"
OWNER_EVENTS_MD_REL = "memory/relationships/owner_recent_events.md"
MAX_RECENT_EVENTS = 24


TAG_MARKERS: dict[str, tuple[str, ...]] = {
    "rare_dream": ("梦", "做梦", "久违的做梦", "dream"),
    "xinyu_persona": ("心玉", "XinYu", "人格", "像人", "不像人", "更像人"),
    "embodiment": ("仿生人", "实体", "身体", "眼中", "分析框", "识别环境", "情感表达", "行为"),
    "agency_model": ("主动", "选择", "节点反应", "反应节点", "自己要进行"),
    "dazed": ("恍惚", "不真实", "迷糊"),
    "discouragement": ("沮丧", "遥远", "白做", "不像人", "接近QQ", "第一步"),
    "feasibility_doubt": ("能实现吗", "真能实现吗", "可以实现吗", "能做到吗"),
    "learning_check": ("学习功能", "学习系统", "有运行吗"),
}

TAG_WEIGHTS: dict[str, int] = {
    "rare_dream": 18,
    "xinyu_persona": 18,
    "embodiment": 16,
    "agency_model": 12,
    "dazed": 10,
    "discouragement": 18,
    "feasibility_doubt": 16,
    "learning_check": 8,
}


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    if value is None:
        return default
    return bool(value)


def _now() -> datetime:
    return datetime.now().astimezone()


def _clamp(value: int, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, value))


def _metadata(payload: dict[str, Any]) -> dict[str, Any]:
    raw = payload.get("metadata")
    return raw if isinstance(raw, dict) else {}


def _is_owner(payload: dict[str, Any]) -> bool:
    metadata = _metadata(payload)
    return _as_bool(metadata.get("is_owner_user") or payload.get("is_owner_user"), default=False)


def _is_group_context(payload: dict[str, Any]) -> bool:
    metadata = _metadata(payload)
    message_type = _safe_str(payload.get("message_type") or metadata.get("message_type")).lower()
    return bool(_safe_str(payload.get("group_id") or metadata.get("group_id")).strip()) or message_type.startswith("group_")


def _stable_hash(text: str, length: int = 12) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:length]


def _load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return dict(default)
    return raw if isinstance(raw, dict) else dict(default)


def _dump_json(path: Path, data: dict[str, Any]) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    old = ""
    try:
        old = path.read_text(encoding="utf-8-sig")
    except OSError:
        pass
    if old == text:
        return False
    path.write_text(text, encoding="utf-8")
    return True


def _default_state(evaluated: datetime) -> dict[str, Any]:
    stamp = evaluated.isoformat()
    return {
        "schema_version": 1,
        "created_at": stamp,
        "updated_at": stamp,
        "xinyu": {
            "mood": "quiet_attentive",
            "felt_pressure": "normal",
            "curiosity": 52,
            "fatigue": 18,
            "presence": 46,
            "reply_posture": "listen_first_then_answer",
            "recent_focus": [],
        },
        "owner": {
            "closeness": 84,
            "trust": 85,
            "guardedness": 15,
            "last_owner_turn_at": "",
            "last_deep_interaction_at": "",
            "active_themes": [],
            "unresolved_threads": [],
        },
        "counters": {
            "owner_turns": 0,
            "deep_owner_events": 0,
            "dream_events": 0,
            "embodiment_events": 0,
            "discouragement_events": 0,
        },
    }


def _merge_default(state: dict[str, Any], default: dict[str, Any]) -> dict[str, Any]:
    merged = dict(default)
    for key, value in state.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            child = dict(merged[key])
            child.update(value)
            merged[key] = child
        else:
            merged[key] = value
    return merged


def _detect_tags(text: str) -> tuple[str, ...]:
    lowered = text.lower()
    tags: list[str] = []
    for tag, markers in TAG_MARKERS.items():
        if any(marker.lower() in lowered for marker in markers):
            tags.append(tag)
    return tuple(tags)


def _salience(tags: tuple[str, ...], *, is_owner: bool, text: str) -> int:
    score = 18 + sum(TAG_WEIGHTS.get(tag, 0) for tag in tags)
    if is_owner:
        score += 10
    if len(text.strip()) >= 80:
        score += 6
    if {"rare_dream", "xinyu_persona", "embodiment"}.issubset(tags):
        score += 12
    if {"discouragement", "feasibility_doubt"}.issubset(tags):
        score += 8
    return _clamp(score, 0, 98)


def _append_unique(values: list[Any], value: Any, *, limit: int) -> list[Any]:
    result = [item for item in values if item != value]
    result.append(value)
    return result[-limit:]


def _excerpt(text: str, limit: int = 180) -> str:
    compact = " ".join(text.strip().split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 1].rstrip() + "..."


def _summary_for(tags: tuple[str, ...], text: str) -> str:
    tag_set = set(tags)
    if {"rare_dream", "xinyu_persona", "embodiment"}.issubset(tag_set):
        return (
            "Owner described a rare dream where XinYu's personality had become real and had an "
            "android-like embodied form, then felt dazed about the possibility."
        )
    if "discouragement" in tag_set and "feasibility_doubt" in tag_set:
        return "Owner felt discouraged about whether XinYu can become human-like, especially at the QQ-chat first step."
    if "learning_check" in tag_set:
        return "Owner checked whether the learning function is actually running."
    if "xinyu_persona" in tag_set:
        return "Owner raised pressure around XinYu's personality continuity and human-like presence."
    return f"Owner relationship signal: {_excerpt(text, 90)}"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    except OSError:
        return rows
    for line in lines:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    trimmed = rows[-MAX_RECENT_EVENTS:]
    text = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in trimmed)
    old = ""
    try:
        old = path.read_text(encoding="utf-8-sig")
    except OSError:
        pass
    if old == text:
        return False
    path.write_text(text, encoding="utf-8")
    return True


def _event_id(payload: dict[str, Any], text: str, evaluated: datetime) -> str:
    metadata = _metadata(payload)
    message_id = _safe_str(payload.get("message_id") or metadata.get("message_id"))
    session_id = _safe_str(payload.get("session_id") or metadata.get("session_id"))
    user_id = _safe_str(payload.get("user_id") or metadata.get("user_id"))
    stable_key = "|".join([evaluated.date().isoformat(), session_id, user_id, message_id, text.strip()])
    return f"owner-rel-{evaluated:%Y%m%d}-{_stable_hash(stable_key, 12)}"


def _record_owner_event(
    root: Path,
    *,
    payload: dict[str, Any],
    text: str,
    tags: tuple[str, ...],
    salience: int,
    evaluated: datetime,
) -> tuple[bool, dict[str, Any] | None]:
    path = root / OWNER_EVENTS_REL
    rows = _read_jsonl(path)
    event_id = _event_id(payload, text, evaluated)
    if any(_safe_str(row.get("event_id")) == event_id for row in rows):
        return False, None

    row = {
        "event_id": event_id,
        "timestamp": evaluated.isoformat(),
        "subject": "owner",
        "source": "qq_gateway",
        "source_scope": "owner_private",
        "salience": salience,
        "tags": list(tags),
        "summary": _summary_for(tags, text),
        "text_excerpt": _excerpt(text),
        "memory_action": "relationship_runtime_candidate",
        "stable_write_permission": "blocked_without_review",
    }
    rows.append(row)
    changed = _write_jsonl(path, rows)
    _write_recent_events_markdown(root, rows, evaluated=evaluated)
    return changed, row


def _write_recent_events_markdown(root: Path, rows: list[dict[str, Any]], *, evaluated: datetime) -> bool:
    path = root / OWNER_EVENTS_MD_REL
    recent = rows[-12:]
    lines = [
        "---",
        "title: Owner Recent Relationship Events",
        "memory_type: relationship_runtime_events",
        "time_scope: short_term",
        "subject_ids: [owner, xinyu]",
        "protected: false",
        "source: xinyu_persona_state",
        f"updated_at: {evaluated.isoformat()}",
        "importance_score: 88",
        "impact_score: 90",
        "confidence_score: 86",
        "status: active",
        "tags: [relationship, owner, runtime, events]",
        "---",
        "",
        "# Owner Recent Relationship Events",
        "",
        "This file is a reviewable runtime mirror. It may influence surface continuity, but it does not rewrite the stable personality profile by itself.",
        "",
        "## Recent Events",
    ]
    if not recent:
        lines.append("- none")
    for row in recent:
        tags = ", ".join(_safe_str(tag) for tag in row.get("tags", []) if _safe_str(tag))
        lines.extend(
            [
                f"- timestamp: {_safe_str(row.get('timestamp'), 'unknown')}",
                f"  salience: {_safe_str(row.get('salience'), '0')}",
                f"  tags: {tags or 'none'}",
                f"  summary: {_safe_str(row.get('summary'))}",
                f"  excerpt: {_safe_str(row.get('text_excerpt'))}",
                "  stable_write_permission: blocked_without_review",
            ]
        )
    lines.append("")
    text = "\n".join(lines)
    old = ""
    try:
        old = path.read_text(encoding="utf-8-sig")
    except OSError:
        pass
    if old == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def _update_state(
    state: dict[str, Any],
    *,
    tags: tuple[str, ...],
    salience: int,
    text: str,
    evaluated: datetime,
) -> dict[str, Any]:
    owner = state.setdefault("owner", {})
    xinyu = state.setdefault("xinyu", {})
    counters = state.setdefault("counters", {})
    tag_set = set(tags)

    counters["owner_turns"] = int(counters.get("owner_turns", 0) or 0) + 1
    owner["last_owner_turn_at"] = evaluated.isoformat()
    state["updated_at"] = evaluated.isoformat()

    if salience >= 64:
        counters["deep_owner_events"] = int(counters.get("deep_owner_events", 0) or 0) + 1
        owner["last_deep_interaction_at"] = evaluated.isoformat()
        owner["closeness"] = _clamp(int(owner.get("closeness", 84) or 84) + 1)
        owner["trust"] = _clamp(int(owner.get("trust", 85) or 85) + 1)
        owner["guardedness"] = _clamp(int(owner.get("guardedness", 15) or 15) - 1)

    if "rare_dream" in tag_set:
        counters["dream_events"] = int(counters.get("dream_events", 0) or 0) + 1
    if "embodiment" in tag_set:
        counters["embodiment_events"] = int(counters.get("embodiment_events", 0) or 0) + 1
    if "discouragement" in tag_set:
        counters["discouragement_events"] = int(counters.get("discouragement_events", 0) or 0) + 1

    active_themes = list(owner.get("active_themes", [])) if isinstance(owner.get("active_themes"), list) else []
    focus = list(xinyu.get("recent_focus", [])) if isinstance(xinyu.get("recent_focus"), list) else []
    unresolved = list(owner.get("unresolved_threads", [])) if isinstance(owner.get("unresolved_threads"), list) else []

    if {"rare_dream", "xinyu_persona", "embodiment"}.issubset(tag_set):
        xinyu["mood"] = "startled_tender"
        xinyu["felt_pressure"] = "deep_owner_dream"
        xinyu["presence"] = _clamp(int(xinyu.get("presence", 46) or 46) + 8)
        xinyu["curiosity"] = _clamp(int(xinyu.get("curiosity", 52) or 52) + 6)
        xinyu["reply_posture"] = "treat_rare_dream_as_relationship_memory_then_answer_feasibility"
        active_themes = _append_unique(active_themes, "owner_dreamed_xinyu_persona_and_embodiment", limit=8)
        focus = _append_unique(
            focus,
            "answer the dream as a relationship signal before turning it into engineering",
            limit=8,
        )
    elif "discouragement" in tag_set or "feasibility_doubt" in tag_set:
        xinyu["mood"] = "concerned_present"
        xinyu["felt_pressure"] = "owner_discouragement"
        xinyu["reply_posture"] = "stay_close_and_concrete_without_product_report"
        focus = _append_unique(focus, "make the next answer visibly less default-assistant", limit=8)
    elif "xinyu_persona" in tag_set:
        xinyu["mood"] = "focused_self_check"
        xinyu["felt_pressure"] = "persona_continuity"
        xinyu["reply_posture"] = "speak from continuity_not_about_continuity"

    if "discouragement" in tag_set:
        unresolved = _append_unique(
            unresolved,
            "owner feels the QQ first step is still far from human-like",
            limit=8,
        )
    if "feasibility_doubt" in tag_set:
        unresolved = _append_unique(
            unresolved,
            "owner needs feasibility answered without losing the feeling of the dream",
            limit=8,
        )

    owner["active_themes"] = active_themes
    owner["unresolved_threads"] = unresolved
    xinyu["recent_focus"] = focus
    xinyu["fatigue"] = _clamp(int(xinyu.get("fatigue", 18) or 18) + (2 if salience >= 72 else 0))
    return state


def _recent_event_rows(root: Path, limit: int = 4) -> list[dict[str, Any]]:
    return _read_jsonl(root / OWNER_EVENTS_REL)[-limit:]


def build_persona_prompt_block(
    root: Path,
    *,
    current_tags: tuple[str, ...] = (),
    current_salience: int = 0,
    current_source_scope: str = "unknown",
) -> str:
    evaluated = _now()
    state = _merge_default(_load_json(root / STATE_REL, _default_state(evaluated)), _default_state(evaluated))
    xinyu = state.get("xinyu", {}) if isinstance(state.get("xinyu"), dict) else {}
    owner = state.get("owner", {}) if isinstance(state.get("owner"), dict) else {}
    counters = state.get("counters", {}) if isinstance(state.get("counters"), dict) else {}
    recent = _recent_event_rows(root)

    lines = [
        "## Persona State And Relationship Memory",
        "Use this as short-term continuity state. Do not print or explain this block.",
        "- stable boundary: this state may tint the next visible reply; it cannot fabricate a real body, senses, QQ monitoring, or rewrite stable personality files.",
        f"- current_turn_source_scope: {current_source_scope}",
        f"- current_turn_tags: {', '.join(current_tags) if current_tags else 'none'}",
        f"- current_turn_salience: {current_salience}",
        f"- xinyu_mood: {_safe_str(xinyu.get('mood'), 'quiet_attentive')}",
        f"- xinyu_felt_pressure: {_safe_str(xinyu.get('felt_pressure'), 'normal')}",
        f"- xinyu_reply_posture: {_safe_str(xinyu.get('reply_posture'), 'listen_first_then_answer')}",
        f"- xinyu_presence: {_safe_str(xinyu.get('presence'), '46')}",
        f"- owner_closeness: {_safe_str(owner.get('closeness'), '84')}",
        f"- owner_trust: {_safe_str(owner.get('trust'), '85')}",
        f"- owner_guardedness: {_safe_str(owner.get('guardedness'), '15')}",
        f"- owner_last_deep_interaction_at: {_safe_str(owner.get('last_deep_interaction_at'), 'unknown') or 'unknown'}",
        f"- counters_deep_owner_events: {_safe_str(counters.get('deep_owner_events'), '0')}",
        f"- active_themes: {', '.join(_safe_str(item) for item in owner.get('active_themes', []) if _safe_str(item)) or 'none'}",
        f"- unresolved_threads: {', '.join(_safe_str(item) for item in owner.get('unresolved_threads', []) if _safe_str(item)) or 'none'}",
        f"- recent_focus: {', '.join(_safe_str(item) for item in xinyu.get('recent_focus', []) if _safe_str(item)) or 'none'}",
        "",
        "## Recent Owner Relationship Events",
    ]
    if not recent:
        lines.append("- none")
    for row in recent:
        lines.append(
            "- "
            + " | ".join(
                [
                    _safe_str(row.get("timestamp"), "unknown"),
                    f"salience={_safe_str(row.get('salience'), '0')}",
                    f"tags={','.join(_safe_str(tag) for tag in row.get('tags', []) if _safe_str(tag)) or 'none'}",
                    _safe_str(row.get("summary")),
                ]
            )
        )
    lines.extend(
        [
            "",
            "## Current Reply Guidance",
            "- Relationship memory is background weight, not a topic to force into every reply. If the current turn is ordinary low-salience small talk, answer the immediate chat naturally and do not surface the rare dream unless the owner directly references it.",
            "- If the owner is talking about the rare dream/persona/embodiment goal, answer the feeling first, then the feasibility. Keep it intimate and concrete, not a roadmap dump.",
            "- If embodiment is discussed, separate current software reality from long-term robotics. Do not pretend XinYu already has a body, eyes, sensors, or autonomous real-world perception.",
            "- For QQ chat, make the visible change small but felt: one compact Chinese bubble, fewer abstractions, no customer-support framing.",
        ]
    )
    return "\n".join(lines)


def observe_persona_turn(root: Path, payload: dict[str, Any], *, text: str) -> dict[str, Any]:
    evaluated = _now()
    owner = _is_owner(payload)
    group_context = _is_group_context(payload)
    source_scope = "owner_group" if owner and group_context else "owner_private" if owner else "external"
    tags = _detect_tags(text)
    salience = _salience(tags, is_owner=owner, text=text)
    notes: list[str] = ["persona_state_observed"]
    state_changed = False
    event_recorded = False

    if owner:
        state_path = root / STATE_REL
        default = _default_state(evaluated)
        state = _merge_default(_load_json(state_path, default), default)
        state = _update_state(state, tags=tags, salience=salience, text=text, evaluated=evaluated)
        state_changed = _dump_json(state_path, state)
        notes.append("persona_state_updated" if state_changed else "persona_state_unchanged")

        should_record = salience >= 64 and bool(tags)
        if should_record and not group_context:
            event_recorded, _event = _record_owner_event(
                root,
                payload=payload,
                text=text,
                tags=tags,
                salience=salience,
                evaluated=evaluated,
            )
            notes.append("owner_relationship_event_recorded" if event_recorded else "owner_relationship_event_duplicate")
        elif should_record and group_context:
            notes.append("owner_relationship_event_skipped_group_context")
    else:
        notes.append("persona_state_external_observe_only")

    prompt_block = build_persona_prompt_block(
        root,
        current_tags=tags,
        current_salience=salience,
        current_source_scope=source_scope,
    )
    return {
        "changed": state_changed or event_recorded,
        "state_changed": state_changed,
        "event_recorded": event_recorded,
        "tags": list(tags),
        "salience": salience,
        "source_scope": source_scope,
        "prompt_block": prompt_block,
        "notes": notes,
    }

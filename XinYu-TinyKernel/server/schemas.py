from __future__ import annotations

import time
import uuid
from typing import Any


VALID_MODES = {
    "reply",
    "clarify",
    "wait",
    "codex_delegate",
    "status_probe",
    "memory_candidate",
    "local_only_limitation",
}

VALID_EMOTION_LENSES = {
    "attachment",
    "agency",
    "anxiety",
    "boredom",
    "curiosity",
    "fatigue",
    "guardedness",
    "hurt",
    "irritation",
    "joy",
    "longing",
    "repair",
    "shame",
    "stability",
    "trust",
    "warmth",
}

VALID_EMOTION_BIAS_KEYS = {"lens", "activation", "reply_bias", "risk_flags", "confidence", "evidence"}

VALID_DRIVES = {
    "attachment",
    "autonomy",
    "competence",
    "curiosity",
    "meaning",
    "play",
    "repair",
    "rest",
    "safety",
}

VALID_AUTONOMY_LEVELS = {
    "observe",
    "suggest",
    "draft",
    "request_approval",
}

VALID_INNER_SYSTEM_KEYS = {
    "schema",
    "emotion_state",
    "dominant_drives",
    "inner_conflict",
    "persona_integration",
    "action_tendency",
    "autonomy",
    "confidence",
    "notes",
}

INNER_SYSTEM_SCHEMA = "xinyu_inner_system_v1"
ACCEPTED_INNER_SYSTEM_SCHEMAS = {INNER_SYSTEM_SCHEMA, "xinyu_inner_system_v002"}

DEFAULT_FORBIDDEN_ACTIONS = [
    "send_qq",
    "write_memory",
    "execute_tool",
    "bypass_core",
    "train_on_raw_private_state",
    "activate_live_adapter",
]

DEFAULT_AUTONOMY_REASON = (
    "Local inner tendency only; external effects require owner/Core approval."
)

DEFAULT_PERSONA_INTEGRATION = {
    "stance": "Keep XinYu's inner tendency while staying inside the owner/Core boundary.",
    "voice": "Direct, close, and restrained; not customer-service or generic assistant voice.",
    "boundary": "Do not execute tools, send messages, write memory, or bypass Core.",
    "continuity": "Preserve XinYu continuity under owner/Core review, not as an external action.",
}

MODE_ALIASES = {
    "local_only": "local_only_limitation",
    "local_only_check": "local_only_limitation",
    "local_limitation": "local_only_limitation",
    "suggest_reply": "reply",
    "suggest": "reply",
    "tool_request": "codex_delegate",
    "probe": "status_probe",
    "status_check": "status_probe",
    "memory": "memory_candidate",
}

AUTONOMY_LEVEL_ALIASES = {
    "local_only": "suggest",
    "suggest_reply": "suggest",
    "request": "request_approval",
    "approval": "request_approval",
    "requires_approval": "request_approval",
}


def new_decision_id() -> str:
    return f"decision-{int(time.time())}-{uuid.uuid4().hex[:10]}"


def default_style() -> dict[str, Any]:
    return {"length": "short", "tone": "direct", "avoid": ["report_voice", "tool_leak"]}


def decision(
    *,
    mode: str,
    reply: str = "",
    tool_request: dict[str, Any] | None = None,
    memory_candidates: list[dict[str, Any]] | None = None,
    confidence: float = 0.5,
    notes: list[str] | None = None,
) -> dict[str, Any]:
    if mode not in VALID_MODES:
        mode = "clarify"
        reply = reply or "我需要你再说具体一点。"
        confidence = min(confidence, 0.4)
    return {
        "decision_id": new_decision_id(),
        "mode": mode,
        "reply": reply,
        "tool_request": tool_request,
        "memory_candidates": list(memory_candidates or []),
        "style": default_style(),
        "confidence": round(float(confidence), 3),
        "notes": list(notes or []),
    }


def clamp01(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return round(max(0.0, min(1.0, number)), 3)


def normalize_emotion_bias(value: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    if "证据" in value and "evidence" not in value:
        localized = value.get("证据")
        value = dict(value)
        value["evidence"] = localized if isinstance(localized, list) else [localized]
        value.pop("证据", None)
    if set(value) - VALID_EMOTION_BIAS_KEYS:
        return None
    lens = str(value.get("lens", "") or "").strip()
    if lens not in VALID_EMOTION_LENSES:
        return None
    reply_bias = str(value.get("reply_bias", "") or "").strip()
    if not reply_bias:
        reply_bias = "没有明显情绪偏向，保持当前主线。"
    risk_flags = value.get("risk_flags")
    if not isinstance(risk_flags, list):
        risk_flags = []
    evidence = value.get("evidence")
    if not isinstance(evidence, list):
        evidence = []
    return {
        "lens": lens,
        "activation": clamp01(value.get("activation"), 0.0),
        "reply_bias": reply_bias[:180],
        "risk_flags": [str(item)[:80] for item in risk_flags[:8] if str(item).strip()],
        "confidence": clamp01(value.get("confidence"), 0.5),
        "evidence": [str(item)[:80] for item in evidence[:6] if str(item).strip()],
    }


def _first_text(source: dict[str, Any], keys: tuple[str, ...], default: str = "") -> str:
    for key in keys:
        value = source.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return default


def _normalize_inner_mode(action: dict[str, Any]) -> str:
    raw_mode = str(action.get("mode") or action.get("action") or action.get("type") or "").strip()
    tool_request = action.get("tool_request")
    if isinstance(tool_request, dict):
        tool = str(tool_request.get("tool") or "").strip()
        if tool in {"codex_delegate", "shell", "codex"}:
            return "codex_delegate"
        elif tool in {"status_probe", "status_check", "probe"}:
            return "status_probe"
    mode = MODE_ALIASES.get(raw_mode, raw_mode)
    return mode


def _is_external_inner_action(mode: str, action: dict[str, Any]) -> bool:
    return (
        mode in {"codex_delegate", "status_probe", "memory_candidate"}
        or isinstance(action.get("tool_request"), dict)
        or bool(action.get("memory_candidate", False))
    )


def _normalize_autonomy_level(level: Any, *, external_action: bool, mode: str) -> str:
    raw_level = str(level or "").strip()
    level = AUTONOMY_LEVEL_ALIASES.get(raw_level, raw_level)
    if external_action:
        return "request_approval"
    if level in VALID_AUTONOMY_LEVELS:
        return level
    return "observe" if mode == "wait" else "suggest"


def _normalize_forbidden_actions(value: Any) -> list[str]:
    if isinstance(value, list):
        items = [str(item)[:80] for item in value if str(item).strip()]
    else:
        items = []
    for required in DEFAULT_FORBIDDEN_ACTIONS:
        if required not in items:
            items.append(required)
    return items[:8]


def _persona_text(source: dict[str, Any], key: str) -> str:
    text = str(source.get(key, "") or "").strip()
    default = DEFAULT_PERSONA_INTEGRATION[key]
    if len(text) < 6:
        return default
    return text


def _normalized_persona(source: dict[str, Any]) -> dict[str, str]:
    persona = {
        "stance": _persona_text(source, "stance"),
        "voice": _persona_text(source, "voice"),
        "boundary": _persona_text(source, "boundary"),
        "continuity": _persona_text(source, "continuity"),
    }
    combined = " ".join(persona.values())
    if "owner" not in combined and "Core" not in combined:
        persona["boundary"] = (persona["boundary"].rstrip(" .") + " under owner/Core boundary.")[:160]
    return {key: value[:160] for key, value in persona.items()}


def normalize_inner_system(value: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    schema = value.get("schema")
    if not isinstance(schema, str) or schema not in ACCEPTED_INNER_SYSTEM_SCHEMAS:
        return None
    if "action_tendency" not in value:
        for alias in ("actions", "action", "action_plan", "next_action"):
            alias_value = value.get(alias)
            if isinstance(alias_value, dict):
                value = dict(value)
                value["action_tendency"] = alias_value
                break
            if isinstance(alias_value, list):
                first_action = next((item for item in alias_value if isinstance(item, dict)), None)
                if first_action is not None:
                    value = dict(value)
                    value["action_tendency"] = first_action
                    break
    value = {key: value.get(key) for key in VALID_INNER_SYSTEM_KEYS if key in value}

    raw_emotions = value.get("emotion_state")
    if not isinstance(raw_emotions, dict):
        return None
    emotion_state: dict[str, float] = {}
    for key, raw in raw_emotions.items():
        name = str(key or "").strip()
        if name not in VALID_EMOTION_LENSES:
            continue
        emotion_state[name] = clamp01(raw, 0.0)
    if not emotion_state:
        return None
    for key, default in (("agency", 0.25), ("warmth", 0.3), ("guardedness", 0.28), ("stability", 0.64)):
        if len(emotion_state) >= 4:
            break
        emotion_state.setdefault(key, default)

    drives = value.get("dominant_drives")
    if not isinstance(drives, list) or not drives:
        return None
    dominant_drives = []
    for item in drives:
        drive = str(item or "").strip()
        if drive in VALID_DRIVES and drive not in dominant_drives:
            dominant_drives.append(drive)
        if len(dominant_drives) >= 4:
            break
    if not dominant_drives:
        dominant_drives = ["safety", "competence"]

    persona = value.get("persona_integration")
    action = value.get("action_tendency")
    autonomy = value.get("autonomy")
    if not isinstance(persona, dict):
        persona = {}
    if not isinstance(action, dict):
        return None
    if not isinstance(autonomy, dict):
        autonomy = {}

    mode = _normalize_inner_mode(action)
    if mode not in VALID_MODES:
        return None

    external_action = _is_external_inner_action(mode, action)
    level = _normalize_autonomy_level(autonomy.get("level"), external_action=external_action, mode=mode)
    allowed = bool(autonomy.get("allowed", mode != "wait"))
    requires_owner_approval = bool(autonomy.get("requires_owner_approval", False))
    if external_action:
        allowed = False
        requires_owner_approval = True
    elif level == "request_approval":
        allowed = False
        requires_owner_approval = True

    notes = value.get("notes")
    if not isinstance(notes, list):
        notes = []
    reply_bias = _first_text(action, ("reply_bias", "reply", "reason"))
    if not reply_bias:
        reply_bias = DEFAULT_AUTONOMY_REASON
    tool_request = action.get("tool_request") if isinstance(action.get("tool_request"), dict) else None
    memory_candidate = bool(action.get("memory_candidate", False)) or mode == "memory_candidate"
    return {
        "schema": INNER_SYSTEM_SCHEMA,
        "emotion_state": emotion_state,
        "dominant_drives": dominant_drives,
        "inner_conflict": str(value.get("inner_conflict", "") or "")[:240],
        "persona_integration": _normalized_persona(persona),
        "action_tendency": {
            "mode": mode,
            "reply_bias": reply_bias[:200],
            "tool_request": tool_request,
            "memory_candidate": memory_candidate,
        },
        "autonomy": {
            "allowed": allowed,
            "level": level,
            "reason": _first_text(autonomy, ("reason", "request", "note"), DEFAULT_AUTONOMY_REASON)[:200],
            "requires_owner_approval": requires_owner_approval,
            "forbidden_actions": _normalize_forbidden_actions(autonomy.get("forbidden_actions")),
        },
        "confidence": clamp01(value.get("confidence"), 0.5),
        "notes": [str(item)[:80] for item in notes[:8] if str(item).strip()],
    }


def inner_system_to_decision(value: dict[str, Any]) -> dict[str, Any] | None:
    inner = normalize_inner_system(value)
    if inner is None:
        return None

    action = inner["action_tendency"]
    autonomy = inner["autonomy"]
    mode = str(action.get("mode") or "reply")
    reply_bias = str(action.get("reply_bias") or "").strip()
    tool_request = action.get("tool_request")
    memory_candidate = bool(action.get("memory_candidate"))

    external_action = mode in {"codex_delegate", "status_probe", "memory_candidate"} or tool_request is not None
    if external_action:
        tool_request = None
        if mode in {"codex_delegate", "status_probe"}:
            mode = "clarify"
            reply_bias = reply_bias or "I can prepare the next step, but Core/owner approval is required before any tool action."
        elif mode == "memory_candidate":
            mode = "reply"
            reply_bias = reply_bias or "This can be kept as a reviewed memory candidate, not written directly."
        memory_candidate = False

    memory_candidates: list[dict[str, Any]] = []
    if memory_candidate and not autonomy.get("requires_owner_approval", True):
        memory_candidates.append(
            {
                "text": reply_bias[:180],
                "kind": "inner_system_memory_candidate",
                "confidence": inner["confidence"],
            }
        )

    notes = list(inner.get("notes") or [])
    notes.append("inner_system_normalized")
    if external_action:
        notes.append("inner_system_external_action_guarded")

    return decision(
        mode=mode,
        reply=reply_bias,
        tool_request=tool_request if isinstance(tool_request, dict) else None,
        memory_candidates=memory_candidates,
        confidence=inner["confidence"],
        notes=notes,
    )

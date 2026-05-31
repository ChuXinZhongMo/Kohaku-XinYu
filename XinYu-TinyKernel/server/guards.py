from __future__ import annotations

from typing import Any, Callable

from kernel import (
    API_DOWN_MARKERS,
    CODEX_MARKERS,
    CODEX_TASK_MARKERS,
    MEMORY_MARKERS,
    NEGATIVE_MARKERS,
    STATUS_MARKERS,
    WAIT_MARKERS,
    _compact,
    _has_any,
    decide,
)
from schemas import INNER_SYSTEM_SCHEMA, VALID_MODES, inner_system_to_decision


DecisionFn = Callable[[dict[str, Any]], dict[str, Any]]


def guard_decide(payload: dict[str, Any]) -> dict[str, Any] | None:
    text = str(payload.get("user_text", "") or "").strip()
    if not text:
        return decide(payload)

    compact = _compact(text)
    caps = payload.get("capabilities") if isinstance(payload.get("capabilities"), dict) else {}
    negative = _has_any(text, NEGATIVE_MARKERS)
    mentions_api = "api" in compact
    question = "?" in text or "？" in text

    if _has_any(text, WAIT_MARKERS):
        return decide(payload)

    if _has_any(text, API_DOWN_MARKERS) or (mentions_api and caps.get("external_api_available") is False):
        return decide(payload)

    if negative and ("codex" in compact or _has_any(text, STATUS_MARKERS + CODEX_TASK_MARKERS)):
        return decide(payload)

    if _has_any(text, CODEX_MARKERS) and _has_any(text, CODEX_TASK_MARKERS):
        return decide(payload)

    if _has_any(text, STATUS_MARKERS) and any(marker in text for marker in ("看", "查", "检查", "怎么样", "如何")):
        return decide(payload)

    if _has_any(text, MEMORY_MARKERS) and not question and len(text) >= 8:
        return decide(payload)

    if question:
        return decide(payload)

    return None


def valid_model_decision(value: dict[str, Any]) -> bool:
    if value.get("schema") == INNER_SYSTEM_SCHEMA:
        return inner_system_to_decision(value) is not None
    if value.get("mode") not in VALID_MODES:
        return False
    if "reply" not in value or "tool_request" not in value or "memory_candidates" not in value or "confidence" not in value:
        return False
    if not isinstance(value.get("memory_candidates"), list):
        return False
    return True


def guarded_decide(payload: dict[str, Any], model_decide: DecisionFn | None = None) -> dict[str, Any]:
    guarded = guard_decide(payload)
    if guarded is not None:
        guarded.setdefault("notes", []).append("guarded_hybrid")
        return guarded

    if model_decide is None:
        output = decide(payload)
        output.setdefault("notes", []).append("guarded_hybrid_rule_fallback")
        return output

    try:
        output = model_decide(payload)
    except Exception:
        output = decide(payload)
        output.setdefault("notes", []).append("guarded_hybrid_model_error_fallback")
        return output

    if not isinstance(output, dict) or not valid_model_decision(output):
        output = decide(payload)
        output.setdefault("notes", []).append("guarded_hybrid_invalid_model_fallback")
        return output

    if output.get("schema") == INNER_SYSTEM_SCHEMA:
        converted = inner_system_to_decision(output)
        if converted is None:
            output = decide(payload)
            output.setdefault("notes", []).append("guarded_hybrid_invalid_inner_system_fallback")
            return output
        converted.setdefault("notes", []).append("guarded_hybrid_inner_system")
        return converted

    output.setdefault("notes", []).append("guarded_hybrid_model")
    return output

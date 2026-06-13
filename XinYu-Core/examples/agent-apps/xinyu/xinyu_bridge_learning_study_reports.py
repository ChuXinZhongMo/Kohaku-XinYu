from __future__ import annotations

from typing import Any, Callable

from xinyu_bridge_learning_sidecars import int_result as _int_result
from xinyu_bridge_values import safe_str as _safe_str


def learning_study_mode(
    payload: dict[str, Any],
    *,
    safe_str: Callable[[Any, str], str] = _safe_str,
) -> str:
    return safe_str(payload.get("mode"), "bridge_learning_study").strip() or "bridge_learning_study"


def _dict_result(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def build_learning_study_response(
    result: dict[str, Any],
    cleanup: dict[str, Any],
    *,
    before_memory: Any,
    after_memory: Any,
    sessions: int,
    safe_str: Callable[[Any, str], str] = _safe_str,
    int_result: Callable[[dict[str, object], str], int] = _int_result,
) -> dict[str, Any]:
    learner_map = _dict_result(result.get("learner_integration", {}))
    quality_map = _dict_result(result.get("learning_quality", {}))
    gate_map = _dict_result(result.get("source_integration_gate", {}))

    integrated = int_result(learner_map, "newly_integrated_materials")
    ready = int_result(learner_map, "ready_materials")
    blocked_unreadable = int_result(learner_map, "blocked_unreadable_materials")
    held_unreadable = int_result(learner_map, "held_unreadable_materials")
    pending = int_result(learner_map, "pending_ready_materials")
    already = int_result(learner_map, "already_integrated_ready_materials")
    quality_grade = safe_str(quality_map.get("quality_grade"), "unknown")
    warning_count = int_result(quality_map, "warning_count")
    gate_reason = safe_str(gate_map.get("gate_reason"), "unknown")

    if integrated > 0:
        reply = f"learning integrated {integrated} material(s); quality={quality_grade}; warnings={warning_count}."
    elif blocked_unreadable > 0:
        reply = f"learning checked; {blocked_unreadable} material(s) were blocked as unreadable."
    elif held_unreadable > 0:
        reply = f"learning checked; {held_unreadable} unreadable material(s) were held."
    elif ready > 0 and already >= ready and pending == 0:
        reply = "learning checked; ready materials were already integrated."
    else:
        reply = f"learning checked; no new ready material. gate={gate_reason}"

    notes = ["learning_study", "no_agent_turn", "session_not_created"]
    if cleanup["cleaned_sessions"]:
        notes.append(f"cleaned_idle_sessions:{cleanup['cleaned_sessions']}")

    return {
        "accepted": True,
        "reply": reply,
        "memory_changed": before_memory != after_memory,
        "library_changed": False,
        "session_created": False,
        "sessions": sessions,
        "source_integration_gate": gate_map,
        "learner_integration": learner_map,
        "learning_quality": quality_map,
        "integrated_materials": integrated,
        "ready_materials": ready,
        "blocked_unreadable_materials": blocked_unreadable,
        "held_unreadable_materials": held_unreadable,
        "quality_grade": quality_grade,
        "warning_count": warning_count,
        "notes": notes,
    }

from __future__ import annotations

from typing import Any

from xinyu_bridge_pre_model_state import InitialSemanticFastState


def exception_note(prefix: str, exc: Exception) -> str:
    return f"{prefix}:{type(exc).__name__}"


def probe_error_decision(exc: Exception) -> dict[str, Any]:
    return {"allowed": False, "notes": [exception_note("semantic_fast_probe_error", exc)]}


def initial_semantic_fast_state(
    *,
    response: dict[str, Any] | None,
    desktop_started_published: bool,
    decision: dict[str, Any],
) -> InitialSemanticFastState:
    return InitialSemanticFastState(
        response=response,
        desktop_started_published=desktop_started_published,
        decision=decision,
    )

from __future__ import annotations

from typing import Any, Callable


AUTONOMOUS_MAINTENANCE_PROMPT = (
    "Maintenance-only pass. This is a low-frequency maintenance pass from "
    "XinYu Core, not a human speaking turn. Refresh time anchor, runtime "
    "bridge state, inner cycle, desktop thoughts, continuity, slow reflection, "
    "creative writing, memory consolidation, learning gates, and archive gates only when each "
    "subsystem is due. Do not initiate visible chat. If any outward text is "
    "unavoidable, output exactly [WAITING]."
)


def create_autonomous_maintenance_event(
    runtime: Any,
    *,
    prompt: str,
    now_iso_func: Callable[[], str],
) -> Any:
    runtime._load_runtime()
    event_cls = runtime._trigger_event_cls
    if event_cls is None:
        raise RuntimeError("TriggerEvent class is unavailable")
    return event_cls(
        type="timer",
        content=prompt,
        context={
            "trigger": "scheduler",
            "source": "xinyu_core_bridge",
            "time": now_iso_func(),
            "session_id": runtime.autonomous_maintenance_session_key,
            "autonomous": True,
        },
        stackable=False,
    )

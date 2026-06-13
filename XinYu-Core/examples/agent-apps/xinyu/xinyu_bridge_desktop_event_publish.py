from __future__ import annotations

from typing import Any


async def publish_event(
    event_bus: Any,
    event_type: str,
    payload: dict[str, Any],
    *,
    source: str,
    privacy: str,
    severity: str | None,
) -> dict[str, Any]:
    if event_bus is None:
        return {}
    try:
        return await event_bus.publish(
            event_type,
            payload,
            source=source,
            privacy=privacy,
            severity=severity,
        )
    except Exception as exc:
        print(f"[xinyu_core_bridge] desktop event publish failed: {event_type}: {exc}", flush=True)
        return {}


def publish_event_threadsafe(
    event_bus: Any,
    event_type: str,
    payload: dict[str, Any],
    *,
    source: str,
    privacy: str,
    severity: str | None,
) -> None:
    if event_bus is None:
        return
    try:
        future = event_bus.publish_threadsafe(
            event_type,
            payload,
            source=source,
            privacy=privacy,
            severity=severity,
        )

        def _log_failure(done: Any) -> None:
            try:
                done.result()
            except Exception as exc:
                print(
                    f"[xinyu_core_bridge] desktop event publish failed: {event_type}: {exc}",
                    flush=True,
                )

        future.add_done_callback(_log_failure)
    except Exception as exc:
        print(f"[xinyu_core_bridge] desktop event publish scheduling failed: {event_type}: {exc}", flush=True)

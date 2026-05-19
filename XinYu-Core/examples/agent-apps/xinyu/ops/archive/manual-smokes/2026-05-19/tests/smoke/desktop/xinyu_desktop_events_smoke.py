from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import argparse
import asyncio
import threading

from xinyu_desktop_events import (
    CursorExpiredError,
    DesktopEventBus,
    event_types,
    render_replay_unavailable_event,
)


async def _smoke() -> list[str]:
    failures: list[str] = []
    loop = asyncio.get_running_loop()
    bus = DesktopEventBus(loop=loop, max_events=3, max_string_chars=40)

    subscription = await bus.subscribe(max_queue_size=2)
    first = await bus.publish(
        "service.status.changed",
        {"service": "core", "status": "starting"},
        source="core",
        privacy="internal_summary",
    )
    observed = await asyncio.wait_for(subscription.next(), timeout=2)
    if observed["id"] != first["id"]:
        failures.append("subscriber did not receive first event")

    second = await bus.publish("core.health.snapshot", {"coreReady": True})
    third = await bus.publish("proactive.candidate.ready", {"candidateId": "c1"})
    fourth = await bus.publish("chat.turn.started", {"turnId": "t1"})

    recent = await bus.recent(limit=10)
    if event_types(recent) != ["core.health.snapshot", "proactive.candidate.ready", "chat.turn.started"]:
        failures.append(f"ring buffer did not retain the expected three events: {event_types(recent)}")

    replay = await bus.replay_since(second["id"])
    if [event["id"] for event in replay] != [third["id"], fourth["id"]]:
        failures.append("replay_since did not return events after the cursor")

    empty_replay = await bus.replay_since(fourth["id"])
    if empty_replay:
        failures.append("replay after latest cursor should be empty")

    try:
        await bus.replay_since(first["id"])
        failures.append("expired cursor unexpectedly replayed")
    except CursorExpiredError as exc:
        if exc.reason != "cursor_not_in_buffer":
            failures.append(f"expired cursor reason was wrong: {exc.reason}")

    long_event = await bus.publish("log.line", {"message": "x" * 120}, severity="info")
    message = long_event["payload"]["message"]
    if "[truncated]" not in message or len(message) > 45:
        failures.append("long payload string was not bounded")

    thread_result: list[str] = []
    thread_error: list[str] = []

    def publish_from_thread() -> None:
        try:
            future = bus.publish_threadsafe(
                "service.status.changed",
                {"service": "qq_gateway", "status": "ready"},
                source="qq-gateway",
                privacy="internal_summary",
            )
            event = future.result(timeout=5)
            thread_result.append(event["id"])
        except Exception as exc:  # pragma: no cover - surfaced in smoke output
            thread_error.append(f"{type(exc).__name__}: {exc}")

    worker = threading.Thread(target=publish_from_thread, name="xinyu-desktop-events-smoke")
    worker.start()
    await asyncio.to_thread(worker.join, 5)
    if worker.is_alive():
        failures.append("threadsafe publish worker did not finish")
    if thread_error:
        failures.extend(thread_error)
    if not thread_result:
        failures.append("threadsafe publish did not return an event id")

    replay_unavailable = render_replay_unavailable_event("missing-cursor", reason="cursor_not_in_buffer")
    if replay_unavailable["type"] != "desktop.event_replay.unavailable":
        failures.append("replay unavailable event type mismatch")
    if replay_unavailable["payload"]["recommendedAction"] != "refresh_snapshot":
        failures.append("replay unavailable event did not request snapshot refresh")

    await subscription.close()
    snapshot = await bus.snapshot()
    if snapshot["subscriber_count"] != 0:
        failures.append("subscription close did not unregister the queue")
    if not snapshot["latest_event_id"]:
        failures.append("snapshot missing latest_event_id")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate XinYu desktop event bus primitives.")
    parser.parse_args()
    failures = asyncio.run(_smoke())
    if failures:
        print("XinYu desktop events smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu desktop events smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

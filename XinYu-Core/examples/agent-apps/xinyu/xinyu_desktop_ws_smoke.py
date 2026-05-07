from __future__ import annotations

import argparse
import asyncio
import json
import logging
from datetime import datetime

import websockets
from websockets.exceptions import ConnectionClosed

from xinyu_desktop_events import DesktopEventBus
from xinyu_desktop_ws import DesktopWSServer


logging.getLogger("xinyu.desktop.ws").setLevel(logging.CRITICAL)


async def _recv_json(websocket) -> dict:
    return json.loads(await asyncio.wait_for(websocket.recv(), timeout=3))


async def _expect_close(uri: str, *, code: int) -> str:
    async with websockets.connect(uri) as websocket:
        try:
            await asyncio.wait_for(websocket.recv(), timeout=3)
        except ConnectionClosed as exc:
            if exc.code != code:
                return f"expected close code {code}, got {exc.code}"
            return ""
    return f"connection did not close with code {code}"


async def _smoke() -> list[str]:
    failures: list[str] = []
    loop = asyncio.get_running_loop()
    bus = DesktopEventBus(loop=loop, max_events=3, max_string_chars=120)
    server = DesktopWSServer(bus=bus, port=0, token="secret", ping_interval=None)
    await server.start()
    try:
        base = f"ws://127.0.0.1:{server.bound_port}"
        unauthorized = await _expect_close(f"{base}/desktop/events?token=wrong", code=4003)
        if unauthorized:
            failures.append(unauthorized)
        missing = await _expect_close(f"{base}/wrong?token=secret", code=4004)
        if missing:
            failures.append(missing)

        async with websockets.connect(f"{base}/desktop/events?token=secret") as websocket:
            ready = await _recv_json(websocket)
            if ready["type"] != "desktop.event_stream.ready":
                failures.append(f"first no-cursor message was not ready: {ready}")
            if ready["payload"]["sinceAccepted"]:
                failures.append("no-cursor connection should not accept a cursor")

        first = await bus.publish("service.status.changed", {"service": "core", "status": "ready"})
        second = await bus.publish(
            "core.health.snapshot",
            {"coreReady": True, "seenAt": datetime(2026, 5, 4, 1, 2, 3)},
        )
        async with websockets.connect(f"{base}/desktop/events?token=secret&since={first['id']}") as websocket:
            ready = await _recv_json(websocket)
            if ready["payload"]["sinceAccepted"] is not True:
                failures.append("valid cursor was not accepted")
            if ready["payload"]["replayedCount"] != 1:
                failures.append(f"valid cursor replay count mismatch: {ready}")
            replayed = await _recv_json(websocket)
            if replayed["id"] != second["id"]:
                failures.append("valid cursor did not replay the missed event")
            live = await bus.publish("chat.turn.started", {"turnId": "turn-live"})
            received_live = await _recv_json(websocket)
            if received_live["id"] != live["id"]:
                failures.append("live event was not pushed after replay")

        await bus.publish("proactive.candidate.ready", {"candidateId": "c1"})
        await bus.publish("chat.turn.finished", {"turnId": "turn-live"})
        async with websockets.connect(f"{base}/desktop/events?token=secret&since={first['id']}") as websocket:
            unavailable = await _recv_json(websocket)
            if unavailable["type"] != "desktop.event_replay.unavailable":
                failures.append(f"expired cursor did not receive replay unavailable: {unavailable}")
            ready = await _recv_json(websocket)
            if ready["type"] != "desktop.event_stream.ready":
                failures.append("expired cursor stream did not send ready after unavailable")
            if ready["payload"]["sinceAccepted"]:
                failures.append("expired cursor should not be accepted")
            live = await bus.publish("log.line", {"service": "core", "message": "after refresh"})
            received_live = await _recv_json(websocket)
            if received_live["id"] != live["id"]:
                failures.append("live event was not pushed after replay unavailable")
    finally:
        await server.stop()
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate XinYu desktop WebSocket event stream.")
    parser.parse_args()
    failures = asyncio.run(_smoke())
    if failures:
        print("XinYu desktop ws smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu desktop ws smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

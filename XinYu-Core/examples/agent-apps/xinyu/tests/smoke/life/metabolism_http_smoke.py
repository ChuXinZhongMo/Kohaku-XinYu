from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import asyncio
import json
import shutil
import threading
import urllib.error
import urllib.request
from pathlib import Path

from xinyu_bridge_http import XinYuBridgeHTTPServer, XinYuBridgeRequestHandler
from xinyu_core_bridge import XinYuBridgeRuntime
from xinyu_desktop_events import DesktopEventBus
from xinyu_metabolism_contract import create_ticket, get_ticket


TOKEN = "metabolism-http-smoke-token"


def _root() -> Path:
    return ROOT / ".metabolism_http_smoke_runtime"


def _post_json(url: str, payload: dict) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {TOKEN}"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def _get_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}"}, method="GET")
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def _get_status_json(url: str) -> tuple[int, dict]:
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {TOKEN}"}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


async def _smoke() -> list[str]:
    failures: list[str] = []
    root = _root()
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    runtime = XinYuBridgeRuntime(
        xinyu_dir=root,
        turn_timeout_seconds=1,
        max_text_chars=2000,
        settle_seconds=0.0,
        outward_renderer=False,
        renderer_mode="off",
        render_timeout_seconds=1,
        session_idle_ttl_seconds=60,
        max_sessions=2,
        proactive_min_interval_seconds=60,
        autonomous_maintenance_enabled=False,
        metabolism_runner_interval_seconds=60,
    )
    runtime.desktop_event_bus = DesktopEventBus(loop=asyncio.get_running_loop())
    server = XinYuBridgeHTTPServer(
        ("127.0.0.1", 0),
        XinYuBridgeRequestHandler,
        runtime=runtime,
        loop=asyncio.get_running_loop(),
        bridge_token=TOKEN,
        max_body_bytes=1_000_000,
        request_timeout_seconds=10,
    )
    thread = threading.Thread(target=server.serve_forever, name="metabolism-http-smoke", daemon=True)
    try:
        created = create_ticket(
            root,
            entropy_state={"entropy_level": 0.78, "scar_level": 0.56, "memory_decay_risk": 0.79},
            resource_request={"requested_seconds": 600, "reason": "smoke"},
            active_desire={"desire_id": "desire:http-smoke", "chosen_action": "request_metabolism_window"},
            input_window={"suppressed_residue_count": 8, "memory_event_count": 8},
        )
        ticket = created.get("ticket") if isinstance(created.get("ticket"), dict) else {}
        ticket_id = str(ticket.get("ticket_id") or "")
        await runtime.start_background_tasks()
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"

        listed = await asyncio.to_thread(_get_json, f"{base}/life/metabolism/tickets?status=requested")
        if not listed.get("tickets"):
            failures.append(f"GET tickets did not list requested ticket: {listed}")

        approved = await asyncio.to_thread(
            _post_json,
            f"{base}/life/metabolism/tickets/{ticket_id}/approve",
            {"owner_decision_id": "http-smoke-decision", "approved_seconds": 600, "note": "今晚可以"},
        )
        if not approved.get("accepted") or approved.get("ticket", {}).get("status") != "approved":
            failures.append(f"HTTP approve failed: {approved}")

        for _attempt in range(20):
            final_ticket = get_ticket(root, ticket_id)
            if final_ticket.get("status") == "settled":
                break
            await asyncio.sleep(0.1)
        else:
            failures.append(f"HTTP approved ticket did not settle: {get_ticket(root, ticket_id)}")

        fetched = await asyncio.to_thread(_get_json, f"{base}/life/metabolism/tickets/{ticket_id}")
        if fetched.get("ticket", {}).get("ticket_id") != ticket_id:
            failures.append(f"GET ticket did not return ticket: {fetched}")
        invalid_status, invalid_payload = await asyncio.to_thread(
            _get_status_json,
            f"{base}/life/metabolism/tickets/{ticket_id}/extra",
        )
        if invalid_status != 404 or invalid_payload.get("error") != "not_found":
            failures.append(f"GET invalid ticket subroute should 404: {invalid_status} {invalid_payload}")
    finally:
        server.shutdown()
        server.server_close()
        await runtime.shutdown()
        shutil.rmtree(root, ignore_errors=True)
    return failures


def main() -> int:
    failures = asyncio.run(_smoke())
    if failures:
        print("Metabolism HTTP smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Metabolism HTTP smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import asyncio
import tempfile
from pathlib import Path

from xinyu_core_bridge import XinYuBridgeRuntime
from xinyu_metabolism_contract import get_ticket, read_ledger


def _suppressed_residue(index: int) -> dict:
    return {
        "eventId": f"suppressed-{index}",
        "kind": "suppressed_desire",
        "textPreview": "忍住了，没有发出去。旧牵挂还在。",
    }


async def _smoke() -> list[str]:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-desktop-metabolism-ticket-") as tmp:
        root = Path(tmp)
        (root / "memory").mkdir(parents=True, exist_ok=True)
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
        )
        runtime._desktop_recent_memory_events = [_suppressed_residue(index) for index in range(8)]

        first = await runtime.desktop_snapshot({})
        desires = first.get("activeDesires") if isinstance(first.get("activeDesires"), list) else []
        desire = desires[0] if desires and isinstance(desires[0], dict) else {}
        ticket_id = str(desire.get("metabolism_ticket_id") or "")
        if desire.get("chosen_action") != "request_metabolism_window":
            failures.append(f"desktop snapshot did not expose metabolism desire: {desire}")
        if not ticket_id:
            failures.append(f"metabolism desire missing ticket id: {desire}")
        ticket = get_ticket(root, ticket_id) if ticket_id else {}
        if ticket.get("status") != "requested":
            failures.append(f"metabolism ticket was not created as requested: {ticket}")
        state = first.get("xinyuState") if isinstance(first.get("xinyuState"), dict) else {}
        if state.get("metabolism_ticket_id") != ticket_id:
            failures.append(f"xinyuState missing metabolism ticket id: {state}")

        second = await runtime.desktop_snapshot({})
        second_desires = second.get("activeDesires") if isinstance(second.get("activeDesires"), list) else []
        second_desire = second_desires[0] if second_desires and isinstance(second_desires[0], dict) else {}
        if second_desire.get("metabolism_ticket_id") != ticket_id:
            failures.append(f"desktop snapshot did not reuse metabolism ticket: {second_desire}")
        requested_events = [event for event in read_ledger(root) if event.get("event") == "ticket_requested"]
        if len(requested_events) != 1:
            failures.append(f"metabolism ticket should be idempotent across snapshots: {requested_events}")

        await runtime.shutdown()
    return failures


def main() -> int:
    failures = asyncio.run(_smoke())
    if failures:
        print("XinYu desktop metabolism ticket smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu desktop metabolism ticket smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

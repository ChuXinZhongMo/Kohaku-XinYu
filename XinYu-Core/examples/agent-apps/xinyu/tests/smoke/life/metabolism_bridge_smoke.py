from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import asyncio
import shutil
from pathlib import Path

from xinyu_core_bridge import XinYuBridgeRuntime
from xinyu_desktop_events import DesktopEventBus
from xinyu_metabolism_contract import create_ticket, get_ticket


def _root() -> Path:
    return ROOT / ".metabolism_bridge_smoke_runtime"


def _entropy() -> dict:
    return {
        "entropy_level": 0.78,
        "scar_level": 0.56,
        "memory_decay_risk": 0.79,
        "entropy_band": "fracture",
    }


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
    try:
        created = create_ticket(
            root,
            entropy_state=_entropy(),
            resource_request={"requested_seconds": 600, "reason": "smoke"},
            active_desire={"desire_id": "desire:bridge-smoke", "chosen_action": "request_metabolism_window"},
            input_window={"suppressed_residue_count": 8, "memory_event_count": 8},
        )
        ticket = created.get("ticket") if isinstance(created.get("ticket"), dict) else {}
        ticket_id = str(ticket.get("ticket_id") or "")
        await runtime.start_background_tasks()
        approved = await runtime.life_metabolism_ticket_approve(
            {
                "ticket_id": ticket_id,
                "owner_decision_id": "bridge-smoke-decision",
                "approved_seconds": 600,
                "note": "今晚可以",
            }
        )
        if not approved.get("accepted") or approved.get("ticket", {}).get("status") != "approved":
            failures.append(f"bridge approve failed: {approved}")
        approve_self_choice = approved.get("selfChoiceState") if isinstance(approved.get("selfChoiceState"), dict) else {}
        if "compute_yield_received" not in approve_self_choice.get("physical_cues", []):
            failures.append(f"approve did not publish self-choice cue: {approve_self_choice}")

        for _attempt in range(20):
            settled = get_ticket(root, ticket_id)
            if settled.get("status") == "settled":
                break
            await asyncio.sleep(0.1)
        else:
            failures.append(f"runner did not settle approved ticket: {get_ticket(root, ticket_id)}")
        for _attempt in range(20):
            private = await runtime.self_choice_store.snapshot_private()
            repair_trust = private.get("affective_sediment", {}).get("repair_trust", 0)
            if float(repair_trust) > 0.2:
                break
            await asyncio.sleep(0.1)
        else:
            failures.append("settled metabolism did not raise self-choice repair trust")

        events = await runtime.desktop_event_bus.recent(limit=20)
        event_types = [event.get("type") for event in events]
        if "metabolism_ticket_updated" not in event_types:
            failures.append(f"metabolism update event missing: {event_types}")
        final_ticket = get_ticket(root, ticket_id)
        artifacts = final_ticket.get("artifacts") if isinstance(final_ticket.get("artifacts"), dict) else {}
        if not (root / str(artifacts.get("dream_log", ""))).is_file():
            failures.append(f"bridge runner did not write dream artifact: {artifacts}")
    finally:
        await runtime.shutdown()
        shutil.rmtree(root, ignore_errors=True)
    return failures


def main() -> int:
    failures = asyncio.run(_smoke())
    if failures:
        print("Metabolism bridge smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Metabolism bridge smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

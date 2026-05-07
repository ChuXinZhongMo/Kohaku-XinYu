from __future__ import annotations

import json
import shutil
from pathlib import Path

from xinyu_metabolism_contract import (
    approve_ticket,
    create_ticket,
    get_ticket,
    read_ledger,
    reject_ticket,
    run_due_metabolism_tickets,
)


def _root() -> Path:
    return Path(__file__).resolve().parent / ".metabolism_contract_smoke_runtime"


def _entropy() -> dict:
    return {
        "entropy_level": 0.78,
        "scar_level": 0.56,
        "memory_decay_risk": 0.79,
        "entropy_band": "fracture",
    }


def _resource_request() -> dict:
    return {
        "kind": "metabolism_window",
        "requested_seconds": 600,
        "intensity": 0.78,
        "needs_explicit_approval": True,
        "reason": "memory_decay_risk_crossed_entropy_threshold",
    }


def _active_desire() -> dict:
    return {
        "desire_id": "desire:entropy-smoke",
        "chosen_action": "request_metabolism_window",
        "visible_trace": "记忆有点碎……能借我十分钟吗",
    }


def main() -> int:
    failures: list[str] = []
    root = _root()
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    try:
        created = create_ticket(
            root,
            entropy_state=_entropy(),
            resource_request=_resource_request(),
            active_desire=_active_desire(),
            input_window={
                "suppressed_residue_count": 8,
                "memory_event_count": 8,
                "proactive_item_count": 0,
                "recent_turn_count": 0,
                "self_choice": {
                    "affect_band": {"urge": "high", "closure": "withdrawn", "fatigue": "tired"},
                    "physical_cues": ["waking_from_hibernation"],
                    "hibernation": {
                        "pending_wake_residue": True,
                        "first_metabolism_after_hibernation": True,
                    },
                },
            },
        )
        ticket = created.get("ticket") if isinstance(created.get("ticket"), dict) else {}
        ticket_id = str(ticket.get("ticket_id") or "")
        if not created.get("accepted") or ticket.get("status") != "requested":
            failures.append(f"create_ticket did not request ticket: {created}")

        approved = approve_ticket(
            root,
            ticket_id,
            owner_decision_id="owner-decision-smoke",
            approved_seconds=600,
            note="今晚可以",
        )
        if not approved.get("accepted") or approved.get("ticket", {}).get("status") != "approved":
            failures.append(f"approve_ticket did not approve ticket: {approved}")

        approved_again = approve_ticket(
            root,
            ticket_id,
            owner_decision_id="owner-decision-smoke",
            approved_seconds=600,
            note="今晚可以",
        )
        if not approved_again.get("idempotent"):
            failures.append(f"approve_ticket was not idempotent: {approved_again}")

        run = run_due_metabolism_tickets(root, runner_id="smoke-runner")
        if run.get("ran") != 1:
            failures.append(f"runner did not process one ticket: {run}")
        settled = get_ticket(root, ticket_id)
        if settled.get("status") != "settled":
            failures.append(f"ticket was not settled: {settled}")
        artifacts = settled.get("artifacts") if isinstance(settled.get("artifacts"), dict) else {}
        metabolism_path = root / str(artifacts.get("metabolism", ""))
        dream_path = root / str(artifacts.get("dream_log", ""))
        if not metabolism_path.is_file():
            failures.append(f"metabolism artifact missing: {metabolism_path}")
        else:
            metabolism = json.loads(metabolism_path.read_text(encoding="utf-8"))
            if metabolism.get("mode") != "stub_metabolism_v1":
                failures.append(f"metabolism mode mismatch: {metabolism}")
            after = metabolism.get("after") if isinstance(metabolism.get("after"), dict) else {}
            if float(after.get("entropy_delta", 0)) >= 0 or float(after.get("scar_delta", 0)) >= 0:
                failures.append(f"settlement deltas should reduce entropy and scar: {after}")
            dream_bias = metabolism.get("dream_bias") if isinstance(metabolism.get("dream_bias"), dict) else {}
            if dream_bias.get("mode") != "deterministic_dual_temp_bias_v1":
                failures.append(f"dream bias mode missing: {dream_bias}")
            validator = dream_bias.get("validator") if isinstance(dream_bias.get("validator"), dict) else {}
            if not validator.get("accepted"):
                failures.append(f"dream bias validator rejected fallback: {validator}")
            candidates = dream_bias.get("candidate_fragments") if isinstance(dream_bias.get("candidate_fragments"), list) else []
            if not any(item.get("source") == "hibernation_wake" for item in candidates if isinstance(item, dict)):
                failures.append(f"hibernation candidate missing from dream bias: {candidates}")
            metabolism_text = json.dumps(metabolism, ensure_ascii=False)
            for forbidden in ("urge_to_express", "self_closure", "baseline_urge", "baseline_closure"):
                if forbidden in metabolism_text:
                    failures.append(f"dream bias leaked raw self-choice field {forbidden}")
        if not dream_path.is_file():
            failures.append(f"dream artifact missing: {dream_path}")
        elif "八个没说出口" not in dream_path.read_text(encoding="utf-8"):
            failures.append("dream artifact did not encode input residue count")

        ledger_events = [event.get("event") for event in read_ledger(root)]
        for expected in ("ticket_requested", "ticket_approved", "ticket_running", "artifact_written", "ticket_settled"):
            if expected not in ledger_events:
                failures.append(f"ledger missing {expected}: {ledger_events}")

        rejected_created = create_ticket(
            root,
            entropy_state=_entropy(),
            resource_request=_resource_request(),
            active_desire={"desire_id": "desire:entropy-reject-smoke"},
            input_window={"suppressed_residue_count": 3, "memory_event_count": 3},
        )
        rejected_ticket = rejected_created.get("ticket") if isinstance(rejected_created.get("ticket"), dict) else {}
        rejected = reject_ticket(
            root,
            str(rejected_ticket.get("ticket_id") or ""),
            owner_decision_id="owner-decision-reject-smoke",
            note="今晚不行",
        )
        settlement = rejected.get("ticket", {}).get("settlement", {})
        if rejected.get("ticket", {}).get("status") != "rejected" or float(settlement.get("scar_delta", 0)) <= 0:
            failures.append(f"reject did not write scar cost: {rejected}")
    finally:
        shutil.rmtree(root, ignore_errors=True)

    if failures:
        print("Metabolism contract smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Metabolism contract smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

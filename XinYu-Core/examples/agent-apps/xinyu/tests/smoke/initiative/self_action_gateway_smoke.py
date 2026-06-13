from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import json
import tempfile
from pathlib import Path

from xinyu_self_action_gateway import (
    APPROVAL_HANDOFF_REL,
    APPROVAL_QUEUE_REL,
    STATE_MD_REL,
    TRACE_REL,
    decide_self_action_approval,
    run_self_action_gateway,
)
from xinyu_self_chosen_goal_ecology import run_self_chosen_goal_ecology


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-self-action-") as tmp:
        root = Path(tmp)
        _write(root / "xinyu_self_chosen_goal_ecology.py", "def ok():\n    return 'goal'\n")
        _write(root / "xinyu_goal_outcome_observer.py", "def ok():\n    return 'observer'\n")
        _write(root / "xinyu_self_action_gateway.py", "def ok():\n    return 'action'\n")
        _write(root / "memory/context/recent_context.md", "Codex runtime pytest work remains active.")
        selected = run_self_chosen_goal_ecology(root, checked_at="2026-05-16T10:00:00+08:00", trigger="smoke")
        result = run_self_action_gateway(root, checked_at="2026-05-16T10:01:00+08:00", trigger="smoke")
        if selected.get("selected_goal_id") != "continue_bounded_work":
            failures.append(f"expected bounded work goal, got {selected}")
        if result.get("executed_action_count") != 1:
            failures.append(f"expected one low-risk action execution, got {result}")
        if result.get("queued_approval_count") != 1:
            failures.append(f"expected one approval queue item, got {result}")
        state = _read(root / STATE_MD_REL)
        queue = _read(root / APPROVAL_QUEUE_REL)
        trace_rows = [
            json.loads(line)
            for line in _read(root / TRACE_REL).splitlines()
            if line.strip()
        ]
        if "low_risk_auto_execute" not in state or "queued_only" not in state:
            failures.append("self action state missing boundary policy")
        if "pending_owner_approval" not in queue:
            failures.append("approval queue item missing")
        if not any(row.get("event_kind") == "self_action_executed" for row in trace_rows):
            failures.append("self action execution trace missing")
        approved = decide_self_action_approval(
            root,
            queue_id="latest",
            decision="approved",
            decided_at="2026-05-16T10:02:00+08:00",
            execute=True,
        )
        handoff = _read(root / APPROVAL_HANDOFF_REL)
        if approved.get("decision") != "approved" or approved.get("execution", {}).get("executed_count") != 1:
            failures.append(f"approval execution did not complete: {approved}")
        if "gateway_effect: local ticket and trace only" not in handoff:
            failures.append("approval handoff missing local-control boundary")

    autonomous_aliases_text = _read(ROOT / "xinyu_bridge_runtime_autonomous_aliases.py")
    maintenance_text = _read(ROOT / "xinyu_bridge_autonomous_maintenance.py")
    context_text = _read(ROOT / "xinyu_runtime_context.py")
    presence_text = _read(ROOT / "xinyu_runtime_presence.py")
    smoke_text = _read(ROOT / "smoke_run.py")
    if "_append_self_action_gateway_note" not in autonomous_aliases_text or "run_self_action_gateway(" not in maintenance_text:
        failures.append("runtime does not run self action gateway")
    if "memory/context/self_action_gateway_state.md" not in context_text:
        failures.append("runtime context does not include self action gateway state")
    if "runtime/self_action_gateway/trace.jsonl" not in presence_text:
        failures.append("runtime presence does not summarize self action gateway trace")
    if "self_action_gateway_smoke.py" not in smoke_text:
        failures.append("smoke_run.py does not include self action gateway smoke")

    if failures:
        print("Self action gateway smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Self action gateway smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

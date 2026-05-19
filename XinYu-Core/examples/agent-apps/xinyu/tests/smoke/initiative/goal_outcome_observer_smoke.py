from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import json
import tempfile
from pathlib import Path

from xinyu_goal_outcome_observer import OBSERVER_STATE_REL, run_goal_outcome_observer
from xinyu_self_chosen_goal_ecology import STATE_JSON_REL, STATE_MD_REL, TRACE_REL, run_self_chosen_goal_ecology


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
    with tempfile.TemporaryDirectory(prefix="xinyu-goal-outcome-") as tmp:
        root = Path(tmp)
        _write(root / "memory/context/recent_context.md", "Codex runtime pytest work remains active.")
        selected = run_self_chosen_goal_ecology(root, checked_at="2026-05-16T10:00:00+08:00", trigger="smoke")
        result = run_goal_outcome_observer(
            root,
            checked_at="2026-05-16T10:05:00+08:00",
            trigger="smoke",
            maintenance_notes=[
                "self_thought:held/request_candidate/runtime",
                "daily_digest:skipped/false",
                "memory_self_review:ok/0",
            ],
        )
        if selected.get("selected_goal_id") != "continue_bounded_work":
            failures.append(f"expected bounded work selection, got {selected}")
        if result.get("status") != "recorded" or result.get("outcome") != "useful":
            failures.append(f"observer did not record useful outcome: {result}")
        state = json.loads((root / STATE_JSON_REL).read_text(encoding="utf-8"))
        if state["goals"]["continue_bounded_work"]["habit_weight"] <= 0:
            failures.append("useful outcome did not increase habit weight")
        observer_state = _read(root / OBSERVER_STATE_REL)
        ecology_state = _read(root / STATE_MD_REL)
        trace = _read(root / TRACE_REL)
        if "Outcome Ecology Report" not in ecology_state:
            failures.append("goal state missing outcome ecology report")
        if "goal_ecology_outcome_observed" not in trace:
            failures.append("outcome observer trace missing")
        if "maintenance_notes_hash" not in observer_state:
            failures.append("observer state missing hashed maintenance signal")

    core_text = _read(ROOT / "xinyu_core_bridge.py")
    presence_text = _read(ROOT / "xinyu_runtime_presence.py")
    smoke_text = _read(ROOT / "smoke_run.py")
    if "run_goal_outcome_observer(" not in core_text:
        failures.append("xinyu_core_bridge.py does not run goal outcome observer")
    if "xinyu_goal_outcome_observer.py" not in presence_text:
        failures.append("runtime presence does not include goal outcome observer in code surface")
    if "goal_outcome_observer_smoke.py" not in smoke_text:
        failures.append("smoke_run.py does not include goal outcome observer smoke")

    if failures:
        print("Goal outcome observer smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Goal outcome observer smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

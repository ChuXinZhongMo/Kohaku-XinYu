from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import json
import tempfile
from pathlib import Path

from xinyu_self_chosen_goal_ecology import (
    STATE_MD_REL,
    TRACE_REL,
    record_self_chosen_goal_outcome,
    run_self_chosen_goal_ecology,
)


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
    with tempfile.TemporaryDirectory(prefix="xinyu-goal-ecology-") as tmp:
        root = Path(tmp)
        _write(root / "memory/context/recent_context.md", "Codex runtime replay pytest work remains active.")
        result = run_self_chosen_goal_ecology(root, checked_at="2026-05-16T10:00:00+08:00", trigger="smoke")
        if result["selected_goal_id"] != "continue_bounded_work":
            failures.append(f"expected bounded work goal, got {result}")
        state = (root / STATE_MD_REL).read_text(encoding="utf-8")
        if "state_only_no_outward_action" not in state:
            failures.append("state-only action policy missing")
        outcome = record_self_chosen_goal_outcome(
            root,
            "continue_bounded_work",
            "blocked",
            observed_at="2026-05-16T10:01:00+08:00",
        )
        if outcome["habit_weight_after"] >= outcome["habit_weight_before"]:
            failures.append(f"blocked outcome did not lower habit weight: {outcome}")
        second = run_self_chosen_goal_ecology(root, checked_at="2026-05-16T10:02:00+08:00", trigger="smoke")
        if second["selected_goal_id"] == "continue_bounded_work":
            failures.append("blocked goal should not be immediately selected again")
        trace_rows = [
            json.loads(line)
            for line in (root / TRACE_REL).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        if not any(row.get("event_kind") == "goal_ecology_outcome_recorded" for row in trace_rows):
            failures.append("outcome trace missing")

    autonomous_aliases_text = _read(ROOT / "xinyu_bridge_runtime_autonomous_aliases.py")
    maintenance_text = _read(ROOT / "xinyu_bridge_autonomous_maintenance.py")
    context_text = _read(ROOT / "xinyu_runtime_context.py")
    presence_text = _read(ROOT / "xinyu_runtime_presence.py")
    if "_append_goal_ecology_note" not in autonomous_aliases_text or "run_self_chosen_goal_ecology(" not in maintenance_text:
        failures.append("runtime does not run self-chosen goal ecology")
    if "memory/context/self_chosen_goal_ecology_state.md" not in context_text:
        failures.append("runtime context does not include self-chosen goal ecology state")
    if "runtime/self_chosen_goal_ecology/trace.jsonl" not in presence_text:
        failures.append("runtime presence does not summarize self-chosen goal ecology trace")

    if failures:
        print("Self-chosen goal ecology smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Self-chosen goal ecology smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

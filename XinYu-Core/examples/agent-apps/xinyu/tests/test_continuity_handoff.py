from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from xinyu_continuity_handoff import refresh_continuity_handoff  # noqa: E402


def test_continuity_handoff_silences_overloaded_learning_thread(tmp_path: Path) -> None:
    state_path = tmp_path / "memory/self/learning_closed_loop_state.md"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        """---
title: Learning Closed Loop State
memory_type: learning_closed_loop_state
---

# Learning Closed Loop State

## Current Loop
- status: trial_active
- latest_failure_kind: owner_reported_context_discontinuity
- active_trial_habit: answer from recent real context first
- expected_next_behavior: connect to the latest real turn before explaining
- repair_count: 12
- success_count: 0
- success_streak: 0
""",
        encoding="utf-8",
    )

    result = refresh_continuity_handoff(
        tmp_path,
        user_text="刚才那个呢",
        observed_at="2026-05-12T17:00:00+08:00",
    )
    state = (tmp_path / "memory/context/continuity_handoff_state.md").read_text(encoding="utf-8")

    assert result["continuity_mode"] == "normal_live_turn"
    assert result["open_loop_count"] == 0
    assert "- learning_thread: none" in state

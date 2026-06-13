from __future__ import annotations

from pathlib import Path

from xinyu_bridge_desktop_snapshot import desktop_private_ecosystem_snapshot
from xinyu_private_ecosystem import run_private_ecosystem_tick


def test_desktop_private_ecosystem_snapshot_shape(tmp_path: Path) -> None:
    # Empty root: snapshot must still be well-formed and safe.
    empty = desktop_private_ecosystem_snapshot(tmp_path)
    assert empty["observed"] is False
    assert empty["ownerPrivateShare"]["paused"] is True
    assert empty["boundaries"]["stableMemoryWrite"] == "blocked"

    run_private_ecosystem_tick(tmp_path, checked_at="2026-06-02T10:00:00+08:00", trigger="test")
    snap = desktop_private_ecosystem_snapshot(tmp_path)

    assert snap["observed"] is True
    assert snap["activeGoalId"] != ""
    assert snap["counters"]["lowRiskExecuted"] >= 1
    assert snap["killSwitch"]["shareEnabled"] is False
    assert snap["browser"]["usesOwnerProfile"] is False
    assert snap["computer"]["multiStepArbitraryControl"] == "disabled"
    assert snap["journal"]["stableMemoryWriteCount"] == 0
    # Required first-screen governance fields are present.
    for key in ("rolloutState", "activeGoalId", "ownerPrivateShare", "killSwitch", "paths"):
        assert key in snap

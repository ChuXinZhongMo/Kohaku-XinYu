from __future__ import annotations

from pathlib import Path

from xinyu_desire_drive_state import STATE_REL, run_desire_drive_state
from xinyu_status import check_state, status_fields


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def test_desire_drive_state_aggregates_desire_without_authorizing_outward_action(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory/context/thought_seeds.md",
        """
        - dominant_drive: owner_long_idle
        """,
    )
    _write(
        tmp_path / "memory/context/impulse_soup_state.md",
        """
        - status: active
        - top_desire_shape: owner_presence_probe
        - top_energy: 48
        - outward_action_allowed: false
        """,
    )
    _write(
        tmp_path / "memory/context/proactive_decision_state.md",
        """
        - source_type: owner_long_idle
        - total_score: 62
        - recommendation: inbox
        - preferred_channel: inbox
        - hard_blocks: qq_send_disabled_for_owner_long_idle_v0
        """,
    )
    _write(
        tmp_path / "memory/context/initiative_lifecycle_state.md",
        """
        - selected_decision: desktop_inbox
        - held_count: 0
        - delivery_level: desktop_inbox
        """,
    )
    _write(
        tmp_path / "memory/context/initiative_spine_state.md",
        """
        - status: active
        - emergence_level: shadow_initiative_pressure
        - action_permission: inner_only_impulse_boundary
        """,
    )

    result = run_desire_drive_state(
        tmp_path,
        checked_at="2026-06-02T01:30:00+08:00",
        trigger="test",
    )
    state = (tmp_path / STATE_REL).read_text(encoding="utf-8")

    assert result["status"] == "active"
    assert result["dominant_drive"] == "owner_long_idle"
    assert result["drive_intensity"] >= 72
    assert result["autonomy_tension"] == "drive_visible_as_local_candidate"
    assert result["candidate_effect"] == "local_desktop_candidate_visible"
    assert result["blocked_by"] == ["inner_only_impulse_boundary"]
    assert result["boundaries"]["no_qq_enqueue"] == "true"
    assert "- stable_memory_write: blocked" in state
    assert "- consciousness_claim: false" in state


def test_status_exposes_desire_drive_state_as_bounded_check(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory/context/proactive_decision_state.md",
        """
        - source_type: reflection_question
        - total_score: 58
        - recommendation: inbox
        - preferred_channel: inbox
        - hard_blocks: none
        """,
    )

    fields = status_fields(tmp_path)
    checks = {check.name: check for check in check_state(tmp_path)}

    assert fields["desire_drive_status"] == "active"
    assert fields["desire_drive_dominant"] == "reflection_question"
    assert fields["desire_drive_no_qq_enqueue"] == "true"
    assert fields["desire_drive_stable_memory_write"] == "blocked"
    assert fields["desire_drive_consciousness_claim"] == "false"
    assert checks["desire_drive_state"].ok is True

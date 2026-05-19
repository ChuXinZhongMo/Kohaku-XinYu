from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from xinyu_scene_frame import build_scene_frame  # noqa: E402
from xinyu_slow_state_modulator import SlowState  # noqa: E402
from xinyu_slow_state_modulator import build_slow_state  # noqa: E402
from xinyu_slow_state_modulator import read_slow_state  # noqa: E402
from xinyu_slow_state_modulator import render_slow_state_prompt_block  # noqa: E402
from xinyu_turn_residue import TurnResidue  # noqa: E402


def test_slow_state_marks_night_shift_fatigue_and_persists(tmp_path: Path) -> None:
    frame = build_scene_frame(
        tmp_path,
        user_text="\u6211\u521a\u4e0b\u5b8c\u591c\u73ed\u6709\u70b9\u56f0",
        evaluated_at="2026-05-19T08:30:00+08:00",
    )
    state = build_slow_state(
        tmp_path,
        scene_frame=frame,
        evaluated_at="2026-05-19T08:30:00+08:00",
        persist=True,
    )
    stored = read_slow_state(tmp_path, evaluated_at="2026-05-19T08:30:00+08:00")

    assert state.fatigue_load >= 70
    assert state.reply_policy == "low_burden_short"
    assert "low_burden_reply" in state.active_policies
    assert stored.fatigue_load == state.fatigue_load


def test_slow_state_decays_fatigue_over_time(tmp_path: Path) -> None:
    previous = SlowState(
        updated_at="2026-05-19T08:00:00+08:00",
        fatigue_load=80,
        relation_guard=0,
        correction_pressure=0,
        initiative_dampening=60,
        reply_policy="low_burden_short",
        initiative_policy="suppress_optional_proactive",
        recall_policy="prefer_recent_time_bound_context_keep_short",
        emotion_policy="normal_shadow_bias",
        active_policies=("low_burden_reply",),
        evidence_signals=("test",),
    )
    state = build_slow_state(
        tmp_path,
        previous_state=previous,
        evaluated_at="2026-05-19T10:30:00+08:00",
    )

    assert 35 <= state.fatigue_load < 80
    assert state.initiative_dampening < 60


def test_slow_state_style_error_holds_proactive_and_changes_by_action(tmp_path: Path) -> None:
    state = build_slow_state(
        tmp_path,
        response_error_decision={"error_class": "style_surface_failure"},
        evaluated_at="2026-05-19T10:00:00+08:00",
    )

    assert state.correction_pressure >= 70
    assert state.reply_policy == "short_present_tense_no_postmortem"
    assert state.initiative_policy == "suppress_optional_proactive"
    assert state.recall_policy == "prefer_recent_corrections_and_current_turn"


def test_slow_state_relationship_context_guards_warmth(tmp_path: Path) -> None:
    state = build_slow_state(
        tmp_path,
        triage_decision={"primary_lane": "relationship_boundary"},
        evaluated_at="2026-05-19T10:00:00+08:00",
    )

    assert state.relation_guard >= 60
    assert state.reply_policy == "warm_boundary_aware"
    assert state.emotion_policy == "allow_guarded_or_warm_residue_without_fact_claim"


def test_slow_state_consumes_turn_residue(tmp_path: Path) -> None:
    residue = TurnResidue(
        scene="owner_relationship_pressure",
        pressure="relationship",
        speech_act="relationship_pressure_reply",
        tone="hurt_pressure_residue",
        felt_residue="test residue",
        reply_shape="compact",
        updated_at="2026-05-19T09:30:00+08:00",
        raw_strength=82,
        decayed_strength=82,
    )
    state = build_slow_state(
        tmp_path,
        turn_residue=residue,
        evaluated_at="2026-05-19T10:00:00+08:00",
    )

    assert state.relation_guard >= 80
    assert "turn_residue:relationship" in state.evidence_signals


def test_slow_state_render_has_no_private_body(tmp_path: Path) -> None:
    frame = build_scene_frame(
        tmp_path,
        user_text="\u79c1\u4eba\u539f\u6587\u4e0d\u8be5\u51fa\u73b0\uff0c\u6211\u56f0\u4e86",
    )
    state = build_slow_state(tmp_path, scene_frame=frame, user_text="\u79c1\u4eba\u539f\u6587\u4e0d\u8be5\u51fa\u73b0")
    rendered = render_slow_state_prompt_block(state)

    assert "## Slow State Modulator" in rendered
    assert "fatigue_load" in rendered
    assert "\u79c1\u4eba\u539f\u6587" not in rendered
    assert "\u4e0d\u8be5\u51fa\u73b0" not in rendered

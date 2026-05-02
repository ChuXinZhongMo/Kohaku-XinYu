from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from xinyu_private_thought_events import (  # noqa: E402
    build_private_thought_note_material,
    record_private_thought_outcome,
    record_private_thought_reply_link,
    refresh_private_thought_event_sync,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _seed_minimal_context(root: Path) -> None:
    _write(
        root / "memory/context/persona_surface_state.md",
        """# Persona Surface State

## Previous Visible Turn
- last_scene: owner_style_pressure
- last_pressure: style
- last_tone: short_affected_guarded
- last_felt_residue: owner still heard the reply as mechanical
- last_reply_shape: compact
- residue_strength: 86
""",
    )
    _write(
        root / "memory/context/initiative_state.md",
        """# Initiative State

## Latest Decision
- decision: defer
- reason: wait for owner signal
- selected_question: none
- visible_posture: quiet_available
""",
    )
    _write(
        root / "memory/context/memory_weight_state.md",
        """# Memory Weight State

## Active Weights
- path: memory/self/core.md | layer: stable_identity | active_weight: 98 | base_weight: 98 | age_hours: 0.00 | floor: 96 | stable: true
""",
    )


def test_private_thought_event_writes_state_log_and_self_model(tmp_path: Path) -> None:
    _seed_minimal_context(tmp_path)

    snapshot = refresh_private_thought_event_sync(
        tmp_path,
        generated_at="2026-04-30T10:00:00+08:00",
        source_kind="deterministic_seed_summary",
        trigger="test",
    )
    material = build_private_thought_note_material(
        tmp_path,
        generated_at="2026-04-30T10:00:00+08:00",
    )

    assert snapshot.event_id.startswith("private-thought-")
    assert snapshot.dominant_drive == "recent_surface_residue"
    assert "Private Thought State" in (tmp_path / "memory/self/private_thought_state.md").read_text(encoding="utf-8")
    assert snapshot.event_id in (tmp_path / "memory/self/private_thought_log.md").read_text(encoding="utf-8")
    assert "Self Model State" in (tmp_path / "memory/self/self_model_state.md").read_text(encoding="utf-8")
    assert "private_thought_event_state" in material
    assert "hidden chain-of-thought" in material


def test_private_thought_feedback_updates_self_model(tmp_path: Path) -> None:
    _seed_minimal_context(tmp_path)
    snapshot = refresh_private_thought_event_sync(
        tmp_path,
        generated_at="2026-04-30T10:00:00+08:00",
        source_kind="deterministic_seed_summary",
        trigger="test",
    )

    linked = record_private_thought_reply_link(
        tmp_path,
        {},
        user_text="你还是太机械了",
        reply="知道了，我这次不解释，直接改。",
        session_key="owner-session",
        linked_at="2026-04-30T10:01:00+08:00",
    )
    outcome = record_private_thought_outcome(
        tmp_path,
        {},
        text="还是没变",
        session_key="owner-session",
        evaluation={
            "evaluated": True,
            "prediction_error": 0.72,
            "notes": ["dialogue_curiosity_high_error"],
        },
        observed_at="2026-04-30T10:02:00+08:00",
    )
    feedback = (tmp_path / "memory/self/private_thought_feedback_state.md").read_text(encoding="utf-8")
    self_model = (tmp_path / "memory/self/self_model_state.md").read_text(encoding="utf-8")

    assert linked["linked"] is True
    assert outcome["outcome"] == "needs_repair"
    assert outcome["repair_signal"] is True
    assert snapshot.event_id in feedback
    assert "outcome: needs_repair" in feedback
    assert "persona_trial_feedback: repair_needed" in feedback
    assert "repair_signal: true" in feedback
    assert "latest_outcome: needs_repair" in self_model
    assert "repair_signal: true" in self_model


def test_private_thought_feedback_distinguishes_weak_acceptance_from_promotion(tmp_path: Path) -> None:
    _seed_minimal_context(tmp_path)
    refresh_private_thought_event_sync(
        tmp_path,
        generated_at="2026-04-30T11:00:00+08:00",
        source_kind="deterministic_seed_summary",
        trigger="test",
    )
    record_private_thought_reply_link(
        tmp_path,
        {"metadata": {"is_owner_user": True}},
        user_text="别套模板",
        reply="嗯，我不讲以后了，这句先改。",
        session_key="owner-session",
        linked_at="2026-04-30T11:01:00+08:00",
    )

    outcome = record_private_thought_outcome(
        tmp_path,
        {"metadata": {"is_owner_user": True}},
        text="好继续",
        session_key="owner-session",
        evaluation={"evaluated": True, "prediction_error": 0.12, "notes": [], "actual_next": {"softening": 1.0}},
        observed_at="2026-04-30T11:02:00+08:00",
    )
    feedback = (tmp_path / "memory/self/private_thought_feedback_state.md").read_text(encoding="utf-8")

    assert outcome["outcome"] == "no_strong_mismatch"
    assert outcome["persona_trial_feedback"] == "weak_acceptance_continue"
    assert outcome["promotion_signal"] is False
    assert "promotion_signal: false" in feedback
    assert "short acceptance or continuation is not proof" in feedback


def test_private_thought_feedback_can_mark_explicit_persona_success(tmp_path: Path) -> None:
    _seed_minimal_context(tmp_path)
    refresh_private_thought_event_sync(
        tmp_path,
        generated_at="2026-04-30T12:00:00+08:00",
        source_kind="deterministic_seed_summary",
        trigger="test",
    )
    record_private_thought_reply_link(
        tmp_path,
        {"metadata": {"is_owner_user": True}},
        user_text="别套模板",
        reply="嗯，我不讲以后了，这句先改。",
        session_key="owner-session",
        linked_at="2026-04-30T12:01:00+08:00",
    )

    outcome = record_private_thought_outcome(
        tmp_path,
        {"metadata": {"is_owner_user": True}},
        text="这句可以，自然多了",
        session_key="owner-session",
        evaluation={"evaluated": True, "prediction_error": 0.10, "notes": [], "actual_next": {"softening": 1.0}},
        observed_at="2026-04-30T12:02:00+08:00",
    )
    feedback = (tmp_path / "memory/self/private_thought_feedback_state.md").read_text(encoding="utf-8")
    self_model = (tmp_path / "memory/self/self_model_state.md").read_text(encoding="utf-8")

    assert outcome["outcome"] == "no_strong_mismatch"
    assert outcome["persona_trial_feedback"] == "promotion_observed"
    assert outcome["promotion_signal"] is True
    assert "promotion_signal: true" in feedback
    assert "persona_trial_feedback: promotion_observed" in self_model


def test_private_thought_feedback_does_not_promote_unbound_generic_better(tmp_path: Path) -> None:
    _seed_minimal_context(tmp_path)
    refresh_private_thought_event_sync(
        tmp_path,
        generated_at="2026-04-30T12:30:00+08:00",
        source_kind="deterministic_seed_summary",
        trigger="test",
    )
    record_private_thought_reply_link(
        tmp_path,
        {"metadata": {"is_owner_user": True}},
        user_text="别套模板",
        reply="嗯，我不讲以后了，这句先改。",
        session_key="owner-session",
        linked_at="2026-04-30T12:31:00+08:00",
    )

    outcome = record_private_thought_outcome(
        tmp_path,
        {"metadata": {"is_owner_user": True}},
        text="身体好多了",
        session_key="owner-session",
        evaluation={"evaluated": True, "prediction_error": 0.10, "notes": [], "actual_next": {"softening": 1.0}},
        observed_at="2026-04-30T12:32:00+08:00",
    )

    assert outcome["persona_trial_feedback"] == "softening_observed"
    assert outcome["promotion_signal"] is False

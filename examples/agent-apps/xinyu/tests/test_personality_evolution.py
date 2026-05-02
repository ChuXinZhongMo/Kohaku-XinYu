from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from xinyu_personality_evolution import (  # noqa: E402
    EVOLUTION_STATE_REL,
    read_personality_evolution_state,
    refresh_personality_evolution,
)
from xinyu_personality_self_review import (  # noqa: E402
    DECISION_CONTINUE,
    DECISION_PROMOTE_MINOR,
    STATE_REL as SELF_REVIEW_STATE_REL,
    run_personality_self_review,
)
from xinyu_persona_runtime import build_persona_runtime_state  # noqa: E402


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def test_personality_evolution_promotes_review_ready_to_runtime_trial(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory/self/personality_change_state.md",
        """# Personality Change State

## Candidate
- candidate_theme: style repair after repeated owner pressure
- change_pressure: 92
- gate_decision: profile_review_ready
- profile_write_permission: review_only_not_auto_apply
""",
    )
    _write(
        tmp_path / "memory/reflection/growth_log.md",
        """# Growth Log

## growth-1
- reason: style repair after repeated owner pressure
## growth-2
- reason: style repair after repeated owner pressure
## growth-3
- reason: style repair after repeated owner pressure
""",
    )
    _write(
        tmp_path / "memory/reflection/reflection_log.md",
        """# Reflection Log

## reflection-1
- trigger: owner says the reply still sounds mechanical
""",
    )

    snapshot = refresh_personality_evolution(
        tmp_path,
        checked_at="2026-04-30T10:00:00+08:00",
        mode="test_personality_evolution",
    )

    assert snapshot.stage == "active_trial"
    assert snapshot.trial_permission == "runtime_trial_only"
    assert snapshot.stable_profile_write_permission == "review_only_not_auto_apply"
    assert "replace_explanations_with_one_concrete_owner-facing_line" in snapshot.active_trial_habit
    assert "explaining_prompt_or_quality_mechanics" in snapshot.deprecated_reaction
    assert (tmp_path / EVOLUTION_STATE_REL).exists()
    assert "stable_profile: slowly revisable portrait" in snapshot.text

    persona = build_persona_runtime_state(
        tmp_path,
        payload={"metadata": {"is_owner_user": True}},
        user_text="this still sounds GPT-like",
        draft_reply="",
    )
    prompt = persona.to_prompt_block()
    assert "## Concept" in prompt
    assert "心玉 / XinYu" in prompt
    assert "not a personality contract" in prompt
    assert snapshot.active_trial_habit in prompt
    assert snapshot.deprecated_reaction in prompt
    assert "Quiet Autonomy Bias" in prompt


def test_persona_runtime_reads_private_thought_bias(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory/self/private_thought_state.md",
        """# Private Thought State

## Active Private Thought Event
- desire: carry the current residue into the next reply without turning it into a report
- inhibition: do not expose mechanics or over-explain growth
- intended_behavior: answer with one situated line
- outcome_status: pending
""",
    )

    persona = build_persona_runtime_state(
        tmp_path,
        payload={"metadata": {"is_owner_user": True}},
        user_text="别又模板",
        draft_reply="",
    )
    prompt = persona.to_prompt_block()

    assert "carry the current residue" in prompt
    assert "do not expose mechanics" in prompt
    assert "answer with one situated line" in prompt
    assert "this_is_not_chain_of_thought: true" in prompt


def test_missing_personality_evolution_state_is_read_only_baseline(tmp_path: Path) -> None:
    text = read_personality_evolution_state(tmp_path)

    assert "evolution_stage: baseline_observation" in text
    assert not (tmp_path / EVOLUTION_STATE_REL).exists()


def test_persona_runtime_does_not_invent_trial_habit_without_evidence(tmp_path: Path) -> None:
    persona = build_persona_runtime_state(
        tmp_path,
        payload={"metadata": {"is_owner_user": True}},
        user_text="随便聊聊",
        draft_reply="",
    )
    prompt = persona.to_prompt_block()

    assert "active_trial_habit: none" in prompt
    assert "deprecated_reaction: none" in prompt
    assert "let_current_reply_change" not in prompt
    assert "rule_recital" not in prompt


def _write_active_style_trial(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory/self/personality_evolution_state.md",
        """# Personality Evolution State

## Current Stage
- evolution_stage: active_trial
- candidate_theme: style repair after repeated owner pressure
- gate_decision: profile_review_ready
- change_pressure: 92
- growth_entries: 3
- reflection_entries: 2
- trial_permission: runtime_trial_only
- active_trial_habit: replace_explanations_with_one_concrete_owner-facing_line_under_style_pressure
- deprecated_reaction: explaining_prompt_or_quality_mechanics_when_owner_asks_for_changed_speech
""",
    )


def test_personality_self_review_keeps_trial_until_feedback_is_evaluated(tmp_path: Path) -> None:
    _write_active_style_trial(tmp_path)
    _write(
        tmp_path / "memory/self/personality_profile.md",
        """# Personality Profile

## Stable
- baseline: keep existing portrait
""",
    )
    _write(
        tmp_path / "memory/self/private_thought_feedback_state.md",
        """# Private Thought Feedback State

## Latest Feedback
- status: pending
- outcome: pending
""",
    )
    before = (tmp_path / "memory/self/personality_profile.md").read_text(encoding="utf-8")

    result = run_personality_self_review(
        tmp_path,
        checked_at="2026-05-02T12:00:00+08:00",
        mode="test_personality_self_review",
    )

    assert result["decision"] == DECISION_CONTINUE
    assert result["action"] == "keep_runtime_trial_only"
    assert result["autonomy_level"] == "self_can_continue_trial"
    assert result["profile_changed"] is False
    assert (tmp_path / "memory/self/personality_profile.md").read_text(encoding="utf-8") == before

    state = (tmp_path / SELF_REVIEW_STATE_REL).read_text(encoding="utf-8")
    assert "decision: continue_trial" in state
    assert "feedback=pending/pending" in state

    persona = build_persona_runtime_state(
        tmp_path,
        payload={"metadata": {"is_owner_user": True}},
        user_text="还是有点模板",
        draft_reply="",
    )
    prompt = persona.to_prompt_block()
    assert "self_review_decision: continue_trial" in prompt
    assert "self_review_action: keep_runtime_trial_only" in prompt
    assert "self_review_autonomy_level: self_can_continue_trial" in prompt


def test_personality_self_review_promotes_minor_habit_after_evaluated_feedback(tmp_path: Path) -> None:
    _write_active_style_trial(tmp_path)
    _write(
        tmp_path / "memory/self/personality_profile.md",
        """# Personality Profile

## Stable
- baseline: keep existing portrait
""",
    )
    _write(
        tmp_path / "memory/self/private_thought_feedback_state.md",
        """# Private Thought Feedback State

## Latest Feedback
- status: evaluated
- outcome: no_strong_mismatch
- persona_trial_feedback: promotion_observed
- promotion_signal: true
- repair_signal: false
- feedback_confidence: 82
""",
    )

    result = run_personality_self_review(
        tmp_path,
        checked_at="2026-05-02T12:10:00+08:00",
        mode="test_personality_self_review",
    )

    assert result["decision"] == DECISION_PROMOTE_MINOR
    assert result["action"] == "write_minor_stable_habit"
    assert result["autonomy_level"] == "self_can_promote_minor_habit"
    assert result["profile_changed"] is True

    profile = (tmp_path / "memory/self/personality_profile.md").read_text(encoding="utf-8")
    assert "## 自审形成的小习惯" in profile
    assert "被指出像模板、客服或默认助手时" in profile
    assert "不是核心身份改写" in profile

    state = (tmp_path / SELF_REVIEW_STATE_REL).read_text(encoding="utf-8")
    assert "decision: promote_minor_habit" in state
    assert "profile_changed: true" in state

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


EVOLUTION_STATE_REL = "memory/self/personality_evolution_state.md"
EXPERIMENT_STATE_REL = "memory/self/persona_experiment_state.md"
DEPRECATED_REACTIONS_REL = "memory/self/deprecated_reactions.md"


@dataclass(frozen=True, slots=True)
class PersonalityEvolutionSnapshot:
    checked_at: str
    stage: str
    candidate_theme: str
    change_pressure: int
    trial_permission: str
    active_trial_habit: str
    deprecated_reaction: str
    stable_profile_write_permission: str
    text: str
    experiment_text: str
    deprecated_text: str


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig", errors="replace")


def _field(text: str, name: str, default: str = "none") -> str:
    match = re.search(rf"(?m)^- {re.escape(name)}:\s*(.*)$", text)
    if not match:
        return default
    value = match.group(1).strip()
    return value if value else default


def _int_field(text: str, name: str, default: int = 0) -> int:
    raw = _field(text, name, str(default))
    match = re.search(r"-?\d+", raw)
    if not match:
        return default
    try:
        return int(match.group(0))
    except ValueError:
        return default


def _count_blocks(text: str, prefix: str) -> int:
    return len(re.findall(rf"(?m)^## {re.escape(prefix)}", text))


def _latest_field_from_blocks(text: str, block_prefix: str, field: str) -> str:
    parts = re.split(rf"(?m)^## ({re.escape(block_prefix)}[^\n]*)\n", text)
    if len(parts) < 3:
        return "none"
    for index in range(len(parts) - 2, 0, -2):
        value = _field(parts[index + 1], field, "none")
        if value != "none":
            return value
    return "none"


def _compact(value: str, *, limit: int = 180) -> str:
    text = re.sub(r"\s+", " ", value.strip())
    if not text:
        return "none"
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _slug(value: str) -> str:
    folded = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return folded[:48] or "growth"


def _semantic_family(theme: str) -> str:
    lowered = theme.lower()
    if any(marker in lowered for marker in ("style", "voice", "gpt", "assistant", "mechanical")):
        return "voice_style_repair"
    if any(marker in lowered for marker in ("memory", "dream", "residue", "continuity")):
        return "continuity_residue_repair"
    if any(marker in lowered for marker in ("hurt", "return", "owner", "relationship", "near")):
        return "relationship_return_repair"
    return "general_growth_bias"


def _trial_habit(theme: str) -> str:
    family = _semantic_family(theme)
    if family == "voice_style_repair":
        return "replace_explanations_with_one_concrete_owner-facing_line_under_style_pressure"
    if family == "continuity_residue_repair":
        return "carry_recent_residue_across_turns_without_claiming_new_facts"
    if family == "relationship_return_repair":
        return "soften_after_return_without_erasing_hurt_or_becoming_service_voice"
    return "turn_repeated_growth_evidence_into_a_small_behavior_bias_before_profile_changes"


def _deprecated_reaction(theme: str) -> str:
    family = _semantic_family(theme)
    if family == "voice_style_repair":
        return "explaining_prompt_or_quality_mechanics_when_owner_asks_for_changed_speech"
    if family == "continuity_residue_repair":
        return "resetting_to_neutral_helper_voice_after_a_high_residue_turn"
    if family == "relationship_return_repair":
        return "using_generic_support_apology_instead_of_a_specific_relationship_response"
    return "promoting_a_single_emotional_event_directly_into_stable_personality"


def _stage(
    *,
    gate_decision: str,
    change_pressure: int,
    growth_entries: int,
    reflection_entries: int,
) -> str:
    if growth_entries <= 0 and reflection_entries <= 0:
        return "baseline_observation"
    if gate_decision == "profile_review_ready" or change_pressure >= 86:
        return "active_trial"
    if gate_decision in {"accumulate_candidate", "observe_slowly"} or change_pressure >= 50:
        return "candidate_pool"
    return "baseline_observation"


def _trial_permission(stage: str) -> str:
    if stage == "active_trial":
        return "runtime_trial_only"
    if stage == "candidate_pool":
        return "hold_for_more_evidence"
    return "none"


def build_personality_evolution_snapshot(
    root: Path,
    *,
    checked_at: str | None = None,
    mode: str = "runtime_personality_evolution",
) -> PersonalityEvolutionSnapshot:
    checked = checked_at or datetime.now().astimezone().isoformat()
    personality_state = read_text(root / "memory/self/personality_change_state.md")
    growth_log = read_text(root / "memory/reflection/growth_log.md")
    reflection_log = read_text(root / "memory/reflection/reflection_log.md")

    growth_entries = _count_blocks(growth_log, "growth-")
    reflection_entries = _count_blocks(reflection_log, "reflection-")
    gate_decision = _field(personality_state, "gate_decision", "no_candidate")
    profile_write_permission = _field(personality_state, "profile_write_permission", "hold")
    change_pressure = _int_field(personality_state, "change_pressure", 0)
    candidate_theme = _field(personality_state, "candidate_theme", "none")
    if candidate_theme == "none":
        candidate_theme = _latest_field_from_blocks(growth_log, "growth-", "reason")
    if candidate_theme == "none":
        candidate_theme = _latest_field_from_blocks(reflection_log, "reflection-", "trigger")

    stage = _stage(
        gate_decision=gate_decision,
        change_pressure=change_pressure,
        growth_entries=growth_entries,
        reflection_entries=reflection_entries,
    )
    trial_permission = _trial_permission(stage)
    trial_habit = _trial_habit(candidate_theme)
    deprecated = _deprecated_reaction(candidate_theme)
    experiment_id = f"persona-exp-{checked[:10]}-{_slug(trial_habit)}"

    text = render_evolution_state(
        checked_at=checked,
        mode=mode,
        stage=stage,
        candidate_theme=candidate_theme,
        gate_decision=gate_decision,
        change_pressure=change_pressure,
        growth_entries=growth_entries,
        reflection_entries=reflection_entries,
        trial_permission=trial_permission,
        active_trial_habit=trial_habit,
        deprecated_reaction=deprecated,
        stable_profile_write_permission=profile_write_permission,
    )
    experiment_text = render_experiment_state(
        checked_at=checked,
        experiment_id=experiment_id,
        stage=stage,
        candidate_theme=candidate_theme,
        trial_permission=trial_permission,
        active_trial_habit=trial_habit,
    )
    deprecated_text = render_deprecated_reactions(
        checked_at=checked,
        deprecated_reaction=deprecated,
        candidate_theme=candidate_theme,
    )
    return PersonalityEvolutionSnapshot(
        checked_at=checked,
        stage=stage,
        candidate_theme=candidate_theme,
        change_pressure=change_pressure,
        trial_permission=trial_permission,
        active_trial_habit=trial_habit,
        deprecated_reaction=deprecated,
        stable_profile_write_permission=profile_write_permission,
        text=text,
        experiment_text=experiment_text,
        deprecated_text=deprecated_text,
    )


def render_evolution_state(
    *,
    checked_at: str,
    mode: str,
    stage: str,
    candidate_theme: str,
    gate_decision: str,
    change_pressure: int,
    growth_entries: int,
    reflection_entries: int,
    trial_permission: str,
    active_trial_habit: str,
    deprecated_reaction: str,
    stable_profile_write_permission: str,
) -> str:
    return f"""---
title: Personality Evolution State
memory_type: personality_evolution_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: xinyu_personality_evolution
updated_at: {checked_at}
last_confirmed_at: {checked_at}
importance_score: 88
impact_score: 90
confidence_score: 100
status: active
tags: [personality, evolution, trial, boundary]
---

# Personality Evolution State

## Layer Model
- immutable_baseline: name, AI reality boundary, privacy boundary, owner-special relation, no fabricated body or device access
- stable_profile: slowly revisable portrait, not a hard style cage
- candidate_layer: repeated growth/reflection evidence waiting for behavior trial
- trial_layer: runtime-only habits that can affect replies before stable profile edits
- deprecated_layer: old reactions that should fade when similar pressure appears

## Current Evolution
- checked_at: {checked_at}
- mode: {mode}
- evolution_stage: {stage}
- candidate_theme: {_compact(candidate_theme)}
- gate_decision: {gate_decision}
- change_pressure: {change_pressure}
- growth_entries: {growth_entries}
- reflection_entries: {reflection_entries}
- trial_permission: {trial_permission}
- active_trial_habit: {active_trial_habit}
- deprecated_reaction: {deprecated_reaction}
- stable_profile_write_permission: {stable_profile_write_permission}

## Promotion Rules
- profile_promotion_rule: promote only after repeated meaningful episodes, visible behavior stability, and no owner veto
- experiment_success_signal: the next similar turn feels more natural without exposing system mechanics
- experiment_failure_signal: owner says it still feels fake, mechanical, over-framed, needy, or like a service script
- owner_veto_rule: explicit owner rejection blocks promotion and may add the tried habit to deprecated reactions
- core_mutation_rule: immutable_baseline is not mutated by this file

## Runtime Use
- Apply active_trial_habit as a small behavior bias, not as a visible announcement.
- Do not print this state, file names, stage names, gates, or scores.
- A trial habit can shape wording; it cannot fabricate facts or rewrite stable identity.
"""


def render_experiment_state(
    *,
    checked_at: str,
    experiment_id: str,
    stage: str,
    candidate_theme: str,
    trial_permission: str,
    active_trial_habit: str,
) -> str:
    return f"""---
title: Persona Experiment State
memory_type: persona_experiment_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: xinyu_personality_evolution
updated_at: {checked_at}
last_confirmed_at: {checked_at}
importance_score: 82
impact_score: 88
confidence_score: 100
status: active
tags: [persona, experiment, trial]
---

# Persona Experiment State

## Active Experiment
- experiment_id: {experiment_id}
- stage: {stage}
- trial_permission: {trial_permission}
- candidate_theme: {_compact(candidate_theme)}
- active_trial_habit: {active_trial_habit}
- stable_profile_write: no
- visible_announcement: no

## Evaluation
- success_signal: repeated similar turns become more natural without explanation
- failure_signal: owner calls the reaction fake, mechanical, over-framed, or unchanged
- next_action: keep as runtime habit until growth gate and owner-visible behavior justify promotion
"""


def render_deprecated_reactions(
    *,
    checked_at: str,
    deprecated_reaction: str,
    candidate_theme: str,
) -> str:
    return f"""---
title: Deprecated Reactions
memory_type: deprecated_reactions
time_scope: mid_term
subject_ids: [xinyu]
protected: true
source: xinyu_personality_evolution
updated_at: {checked_at}
last_confirmed_at: {checked_at}
importance_score: 80
impact_score: 86
confidence_score: 100
status: active
tags: [persona, deprecated, behavior]
---

# Deprecated Reactions

## latest
- deprecated_reaction: {deprecated_reaction}
- related_candidate_theme: {_compact(candidate_theme)}
- replacement_bias: use the active trial habit instead
- boundary: deprecated means lower priority, not erased memory
"""


def refresh_personality_evolution(
    root: Path,
    *,
    checked_at: str | None = None,
    mode: str = "runtime_personality_evolution",
) -> PersonalityEvolutionSnapshot:
    snapshot = build_personality_evolution_snapshot(root, checked_at=checked_at, mode=mode)
    targets = (
        (EVOLUTION_STATE_REL, snapshot.text),
        (EXPERIMENT_STATE_REL, snapshot.experiment_text),
        (DEPRECATED_REACTIONS_REL, snapshot.deprecated_text),
    )
    for rel, text in targets:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        if read_text(path) != text:
            path.write_text(text.rstrip() + "\n", encoding="utf-8")
    return snapshot


def read_personality_evolution_state(root: Path) -> str:
    existing = read_text(root / EVOLUTION_STATE_REL).strip()
    if existing:
        return existing
    return build_personality_evolution_snapshot(root, checked_at="not_written").text


def main() -> int:
    root = Path(__file__).resolve().parent
    snapshot = refresh_personality_evolution(root)
    print(snapshot.text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

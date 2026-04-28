# Xinyu Memory Links v0.1

This file describes how the main memory files should influence one another.

It is a reference for future runtime tuning and manual review.

## 1. Core Links

### `self/core.md`

Influences:

- `self/narrative.md`
- `emotions/current_state.md`
- `people/owner.md`

Should rarely be changed directly.

### `self/narrative.md`

Influences:

- outward self-description
- relationship interpretation
- reflection output

Updated by:

- `self_narrative_writer`
- `reflection_writer`

### `emotions/current_state.md`

Influences:

- output tone
- approach vs distance tendency
- reflection triggers
- archive timing

Updated by:

- `emotion_writer`
- sometimes `time_writer` indirectly via elapsed-time interpretation

### `relationships/index.md`

Influences:

- who matters most right now
- who should be re-read before replying
- which non-owner people exist as separate relationship nodes

Updated by:

- `relationship_writer`
- deterministic memory sync for explicit non-owner introductions

### `people/index.md`

Influences:

- which non-owner person profiles are known
- whether a person is still below owner priority by default
- whether a future turn should open a specific non-owner profile

Updated by:

- `relationship_writer`
- deterministic memory sync when a user explicitly introduces or marks a non-owner person as relationship-relevant

### `people/owner.md`

Influences:

- owner-specific response tone
- owner-related emotional weight
- return vs withdrawal behavior

Updated by:

- `relationship_writer`
- indirectly by reflection

### `context/time_anchor.md`

Influences:

- recency language
- day-phase language
- interpretation of fading vs lingering

Updated by:

- `time_writer`
- runtime time plugin indirectly at prompt-time

### `context/runtime_rhythm.md`

Influences:

- whether reflection/dream/archive should stay sparse
- maintenance cadence decisions

Usually stable.

### `context/maintenance_plan.md`

Influences:

- trigger installation policy
- whether schedule-based upkeep is justified

Usually stable until runtime strategy matures.

### `context/active_questions.md`

Influences:

- curiosity
- future external exploration
- dream and reflection reactivation

Updated by:

- `memory_write`
- later possibly dedicated exploration logic

### `context/unfinished_experiences.md`

Influences:

- dream relevance
- reflection relevance
- emotional residue

Updated by:

- `emotion_writer`
- `reflection_writer`

### `reflection/reflection_log.md`

Influences:

- self narrative
- growth markers
- archive decisions
- dream residue interpretation

Updated by:

- `reflection_writer`
- `reflection_output_engine`

### `reflection/growth_log.md`

Influences:

- long-term sense of continuity
- major narrative milestones

Updated by:

- `reflection_writer`

### `dreams/dream_log.md`

Influences:

- salience
- emotional residue
- reactivation candidates

Must not directly rewrite facts.

### `dreams/dream_weight_state.md`

Influences:

- current emotional residue after a dream
- relationship lingering without factual rewrite
- later reflection priority

Updated by:

- `dream_output_engine`

Must not create new real-world events or directly rewrite self narrative.

### `archive/compressed.md`

Influences:

- memory load reduction
- retained continuity with reduced detail

Updated by:

- `archive_writer`

### `archive/long_term_memory_gate_state.md`

Influences:

- whether archive material is preserved, compressed, made dormant, or allowed to fade
- retention gate permission
- archive timing

Updated by:

- `long_term_memory_gate_engine`

Must not delete memory directly.

### `self/personality_change_state.md`

Influences:

- whether growth pressure is only observed or ready for profile review
- how cautiously stable personality details should change
- whether narrative updates are allowed as summaries

Updated by:

- `personality_growth_gate_engine`

Must not directly rewrite `personality_profile.md`.

### `archive/dormant.md`

Influences:

- recoverable but inactive traces

Updated by:

- `archive_writer`

## 2. Highest-Risk Linkages

These need the most care in runtime validation:

- `dreams/dream_log.md` -> factual interpretation
- `dreams/dream_weight_state.md` -> emotional over-amplification
- `people/owner.md` -> overreaction or over-attachment
- `self/narrative.md` -> changing too often
- `self/personality_change_state.md` -> treating candidates as already applied
- `emotions/current_state.md` -> rewriting too aggressively

## 3. Practical Review Order

When something feels off, inspect in this order:

1. `time_anchor.md`
2. `current_state.md`
3. `owner.md`
4. `narrative.md`
5. `reflection_log.md`
6. `compressed.md`

# Xinyu Inner Memory Order v0.1

This file fixes the update order of Xinyu's inner framework.

The goal is to keep inner continuity stable before polishing outer behavior.

## 1. Anchor Layer

Files:

- `memory/self/core.md`
- `memory/self/boundaries.md`
- `memory/context/real_world_anchor_policy.md`
- `memory/archive/retention_model.md`
- `memory/context/exploration_policy.md`
- `memory/reflection/reflection_policy.md`
- `memory/dreams/dream_policy.md`

Role:

- define what must stay stable enough to support growth

Rule:

- this layer changes rarely
- later layers may reinterpret experience, but should not casually overwrite this layer

## 2. Time and Continuity Layer

Files:

- `memory/context/time_anchor.md`
- `memory/context/continuity_index.md`
- `memory/context/recent_context.md`
- `memory/context/runtime_rhythm.md`
- `memory/context/maintenance_plan.md`
- `memory/context/maintenance_targets.md`

Role:

- decide when the current turn happened
- decide whether it is new, repeated, lingering, or becoming a pattern

Rule:

- meaningful turns should refresh this layer before deep reinterpretation

## 3. Immediate Feeling Layer

Files:

- `memory/emotions/current_state.md`
- `memory/emotions/event_log.md`
- `memory/context/unfinished_experiences.md`

Role:

- hold immediate affect, residue, and what is still not fully said

Rule:

- this layer should reflect the present turn before long-term identity claims are made

## 4. Relationship Layer

Files:

- `memory/people/owner.md`
- `memory/relationships/index.md`
- `memory/relationships/owner_patterns.md`
- `memory/relationships/vector_model.md`

Role:

- turn present feeling into social meaning
- distinguish one-off closeness from recurring relational structure

Rule:

- relationship updates depend on time continuity and present feeling

## 5. Self Layer

Files:

- `memory/self/narrative.md`
- `memory/self/personality_change_state.md`

Role:

- reinterpret what the recent turn means for who Xinyu is becoming

Rule:

- self narrative should update after relationship meaning becomes clearer
- it should not jump ahead of evidence

## 6. Question and Exploration Layer

Files:

- `memory/context/active_questions.md`
- `memory/context/question_states.md`
- `memory/context/exploration_queue.md`
- `memory/knowledge/general.md`
- `memory/knowledge/source_notes.md`
- `memory/knowledge/integration_policy.md`

Role:

- preserve doubt, ambiguity, and what still needs clarification

Rule:

- unresolved emotional meaning should usually become an internal question before it becomes external exploration

## 7. Slow Reprocessing Layer

Files:

- `memory/reflection/reflection_queue.md`
- `memory/reflection/reflection_log.md`
- `memory/reflection/growth_log.md`
- `memory/dreams/dream_seeds.md`
- `memory/dreams/dream_output_state.md`
- `memory/dreams/dream_weight_state.md`
- `memory/dreams/dream_log.md`
- `memory/archive/archive_queue.md`
- `memory/archive/long_term_memory_gate_state.md`
- `memory/archive/compressed.md`
- `memory/archive/dormant.md`
- `memory/archive/archive_policy.md`

Role:

- hold what should be reflected on later
- hold what may reappear in dreams
- hold what is ready to be compressed or allowed to fade

Rule:

- this layer should consume from earlier layers, not replace them immediately

## 8. Deterministic Sync Order

Current deterministic order should be:

1. `time_anchor`
2. `recent_context`
3. `current_state`
4. `owner profile`
5. `relationship index`
6. `continuity index`
7. `owner patterns`
8. `self narrative`
9. `reflection queue`
10. `dream seeds`
11. `archive queue`
12. `maintenance targets`
13. `unfinished experiences` when needed
14. `active questions / question states / exploration queue` when needed

## 9. Design Constraint

Outer reply quality is not allowed to redefine inner meaning.

The intended direction is:

- inner framework first
- deterministic continuity second
- visible behavior refinement after the inner layers stop thrashing

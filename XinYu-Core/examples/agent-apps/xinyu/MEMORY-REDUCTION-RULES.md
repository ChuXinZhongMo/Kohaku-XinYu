# XinYu Memory Reduction Rules

Status: active engineering contract.

These rules translate the 2026-05-17 neuroscience-inspired review into
XinYu-specific implementation constraints. They are engineering rules only;
they do not claim biological memory, sentience, or real emotion.

The source-backed engineering rule table lives in
`xinyu_neuro_memory_rules.py`; the human-readable companion note is
`NEURO-INSPIRED-ENGINEERING-RULES.md`.

## 1. Index, Do Not Dump

Long-lived memory should store compact indexes, not transcript-sized prompt
payloads.

Each durable item should prefer:

- source reference
- short summary
- why it was admitted
- confidence
- last touched time
- privacy / owner scope

`xinyu_living_memory_recall.py` is the recall owner. Its single live algorithm
entry is `run_living_memory_recall_algorithm`: current turn -> sparse route ->
candidate recall -> need rerank -> compact prompt block -> buckets -> optional
safe trace log. It should return compact source-indexed context, not raw chat
dumps.

## 2. Recall By Turn Goal

Recall scoring must include the current turn goal.

Examples:

- technical work should prefer project, runtime, and task memory
- relationship repair should prefer recent owner-facing residue and corrections
- daily care should prefer current state and immediate context
- direct recall should prefer source-indexed memory and uncertainty notes

Irrelevant lanes should stay quiet even if their memories are emotionally
salient.

## 3. Stable Writes Need Evidence

Stable memory rewrites require at least one explicit gate:

- owner correction
- repeated pattern
- owner-approved summary
- high prediction error
- reflection-confirmed residue

A single intense turn can create residue or a review candidate. It must not
rewrite stable self, owner, relationship, emotion, or knowledge layers by
itself.

## 4. Emotion Modulates, It Does Not Prove

Emotion and pressure state can change:

- priority
- decay rate
- recall bias
- initiative threshold
- visible voice pressure

Emotion alone cannot create factual memory. Every fact needs an external event,
owner statement, source reference, or explicit review note.

## 5. Recent Context Becomes Events

Recent context should compress into event slots and repeated patterns rather
than grow as a continuous log.

Preferred event fields:

- event id
- boundary reason
- actors
- goal
- affect / pressure
- unresolved points
- promoted or dormant status

Repeated low-value events should merge into a pattern summary.

## 6. Forgetting Is Maintenance

The default maintenance posture is decay unless promoted.

Runtime traces, dream seeds, archive candidates, and temporary sidecars should
be demoted or consumed unless a current goal, repeated owner signal, or review
gate proves they still matter.

## 7. Dream And Replay Are Not Facts

Dream, replay, and reflection output can change:

- priority
- questions to reflect on
- summary wording
- candidate confidence

They cannot create reality facts, rewrite the timeline, or restore deleted
facts without source evidence.

## Validation Anchors

Use these when changing recall, stable writes, dream/reflection/archive, or
persona pressure:

- `tests/test_living_memory_recall.py`
- `tests/test_neuro_memory_rules.py`
- `tests/test_retrieval_need_reranker.py`
- `tests/test_recent_context_guard.py`
- `tests/smoke/dialogue/integration/behavior_regression_smoke.py`
- `tests/smoke/dialogue/integration/phase3_lived_session_smoke.py`
- `tests/smoke/life/integration/dream_weight_smoke.py`
- `tests/smoke/life/integration/dream_reflection_growth_cycle_smoke.py`
- `tests/smoke/memory/integration/long_term_memory_gate_smoke.py`
- `tests/smoke/memory/integration/memory_pressure_smoke.py`
- `tests/smoke/life/integration/dormancy_reactivation_smoke.py`

When a smoke can mutate local state, use its `--restore-after` option or run it
through `smoke_run.py --restore-after` if supported.

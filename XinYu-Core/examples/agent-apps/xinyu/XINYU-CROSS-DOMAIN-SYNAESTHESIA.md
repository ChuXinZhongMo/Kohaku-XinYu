# XinYu Cross-Domain Synaesthesia Ledger

Status: Batch A registry seed.

This ledger turns cross-domain inspiration into testable XinYu engineering
rules. "Synaesthesia" here means mechanism transfer, not sensory decoration or
biological overclaiming.

## Contract

Every useful entry must answer:

- What mature mechanism does the outside field offer?
- Which XinYu problem does it address?
- Where can it land in the existing simplified runtime?
- What is the smallest test?
- What boundary prevents metaphor from becoming fake biology or bloat?

The registry source of truth is:

- `stores/cross_domain_synaesthesia_registry.json`

## Runtime Spine

The cross-domain track feeds the existing spine:

```text
current owner turn
-> turn triage gate
-> canonical living memory recall
-> temporal context binding
-> Scene Frame
-> life reply policy
-> emotion council modulation
-> final visible reply guard
-> response error loop / replay candidate
-> memory immune gate for write candidates
```

It must not create a second memory recall algorithm.

## Adopted Baseline

### Neuroscience-Inspired Memory Rules

Mechanism:

- compact indexing rather than dumping full traces.
- goal-gated recall.
- temporal binding.
- mismatch-gated reconsolidation.
- emotion as modulation, not fact.
- sleep/replay as weight, not reality rewrite.

XinYu mapping:

- `xinyu_neuro_memory_rules.py`
- `xinyu_living_memory_recall.py`
- `xinyu_temporal_memory_context.py`
- `xinyu_emotion_council.py`

Boundary:

- These are engineering analogies only.
- They do not imply biological memory, consciousness, or real emotion.

## Tier 1 Planned Mechanisms

### Control Theory / Cybernetics

Mechanism:

- feedback loop, error classification, correction, overcorrection guard.

XinYu problem:

- reply failures are often fixed locally without a durable correction loop.

Landing:

- `xinyu_response_error_loop.py`
- final guard / expression learning / replay candidate queue.

Small test:

- owner says the previous answer missed the task -> `task_miss`.
- owner says tone is wrong -> `tone_miss`.
- owner corrects a recalled fact -> `memory_miss`.

Boundary:

- One correction cannot rewrite stable personality.

### Medical Triage

Mechanism:

- route urgent/important cases before treatment details.

XinYu problem:

- short commands and mixed turns need priority sorting before recall/tool/action.

Landing:

- `xinyu_turn_triage_gate.py`
- Scene Frame provider input.

Small test:

- "continue/start/next" resumes the active task when a plan or worklog exists.
- explicit correction outranks stale memory.
- low-energy owner state suppresses optional expansion.

Boundary:

- triage advises priority; current owner text still wins.

### Immune System / Danger Theory

Mechanism:

- danger signals, quarantine, tolerance, inflammation control.

XinYu problem:

- external material, group chat, stale memory, or hallucinated replies can
  contaminate stable memory.

Landing:

- `xinyu_memory_immune_gate.py`
- memory candidate extractor.
- public dataset/source material importers.

Small test:

- group-only content cannot become owner-private memory.
- external article cannot rewrite persona or relationship memory.
- owner explicit preference can enter review.

Boundary:

- quarantine is not deletion; learning must still be possible after review.

### Allostasis / Slow Predictive State

Mechanism:

- slow regulation that predicts needs before a crisis.

XinYu problem:

- fatigue, guardedness, curiosity, and closeness can reset too quickly between turns.

Landing:

- `xinyu_slow_state_modulator.py`
- life reply policy.
- emotion council.
- proactive request threshold.

Small test:

- night-shift fatigue persists briefly and decays.
- repeated owner dismissal raises proactive threshold.

Boundary:

- slow state modulates reply energy; it cannot create facts.

### Ecology / Gardening

Mechanism:

- niche, competition, dormancy, pruning, succession, invasive pressure.

XinYu problem:

- modules and memories accumulate unless each has a role and retirement rule.

Landing:

- `ops/validation/module_ecology_audit.py`
- memory pruning policy.

Small test:

- referenced modules cannot be delete candidates.
- duplicate module families become merge candidates.

Boundary:

- no destructive delete without reference evidence and recovery path.

## Tier 2 Candidate Mechanisms

### Legal / Evidence Systems

Mechanism:

- evidence grade, testimony, review, appeal, reversal.

Landing:

- `memory_evidence_grade`
- memory immune gate / memory self-review.

Small test:

- owner explicit statement outranks inference.
- emotion residue cannot become fact.

### Library Science / Faceted Classification

Mechanism:

- facets, controlled vocabulary, catalog metadata.

Landing:

- `memory_facet_index`
- memory/library/cases/runtime metadata.

Small test:

- retrieval can filter by scope, sensitivity, time, source, and use case before
  keyword fallback.

### Information Foraging

Mechanism:

- information scent, expected gain, search cost.

Landing:

- `retrieval_scent_budget`
- recall and external search continuation policy.

Small test:

- obvious direct answer avoids unnecessary retrieval.
- ambiguous recall follows high-scent evidence.

### High Reliability / Aviation Safety

Mechanism:

- near-miss logging, checklist, preoccupation with failure.

Landing:

- `near_miss_replay_queue`
- final guard / bridge errors / memory pollution incidents.

Small test:

- serious guard failure records redacted replay metadata.

### Distributed Cognition

Mechanism:

- cognition distributed across person, artifacts, tools, and environment.

Landing:

- `distributed_context_map`
- Desktop, QQ, Codex, attachment, memory role mapping.

Small test:

- current turn records which external artifact participates in the cognitive loop.

## Tier 3 Watchlist

- Drama / literature: useful for living-surface replay eval, risky if turned into scripts.
- Game AI: useful for initiative behavior state, risky if it creates owner-facing quest spam.
- Operating systems: useful for dependency boundaries, risky if it becomes naming churn.
- Supply chain / queueing: useful for backpressure, risky if dashboards outrun behavior.
- Education / scaffolding: useful for answer depth, risky if it becomes patronizing.

## Next Batch

Recommended next batch:

1. Use the registry to select `medical_triage`.
2. Implement `xinyu_turn_triage_gate.py`.
3. Add replay tests for short owner commands and mixed-priority turns.

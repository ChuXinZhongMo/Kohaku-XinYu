# Memory Event Sourcing And Consistency Plan

status: phase_c_started
created_at: 2026-04-28
scope: raw event preservation, atomic claims, summary coverage, and consistency gates

## 1. Purpose

This workstream addresses information loss caused by model-authored memory
summaries. The goal is not to make summaries longer. The goal is to make every
summary a derived, checkable view over preserved source events and typed claims.

The target pipeline is:

```text
Raw Event -> Structured Event -> Atomic Claim -> Candidate Memory -> Summary View -> Stable Memory
```

Stable memory must never depend on an untraceable natural-language summary.

## 2. Core Principles

- Raw events are append-only source material.
- Structured events classify the raw event without replacing it.
- Atomic claims are the smallest memory units that can be checked.
- Summaries are index views, not authority.
- Stable memory accepts only claims with evidence and gate approval.
- Dream, group, non-owner, source-candidate, and owner-private material keep
  separate routing boundaries.
- Compression must record what was retained, discarded, and blocked from
  discard.

## 3. Data Layers

### Raw Events

Target file:

```text
memory/events/raw_events.jsonl
```

Required fields:

- `event_id`
- `timestamp`
- `source_channel`
- `actor_scope`
- `raw_text`
- `raw_hash`
- `privacy_scope`

Raw events preserve the original text or the highest-fidelity local transcript
available to the adapter. Later layers may redact or summarize, but they must
cite raw event ids.

### Structured Events

Target file:

```text
memory/events/structured_events.jsonl
```

Required fields:

- `structured_id`
- `event_id`
- `event_kind`
- `turn_mode`
- `allowed_memory_layers`
- `blocked_memory_layers`
- `salience`
- `routing_notes`

Structured events decide what the event is allowed to become. For example,
priority learning group material may become a source candidate, but it may not
become owner relationship memory.

### Atomic Claims

Target file:

```text
memory/events/atomic_claims.jsonl
```

Required fields:

- `claim_id`
- `claim_type`
- `subject`
- `predicate`
- `object`
- `status`
- `target_memory_layer`
- `evidence_event_ids`
- `evidence_spans`
- `confidence`

Claim types are deliberately narrow: `fact`, `preference`, `emotion`,
`relationship_residue`, `dream_residue`, `source_candidate`,
`voice_correction`, `question`, and `system_state`.

### Summary Views

Target file:

```text
memory/events/summary_views.jsonl
```

Required fields:

- `summary_id`
- `summary_text`
- `retained_claim_ids`
- `source_event_ids`
- `loss_notes`
- `discarded_signals`
- `blocked_from_discard`

Every summary must say what it kept and what it knowingly did not keep. If it
cannot cite source events, it cannot feed stable memory.

## 4. Consistency Gate

The gate checks four categories.

### Reference Integrity

- Every structured event points to an existing raw event.
- Every claim points to existing evidence events.
- Every summary points to existing claims and source events.
- Summary source events cover the evidence events of retained claims.

### Source Boundary

- Dream material cannot become factual memory.
- Group and non-owner material cannot write owner relationship memory.
- Source candidates cannot become stable knowledge without source comparison
  and learner integration.
- Owner-private material can create relationship or voice candidates, but still
  needs the relevant writer/growth gate before stable profile mutation.

### Evidence Span Check

- Evidence spans must reference an existing event.
- If a span includes text, the text must occur in the raw event text.
- If start/end offsets are present, they should match the cited text.

### Coverage Check

- Summaries must include retained claims, source events, loss notes, discarded
  signals, and blocked-from-discard signals.
- High-value signals such as owner corrections, relationship hurt/return,
  source URLs, and explicit preferences must be blocked from discard unless a
  higher gate explicitly permits fading.

## 5. Rollout Phases

### Phase A: Sidecar Gate

Create the event model and run consistency checks on fixtures only. No runtime
memory writer is changed.

Acceptance:

- Valid owner/private and group/source-candidate fixtures pass.
- Invalid group-to-owner-relationship and uncited-summary fixtures fail.
- The gate writes `memory/events/consistency_gate_state.md`.

### Phase B: Adapter Event Capture

Route QQ private, group observe, and learning ingest events into raw and
structured JSONL sidecars.

Acceptance:

- Existing chat behavior stays unchanged.
- Priority passive learning groups become raw events and source candidates only.
- Owner private corrections can become review-only voice or preference claims.

### Phase C: Summary Coverage Before Archive

Archive output must cite summary views and retained claims before compression.
Coverage is enforced only for archive queue items that explicitly opt in with
`coverage_required: true` or cite `source_event_ids` / `retained_claim_ids`.
Legacy archive candidates without those markers remain compatible until they are
migrated.
Runtime sync now also tries to create event-sourced archive candidates for
selective-memory material. When the source turn already exists in sidecars, the
queue item is born with `coverage_required`, `source_event_ids`,
`retained_claim_ids`, and `summary_ids`.

Acceptance:

- Archive commit is blocked when a summary lacks source coverage.
- New selective-memory archive candidates carry source trace ids when sidecars
  exist.
- Event-sourced archive items must cite source events and retained claims.
- Covering summaries must keep loss notes, discarded signals, and
  blocked-from-discard signals.
- Dormant memory keeps source item and wake conditions.

### Phase D: Stable Writer Integration

Stable writers accept typed claims instead of free-form summaries where possible.

Acceptance:

- Stable memory changes remain source-traceable.
- Corrections can invalidate or supersede individual claims.
- Dream/reflection/archive can change weights and salience without becoming
  untraceable fact writes.

## 6. Non-Goals

- This does not preserve every trivial turn forever.
- This does not expose hidden chain-of-thought.
- This does not make group chat owner memory.
- This does not bypass source, learning, privacy, or personality-review gates.

## 7. First Implementation Slice

- `custom/memory_event_schema.py`
- `custom/memory_consistency_gate_engine.py`
- `custom/summary_coverage_engine.py`
- `memory/events/README.md`
- `memory_event_sourcing_smoke.py`
- `archive_queue_trace_smoke.py`
- `summary_coverage_smoke.py`

This slice validates the architecture without changing live memory mutation
behavior.

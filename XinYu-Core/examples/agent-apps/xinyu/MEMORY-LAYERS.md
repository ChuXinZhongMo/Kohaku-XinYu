# XinYu Memory Layers

XinYu separates runtime facts from durable memory. A timeout, trace, or one-off mood must not become stable memory directly.

## Layers

- Runtime trace: JSONL/state files under `runtime/`. Operational only; safe for health and debugging.
- Dialogue tail: short recent session context. Useful for continuity, not a durable belief store.
- Event sourcing: structured turn events used to reconstruct what happened.
- Candidate memory: proposed memories with provenance, risk flags, source turn id, source message ids, and review status.
- Approved long-term memory: durable memory that passed the appropriate owner or gate review.
- Seed memory: repository-shipped baseline memory under `memory-seeds/`; public and reviewable.

## Promotion Rule

Only candidate memory can be promoted. Runtime trace, timeout notes, health snapshots, and gateway errors are evidence, not memory.

High-risk candidates involving identity, relationship, permissions, personality, credentials, or long-term owner preference require owner review.

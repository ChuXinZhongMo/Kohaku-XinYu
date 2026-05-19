# XinYu P34 Dialogue Archive Unguarded Timestamp Guard Batch

Date: 2026-05-19

## Goal

Reduce `unguarded_candidate` findings for one capability group: `xinyu_dialogue_archive.py`.

This group is high priority because dialogue archive timestamps are the basis for time-aware recall, session continuity, and later memory candidate review.

## Completed

- Added local ISO parsing and `_timestamp_or_now_iso`.
- Guarded `archive_message` caller-provided `created_at` with payload-event fallback.
- Guarded `archive_dialogue_turn` user and assistant message timestamps through the same normalizer.
- Tightened `timestamp_writer_guard_audit.py` so SQL destination fields and `row[...]` reads are classified as `reference_only`.
- Added audit coverage for SQL targets and row reads.

## Result

- `xinyu_dialogue_archive.py` unguarded candidates: 5 -> 0.
- Global `unguarded_candidate`: 44 -> 36.
- Direct writer candidates remain: 0.

Post-P34 timestamp writer guard audit counts:

```json
{
  "guarded": 324,
  "reference_only": 120,
  "report_metadata_candidate": 66,
  "template_timestamp_candidate": 167,
  "unguarded_candidate": 36
}
```

## Validation

- `python -m py_compile xinyu_dialogue_archive.py ops/validation/timestamp_writer_guard_audit.py`: passed.
- Focused pytest:
  `tests/test_timestamp_writer_guard_audit.py tests/test_memory_event_time_provenance.py tests/test_dialogue_semantic_backend.py tests/test_context_retrieval_owner_scenarios.py -q`
  passed: 17 passed.
- Focused smokes passed:
  `tests/smoke/dialogue/dialogue_archive_smoke.py`,
  `tests/smoke/memory/context_retrieval_smoke.py`.
- Full pytest passed: 576 passed.
- Quick smoke passed: `smoke_run.py --group quick --restore-after`.
- `git diff --check` passed with LF/CRLF warnings only.

## Next

Continue P35 against the next largest remaining `unguarded_candidate` group:

- `xinyu_bridge_observation.py`: 4 candidates
- `xinyu_proactivity_scorer.py`: 4 candidates
- `xinyu_v1/app.py`: 3 candidates
- `xinyu_bridge_action_routes.py`: 3 candidates

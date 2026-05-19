# XinYu P35 Bridge Observation Unguarded Timestamp Guard Batch

Date: 2026-05-19

## Goal

Reduce `unguarded_candidate` findings for one capability group: `xinyu_bridge_observation.py`.

This group is high priority because bridge observation writes group-learning observation files and real-life input event surfaces.

## Completed

- Normalized `observed_at` into `safe_observed_at` before creating group-learning observation headers.
- Normalized `observed_at` into `safe_observed_at` before creating real-life input event headers.
- Kept existing `_timestamp_or_now_iso` behavior for update paths and event blocks.

## Result

- `xinyu_bridge_observation.py` unguarded candidates: 4 -> 0.
- Global `unguarded_candidate`: 36 -> 32.
- Direct writer candidates remain: 0.

Post-P35 timestamp writer guard audit counts:

```json
{
  "guarded": 328,
  "reference_only": 120,
  "report_metadata_candidate": 66,
  "template_timestamp_candidate": 167,
  "unguarded_candidate": 32
}
```

## Validation

- `python -m py_compile xinyu_bridge_observation.py`: passed.
- Focused pytest:
  `tests/test_learning_observe_paths.py tests/test_timestamp_writer_guard_audit.py -q`
  passed: 12 passed.
- Focused smoke passed: `tests/smoke/runtime/service_boundary_smoke.py`.
- Full pytest passed: 576 passed.
- Quick smoke passed: `smoke_run.py --group quick --restore-after`.
- `git diff --check` passed with LF/CRLF warnings only.

## Next

Continue P36 against the next largest remaining `unguarded_candidate` group:

- `xinyu_proactivity_scorer.py`: 4 candidates
- `xinyu_v1/app.py`: 3 candidates
- `xinyu_bridge_action_routes.py`: 3 candidates

# XinYu P51 GitHub Autonomous Learning Timestamp Guard Batch

Date: 2026-05-19

## Goal

Reduce `unguarded_candidate` findings for one capability group:
`custom/github_autonomous_learning_engine.py`.

This module stages public GitHub repository candidates. Candidate `last_seen_at`
and related merge metadata must use normalized event time before the material
can move further through the learning pipeline.

## Completed

- Guarded `merge_candidate(... updated_at=...)` with `_timestamp_or_now_iso`.
- Preserved existing `checked_at` normalization and candidate merge behavior.

## Result

- `custom/github_autonomous_learning_engine.py` unguarded candidates: 1 -> 0.
- Global `unguarded_candidate`: 4 -> 3.
- Direct writer candidates remain: 0.

Post-P51 timestamp writer guard audit counts:

```json
{
  "guarded": 357,
  "reference_only": 124,
  "report_metadata_candidate": 61,
  "template_timestamp_candidate": 167,
  "unguarded_candidate": 3
}
```

Audit outputs:

- `worklog/xinyu-timestamp-writer-guard-audit-post-p51-2026-05-19.json`
- `worklog/xinyu-timestamp-writer-guard-audit-post-p51-2026-05-19.md`

## Validation

- `python -m py_compile custom/github_autonomous_learning_engine.py`: passed.
- Focused pytest: `tests/test_timestamp_writer_guard_audit.py -q` passed, 13 passed.
- Focused smoke: `tests/smoke/learning/github_autonomous_learning_smoke.py` passed.
- Full pytest passed: 579 passed.
- Quick smoke passed: `smoke_run.py --group quick --restore-after`.
- `git diff --check` passed with LF/CRLF warnings only.

## Next

Continue P52 through the remaining one-candidate groups:

- `xinyu_bridge_v1_routes.py`
- `xinyu_interaction_journal.py`
- `xinyu_initiative_orchestrator.py`

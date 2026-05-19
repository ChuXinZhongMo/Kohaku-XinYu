# XinYu P42 Dialogue Working Memory Timestamp Condition Classifier Batch

Date: 2026-05-19

## Goal

Reduce false-positive `unguarded_candidate` findings for one capability group:
`xinyu_dialogue_working_memory.py`.

This group was not writing raw event time. The remaining hits were timestamp-only
conditionals such as `if recorded_at:`, used to decide retention behavior after
an earlier timestamp had already been read.

## Completed

- Added `TIMESTAMP_CONDITION_RE` to the timestamp writer guard audit.
- Classified timestamp-only conditionals as `reference_only` with
  `schema_or_reference` line kind.
- Added a regression test proving timestamp conditionals stay reference-only.
- Fixed the test fixture so it does not emit a timestamp-shaped dict while
  testing a read-only conditional.

## Result

- `xinyu_dialogue_working_memory.py` unguarded candidates: 2 -> 0.
- Global `unguarded_candidate`: 16 -> 14.
- Direct writer candidates remain: 0.

Post-P42 timestamp writer guard audit counts:

```json
{
  "guarded": 347,
  "reference_only": 122,
  "report_metadata_candidate": 63,
  "template_timestamp_candidate": 167,
  "unguarded_candidate": 14
}
```

Audit outputs:

- `worklog/xinyu-timestamp-writer-guard-audit-post-p42-2026-05-19.json`
- `worklog/xinyu-timestamp-writer-guard-audit-post-p42-2026-05-19.md`

## Validation

- `python -m py_compile ops/validation/timestamp_writer_guard_audit.py xinyu_dialogue_working_memory.py`: passed.
- Focused pytest: `tests/test_timestamp_writer_guard_audit.py -q` passed, 12 passed.
- Focused smoke: `tests/smoke/dialogue/dialogue_tail_retention_smoke.py` passed.
- Full pytest passed: 578 passed.
- Quick smoke passed: `smoke_run.py --group quick --restore-after`.
- `git diff --check` passed with LF/CRLF warnings only.

## Next

Continue P43 against one remaining 2-candidate group:

- `xinyu_self_code_watchdog.py`: 2 candidates
- `xinyu_initiative_research_shadow.py`: 2 candidates

Then clear the remaining 1-candidate groups.

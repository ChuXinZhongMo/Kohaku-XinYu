# XinYu P52 Bridge V1 Routes Timestamp Guard Batch

Date: 2026-05-19

## Goal

Reduce `unguarded_candidate` findings for one capability group:
`xinyu_bridge_v1_routes.py`.

The v1 owner-simple canary publishes a desktop chat-finished event after
intercepting a turn. Its `started_at` field should be normalized at the publish
boundary.

## Completed

- Added local `_timestamp_or_now_iso`.
- Guarded desktop chat-finished `started_at` with that helper.
- Preserved v1 canary routing, readiness observation, and reply guard behavior.

## Result

- `xinyu_bridge_v1_routes.py` unguarded candidates: 1 -> 0.
- Global `unguarded_candidate`: 3 -> 2.
- Direct writer candidates remain: 0.

Post-P52 timestamp writer guard audit counts:

```json
{
  "guarded": 358,
  "reference_only": 124,
  "report_metadata_candidate": 61,
  "template_timestamp_candidate": 167,
  "unguarded_candidate": 2
}
```

Audit outputs:

- `worklog/xinyu-timestamp-writer-guard-audit-post-p52-2026-05-19.json`
- `worklog/xinyu-timestamp-writer-guard-audit-post-p52-2026-05-19.md`

## Validation

- `python -m py_compile xinyu_bridge_v1_routes.py`: passed.
- Focused pytest:
  `tests/test_v1_canary_readiness.py tests/v1/test_v1_smoke_contract.py tests/test_timestamp_writer_guard_audit.py -q`
  passed: 21 passed.
- Focused smoke: `tests/smoke/bridge/bridge_renderer_guard_flags_smoke.py` passed.
- Full pytest passed: 579 passed.
- Quick smoke passed: `smoke_run.py --group quick --restore-after`.
- `git diff --check` passed with LF/CRLF warnings only.

## Next

Continue P53 through the remaining one-candidate groups:

- `xinyu_interaction_journal.py`
- `xinyu_initiative_orchestrator.py`

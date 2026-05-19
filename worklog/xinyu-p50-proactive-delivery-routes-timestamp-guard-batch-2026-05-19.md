# XinYu P50 Proactive Delivery Routes Timestamp Guard Batch

Date: 2026-05-19

## Goal

Reduce `unguarded_candidate` findings for one capability group:
`xinyu_bridge_proactive_delivery_routes.py`.

This route records proactive outbound QQ delivery into the live dialogue tail
and archive after an ack. The claim time comes from dispatch state and must be
normalized before it becomes dialogue evidence.

## Completed

- Added local `_timestamp_or_now_iso`.
- Normalized `last_claimed_at` read from proactive dispatch state.
- Guarded the dialogue-tail `recorded_at` write.
- Guarded the archive `created_at` write.

## Result

- `xinyu_bridge_proactive_delivery_routes.py` unguarded candidates: 1 -> 0.
- Global `unguarded_candidate`: 5 -> 4.
- Direct writer candidates remain: 0.

Post-P50 timestamp writer guard audit counts:

```json
{
  "guarded": 356,
  "reference_only": 124,
  "report_metadata_candidate": 61,
  "template_timestamp_candidate": 167,
  "unguarded_candidate": 4
}
```

Audit outputs:

- `worklog/xinyu-timestamp-writer-guard-audit-post-p50-2026-05-19.json`
- `worklog/xinyu-timestamp-writer-guard-audit-post-p50-2026-05-19.md`

## Validation

- `python -m py_compile xinyu_bridge_proactive_delivery_routes.py`: passed.
- Focused pytest: `tests/test_timestamp_writer_guard_audit.py -q` passed, 13 passed.
- Focused smoke: `tests/smoke/desktop/xinyu_desktop_proactive_smoke.py` passed.
- Full pytest passed: 579 passed.
- Quick smoke passed: `smoke_run.py --group quick --restore-after`.
- `git diff --check` passed with LF/CRLF warnings only.

## Next

Continue P51 through the remaining one-candidate groups:

- `custom/github_autonomous_learning_engine.py`
- `xinyu_bridge_v1_routes.py`
- `xinyu_interaction_journal.py`
- `xinyu_initiative_orchestrator.py`

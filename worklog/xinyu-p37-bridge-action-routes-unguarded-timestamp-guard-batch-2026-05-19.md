# XinYu P37 Bridge Action Routes Unguarded Timestamp Guard Batch

Date: 2026-05-19

## Goal

Reduce `unguarded_candidate` findings for one capability group: `xinyu_bridge_action_routes.py`.

This group is high priority because action-layer and action-followup routes publish finished-turn timing into the desktop/runtime bridge.

## Completed

- Added a local `_timestamp_or_now_iso` guard.
- Guarded `started_at` for action-layer publish completion.
- Guarded `started_at` for recent-action followup publish completion.
- Guarded `started_at` for action-digest followup publish completion.

## Result

- `xinyu_bridge_action_routes.py` unguarded candidates: 3 -> 0.
- Global `unguarded_candidate`: 28 -> 25.
- Direct writer candidates remain: 0.

Post-P37 timestamp writer guard audit counts:

```json
{
  "guarded": 338,
  "reference_only": 120,
  "report_metadata_candidate": 63,
  "template_timestamp_candidate": 167,
  "unguarded_candidate": 25
}
```

## Validation

- `python -m py_compile xinyu_bridge_action_routes.py`: passed.
- Focused pytest:
  `tests/test_timestamp_writer_guard_audit.py -q`
  passed: 11 passed.
- Focused smokes passed:
  `tests/smoke/bridge/bridge_memory_snapshot_smoke.py`,
  `tests/smoke/bridge/bridge_renderer_guard_flags_smoke.py`,
  `tests/smoke/initiative/self_action_gateway_smoke.py`.
- Full pytest passed: 576 passed.
- Quick smoke passed: `smoke_run.py --group quick --restore-after`.
- `git diff --check` passed with LF/CRLF warnings only.

## Next

Continue P38 against the next largest remaining `unguarded_candidate` group:

- `xinyu_v1/app.py`: 3 candidates
- `xinyu_learning_closed_loop.py`: 2 candidates
- `xinyu_initiative_research_shadow.py`: 2 candidates

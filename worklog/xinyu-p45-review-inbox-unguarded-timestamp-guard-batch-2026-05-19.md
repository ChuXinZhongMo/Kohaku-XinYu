# XinYu P45 Review Inbox Unguarded Timestamp Guard Batch

Date: 2026-05-19

## Goal

Reduce `unguarded_candidate` findings for one capability group:
`xinyu_review_inbox.py`.

The review inbox cursor is a control-plane queue artifact. Its creation time
must be normalized before later review commands use the cursor for decision
matching.

## Completed

- Guarded `_generate_locked` cursor creation by passing
  `_timestamp_or_now_iso(observed)` into `_cursor_for_items`.
- Kept cursor TTL and review queue behavior unchanged.

## Result

- `xinyu_review_inbox.py` unguarded candidates: 1 -> 0.
- Global `unguarded_candidate`: 10 -> 9.
- Direct writer candidates remain: 0.

Post-P45 timestamp writer guard audit counts:

```json
{
  "guarded": 352,
  "reference_only": 122,
  "report_metadata_candidate": 63,
  "template_timestamp_candidate": 167,
  "unguarded_candidate": 9
}
```

Audit outputs:

- `worklog/xinyu-timestamp-writer-guard-audit-post-p45-2026-05-19.json`
- `worklog/xinyu-timestamp-writer-guard-audit-post-p45-2026-05-19.md`

## Validation

- `python -m py_compile xinyu_review_inbox.py`: passed.
- Focused pytest:
  `tests/test_review_state_store.py tests/test_timestamp_writer_guard_audit.py -q`
  passed: 13 passed.
- Focused smoke: `tests/smoke/tools/xinyu_review_inbox_smoke.py` passed.
- Full pytest passed: 578 passed.
- Quick smoke passed: `smoke_run.py --group quick --restore-after`.
- `git diff --check` passed with LF/CRLF warnings only.

## Next

Continue P46 through the remaining one-candidate groups:

- `xinyu_qq_gateway.py`
- `xinyu_self_action_patch_executor.py`
- `xinyu_turn_residue.py`
- `xinyu_self_thought_loop.py`
- `xinyu_bridge_proactive_delivery_routes.py`
- `custom/github_autonomous_learning_engine.py`
- `xinyu_bridge_v1_routes.py`
- `xinyu_interaction_journal.py`
- `xinyu_initiative_orchestrator.py`

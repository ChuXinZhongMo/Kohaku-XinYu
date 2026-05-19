# XinYu P43 Self Code Watchdog Unguarded Timestamp Guard Batch

Date: 2026-05-19

## Goal

Reduce `unguarded_candidate` findings for one capability group:
`xinyu_self_code_watchdog.py`.

This group protects self-code snapshots and restore traces, so its event times
need to be normalized before they enter state, manifest, or trace outputs.

## Completed

- Normalized watchdog `observed_at` inputs through `_timestamp_or_now_iso`.
- Kept timestamp guard calls directly on manifest, state, and trace write sites
  so the writer guard audit can verify each emitted timestamp.
- Preserved existing snapshot and restore behavior.

## Result

- `xinyu_self_code_watchdog.py` unguarded candidates: 2 -> 0.
- Global `unguarded_candidate`: 14 -> 12.
- Direct writer candidates remain: 0.

Post-P43 timestamp writer guard audit counts:

```json
{
  "guarded": 349,
  "reference_only": 122,
  "report_metadata_candidate": 63,
  "template_timestamp_candidate": 167,
  "unguarded_candidate": 12
}
```

Audit outputs:

- `worklog/xinyu-timestamp-writer-guard-audit-post-p43-2026-05-19.json`
- `worklog/xinyu-timestamp-writer-guard-audit-post-p43-2026-05-19.md`

## Validation

- `python -m py_compile xinyu_self_code_watchdog.py`: passed.
- Focused pytest:
  `tests/test_self_code_watchdog.py tests/test_timestamp_writer_guard_audit.py -q`
  passed: 13 passed.
- Focused smoke: `tests/smoke/codex/self_code_watchdog_smoke.py` passed.
- Full pytest passed: 578 passed.
- Quick smoke passed: `smoke_run.py --group quick --restore-after`.
- `git diff --check` passed with LF/CRLF warnings only.

## Next

Continue P44 against `xinyu_initiative_research_shadow.py`, which still has
2 unguarded `evaluated_at` writes in `_seed_context_gate`.

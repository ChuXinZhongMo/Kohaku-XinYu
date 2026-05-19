# XinYu P36 Proactivity Scorer Unguarded Timestamp Guard Batch

Date: 2026-05-19

## Goal

Reduce `unguarded_candidate` findings for one capability group: `xinyu_proactivity_scorer.py`.

This group is high priority because proactivity candidate timestamps control freshness, expiry, repetition penalties, and owner-facing interruption timing.

## Completed

- Guarded runtime-program-awareness candidate `created_at` fields with `_timestamp_or_now_iso`.
- Guarded owner-long-idle candidate `created_at`.
- Guarded final `ProactiveCandidate.created_at` assignment.
- Left existing `_make_candidate` normalization intact so invalid source timestamps still fall back to `checked_at`.

## Result

- `xinyu_proactivity_scorer.py` unguarded candidates: 4 -> 0.
- Global `unguarded_candidate`: 32 -> 28.
- Direct writer candidates remain: 0.

Post-P36 timestamp writer guard audit counts:

```json
{
  "guarded": 335,
  "reference_only": 120,
  "report_metadata_candidate": 63,
  "template_timestamp_candidate": 167,
  "unguarded_candidate": 28
}
```

## Validation

- `python -m py_compile xinyu_proactivity_scorer.py`: passed.
- Focused pytest:
  `tests/test_initiative_orchestrator.py -q`
  passed: 19 passed.
- Focused smoke passed: `tests/smoke/initiative/proactivity_scorer_smoke.py`.
- Full pytest passed: 576 passed.
- Quick smoke passed: `smoke_run.py --group quick --restore-after`.
- `git diff --check` passed with LF/CRLF warnings only.

## Next

Continue P37 against the next largest remaining `unguarded_candidate` group:

- `xinyu_bridge_action_routes.py`: 3 candidates
- `xinyu_v1/app.py`: 3 candidates
- `xinyu_self_code_watchdog.py`: 2 candidates

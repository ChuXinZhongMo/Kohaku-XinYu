# XinYu P40 Proactive Presence Unguarded Timestamp Guard Batch

Date: 2026-05-19

## Goal

Reduce `unguarded_candidate` findings for one capability group: `xinyu_proactive_presence.py`.

This group is high priority because proactive presence controls whether XinYu may surface a short proactive message and how claim/ack times are recorded.

## Completed

- Added `_timestamp_or_now_iso`.
- Normalized `evaluated_at` in proactive presence evaluation and claim flow.
- Normalized `acked_at` in proactive QQ acknowledgement flow.
- Guarded request delivery `updated_at` writes for claim and ack updates.
- Allowed `Z` suffix timestamps in `_parse_iso`.

## Result

- `xinyu_proactive_presence.py` unguarded candidates: 2 -> 0.
- Global `unguarded_candidate`: 20 -> 18.
- Direct writer candidates remain: 0.

Post-P40 timestamp writer guard audit counts:

```json
{
  "guarded": 345,
  "reference_only": 120,
  "report_metadata_candidate": 63,
  "template_timestamp_candidate": 167,
  "unguarded_candidate": 18
}
```

## Validation

- `python -m py_compile xinyu_proactive_presence.py`: passed.
- Focused smokes passed:
  `tests/smoke/initiative/proactive_presence_smoke.py`,
  `tests/smoke/initiative/proactive_request_loop_smoke.py`,
  `tests/smoke/desktop/xinyu_desktop_proactive_smoke.py`.
- Full pytest passed: 577 passed.
- Quick smoke passed: `smoke_run.py --group quick --restore-after`.
- `git diff --check` passed with LF/CRLF warnings only.

## Next

Continue P41 against one of the remaining 2-candidate groups:

- `xinyu_learning_closed_loop.py`: 2 candidates
- `xinyu_initiative_research_shadow.py`: 2 candidates
- `xinyu_self_code_watchdog.py`: 2 candidates
- `xinyu_dialogue_working_memory.py`: 2 candidates

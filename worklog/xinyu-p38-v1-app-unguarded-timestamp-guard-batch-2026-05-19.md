# XinYu P38 V1 App Unguarded Timestamp Guard Batch

Date: 2026-05-19

## Goal

Reduce `unguarded_candidate` findings for one capability group: `xinyu_v1/app.py`.

This group is high priority because the v1 app records raw user events and visible assistant replies into the v1 memory orchestrator.

## Completed

- Added instance-level `_timestamp_or_now_iso` with ISO, numeric seconds, and numeric milliseconds support.
- Guarded raw inbound event timestamps before `MemoryEvent.from_text`.
- Reused the guarded inbound timestamp for the matching `MemoryWriteIntent`.
- Guarded assistant reply write timestamps derived from the recorded event.

## Result

- `xinyu_v1/app.py` unguarded candidates: 3 -> 0.
- Global `unguarded_candidate`: 25 -> 22.
- Direct writer candidates remain: 0.

Post-P38 timestamp writer guard audit counts:

```json
{
  "guarded": 341,
  "reference_only": 120,
  "report_metadata_candidate": 63,
  "template_timestamp_candidate": 167,
  "unguarded_candidate": 22
}
```

## Validation

- `python -m py_compile xinyu_v1/app.py`: passed.
- Focused pytest:
  `tests/test_v1_canary_readiness.py tests/v1 -q`
  passed: 29 passed.
- Full pytest passed: 576 passed.
- Quick smoke passed: `smoke_run.py --group quick --restore-after`.
- `git diff --check` passed with LF/CRLF warnings only.

## Next

Continue P39 against one of the remaining 2-candidate groups:

- `xinyu_proactive_presence.py`: 2 candidates
- `xinyu_initiative_research_shadow.py`: 2 candidates
- `xinyu_learning_closed_loop.py`: 2 candidates
- `xinyu_self_code_watchdog.py`: 2 candidates
- `xinyu_dialogue_working_memory.py`: 2 candidates
- `xinyu_bridge_turn_pipeline.py`: 2 candidates

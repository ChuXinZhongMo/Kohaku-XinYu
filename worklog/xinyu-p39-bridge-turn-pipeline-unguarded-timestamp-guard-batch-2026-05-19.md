# XinYu P39 Bridge Turn Pipeline Unguarded Timestamp Guard Batch

Date: 2026-05-19

## Goal

Reduce `unguarded_candidate` findings for one capability group: `xinyu_bridge_turn_pipeline.py`.

This group is high priority because it sits on the main pre-model turn path and publishes turn timing to sidecar/runtime surfaces.

## Completed

- Added a local `_timestamp_or_now_iso` guard.
- Guarded tinykernel shadow `observed_at`.
- Guarded runtime-repair status desktop publish `started_at`.

## Result

- `xinyu_bridge_turn_pipeline.py` unguarded candidates: 2 -> 0.
- Global `unguarded_candidate`: 22 -> 20.
- Direct writer candidates remain: 0.

Post-P39 timestamp writer guard audit counts:

```json
{
  "guarded": 343,
  "reference_only": 120,
  "report_metadata_candidate": 63,
  "template_timestamp_candidate": 167,
  "unguarded_candidate": 20
}
```

## Validation

- `python -m py_compile xinyu_bridge_turn_pipeline.py`: passed.
- Focused smokes passed:
  `tests/smoke/initiative/turn_coherence_smoke.py`,
  `tests/smoke/bridge/bridge_renderer_guard_flags_smoke.py`,
  `tests/smoke/runtime/runtime_presence_smoke.py`.
- Full pytest passed: 576 passed.
- Quick smoke passed after retry: `smoke_run.py --group quick --restore-after`.
  First quick-smoke run stopped at `mojibake_guard_smoke`; direct rerun of that smoke and the full quick group both passed without code changes.
- `git diff --check` passed with LF/CRLF warnings only.

## Next

Continue P40 against one of the remaining 2-candidate groups:

- `xinyu_self_code_watchdog.py`: 2 candidates
- `xinyu_initiative_research_shadow.py`: 2 candidates
- `xinyu_proactive_presence.py`: 2 candidates
- `xinyu_dialogue_working_memory.py`: 2 candidates
- `xinyu_learning_closed_loop.py`: 2 candidates

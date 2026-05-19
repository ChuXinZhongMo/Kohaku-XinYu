# XinYu Persona Runtime Overlay Store Boundary Batch

Date: 2026-05-18
Plan: `plan-next-2.md` Batch 4

## Completed

- Added `stores/persona_runtime_overlay.py` as the explicit owner for `memory/self/goldmark_positive_overlay.json`.
- Kept the physical JSON file at the legacy `memory/self` path as compatibility storage.
- Updated `xinyu_goldmark.py` to read/write overlay entries through the store boundary while preserving `OVERLAY_REL` and `read_goldmark_overlay`.
- Updated `xinyu_goldmark_dehydrate.py` to use the store writer for processing/done/failed/stale recovery mutations.
- Updated `xinyu_runtime_context.py` to read Goldmark runtime expression auth through the store boundary.
- Updated `stores/README.md`.
- Added `tests/test_persona_runtime_overlay_store.py`.
- Updated P0 structured memory triage so `goldmark_positive_overlay.json` now reports:
  - `decision=compat_store_owner_exists`
  - `target=stores/persona_runtime_overlay`
- Refreshed:
  - `worklog/xinyu-memory-structured-p0-triage-post-persona-overlay-store-2026-05-18.md`
  - `worklog/xinyu-memory-structured-p0-triage-post-persona-overlay-store-2026-05-18.json`

## Validation

- `.\.venv\Scripts\python.exe -m py_compile stores\persona_runtime_overlay.py xinyu_goldmark.py xinyu_goldmark_dehydrate.py xinyu_runtime_context.py tests\test_persona_runtime_overlay_store.py`
- `.\.venv\Scripts\python.exe -m pytest tests\test_persona_runtime_overlay_store.py tests\test_goldmark_mark.py tests\test_goldmark_dehydrate.py tests\test_runtime_context.py tests\test_dialogue_curiosity_bridge_injection.py tests\test_persona_runtime_contract.py tests\test_persona_runtime_boundaries.py tests\test_personality_evolution.py -q`
  - Result: 80 passed.
- `.\.venv\Scripts\python.exe -m pytest tests\test_persona_runtime_overlay_store.py tests\test_memory_structured_p0_triage.py -q`
  - Result: 5 passed.
- Focused smokes:
  - `.\.venv\Scripts\python.exe tests\smoke\voice\persona_runtime_smoke.py`
  - `.\.venv\Scripts\python.exe tests\smoke\voice\persona_stability_layers_smoke.py`
  - `.\.venv\Scripts\python.exe tests\smoke\voice\integration\persona_contract_absence_smoke.py`
  - `.\.venv\Scripts\python.exe mark_smoke_test.py`
  - Result: all passed.

## Privacy Note

- This batch did not read or print the live Goldmark overlay body.

## Remaining

- Continue `plan-next-2.md` Batch 5: full validation, change package refresh, final audit, then create `plan-next-3.md` if useful.

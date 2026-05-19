# XinYu Source Material Parser Consolidation Batch

Date: 2026-05-18
Plan: `plan-next-2.md` Batch 3

## Completed

- Added `custom/source_material_parser.py`.
- Consolidated shared material parsing concerns:
  - `## material-*` section splitting.
  - `- key: value` field extraction.
  - fixed-shape material field maps with caller-owned defaults.
  - integrated source material id extraction.
- Kept old public function names as shims:
  - `source_comparison_engine.split_material_blocks`
  - `learner_integration_engine.split_materials`
  - `source_integration_gate_engine.split_materials`
  - `learner_integration_engine.integrated_source_material_ids`
  - `source_integration_gate_engine.integrated_source_material_ids`
- Kept gate/readiness/quality decisions local to their existing engines.
- Added `tests/test_source_material_parser.py`.

## Validation

- `.\.venv\Scripts\python.exe -m py_compile custom\source_material_parser.py custom\source_comparison_engine.py custom\learner_integration_engine.py custom\source_integration_gate_engine.py tests\test_source_material_parser.py`
- `.\.venv\Scripts\python.exe -m pytest tests\test_source_material_parser.py tests\test_source_protocol_utils.py tests\test_source_material_quality.py tests\test_learning_closed_loop.py -q`
  - Result: 26 passed.
- Restore-protected smokes with body diffs disabled:
  - `.\.venv\Scripts\python.exe tests\smoke\learning\integration\source_comparison_smoke.py --restore-after --diff-lines 0`
  - `.\.venv\Scripts\python.exe tests\smoke\learning\integration\learner_integration_smoke.py --restore-after --diff-lines 0`
  - `.\.venv\Scripts\python.exe tests\smoke\learning\integration\source_reliability_gate_smoke.py --restore-after --diff-lines 0`
  - `.\.venv\Scripts\python.exe tests\smoke\learning\integration\source_learning_chain_smoke.py --restore-after --diff-lines 0`
  - Result: all exited 0.

## Recovery Note

- I initially ran the four source smokes without `--restore-after`; these smoke scripts mutate ignored `memory/**` files by design.
- The files are ignored by git, no pre-smoke snapshot was persisted by the smoke scripts when `--restore-after` is omitted, and I did not use destructive git recovery.
- I reran the same smokes with `--restore-after --diff-lines 0` and will use those flags for all remaining mutation-capable smokes.

## Remaining

- Continue `plan-next-2.md` Batch 4: add a persona runtime overlay store boundary for `memory/self/goldmark_positive_overlay.json`.

# XinYu Source Material Quality Consolidation - 2026-05-17

Status: applied as one duplicate-consolidation batch.

## Batch Scope

- Capability group: source learning / source integration quality checks.
- Goal: merge repeated claim quality heuristics into one canonical helper while
  preserving existing learner and source integration behavior.

## Completed

- Added `custom/source_material_quality.py`.
  - `claim_looks_garbled(claim)`
  - `claim_is_placeholder(claim)`
  - `claim_is_too_thin(claim)`
- Updated `custom/learner_integration_engine.py`.
  - Removed local duplicate claim quality functions.
  - Imports shared source material quality helpers.
- Updated `custom/source_integration_gate_engine.py`.
  - Removed local duplicate claim quality functions.
  - Imports shared source material quality helpers.
- Added `tests/test_source_material_quality.py`.
  - Covers placeholder/thin rejection.
  - Covers substantive plain claim acceptance.

## Validation

Passed:

```powershell
.\.venv\Scripts\python.exe -m py_compile custom\source_material_quality.py custom\learner_integration_engine.py custom\source_integration_gate_engine.py
.\.venv\Scripts\python.exe -m pytest tests\test_source_material_quality.py
.\.venv\Scripts\python.exe tests\smoke\learning\integration\learner_integration_smoke.py --restore-after --require-integration --diff-lines 0
.\.venv\Scripts\python.exe tests\smoke\learning\integration\source_reliability_gate_smoke.py --restore-after
.\.venv\Scripts\python.exe tests\smoke\learning\integration\source_quality_followup_smoke.py --restore-after --diff-lines 0
.\.venv\Scripts\python.exe tests\smoke\learning\integration\source_learning_chain_smoke.py --restore-after --diff-lines 0
git diff --check -- XinYu-Core/examples/agent-apps/xinyu/custom/source_material_quality.py XinYu-Core/examples/agent-apps/xinyu/custom/learner_integration_engine.py XinYu-Core/examples/agent-apps/xinyu/custom/source_integration_gate_engine.py XinYu-Core/examples/agent-apps/xinyu/tests/test_source_material_quality.py
```

Results:

- Focused pytest: 2 passed.
- Learning integration smoke: passed.
- Source reliability gate smoke: passed.
- Source quality follow-up smoke: passed.
- Source learning chain smoke: passed.
- Duplicate definition check:
  `rg -n "^def claim_(looks_garbled|is_placeholder|is_too_thin)" custom tests`
  now finds only `custom/source_material_quality.py`.
- Diff check: whitespace clean; only CRLF normalization warnings.

## DoD Impact

- Repeated source material claim quality logic is now merged behind one helper.
- Learner integration and source integration gate remain compatibility callers.
- No private memory bodies, tokens, or secrets were printed.
- No git commit was made.

## Remaining

- Final audit still needs to list kept / merged / archived / deleted /
  remaining risks.
- Compatibility/manual `memory/knowledge` strings need one last audit to decide
  which are intentional references and which still need canonical helpers.
- Known unrelated smoke issue remains:
  `tests/smoke/bridge/bridge_values_smoke.py` expects `_optional_int` from
  `xinyu_core_bridge.py`.

## Next Batch

Run a final DoD audit pass. If the audit finds a narrow remaining live-path
cleanup, handle that as the next single capability group before final summary.

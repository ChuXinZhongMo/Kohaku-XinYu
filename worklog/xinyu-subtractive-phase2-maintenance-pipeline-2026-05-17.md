# XinYu Subtractive Phase 2 - Maintenance Pipeline - 2026-05-17

Status: batch 2 complete.

## Scope

This batch started collapsing repeated `custom/*_bridge_plugin.py` maintenance
logic without changing the source/learning engines.

## Changes

- Added `custom/maintenance_bridge_utils.py` as the shared owner for:
  - maintenance root resolution
  - maintenance trace writing
  - maintenance-turn gating
  - recommendation/dispatch marker checks
  - plugin cooldown checks
- Migrated these source-chain bridge plugins to the shared helper:
  - `custom/source_gate_bridge_plugin.py`
  - `custom/source_reliability_bridge_plugin.py`
  - `custom/source_integration_gate_bridge_plugin.py`
  - `custom/source_request_planner_bridge_plugin.py`
  - `custom/source_search_resolver_bridge_plugin.py`
  - `custom/search_result_gate_bridge_plugin.py`
  - `custom/outward_source_bridge_plugin.py`
- Added `tests/test_maintenance_bridge_utils.py`.
- Added the migrated maintenance bridge files to `smoke_run.py` quick
  py-compile coverage.

## Validation

Passed:

```powershell
.\.venv\Scripts\python.exe -m py_compile custom\maintenance_bridge_utils.py custom\source_gate_bridge_plugin.py custom\source_reliability_bridge_plugin.py custom\source_integration_gate_bridge_plugin.py custom\source_request_planner_bridge_plugin.py custom\source_search_resolver_bridge_plugin.py custom\search_result_gate_bridge_plugin.py custom\outward_source_bridge_plugin.py tests\test_maintenance_bridge_utils.py
```

Passed:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_maintenance_bridge_utils.py -q
```

Result:

```text
3 passed
```

Passed with restore enabled:

```powershell
.\.venv\Scripts\python.exe tests\smoke\learning\integration\source_reliability_gate_smoke.py --restore-after
.\.venv\Scripts\python.exe tests\smoke\learning\integration\source_request_planner_smoke.py --restore-after
.\.venv\Scripts\python.exe tests\smoke\learning\integration\source_search_resolution_smoke.py --restore-after
.\.venv\Scripts\python.exe tests\smoke\learning\integration\outward_source_smoke.py --restore-after
.\.venv\Scripts\python.exe tests\smoke\learning\integration\source_learning_chain_smoke.py --restore-after
```

Passed:

```powershell
.\.venv\Scripts\python.exe smoke_run.py --group learning
.\.venv\Scripts\python.exe smoke_run.py --group quick --timeout-seconds 300
```

Results:

```text
smoke_run group=learning: ok
smoke_run group=quick: ok
```

## Validation Note

The first manual source-chain smoke run was launched without `--restore-after`.
Those legacy smokes write local ignored `memory/knowledge` smoke state by
design. Subsequent validation used `--restore-after`; future direct runs of
those source-chain smokes should keep that flag unless the goal is to update
local learning/source state.

## Remaining

- Migrate the remaining source/learning bridge plugins that still duplicate
  maintenance gating:
  - done in batch 3, see below.
- Then apply the same pattern to archive/retention/consolidation and
  AI-self-iteration review gates.

## Batch 3 Update

Status: source/learning maintenance bridge migration complete.

Added shared helper split points:

- `maintenance_preflight(...)`
- `cooldown_ready(...)`

Migrated the remaining source/learning bridge plugins:

- `custom/autonomous_search_activation_bridge_plugin.py`
- `custom/source_search_provider_bridge_plugin.py`
- `custom/source_comparison_bridge_plugin.py`
- `custom/learner_integration_bridge_plugin.py`
- `custom/learning_quality_bridge_plugin.py`

Extended `tests/test_maintenance_bridge_utils.py` to cover provider activation
gating.

Validation passed:

```powershell
.\.venv\Scripts\python.exe -m py_compile custom\maintenance_bridge_utils.py custom\autonomous_search_activation_bridge_plugin.py custom\source_search_provider_bridge_plugin.py custom\source_comparison_bridge_plugin.py custom\learner_integration_bridge_plugin.py custom\learning_quality_bridge_plugin.py tests\test_maintenance_bridge_utils.py smoke_run.py
.\.venv\Scripts\python.exe -m pytest tests\test_maintenance_bridge_utils.py -q
```

Result:

```text
4 passed
```

Source-chain smokes passed with restore enabled:

```powershell
.\.venv\Scripts\python.exe tests\smoke\learning\integration\source_search_provider_smoke.py --restore-after
.\.venv\Scripts\python.exe tests\smoke\learning\integration\source_comparison_smoke.py --restore-after
.\.venv\Scripts\python.exe tests\smoke\learning\integration\learning_quality_smoke.py --restore-after
.\.venv\Scripts\python.exe tests\smoke\learning\integration\source_learning_chain_smoke.py --restore-after
```

Grouped validation passed:

```powershell
.\.venv\Scripts\python.exe smoke_run.py --group learning
.\.venv\Scripts\python.exe smoke_run.py --group quick --timeout-seconds 300
```

Results:

```text
smoke_run group=learning: ok
smoke_run group=quick: ok
```

Remaining custom maintenance collapse:

- archive/retention/consolidation bridge plugins
- AI self-iteration gate/review bridge plugins
- personality growth gate bridge plugin

## Batch 4 Update

Status: archive, AI/personality, and high-duplication runtime maintenance bridge
migration complete.

Migrated archive/retention/consolidation plugins:

- `custom/consolidation_bridge_plugin.py`
- `custom/long_term_memory_gate_bridge_plugin.py`
- `custom/retention_gate_bridge_plugin.py`
- `custom/archive_output_bridge_plugin.py`
- `custom/archive_commit_bridge_plugin.py`

Migrated AI/personality plugins:

- `custom/ai_self_iteration_gate_bridge_plugin.py`
- `custom/ai_self_iteration_review_bridge_plugin.py`
- `custom/personality_growth_gate_bridge_plugin.py`

Migrated high-duplication runtime maintenance plugins:

- `custom/question_pipeline_bridge_plugin.py`
- `custom/slow_reprocess_bridge_plugin.py`
- `custom/reflection_output_bridge_plugin.py`
- `custom/dream_output_bridge_plugin.py`
- `custom/research_handoff_bridge_plugin.py`

Added focused tests:

- `tests/test_ai_personality_maintenance_bridge.py`
- extended `tests/test_maintenance_bridge_utils.py`

Validation passed:

```powershell
.\.venv\Scripts\python.exe -B -m py_compile custom\maintenance_bridge_utils.py custom\*_bridge_plugin.py tests\test_maintenance_bridge_utils.py tests\test_ai_personality_maintenance_bridge.py
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests\test_maintenance_bridge_utils.py tests\test_ai_personality_maintenance_bridge.py
```

Result:

```text
12 passed
```

Restore-safe targeted smokes passed:

```powershell
.\.venv\Scripts\python.exe -B tests\smoke\memory\integration\archive_commit_smoke.py --restore-after --require-commit --diff-lines 0
.\.venv\Scripts\python.exe -B tests\smoke\memory\integration\long_term_memory_gate_smoke.py --restore-after --require-gate --diff-lines 0
.\.venv\Scripts\python.exe -B tests\smoke\life\integration\consolidation_dream_weight_smoke.py --restore-after --require-hold --diff-lines 0
.\.venv\Scripts\python.exe -B tests\smoke\initiative\integration\ai_self_iteration_gate_smoke.py --restore-after --require-gate --diff-lines 0
.\.venv\Scripts\python.exe -B tests\smoke\initiative\integration\ai_self_iteration_review_bridge_smoke.py
.\.venv\Scripts\python.exe -B tests\smoke\voice\integration\personality_growth_gate_smoke.py --restore-after --require-ready --diff-lines 0
.\.venv\Scripts\python.exe -B tests\smoke\learning\integration\source_learning_chain_smoke.py --restore-after --require-chain --diff-lines 0
.\.venv\Scripts\python.exe -B tests\smoke\learning\integration\question_pipeline_smoke.py --restore-after --require-queue --require-routing --diff-lines 0
.\.venv\Scripts\python.exe -B tests\smoke\learning\integration\research_handoff_smoke.py
.\.venv\Scripts\python.exe -B tests\smoke\life\integration\reflection_dream_residue_smoke.py --restore-after --require-reflection --diff-lines 0
.\.venv\Scripts\python.exe -B tests\smoke\life\integration\dream_reflection_growth_cycle_smoke.py --restore-after --require-cycle --diff-lines 0
```

## Batch 5 Update

Status: remaining bridge root/trace duplication collapse complete.

Migrated root/trace helpers in:

- `custom/automation_bridge_plugin.py`
- `custom/desktop_thoughts_bridge_plugin.py`
- `custom/github_autonomous_learning_bridge_plugin.py`
- `custom/initiative_loop_bridge_plugin.py`
- `custom/inner_cycle_bridge_plugin.py`
- `custom/maintenance_schedule_bridge_plugin.py`
- `custom/turn_mode_bridge_plugin.py`

`custom/github_autonomous_learning_bridge_plugin.py` now also delegates its
maintenance-turn and cooldown gate to `maintenance_should_run(...)`.

`custom/automation_bridge_plugin.py` keeps its large suggestion algorithm in
place, but its root, trace, and text-read primitives now come from
`maintenance_bridge_utils`.

`smoke_run.py` quick py-compile coverage now includes the migrated maintenance
bridge set. The grouped `quick` smoke was not rerun in this batch because the
runner still does not pass `--restore-after` to stateful child smokes.

Validation passed:

```powershell
.\.venv\Scripts\python.exe -B -m py_compile smoke_run.py custom\maintenance_bridge_utils.py custom\*_bridge_plugin.py tests\test_maintenance_bridge_utils.py tests\test_ai_personality_maintenance_bridge.py
.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests\test_maintenance_bridge_utils.py tests\test_ai_personality_maintenance_bridge.py
.\.venv\Scripts\python.exe -B tests\smoke\learning\github_autonomous_learning_smoke.py
.\.venv\Scripts\python.exe -B tests\smoke\initiative\integration\initiative_loop_smoke.py --restore-after --diff-lines 0
.\.venv\Scripts\python.exe -B tests\smoke\initiative\automation_bridge_live_turn_smoke.py
.\.venv\Scripts\python.exe -B tests\smoke\dialogue\integration\resource_boundary_smoke.py
.\.venv\Scripts\python.exe -B tests\smoke\dialogue\integration\resource_boundary_live_smoke.py
```

Duplicate scan:

```powershell
Get-ChildItem -LiteralPath custom -Filter '*_bridge_plugin.py' |
  Select-String -Pattern 'def _default_root|def _resolve_root|trace_path = root|stamp = datetime\.now\(\)\.astimezone\(\)\.isoformat\(\)'
```

Result: no matches.

Remaining follow-up:

- Add restore-safe support to `smoke_run.py` before using grouped `quick` as a
  final gate for state-writing memory/source smokes.

## Batch 6 Update

Status: restore-safe grouped smoke runner support added and validated.

`smoke_run.py` now supports:

```powershell
.\.venv\Scripts\python.exe -B smoke_run.py --group quick --restore-after --timeout-seconds 300
```

Behavior:

- snapshots project `memory/` plus the stable research-handoff runtime trace
  before a grouped run
- restores that snapshot after each child smoke
- passes `--restore-after` to child smoke scripts that explicitly support it
- leaves Python module commands, py-compile, and pytest commands unchanged

Implementation note:

- The restore snapshot intentionally does not copy the whole `runtime/`
  directory because that tree contains locked pytest/codex temporary folders on
  Windows. The stable runtime trace file is restored explicitly instead.

Validation passed:

```powershell
.\.venv\Scripts\python.exe -B -m py_compile smoke_run.py
.\.venv\Scripts\python.exe -B smoke_run.py --group replay --restore-after --timeout-seconds 120
.\.venv\Scripts\python.exe -B smoke_run.py --group quick --restore-after --timeout-seconds 300
git status --short -- memory runtime\research_handoff_bridge_trace.log
git diff --check -- XinYu-Core/examples/agent-apps/xinyu/custom XinYu-Core/examples/agent-apps/xinyu/tests/test_maintenance_bridge_utils.py XinYu-Core/examples/agent-apps/xinyu/tests/test_ai_personality_maintenance_bridge.py XinYu-Core/examples/agent-apps/xinyu/smoke_run.py worklog/xinyu-subtractive-phase2-maintenance-pipeline-2026-05-17.md worklog/xinyu-phase2-validation-observer-2026-05-17.md
```

Results:

```text
replay: 21 passed
smoke_run group=quick: ok
memory/runtime status after restore: clean for checked paths
git diff --check: no whitespace errors; CRLF normalization warnings only
```

# XinYu Source Request Planner Knowledge Path - 2026-05-17

Status: applied as a single source-request planner migration.

## Batch Scope

- Capability group: source request planner.
- Goal: replace hard-coded `memory/knowledge/...` reads/writes in the planner
  engine with `knowledge_file_path(...)`, without changing planning behavior.

## Completed

- Updated `custom/source_request_planner_engine.py`.
- Added local `_knowledge(root, filename)` helper.
- Migrated helper resolution for:
  - `source_integration_gate_state.md`
  - `source_gate_state.md`
  - `learning_quality_state.md`
  - `source_requests.md`
  - `source_request_planner_state.md`

## Validation

Passed:

```powershell
.\.venv\Scripts\python.exe -m py_compile custom\source_request_planner_engine.py custom\source_request_planner_bridge_plugin.py xinyu_storage_paths.py
.\.venv\Scripts\python.exe tests\smoke\learning\integration\source_request_planner_smoke.py --restore-after --require-plan --diff-lines 0
.\.venv\Scripts\python.exe tests\smoke\learning\integration\source_learning_chain_smoke.py --restore-after --diff-lines 0
rg -n -F -e 'root / "memory/knowledge' -e 'memory/knowledge/source_integration_gate_state' -e 'memory/knowledge/source_gate_state' -e 'memory/knowledge/learning_quality_state' -e 'memory/knowledge/source_requests' -e 'memory/knowledge/source_request_planner_state' .\custom\source_request_planner_engine.py
git diff --check -- XinYu-Core/examples/agent-apps/xinyu/custom/source_request_planner_engine.py
```

Results:

- Source request planner smoke: passed.
- Source learning chain smoke: passed.
- Protected files changed: none.
- Restore-after completed for both smokes.
- Hard-coded knowledge path check in planner engine: no matches.
- Diff check: whitespace clean; only CRLF normalization warning.

## Not Changed

- Bridge trace path behavior remains unchanged.
- No knowledge files or private memory bodies were moved.
- No raw private contents were printed.
- No git commit was made.

## Remaining

- Source gate, reliability, integration, outward source, source comparison,
  learner integration, and learning quality still have hard-coded
  `memory/knowledge/...` paths.

## Next Batch

Migrate the source gate/reliability/integration gate group, then run their
focused smokes and the source learning chain smoke serially.

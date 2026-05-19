# XinYu Learner Integration Knowledge Path - 2026-05-17

Status: applied as a single learner integration migration.

## Batch Scope

- Capability group: learner integration.
- Goal: replace hard-coded `memory/knowledge/...` reads/writes in learner
  integration runtime code with `knowledge_file_path(...)`, without changing
  integration eligibility, claim quality gates, or bridge run conditions.

## Completed

- Updated `custom/learner_integration_engine.py`.
- Updated `custom/learner_integration_bridge_plugin.py`.
- Added local `_knowledge(root, filename)` helpers.
- Migrated helper resolution for:
  - `source_integration_gate_state.md`
  - `source_materials.md`
  - `general.md`
  - `source_notes.md`
  - `learner_integration_state.md`

## Validation

Passed:

```powershell
.\.venv\Scripts\python.exe -m py_compile custom\learner_integration_engine.py custom\learner_integration_bridge_plugin.py xinyu_storage_paths.py
rg -n -F -e 'root / "memory/knowledge' -e 'memory/knowledge/source_integration_gate_state' -e 'memory/knowledge/source_materials' -e 'memory/knowledge/general.md' -e 'memory/knowledge/source_notes' -e 'memory/knowledge/learner_integration_state' .\custom\learner_integration_engine.py .\custom\learner_integration_bridge_plugin.py
.\.venv\Scripts\python.exe -m pytest tests\test_maintenance_bridge_utils.py
.\.venv\Scripts\python.exe tests\smoke\learning\integration\learner_integration_smoke.py --restore-after --require-integration --diff-lines 0
.\.venv\Scripts\python.exe tests\smoke\learning\integration\source_learning_chain_smoke.py --restore-after --diff-lines 0
git diff --check -- XinYu-Core/examples/agent-apps/xinyu/custom/learner_integration_engine.py XinYu-Core/examples/agent-apps/xinyu/custom/learner_integration_bridge_plugin.py
```

Results:

- Maintenance bridge utils tests: 9 passed.
- Learner integration smoke: passed.
- Source learning chain smoke: passed.
- Restore-after completed for smokes.
- Protected files changed: none.
- Hard-coded knowledge path check in touched files: no matches for migrated
  learner integration knowledge files.
- Diff check: whitespace clean; only CRLF normalization warnings.

## Not Changed

- `custom/learner_integration_bridge_plugin.py` trace path remains a relative
  trace string and was not migrated in this batch.
- Memory context paths used for question states, active questions, and
  exploration queue remain unchanged because they are not `memory/knowledge`
  storage boundaries.
- No knowledge files or private memory bodies were moved.
- No raw private contents were printed.
- No git commit was made.

## Remaining

- Learning quality and selected recall/router modules still have hard-coded
  `memory/knowledge` paths.
- Neuro-inspired rule traceability remains open.
- Duplicate bridge/helper consolidation remains open as a later batch.

## Next Batch

Migrate the learning quality group, then run its focused smoke and the source
quality/source learning smokes serially.

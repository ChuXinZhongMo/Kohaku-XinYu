# XinYu Source Comparison Knowledge Path - 2026-05-17

Status: applied as a single source comparison migration.

## Batch Scope

- Capability group: source comparison.
- Goal: replace hard-coded `memory/knowledge/...` reads/writes in source
  comparison runtime code with `knowledge_file_path(...)`, without changing
  material comparison, hold routing, or bridge run conditions.

## Completed

- Updated `custom/source_comparison_engine.py`.
- Updated `custom/source_comparison_bridge_plugin.py`.
- Added local `_knowledge(root, filename)` helpers.
- Migrated helper resolution for:
  - `source_notes.md`
  - `source_materials.md`
  - `source_comparison_state.md`

## Validation

Passed:

```powershell
.\.venv\Scripts\python.exe -m py_compile custom\source_comparison_engine.py custom\source_comparison_bridge_plugin.py xinyu_storage_paths.py
rg -n -F -e 'root / "memory/knowledge' -e 'memory/knowledge/source_notes' -e 'memory/knowledge/source_materials' -e 'memory/knowledge/source_comparison_state' .\custom\source_comparison_engine.py .\custom\source_comparison_bridge_plugin.py
.\.venv\Scripts\python.exe -m pytest tests\test_maintenance_bridge_utils.py
.\.venv\Scripts\python.exe tests\smoke\learning\integration\source_comparison_smoke.py --restore-after --require-comparison --diff-lines 0
.\.venv\Scripts\python.exe tests\smoke\learning\integration\source_learning_chain_smoke.py --restore-after --diff-lines 0
git diff --check -- XinYu-Core/examples/agent-apps/xinyu/custom/source_comparison_engine.py XinYu-Core/examples/agent-apps/xinyu/custom/source_comparison_bridge_plugin.py
```

Results:

- Maintenance bridge utils tests: 9 passed.
- Source comparison smoke: passed.
- Source learning chain smoke: passed.
- Restore-after completed for smokes.
- Protected files changed: none.
- Hard-coded knowledge path check in touched files: no matches for migrated
  source comparison knowledge files.
- Diff check: whitespace clean; only CRLF normalization warnings.

## Not Changed

- `custom/source_comparison_bridge_plugin.py` trace path remains a relative
  trace string and was not migrated in this batch.
- Memory context paths used for active questions, question states, and
  exploration queue remain unchanged because they are not `memory/knowledge`
  storage boundaries.
- No knowledge files or private memory bodies were moved.
- No raw private contents were printed.
- No git commit was made.

## Remaining

- Learner integration, learning quality, and selected recall/router modules
  still have hard-coded `memory/knowledge` paths.
- Neuro-inspired rule traceability remains open.
- Duplicate bridge/helper consolidation remains open as a later batch.

## Next Batch

Migrate the learner integration group, then run its focused smoke and the source
learning chain smoke serially.

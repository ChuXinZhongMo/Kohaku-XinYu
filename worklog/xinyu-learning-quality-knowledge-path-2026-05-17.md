# XinYu Learning Quality Knowledge Path - 2026-05-17

Status: applied as a single learning quality migration.

## Batch Scope

- Capability group: learning quality.
- Goal: replace hard-coded `memory/knowledge/...` reads/writes in learning
  quality runtime code with `knowledge_file_path(...)`, without changing
  quality grading, warning generation, or bridge run conditions.

## Completed

- Updated `custom/learning_quality_engine.py`.
- Updated `custom/learning_quality_bridge_plugin.py`.
- Added local `_knowledge(root, filename)` helpers.
- Migrated helper resolution for:
  - `source_notes.md`
  - `source_materials.md`
  - `general.md`
  - `learning_quality_state.md`

## Validation

Passed:

```powershell
.\.venv\Scripts\python.exe -m py_compile custom\learning_quality_engine.py custom\learning_quality_bridge_plugin.py xinyu_storage_paths.py
rg -n -F -e 'root / "memory/knowledge' -e 'memory/knowledge/source_notes' -e 'memory/knowledge/source_materials' -e 'memory/knowledge/general.md' -e 'memory/knowledge/learning_quality_state' .\custom\learning_quality_engine.py .\custom\learning_quality_bridge_plugin.py
.\.venv\Scripts\python.exe -m pytest tests\test_maintenance_bridge_utils.py
.\.venv\Scripts\python.exe tests\smoke\learning\integration\learning_quality_smoke.py --restore-after --require-quality --diff-lines 0
.\.venv\Scripts\python.exe tests\smoke\learning\integration\source_quality_followup_smoke.py --restore-after --diff-lines 0
.\.venv\Scripts\python.exe tests\smoke\learning\integration\source_learning_chain_smoke.py --restore-after --diff-lines 0
git diff --check -- XinYu-Core/examples/agent-apps/xinyu/custom/learning_quality_engine.py XinYu-Core/examples/agent-apps/xinyu/custom/learning_quality_bridge_plugin.py
```

Results:

- Maintenance bridge utils tests: 9 passed.
- Learning quality smoke: passed.
- Source quality followup smoke: passed.
- Source learning chain smoke: passed.
- Restore-after completed for smokes.
- Protected files changed: none.
- Hard-coded knowledge path check in touched files: no matches for migrated
  learning quality knowledge files.
- Diff check: whitespace clean; only CRLF normalization warnings.

## Not Changed

- `custom/learning_quality_bridge_plugin.py` trace path remains a relative
  trace string and was not migrated in this batch.
- No knowledge files or private memory bodies were moved.
- No raw private contents were printed.
- No git commit was made.

## Remaining

- Selected recall/router modules still have hard-coded `memory/knowledge`
  paths, especially `xinyu_context_retrieval.py` and
  `xinyu_sparse_memory_router.py`.
- Neuro-inspired rule traceability remains open.
- Duplicate bridge/helper consolidation remains open as a later batch.

## Next Batch

Audit remaining active hard-coded `memory/knowledge` paths, then migrate the
recall/router group with focused recall/router tests.

# XinYu Outward Source Knowledge Path - 2026-05-17

Status: applied as a single outward source migration.

## Batch Scope

- Capability group: outward source fetch/staging.
- Goal: replace hard-coded `memory/knowledge/...` reads/writes in the outward
  source engine with `knowledge_file_path(...)`, without changing fetch,
  staging, or restore behavior.

## Completed

- Updated `custom/outward_source_engine.py`.
- Added local `_knowledge(root, filename)` helper.
- Migrated helper resolution for:
  - `source_materials.md`
  - `source_integration_gate_state.md`
  - `source_gate_state.md`
  - `source_requests.md`
  - `outward_source_state.md`

## Validation

Passed:

```powershell
.\.venv\Scripts\python.exe -m py_compile custom\outward_source_engine.py custom\outward_source_bridge_plugin.py xinyu_storage_paths.py
rg -n -F -e 'root / "memory/knowledge' -e 'memory/knowledge/source_materials' -e 'memory/knowledge/source_integration_gate_state' -e 'memory/knowledge/source_gate_state' -e 'memory/knowledge/source_requests' -e 'memory/knowledge/outward_source_state' .\custom\outward_source_engine.py
.\.venv\Scripts\python.exe tests\smoke\learning\integration\outward_source_smoke.py --restore-after --require-stage --diff-lines 0
.\.venv\Scripts\python.exe tests\smoke\learning\integration\source_learning_chain_smoke.py --restore-after --diff-lines 0
git diff --check -- XinYu-Core/examples/agent-apps/xinyu/custom/outward_source_engine.py
```

Results:

- Outward source smoke: passed.
- Source learning chain smoke: passed.
- Restore-after completed for both smokes.
- Protected files changed: none.
- Hard-coded knowledge path check in touched engine: no matches.
- Diff check: whitespace clean; only CRLF normalization warning.

## Not Changed

- `custom/outward_source_bridge_plugin.py` trace path remains a relative trace
  string and was not migrated in this batch.
- No knowledge files or private memory bodies were moved.
- No raw private contents were printed.
- No git commit was made.

## Remaining

- Search result gate, source comparison, learner integration, learning quality,
  and selected recall/router modules still have hard-coded `memory/knowledge`
  paths.
- Subagent audit also found a traceability gap: neuro-inspired rules exist and
  are behaviorally reflected, but runtime flows do not yet expose rule IDs from
  `xinyu_neuro_memory_rules.py`.

## Next Batch

Migrate the search result gate group, then run its focused smoke and the source
learning chain smoke serially.

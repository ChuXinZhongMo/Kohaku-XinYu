# XinYu Source Search Knowledge Path - 2026-05-17

Status: applied as a single source-search pipeline migration.

## Batch Scope

- Capability group: source search provider/resolver.
- Goal: replace hard-coded `memory/knowledge/...` reads/writes in source search
  provider/resolver code with `knowledge_file_path(...)`, without changing
  search, gate, or render behavior.

## Completed

- Updated `custom/source_search_provider_engine.py`.
- Updated `custom/source_search_resolver_engine.py`.
- Updated `custom/source_search_provider_bridge_plugin.py` activation-state
  read.
- Added local `_knowledge(root, filename)` helpers in provider/resolver engines.
- Migrated helper resolution for:
  - `autonomous_search_activation_state.md`
  - `source_requests.md`
  - `source_search_results.md`
  - `source_search_provider_state.md`
  - `source_search_resolver_state.md`

## Validation

Passed:

```powershell
.\.venv\Scripts\python.exe -m py_compile custom\source_search_provider_engine.py custom\source_search_resolver_engine.py custom\source_search_provider_bridge_plugin.py custom\source_search_resolver_bridge_plugin.py xinyu_storage_paths.py
.\.venv\Scripts\python.exe tests\smoke\learning\integration\source_search_provider_smoke.py --restore-after --require-provider --diff-lines 0
.\.venv\Scripts\python.exe tests\smoke\learning\integration\source_search_resolution_smoke.py --restore-after --require-resolution --diff-lines 0
.\.venv\Scripts\python.exe tests\smoke\learning\integration\source_learning_chain_smoke.py --restore-after --diff-lines 0
rg -n -F -e 'root / "memory/knowledge' -e 'memory/knowledge/source_requests' -e 'memory/knowledge/source_search_results' -e 'memory/knowledge/source_search_provider_state' -e 'memory/knowledge/source_search_resolver_state' -e 'memory/knowledge/autonomous_search_activation_state' .\custom\source_search_provider_engine.py .\custom\source_search_resolver_engine.py .\custom\source_search_provider_bridge_plugin.py
git diff --check -- XinYu-Core/examples/agent-apps/xinyu/custom/source_search_provider_engine.py XinYu-Core/examples/agent-apps/xinyu/custom/source_search_resolver_engine.py XinYu-Core/examples/agent-apps/xinyu/custom/source_search_provider_bridge_plugin.py
```

Results:

- Source search provider smoke: passed.
- Source search resolution smoke: passed.
- Source learning chain smoke: passed.
- Protected files changed: none.
- Restore-after completed for all smokes.
- Hard-coded knowledge path check in touched files: no matches.
- Diff check: whitespace clean; only CRLF normalization warnings.

## Recovery Note

The provider and resolver smokes mutate the same `memory/knowledge` files. They
must be run serially. A parallel attempt caused expected cross-smoke
interference before the final serial validation passed.

## Not Changed

- Trace path behavior remains unchanged.
- No knowledge files or private memory bodies were moved.
- No raw private contents were printed.
- No git commit was made.

## Remaining

- Other source/learning engines still hard-code `memory/knowledge/...`,
  especially request planner, source gate/reliability/integration, outward
  source, source comparison, learner integration, and learning quality.

## Next Batch

Migrate the source request planner knowledge paths, then run
`source_request_planner_smoke.py` and `source_learning_chain_smoke.py`
serially with restore.

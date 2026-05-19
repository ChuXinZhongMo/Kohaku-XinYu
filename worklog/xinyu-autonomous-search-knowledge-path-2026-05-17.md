# XinYu Autonomous Search Knowledge Path - 2026-05-17

Status: applied as a single-pipeline storage helper migration.

## Batch Scope

- Capability group: autonomous search activation.
- Goal: replace hard-coded `memory/knowledge/...` reads/writes in this engine
  with `knowledge_file_path(...)`, without changing gate behavior.

## Completed

- Updated `custom/autonomous_search_activation_engine.py`.
- Added a local `_knowledge(root, filename)` helper that delegates to
  `xinyu_storage_paths.knowledge_file_path(...)`.
- Migrated these files to helper resolution:
  - `source_requests.md`
  - `source_search_results.md`
  - `source_integration_gate_state.md`
  - `learning_quality_state.md`
  - `autonomous_search_activation_state.md`

## Validation

Passed:

```powershell
.\.venv\Scripts\python.exe -m py_compile custom\autonomous_search_activation_engine.py custom\autonomous_search_activation_bridge_plugin.py xinyu_storage_paths.py
.\.venv\Scripts\python.exe tests\smoke\learning\integration\autonomous_search_activation_smoke.py --restore-after --require-activation --diff-lines 0
.\.venv\Scripts\python.exe tests\smoke\learning\integration\source_learning_chain_smoke.py --restore-after --diff-lines 0
rg -n -F -e 'root / "memory/knowledge' -e 'memory/knowledge/source_requests' -e 'memory/knowledge/source_search_results' -e 'memory/knowledge/source_integration_gate_state' -e 'memory/knowledge/learning_quality_state' -e 'memory/knowledge/autonomous_search_activation_state' .\custom\autonomous_search_activation_engine.py
git diff --check -- XinYu-Core/examples/agent-apps/xinyu/custom/autonomous_search_activation_engine.py
```

Results:

- Autonomous search activation smoke: passed with expected disabled,
  dry-run, quality-blocked, quality-followup, high-override, no-pending, and
  enabled cases.
- Source learning chain smoke: passed.
- Protected files changed: none.
- Restore-after completed for both smokes.
- Hard-coded knowledge path check in this engine: no matches.
- Diff check: whitespace clean; only CRLF normalization warning for the engine.

## Not Changed

- No trace path behavior changed in the bridge plugin.
- No knowledge files or private memory bodies were moved.
- No raw runtime/private contents were printed.
- No git commit was made.

## Remaining

- Other source/learning engines still hard-code `memory/knowledge/...`.
- The next safe group is one source-search provider/resolver pair or the
  source-request planner, with its focused smoke.

## Next Batch

Migrate source search provider/resolver knowledge paths to
`knowledge_file_path(...)`, then run their provider/resolution smokes.

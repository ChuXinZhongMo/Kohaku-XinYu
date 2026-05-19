# XinYu Inner Cycle Manifest Knowledge Path - 2026-05-17

Status: applied as a single inner cycle/manifest migration.

## Batch Scope

- Capability group: inner cycle status summary and inner framework manifest.
- Goal: replace hard-coded `memory/knowledge/...` runtime reads with
  `knowledge_file_path(...)`, and express manifest knowledge refs through
  `knowledge_ref(...)` while preserving the same reference text.

## Completed

- Updated `custom/inner_cycle_engine.py`.
  - Added local `_knowledge(root, filename)` helper.
  - Migrated source/learning status reads for:
    - `source_gate_state.md`
    - `source_reliability_state.md`
    - `source_integration_gate_state.md`
    - `source_request_planner_state.md`
    - `source_search_resolver_state.md`
    - `autonomous_search_activation_state.md`
    - `source_search_provider_state.md`
    - `search_result_gate_state.md`
    - `outward_source_state.md`
    - `source_comparison_state.md`
    - `learner_integration_state.md`
    - `learning_quality_state.md`
- Updated `custom/inner_framework_manifest.py`.
  - Replaced question/exploration knowledge file strings with `knowledge_ref(...)`.

## Validation

Passed:

```powershell
.\.venv\Scripts\python.exe -m py_compile custom\inner_cycle_engine.py custom\inner_framework_manifest.py custom\inner_cycle_bridge_plugin.py xinyu_storage_paths.py
rg -n -F 'memory/knowledge' .\custom\inner_cycle_engine.py .\custom\inner_framework_manifest.py
@'<manifest import check>'@ | .\.venv\Scripts\python.exe -
@'<inner cycle temp-root smoke>'@ | .\.venv\Scripts\python.exe -
git diff --check -- XinYu-Core/examples/agent-apps/xinyu/custom/inner_cycle_engine.py XinYu-Core/examples/agent-apps/xinyu/custom/inner_framework_manifest.py
```

Results:

- Manifest import check: passed.
- Inner cycle temp-root smoke: passed.
- Hard-coded knowledge path check in touched files: no matches.
- Diff check: whitespace clean; only CRLF normalization warnings.

## Not Changed

- Non-knowledge context, reflection, dream, self, and archive summary paths
  remain unchanged.
- Manifest still exposes compatible `memory/knowledge/<filename>` refs through
  `knowledge_ref(...)`.
- No knowledge files or private memory bodies were moved.
- No raw private contents were printed.
- No git commit was made.

## Remaining

- Active hard-coded knowledge paths remain in selected review/ops/manual/probe
  tools and trace constants.
- Neuro-inspired rule traceability remains open.
- Duplicate bridge/helper consolidation remains open as a later batch.

## Next Batch

Audit remaining active hard-coded `memory/knowledge` paths and decide whether
to migrate review/probe/ops tools or switch to neuro rule traceability.

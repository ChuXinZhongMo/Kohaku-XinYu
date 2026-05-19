# XinYu Ops Probe Status Knowledge Path - 2026-05-17

Status: applied as a single ops/probe/status migration.

## Batch Scope

- Capability group: research dry-run probe and long-run status validation.
- Goal: replace hard-coded `memory/knowledge/...` reads/writes in ops tools
  with `knowledge_file_path(...)`, without changing CLI output or smoke
  behavior.

## Completed

- Updated `ops/probes/xinyu_research_loop_dry_run.py`.
  - Added local `_knowledge(root, filename)` helper.
  - Migrated `source_requests.md` and `research_loop_dry_run_state.md`.
- Updated `ops/validation/long_run_status.py`.
  - Added local `_knowledge(root, filename)` helper.
  - Migrated status reads for:
    - `learning_quality_state.md`
    - `autonomous_search_activation_state.md`
    - `social_inquiry_policy_state.md`

## Validation

Passed:

```powershell
.\.venv\Scripts\python.exe -m py_compile ops\probes\xinyu_research_loop_dry_run.py ops\validation\long_run_status.py xinyu_storage_paths.py
rg -n -F 'memory/knowledge' .\ops\probes\xinyu_research_loop_dry_run.py .\ops\validation\long_run_status.py
.\.venv\Scripts\python.exe tests\smoke\learning\integration\research_loop_dry_run_smoke.py
.\.venv\Scripts\python.exe ops\validation\long_run_status.py --skip-deployment-gate
git diff --check -- XinYu-Core/examples/agent-apps/xinyu/ops/probes/xinyu_research_loop_dry_run.py XinYu-Core/examples/agent-apps/xinyu/ops/validation/long_run_status.py
```

Results:

- Research loop dry-run smoke: passed.
- Long-run status command: passed with deployment gate skipped offline.
- Hard-coded knowledge path check in touched files: no matches.
- Diff check: whitespace clean.

## Not Changed

- Context and runtime paths in these ops tools remain unchanged.
- No knowledge files or private memory bodies were moved.
- No raw private contents were printed.
- No git commit was made.

## Remaining

- Hard-coded knowledge strings remain in manual tools, trace constants,
  `custom/automation_bridge_manifest.py`, `xinyu_storage_paths.py`, and V1
  legacy markdown layer mapping.
- Neuro-inspired rule traceability remains open.
- Duplicate bridge/helper consolidation remains open as a later batch.

## Next Batch

Switch to neuro-inspired rule traceability because remaining path hits are
mostly compatibility/trace/manual strings rather than high-value live reads.

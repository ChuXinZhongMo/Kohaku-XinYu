# XinYu Source Gate Reliability Integration Knowledge Path - 2026-05-17

Status: applied as a single source gate/reliability/integration migration.

## Batch Scope

- Capability group: source gate, source reliability, source integration gate.
- Goal: replace hard-coded `memory/knowledge/...` reads/writes in the three
  gate engines with `knowledge_file_path(...)`, without changing gate behavior.

## Completed

- Updated `custom/source_gate_engine.py`.
- Updated `custom/source_reliability_engine.py`.
- Updated `custom/source_integration_gate_engine.py`.
- Added local `_knowledge(root, filename)` helpers where needed.
- Migrated helper resolution for:
  - `source_gate_state.md`
  - `source_notes.md`
  - `source_reliability_state.md`
  - `learning_quality_state.md`
  - `source_materials.md`
  - `general.md`
  - `source_requests.md`
  - `source_integration_gate_state.md`

## Validation

Passed:

```powershell
.\.venv\Scripts\python.exe -m py_compile custom\source_gate_engine.py custom\source_reliability_engine.py custom\source_integration_gate_engine.py custom\source_gate_bridge_plugin.py custom\source_reliability_bridge_plugin.py custom\source_integration_gate_bridge_plugin.py xinyu_storage_paths.py
.\.venv\Scripts\python.exe tests\smoke\learning\integration\source_reliability_gate_smoke.py --restore-after
.\.venv\Scripts\python.exe tests\smoke\learning\integration\source_quality_followup_smoke.py --restore-after --diff-lines 0
.\.venv\Scripts\python.exe tests\smoke\learning\integration\source_learning_chain_smoke.py --restore-after --diff-lines 0
rg -n -F -e 'root / "memory/knowledge' -e 'memory/knowledge/source_gate_state' -e 'memory/knowledge/source_notes' -e 'memory/knowledge/source_reliability_state' -e 'memory/knowledge/learning_quality_state' -e 'memory/knowledge/source_materials' -e 'memory/knowledge/general.md' -e 'memory/knowledge/source_requests' -e 'memory/knowledge/source_integration_gate_state' .\custom\source_gate_engine.py .\custom\source_reliability_engine.py .\custom\source_integration_gate_engine.py
git diff --check -- XinYu-Core/examples/agent-apps/xinyu/custom/source_gate_engine.py XinYu-Core/examples/agent-apps/xinyu/custom/source_reliability_engine.py XinYu-Core/examples/agent-apps/xinyu/custom/source_integration_gate_engine.py
```

Results:

- Source reliability gate smoke: passed.
- Source quality followup smoke: passed.
- Source learning chain smoke: passed.
- Restore-after completed for smokes.
- Protected files changed: none.
- Hard-coded knowledge path check in touched files: no matches.
- Diff check: whitespace clean; only CRLF normalization warnings.

## Not Changed

- Bridge trace path behavior remains unchanged.
- No knowledge files or private memory bodies were moved.
- No raw private contents were printed.
- No git commit was made.

## Remaining

- Outward source, source comparison, learner integration, and learning quality
  still need the same focused `knowledge_file_path(...)` migration.
- Broader DoD remains open until the final audit proves kept/merged/archived/
  deleted status and remaining risks.

## Next Batch

Migrate the outward source group, then run its focused smoke and the source
learning chain smoke serially.

# XinYu Maintenance Bridge Runner - 2026-05-18

Status: applied as bridge-plugin shell consolidation batch.

## Batch Scope

- Capability group: maintenance bridge plugin execution shell.
- Goal: reduce repeated `post_llm_call` shell logic while keeping plugin class
  names, plugin names, priorities, and individual gates intact.

## Completed

- Updated `custom/maintenance_bridge_utils.py`.
  - Added `run_maintenance_bridge_once(...)`.
  - Shared behavior:
    - trace post-LLM entry
    - call plugin-specific `should_run`
    - trace should-run reason
    - generate timestamp
    - call engine
    - set cooldown state
    - trace result summary
    - trace exceptions
- Migrated three same-shape source bridge plugins:
  - `custom/source_gate_bridge_plugin.py`
  - `custom/source_reliability_bridge_plugin.py`
  - `custom/source_integration_gate_bridge_plugin.py`
- Extended `tests/test_maintenance_bridge_utils.py` with runner coverage.

## Validation

Passed:

```powershell
.\.venv\Scripts\python.exe -m py_compile custom\maintenance_bridge_utils.py custom\source_gate_bridge_plugin.py custom\source_reliability_bridge_plugin.py custom\source_integration_gate_bridge_plugin.py
.\.venv\Scripts\python.exe -m pytest tests\test_maintenance_bridge_utils.py
.\.venv\Scripts\python.exe tests\smoke\learning\integration\source_reliability_gate_smoke.py --restore-after
.\.venv\Scripts\python.exe tests\smoke\learning\integration\source_learning_chain_smoke.py --restore-after --diff-lines 0
git diff --check -- XinYu-Core/examples/agent-apps/xinyu/custom/maintenance_bridge_utils.py XinYu-Core/examples/agent-apps/xinyu/custom/source_gate_bridge_plugin.py XinYu-Core/examples/agent-apps/xinyu/custom/source_reliability_bridge_plugin.py XinYu-Core/examples/agent-apps/xinyu/custom/source_integration_gate_bridge_plugin.py XinYu-Core/examples/agent-apps/xinyu/tests/test_maintenance_bridge_utils.py
```

Results:

- Maintenance bridge utils pytest: 10 passed.
- Source reliability gate smoke: passed.
- Source learning chain smoke: passed.
- Diff check: tracked file whitespace clean; CRLF normalization warnings only.

## Direct Impact

- The source gate bridge trio no longer carries three copies of the same
  post-LLM execution shell.
- Their external compatibility surfaces remain stable.

## Not Changed

- Special bridge gates were not merged.
- Plugin names/classes/priorities were not changed.
- No git commit was made.

## Next Batch

Add a synthetic persona realism evaluation set so future voice/persona tuning
has a testable boundary instead of relying on subjective feel.

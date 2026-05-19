# XinYu Source Protocol Utils - 2026-05-18

Status: applied as source/learning protocol consolidation batch.

## Batch Scope

- Capability group: source/learning request and search-result protocol parsing.
- Goal: merge repeated pure parser/id helper logic without changing source
  learning behavior or public module entry points.

## Completed

- Added `custom/source_protocol_utils.py`.
  - `extract_dash_value(...)`
  - `is_allowed_source_url(...)`
  - `split_source_requests(...)`
  - `split_search_results(...)`
  - `next_dated_id(...)`
- Updated compatibility shims:
  - `custom/source_request_planner_engine.py`
    - `is_allowed_url(...)` delegates to shared URL validator.
    - `split_requests(...)` delegates to shared source request parser.
    - `next_request_id(...)` delegates to shared dated-id helper.
  - `custom/source_search_resolver_engine.py`
    - request parser now comes from shared helper instead of planner engine.
    - result parser and result id helper delegate to shared helper.
  - `custom/search_result_gate_engine.py`
    - request id helper delegates to shared dated-id helper.
  - `custom/source_integration_gate_engine.py`
    - request parser delegates to shared helper with its narrower field set.
- Added `tests/test_source_protocol_utils.py`.

## Validation

Passed:

```powershell
.\.venv\Scripts\python.exe -m py_compile custom\source_protocol_utils.py custom\source_request_planner_engine.py custom\source_search_resolver_engine.py custom\source_search_provider_engine.py custom\search_result_gate_engine.py custom\source_integration_gate_engine.py
.\.venv\Scripts\python.exe -m pytest tests\test_source_protocol_utils.py tests\test_source_material_quality.py
.\.venv\Scripts\python.exe tests\smoke\learning\integration\source_request_planner_smoke.py --restore-after
.\.venv\Scripts\python.exe tests\smoke\learning\integration\source_search_resolution_smoke.py --restore-after
.\.venv\Scripts\python.exe tests\smoke\learning\integration\source_search_provider_smoke.py --restore-after
.\.venv\Scripts\python.exe tests\smoke\learning\integration\source_learning_chain_smoke.py --restore-after --diff-lines 0
git diff --check -- XinYu-Core/examples/agent-apps/xinyu/custom/source_protocol_utils.py XinYu-Core/examples/agent-apps/xinyu/custom/source_request_planner_engine.py XinYu-Core/examples/agent-apps/xinyu/custom/source_search_resolver_engine.py XinYu-Core/examples/agent-apps/xinyu/custom/search_result_gate_engine.py XinYu-Core/examples/agent-apps/xinyu/custom/source_integration_gate_engine.py XinYu-Core/examples/agent-apps/xinyu/tests/test_source_protocol_utils.py
```

Results:

- Focused pytest: 6 passed.
- Source request planner smoke: passed.
- Source search resolution smoke: passed.
- Source search provider smoke: passed.
- Source learning chain smoke: passed.
- Diff check: whitespace clean; CRLF normalization warnings only.

## Direct Impact

- Source request/search-result parsing now has one shared implementation.
- Old function names remain available as shims, so existing imports and smokes
  continue to work.
- Search provider/resolver/gate behavior is unchanged at the source chain level.

## Not Changed

- No source learning gate policy was changed.
- No memory/knowledge files were permanently mutated by smokes; restore-after
  was used.
- No private memory bodies or raw QQ content were printed.
- No git commit was made.

## Next Batch

Reduce repeated maintenance bridge plugin shells behind a thin shared runner
while preserving plugin class names and per-plugin gates.

# XinYu Source Protocol Shim Prune - 2026-05-18

Status: complete as low-risk source protocol shim cleanup batch.

## Batch Scope

- Capability group: source/learning protocol.
- Goal: remove remaining duplicate protocol parsing where it can be done without breaking public compatibility.
- Safety rule: old public function names stay as compatibility shims unless callers are fully audited.

## Completed

- Updated `xinyu_self_thought_loop.py`.
  - `_split_source_requests(...)` now delegates to `custom.source_protocol_utils.split_source_requests(...)`.
  - Legacy defaults are preserved:
    - missing `target` remains `general`;
    - missing `reason` remains `none`;
    - `question_id: none` is still retained for self-thought routing.
- Updated `custom/outward_source_engine.py`.
  - `is_allowed_url(...)` now delegates to `source_protocol_utils.is_allowed_source_url(...)`.
  - The public local name remains for existing callers.
- Updated `ops/probes/xinyu_research_loop_dry_run.py`.
  - `split_requests(...)` now delegates to the canonical source request parser.
  - The probe's legacy output shape keeps `id` instead of `request_id`.
- Extended `tests/test_source_protocol_utils.py` to cover both compatibility cases.

## Remaining Compatibility Shims

Kept intentionally:

- `custom/source_request_planner_engine.py`
  - `is_allowed_url`
  - `split_requests`
  - `next_request_id`
- `custom/source_search_resolver_engine.py`
  - `split_requests`
  - `is_allowed_url`
  - `split_existing_results`
  - `next_result_id`
- `custom/search_result_gate_engine.py`
  - `next_request_id`
- `custom/source_integration_gate_engine.py`
  - `split_requests`
- `xinyu_self_thought_loop.py`
  - `_split_source_requests`
- `ops/probes/xinyu_research_loop_dry_run.py`
  - `split_requests`

Reason:

- These names are compatibility entry points or local semantic adapters.
- Removing them should wait for a caller audit package; this batch only removed duplicated parser logic behind them.

## Validation

Passed:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe -m py_compile xinyu_self_thought_loop.py custom\outward_source_engine.py ops\probes\xinyu_research_loop_dry_run.py custom\source_protocol_utils.py
.\.venv\Scripts\python.exe -m pytest tests\test_source_protocol_utils.py tests\test_learning_closed_loop.py -q
.\.venv\Scripts\python.exe tests\smoke\initiative\self_thought_loop_smoke.py --restore-after
.\.venv\Scripts\python.exe tests\smoke\learning\integration\outward_source_smoke.py --restore-after
.\.venv\Scripts\python.exe tests\smoke\learning\integration\source_learning_chain_smoke.py --restore-after
```

Results:

- Focused pytest: 19 passed.
- Self thought loop smoke: passed.
- Outward source smoke: passed.
- Source learning chain smoke: passed.

## Direct Impact

- The source protocol parser is now used outside the original source modules too.
- The remaining shim surface is smaller and documented.
- No source learning behavior or public function names were intentionally broken.

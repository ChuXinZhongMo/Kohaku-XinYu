# XinYu Self-Action Queue Store Boundary Batch

Date: 2026-05-18
Plan: `plan-next-2.md` Batch 2

## Completed

- Added `stores/self_action_queue.py` as the explicit owner for `memory/context/self_action_gateway_approval_queue.jsonl`.
- Kept the physical JSONL file at the legacy `memory/context` path as compatibility storage.
- Updated `xinyu_self_action_gateway.py` to append/read approval queue events through the store boundary.
- Updated `xinyu_bridge_desktop_snapshot.py` to read approval queue event tails through the store boundary.
- Updated `stores/README.md`.
- Added `tests/test_self_action_queue_store.py`.
- Updated P0 structured memory triage so this queue now reports:
  - `decision=compat_store_owner_exists`
  - `target=stores/self_action_queue`
- Refreshed:
  - `worklog/xinyu-memory-structured-p0-triage-post-self-action-queue-store-2026-05-18.md`
  - `worklog/xinyu-memory-structured-p0-triage-post-self-action-queue-store-2026-05-18.json`

## Validation

- `.\.venv\Scripts\python.exe -m py_compile stores\self_action_queue.py xinyu_self_action_gateway.py xinyu_bridge_desktop_snapshot.py tests\test_self_action_queue_store.py`
- `.\.venv\Scripts\python.exe -m pytest tests\test_self_action_queue_store.py tests\test_self_action_gateway.py tests\test_self_action_approval_controls.py tests\test_desktop_self_action_snapshot.py -q`
  - Result: 18 passed.
- `.\.venv\Scripts\python.exe -m pytest tests\test_self_action_queue_store.py tests\test_self_action_gateway.py tests\test_self_action_approval_controls.py tests\test_desktop_self_action_snapshot.py tests\test_memory_structured_p0_triage.py -q`
  - Result: 21 passed.
- `.\.venv\Scripts\python.exe tests\smoke\initiative\self_action_gateway_smoke.py`
  - Result: passed.

## Notes

- The first parallel P0 triage refresh timed out because the audit scans a large dirty tree with `rg --no-ignore`; rerunning the reports one at a time with a longer timeout succeeded.
- No private queue body, raw QQ payload, token, or memory body was printed or moved.

## Remaining

- Continue `plan-next-2.md` Batch 3: consolidate source material parser duplication while keeping old function names as shims.

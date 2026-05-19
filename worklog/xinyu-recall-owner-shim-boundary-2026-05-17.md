# XinYu Recall Owner Shim Boundary - 2026-05-17

Status: applied as a behavior-preserving recall ownership marker batch.

## Batch Scope

- Capability group: living memory recall.
- Goal: make the canonical owner/provider split testable without changing
  ranking, prompt rendering, trace logging, or runtime call order.

## Completed

- Added explicit owner/result/provider constants to
  `xinyu_living_memory_recall.py`.
- Added matching provider/compatibility metadata to
  `xinyu_context_retrieval.py`.
- Documented `_retrieve_living_memory_core(...)` as the provider delegate under
  the owner algorithm path.
- Added a focused test proving:
  - `run_living_memory_recall_algorithm(...)` is the canonical public owner.
  - `RecalledContextResult` remains the public result shape.
  - `xinyu_context_retrieval.retrieve_recalled_context(...)` is the legacy
    provider/compatibility entry.
  - `retrieve_recalled_context` in the owner module remains a shim to
    `retrieve_living_memory`.

## Validation

Passed:

```powershell
.\.venv\Scripts\python.exe -m py_compile xinyu_living_memory_recall.py xinyu_context_retrieval.py xinyu_core_bridge.py
.\.venv\Scripts\python.exe -m pytest -q tests\test_living_memory_recall.py tests\test_context_retrieval_owner_scenarios.py tests\test_retrieval_need_reranker.py tests\test_sparse_memory_router.py tests\test_retrieval_replay_cases.py tests\test_chat_replay_fixture_exporter.py
.\.venv\Scripts\python.exe tests\smoke\memory\context_retrieval_smoke.py
.\.venv\Scripts\python.exe smoke_run.py --group quick --restore-after --timeout-seconds 300
git diff --check -- XinYu-Core/examples/agent-apps/xinyu/xinyu_living_memory_recall.py XinYu-Core/examples/agent-apps/xinyu/xinyu_context_retrieval.py XinYu-Core/examples/agent-apps/xinyu/tests/test_living_memory_recall.py
```

Results:

- Focused recall tests: `28 passed`.
- Memory smoke: `context_retrieval_smoke ok`.
- Quick smoke: `smoke_run group=quick: ok`.
- Diff check: whitespace clean; only CRLF normalization warning for
  `xinyu_context_retrieval.py`.

## Not Changed

- No recall scoring behavior changed.
- No prompt block shape changed.
- No private memory, QQ logs, runtime secrets, or raw dialogue content was read
  or printed.
- No git commit was made.

## Remaining

- Old recall-adjacent modules still need clearer provider/offline labels:
  `xinyu_contextual_recall.py`, contextual self-loop/replay/observatory, and
  conversation experience matchers.
- Broader deletion/archive proof is still incomplete because the worktree has
  many pre-existing deletes and untracked files.
- Directory classification is documented, but live module moves should remain
  one capability group at a time.

## Next Batch

Continue with recall-adjacent/offline context modules. The safe target is to
classify them as renderer/offline providers or compatibility shims, add tests
for that boundary, and avoid changing runtime recall behavior.

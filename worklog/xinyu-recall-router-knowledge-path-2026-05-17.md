# XinYu Recall Router Knowledge Path - 2026-05-17

Status: applied as a single recall/router migration.

## Batch Scope

- Capability group: live recall provider and sparse memory router.
- Goal: remove direct `memory/knowledge/...` literals from recall/router
  runtime modules while preserving compatible `memory_ref` strings and recall
  behavior.

## Completed

- Updated `xinyu_storage_paths.py`.
  - Added `knowledge_ref(filename)` for canonical reference strings.
- Updated `xinyu_context_retrieval.py`.
  - Replaced knowledge memory targets with `knowledge_ref(...)`.
  - Added a local reference-to-filename map.
  - Reads knowledge-backed memory refs through `knowledge_file_path(...)`.
- Updated `xinyu_sparse_memory_router.py`.
  - Replaced knowledge memory refs in expert specs with `knowledge_ref(...)`.
- Updated tests:
  - `tests/test_storage_paths.py`
  - `tests/test_sparse_memory_router.py`
  - `tests/test_context_retrieval_owner_scenarios.py`

## Validation

Passed:

```powershell
.\.venv\Scripts\python.exe -m py_compile xinyu_storage_paths.py xinyu_context_retrieval.py xinyu_sparse_memory_router.py
rg -n -F 'memory/knowledge' .\xinyu_context_retrieval.py .\xinyu_sparse_memory_router.py
.\.venv\Scripts\python.exe -m pytest tests\test_storage_paths.py tests\test_sparse_memory_router.py tests\test_context_retrieval_owner_scenarios.py tests\test_living_memory_recall.py
.\.venv\Scripts\python.exe tests\smoke\memory\context_retrieval_smoke.py
.\.venv\Scripts\python.exe smoke_run.py --group quick
git diff --check -- XinYu-Core/examples/agent-apps/xinyu/xinyu_storage_paths.py XinYu-Core/examples/agent-apps/xinyu/xinyu_context_retrieval.py XinYu-Core/examples/agent-apps/xinyu/xinyu_sparse_memory_router.py XinYu-Core/examples/agent-apps/xinyu/tests/test_storage_paths.py XinYu-Core/examples/agent-apps/xinyu/tests/test_sparse_memory_router.py XinYu-Core/examples/agent-apps/xinyu/tests/test_context_retrieval_owner_scenarios.py
```

Results:

- Focused pytest set: 19 passed.
- Context retrieval smoke: passed.
- Quick smoke group: passed.
- Hard-coded `memory/knowledge` check in recall/router runtime files: no
  matches.
- Diff check: whitespace clean; only CRLF normalization warning.

Note: an older quick-smoke command shape, `smoke_run.py --quick`, was rejected
by argparse. The current supported command is `smoke_run.py --group quick`, and
that passed.

## Not Changed

- Compatible `memory_ref` values remain `memory/knowledge/<filename>` through
  `knowledge_ref(...)`.
- Non-knowledge memory refs such as `memory/context/...`, `memory/self/...`,
  `memory/people/...`, and project plan refs remain unchanged.
- No knowledge files or private memory bodies were moved.
- No raw private contents were printed.
- No git commit was made.

## Remaining

- Active hard-coded knowledge paths remain in self-thought/source request
  context, expression self-learning, github autonomous learning, learning
  library staging, question pipeline/social inquiry, inner cycle/manifest, and
  ops/manual/probe status tools.
- Neuro-inspired rule traceability remains open.
- Duplicate bridge/helper consolidation remains open as a later batch.

## Next Batch

Migrate the self-thought/research-request context group:
`xinyu_self_thought_loop.py` and `xinyu_expression_self_learning.py`.

# XinYu Self Thought Expression Knowledge Path - 2026-05-17

Status: applied as a single self-thought/research-request migration.

## Batch Scope

- Capability group: self-thought research context and expression self-learning
  source-request staging.
- Goal: replace hard-coded `memory/knowledge/...` reads/writes in the two
  runtime modules with `knowledge_file_path(...)`, without changing proactive
  focus selection or source request rendering.

## Completed

- Updated `xinyu_self_thought_loop.py`.
  - Added local `_knowledge(root, filename)` helper.
  - Migrated research snapshot reads for:
    - `source_requests.md`
    - `source_search_provider_state.md`
    - `source_search_resolver_state.md`
    - `autonomous_search_activation_state.md`
- Updated `xinyu_expression_self_learning.py`.
  - Added local `_knowledge(root, filename)` helper.
  - Migrated source request upsert path for `source_requests.md`.

## Validation

Passed:

```powershell
.\.venv\Scripts\python.exe -m py_compile xinyu_self_thought_loop.py xinyu_expression_self_learning.py xinyu_storage_paths.py
rg -n -F 'memory/knowledge' .\xinyu_self_thought_loop.py .\xinyu_expression_self_learning.py
.\.venv\Scripts\python.exe -m pytest tests\test_expression_self_learning.py tests\test_learning_closed_loop.py
.\.venv\Scripts\python.exe tests\smoke\initiative\self_thought_loop_smoke.py
.\.venv\Scripts\python.exe tests\smoke\learning\integration\research_handoff_smoke.py --restore-after --diff-lines 0
.\.venv\Scripts\python.exe tests\smoke\learning\integration\source_request_planner_smoke.py --restore-after --require-plan --diff-lines 0
git diff --check -- XinYu-Core/examples/agent-apps/xinyu/xinyu_self_thought_loop.py XinYu-Core/examples/agent-apps/xinyu/xinyu_expression_self_learning.py
```

Results:

- Focused pytest set: 29 passed.
- Self thought loop smoke: passed.
- Research handoff smoke: passed.
- Source request planner smoke: passed.
- Restore-after completed where supported.
- Hard-coded knowledge path check in touched files: no matches.
- Diff check: whitespace clean; only CRLF normalization warnings.

## Not Changed

- Non-knowledge context, dream, reflection, proactive, runtime, and self paths
  remain unchanged.
- No knowledge files or private memory bodies were moved.
- No raw private contents were printed.
- No git commit was made.

## Remaining

- Active hard-coded knowledge paths remain in github autonomous learning,
  learning library staging, question pipeline/social inquiry, inner cycle/
  manifest, selected review/ops/manual/probe tools, and a few trace constants.
- Neuro-inspired rule traceability remains open.
- Duplicate bridge/helper consolidation remains open as a later batch.

## Next Batch

Migrate the github autonomous learning/library staging group:
`custom/github_autonomous_learning_engine.py` and `xinyu_learning_library.py`.

# XinYu Review Core Knowledge Ref - 2026-05-17

Status: applied as a single review/core knowledge reference migration.

## Batch Scope

- Capability group: AI self-iteration review proposals, review inbox learning
  quality items, and core prompt-context signature refs.
- Goal: remove direct `memory/knowledge/...` literals from these runtime-facing
  modules while preserving compatible reference text via `knowledge_ref(...)`
  and using `knowledge_file_path(...)` for actual reads.

## Completed

- Updated `custom/ai_self_iteration_review_engine.py`.
  - Replaced proposal references to `integration_policy.md` with
    `knowledge_ref("integration_policy.md")`.
- Updated `xinyu_review_inbox.py`.
  - Replaced `LEARNING_QUALITY_REL` with `LEARNING_QUALITY_FILENAME`.
  - Reads `learning_quality_state.md` through `knowledge_file_path(...)`.
  - Emits source path through `knowledge_ref(...)`.
- Updated `xinyu_core_bridge.py`.
  - Replaced prompt signature knowledge refs for `ai_domain.md` and
    `social_inquiry_policy.md` with `knowledge_ref(...)`.

## Validation

Passed:

```powershell
.\.venv\Scripts\python.exe -m py_compile custom\ai_self_iteration_review_engine.py xinyu_review_inbox.py xinyu_core_bridge.py xinyu_storage_paths.py
rg -n -F 'memory/knowledge' .\custom\ai_self_iteration_review_engine.py .\xinyu_review_inbox.py .\xinyu_core_bridge.py
.\.venv\Scripts\python.exe tests\smoke\initiative\integration\ai_self_iteration_review_smoke.py --restore-after --diff-lines 0
.\.venv\Scripts\python.exe tests\smoke\tools\xinyu_review_inbox_smoke.py
.\.venv\Scripts\python.exe tests\smoke\bridge\bridge_renderer_guard_flags_smoke.py
git diff --check -- XinYu-Core/examples/agent-apps/xinyu/custom/ai_self_iteration_review_engine.py XinYu-Core/examples/agent-apps/xinyu/xinyu_review_inbox.py XinYu-Core/examples/agent-apps/xinyu/xinyu_core_bridge.py
```

Results:

- AI self-iteration review smoke: passed.
- Review inbox smoke: passed.
- Bridge renderer guard flags smoke: passed.
- Hard-coded knowledge path check in touched files: no matches.
- Diff check: whitespace clean; only CRLF normalization warnings.

Known unrelated validation gap:

- `tests/smoke/bridge/bridge_values_smoke.py` currently fails because it imports
  `_optional_int` from `xinyu_core_bridge.py`, but that name is not exported by
  the current module. This failure is unrelated to the knowledge-ref migration;
  bridge import/runtime was covered by py_compile and renderer guard smoke.

## Not Changed

- Compatible visible/reference values remain `memory/knowledge/<filename>` via
  `knowledge_ref(...)`.
- No knowledge files or private memory bodies were moved.
- No raw private contents were printed.
- No git commit was made.

## Remaining

- Active hard-coded knowledge paths remain in ops/probe/status/manual tools and
  trace constants.
- Neuro-inspired rule traceability remains open.
- Duplicate bridge/helper consolidation remains open as a later batch.

## Next Batch

Migrate ops/probe/status knowledge paths:
`ops/probes/xinyu_research_loop_dry_run.py` and
`ops/validation/long_run_status.py`.

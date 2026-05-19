# XinYu Question Social Knowledge Path - 2026-05-17

Status: applied as a single question/social migration.

## Batch Scope

- Capability group: question pipeline and social inquiry policy.
- Goal: replace hard-coded `memory/knowledge/...` reads/writes in question and
  social inquiry runtime code with `knowledge_file_path(...)`, without changing
  question classification, source routing, or social inquiry policy decisions.

## Completed

- Updated `custom/question_pipeline_engine.py`.
  - Added local `_knowledge(root, filename)` helper.
  - Migrated reads/writes for `general.md` and `source_notes.md`.
- Updated `custom/social_inquiry_policy_engine.py`.
  - Added local `_knowledge(root, filename)` helper.
  - Migrated reads/writes for:
    - `social_inquiry_answers.md`
    - `social_inquiry_policy_state.md`
    - `source_notes.md`

## Validation

Passed:

```powershell
.\.venv\Scripts\python.exe -m py_compile custom\question_pipeline_engine.py custom\question_pipeline_bridge_plugin.py custom\social_inquiry_policy_engine.py xinyu_storage_paths.py
rg -n -F 'memory/knowledge' .\custom\question_pipeline_engine.py .\custom\social_inquiry_policy_engine.py
.\.venv\Scripts\python.exe tests\smoke\learning\integration\question_pipeline_smoke.py --restore-after --diff-lines 0
.\.venv\Scripts\python.exe tests\smoke\dialogue\integration\social_inquiry_policy_smoke.py --restore-after --diff-lines 0
.\.venv\Scripts\python.exe tests\smoke\learning\integration\ai_domain_source_smoke.py --restore-after --diff-lines 0
git diff --check -- XinYu-Core/examples/agent-apps/xinyu/custom/question_pipeline_engine.py XinYu-Core/examples/agent-apps/xinyu/custom/social_inquiry_policy_engine.py
```

Results:

- Question pipeline smoke: passed.
- Social inquiry policy smoke: passed.
- AI domain source smoke: passed.
- Restore-after completed for smokes.
- Hard-coded knowledge path check in touched files: no matches.
- Diff check: whitespace clean; only CRLF normalization warnings.

## Not Changed

- Context paths for active questions, question states, exploration queue, and
  social inquiry candidates remain unchanged.
- No knowledge files or private memory bodies were moved.
- No raw private contents were printed.
- No git commit was made.

## Remaining

- Active hard-coded knowledge paths remain in inner cycle/manifest, selected
  review/ops/manual/probe tools, and trace constants.
- Neuro-inspired rule traceability remains open.
- Duplicate bridge/helper consolidation remains open as a later batch.

## Next Batch

Migrate the inner cycle status/manifest group:
`custom/inner_cycle_engine.py` and `custom/inner_framework_manifest.py`.

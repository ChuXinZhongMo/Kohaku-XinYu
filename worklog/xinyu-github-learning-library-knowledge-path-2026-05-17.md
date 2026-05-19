# XinYu GitHub Learning Library Knowledge Path - 2026-05-17

Status: applied as a single github/library staging migration.

## Batch Scope

- Capability group: GitHub autonomous learning and learning-library source
  material staging.
- Goal: replace hard-coded `memory/knowledge/...` reads/writes in runtime
  staging code with `knowledge_file_path(...)`, without changing candidate
  discovery, duplicate detection, or source material staging behavior.

## Completed

- Updated `custom/github_autonomous_learning_engine.py`.
  - Replaced `CANDIDATES_REL` with `CANDIDATES_FILENAME`.
  - Added local `_knowledge(root, filename)` helper.
  - Migrated candidate and source material paths for:
    - `github_learning_candidates.md`
    - `source_materials.md`
- Updated `xinyu_learning_library.py`.
  - Added local `_knowledge(root, filename)` helper.
  - Migrated source material staging path for `source_materials.md`.
  - Reworded CLI help to avoid recommending a raw storage path.

## Validation

Passed:

```powershell
rg -n -F 'memory/knowledge' .\custom\github_autonomous_learning_engine.py .\xinyu_learning_library.py
.\.venv\Scripts\python.exe -m py_compile custom\github_autonomous_learning_engine.py custom\github_autonomous_learning_bridge_plugin.py xinyu_learning_library.py xinyu_storage_paths.py
.\.venv\Scripts\python.exe -m pytest tests\test_learning_library_quality.py
.\.venv\Scripts\python.exe tests\smoke\learning\learning_library_smoke.py
.\.venv\Scripts\python.exe tests\smoke\learning\github_autonomous_learning_smoke.py
git diff --check -- XinYu-Core/examples/agent-apps/xinyu/custom/github_autonomous_learning_engine.py XinYu-Core/examples/agent-apps/xinyu/xinyu_learning_library.py
```

Results:

- Learning library quality tests: 4 passed.
- Learning library smoke: passed.
- GitHub autonomous learning smoke: passed.
- Hard-coded knowledge path check in touched files: no matches.
- Diff check: whitespace clean; only CRLF normalization warnings.

## Not Changed

- GitHub learning config/state/trace paths remain in their existing context and
  runtime stores.
- No repository code is executed by this lane.
- No knowledge files or private memory bodies were moved.
- No raw private contents were printed.
- No git commit was made.

## Remaining

- Active hard-coded knowledge paths remain in question pipeline/social inquiry,
  inner cycle/manifest, selected review/ops/manual/probe tools, and trace
  constants.
- Neuro-inspired rule traceability remains open.
- Duplicate bridge/helper consolidation remains open as a later batch.

## Next Batch

Migrate the question pipeline/social inquiry group:
`custom/question_pipeline_engine.py` and
`custom/social_inquiry_policy_engine.py`.

# XinYu Storage Boundary Table - 2026-05-17

Status: applied as canonical/legacy storage boundary metadata and tests.

## Batch Scope

- Capability group: storage path boundaries.
- Goal: make cases, public datasets, and mixed knowledge storage boundaries
  explicit and testable without moving private memory bodies.

## Completed

- Added `STORAGE_BOUNDARY_TABLE` and `storage_boundary_table()` to
  `xinyu_storage_paths.py`.
- Declared:
  - `cases.conversation`: canonical `cases/conversation`, legacy fallback
    `data/conversation_experience`.
  - `library.datasets`: canonical `library/datasets`, legacy fallback
    `data/external`.
  - `memory.knowledge`: current mixed `memory/knowledge`, pending future
    library split.
- Added `tests/test_storage_paths.py` coverage for:
  - canonical/legacy table shape.
  - cases canonical priority over legacy fallback.
  - public dataset canonical source directories before legacy source
    directories.
  - existing knowledge bare-filename guard behavior.

## Validation

Passed:

```powershell
.\.venv\Scripts\python.exe -m py_compile xinyu_storage_paths.py tests\test_storage_paths.py xinyu_public_dataset_registry.py xinyu_public_dataset_case_importer.py xinyu_conversation_experience_cases.py
.\.venv\Scripts\python.exe -m pytest -q tests\test_storage_paths.py tests\test_public_dataset_registry.py tests\test_public_dataset_case_importer.py tests\test_conversation_experience_cases.py tests\test_conversation_experience_matcher.py tests\test_memory_library_manifest.py
.\.venv\Scripts\python.exe ops\validation\validate_memory_library_manifest.py --json
.\.venv\Scripts\python.exe tests\smoke\dialogue\conversation_experience_cases_smoke.py
.\.venv\Scripts\python.exe tests\smoke\dialogue\conversation_experience_sidecar_smoke.py
.\.venv\Scripts\python.exe tools\conversation_experience_cases.py import-public --dataset-id lufy --dataset lufy --limit 1 --dry-run
git diff --check -- XinYu-Core/examples/agent-apps/xinyu/xinyu_storage_paths.py XinYu-Core/examples/agent-apps/xinyu/tests/test_storage_paths.py
```

Results:

- Focused storage/case/manifest tests: `43 passed`.
- Memory/library manifest validation: `ok: true`.
- Conversation experience cases smoke: passed.
- Conversation experience sidecar smoke: passed.
- Public dataset dry-run import generated one pending abstract case and wrote
  nothing.
- Diff check: clean.

## Not Changed

- No private memory or raw dataset contents were moved.
- No legacy path was removed.
- No raw QQ/private memory/log content was printed.
- No git commit was made.

## Remaining

- Many source/learning modules still hard-code `memory/knowledge/...`.
  They should be migrated in capability-sized batches to
  `knowledge_file_path(...)`.
- The current boundary intentionally marks `memory/knowledge` as mixed and
  pending a future library split.

## Next Batch

Start migrating one source/learning subgroup from hard-coded
`memory/knowledge/...` paths to `knowledge_file_path(...)`. Keep each batch to
one pipeline group and run its focused smoke.

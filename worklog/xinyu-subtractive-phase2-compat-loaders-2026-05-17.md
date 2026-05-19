# XinYu Subtractive Phase 2 - Compatibility Loaders - 2026-05-17

Status: batch 1 complete.

## Scope

This batch did not move private memory, raw public datasets, or reviewed case
files. It added compatibility loaders so the future target paths can be used
before the legacy live paths are removed.

## Changes

- Added `xinyu_storage_paths.py` as the storage path owner for this slice.
- Public dataset registry lookup now resolves:
  - `cases/conversation/public_dataset_registry.json`
  - fallback: `XinYu-Core/examples/agent-apps/xinyu/data/conversation_experience/public_dataset_registry.json`
- Seed owner case lookup now resolves:
  - `cases/conversation/seed_owner_cases.jsonl`
  - fallback: `XinYu-Core/examples/agent-apps/xinyu/data/conversation_experience/seed_owner_cases.jsonl`
- Public dataset inputs now resolve alias/path candidates through:
  - `library/datasets/`
  - fallback: `XinYu-Core/examples/agent-apps/xinyu/data/external/`
- Updated public dataset import and contextual replay to use the resolver.
- Added the resolver to runtime source digest awareness.
- Added boundary docs:
  - `cases/conversation/README.md`
  - `library/datasets/README.md`
- Updated `PUBLIC-DATA-REPLAY.md`, `cases/README.md`, and `library/README.md`.

## Validation

Passed:

```powershell
.\.venv\Scripts\python.exe -m py_compile xinyu_storage_paths.py xinyu_public_dataset_registry.py xinyu_conversation_experience_cases.py xinyu_public_dataset_case_importer.py xinyu_contextual_self_replay.py xinyu_runtime_security.py
```

Passed:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_public_dataset_registry.py tests\test_conversation_experience_cases.py tests\test_public_dataset_case_importer.py tests\test_contextual_self_replay.py tests\test_code_awareness.py -q
```

Result:

```text
32 passed
```

Passed:

```powershell
.\.venv\Scripts\python.exe smoke_run.py --group replay
```

Result:

```text
21 passed
smoke_run group=replay: ok
```

## Remaining

- Do not delete legacy `data/conversation_experience` or `data/external` yet.
- Next safe subtraction target is the custom gate/plugin chain: classify live
  config plugins, then route maintenance/review gates through one owner or move
  inactive experiments toward `lab`.

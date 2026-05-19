# XinYu Mutation Smoke Restore Guard Batch

Date: 2026-05-18
Plan: `plan-next-3.md` Batch 1

## Completed

- Added `ops/validation/mutation_smoke_restore_guard.py`.
- Added `tests/test_mutation_smoke_restore_guard.py`.
- Generated restore-safety reports:
  - `worklog/xinyu-mutation-smoke-restore-guard-2026-05-18.md`
  - `worklog/xinyu-mutation-smoke-restore-guard-2026-05-18.json`

## Result

- total_smokes: 22
- mutation_capable_count: 19
- restore_after_supported_count: 19
- diff_suppression_supported_count: 19
- missing_restore_count: 0
- missing_diff_suppression_count: 0

## Validation

- `.\.venv\Scripts\python.exe -m py_compile ops\validation\mutation_smoke_restore_guard.py tests\test_mutation_smoke_restore_guard.py`
- `.\.venv\Scripts\python.exe -m pytest tests\test_mutation_smoke_restore_guard.py -q`
  - Result: 2 passed.
- `.\.venv\Scripts\python.exe ops\validation\mutation_smoke_restore_guard.py --repo-root D:\XinYu --strict ...`
  - Result: passed.

## Rule For Future Batches

- Mutation-capable source/memory smokes must be run with `--restore-after`.
- When available, also pass `--diff-lines 0` to avoid printing memory body diffs.

## Remaining

- Continue `plan-next-3.md` Batch 2: prune dead local I/O helper definitions in source engines.

# XinYu Commit Readiness Audit

Generated from `git status --short` paths plus metadata-only validation reports.
It does not read or print private memory bodies, raw QQ payload bodies, tokens, or secrets.

- status: ready_for_review
- total_dirty_entries: 1001
- package_count: 8
- unknown_entry_count: 0
- boundary_status: pass
- archive_delete_holds: 0

## Package Overview

| package | risk | count | action |
| --- | --- | ---: | --- |
| P00 docs-worklogs-plans | low | 49 | keep_docs_review |
| P01 ops-validation-tools | medium | 378 | keep_ops_validation |
| P02 tests-smokes-regression | medium | 109 | keep_regression_tests |
| P03 core-runtime-services-stores | high | 170 | merge_review_core_runtime |
| P04 adapters-bridges-io | high | 30 | merge_review_adapters |
| P05 desktop-shell | medium | 18 | keep_desktop_shell |
| P06 memory-data-review-only | high | 5 | keep_memory_data_review_only |
| P07 archive-delete-candidates | medium | 242 | archive_delete_review |

## Review Order

- `P00`
- `P01`
- `P02`
- `P03`
- `P04`
- `P05`
- `P06`
- `P07`

## Archive/Delete Decisions

- accept_delete_no_live_refs: 7
- accept_delete_relocated: 235

## Closeout Summary

### kept
- P00 docs-worklogs-plans (49 paths)
- P01 ops-validation-tools (378 paths)
- P02 tests-smokes-regression (109 paths)
- P05 desktop-shell (18 paths)
- P06 memory-data-review-only (5 paths)

### merged
- P03 core-runtime-services-stores (170 paths)
- P04 adapters-bridges-io (30 paths)

### archived
- 235 cleanup deletions have relocated replacements.

### deleted
- 7 cleanup deletions have no live references in the audit.

### hold
- none

## Remaining Risks

- High-risk packages need behavior review: P03 core-runtime-services-stores, P04 adapters-bridges-io, P06 memory-data-review-only.
- P06 memory-data remains review-only; do not auto-delete or move private bodies.
- 11 orphan runtime-state paths are intentionally held for manual ownership review.

## Required Validation

- `git diff --check`
- `.\.venv\Scripts\python.exe -m pytest tests -q`
- `.\.venv\Scripts\python.exe smoke_run.py --group quick --restore-after --timeout-seconds 300`
- `npm run typecheck`
- `npm run build`

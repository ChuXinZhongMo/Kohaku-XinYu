# XinYu P70 Module Ecology Full Audit Batch - 2026-05-19

## Scope

Batch: full-field module ecology audit.

Goal: turn `xinyu_module_ecology_audit.py` from an advisory provider into a
repeatable CLI/report path, then run it across the current app tree without
printing memory/runtime/data/library/cases bodies.

## Completed

- Added CLI support to `xinyu_module_ecology_audit.py`.
  - `--root`
  - `--output`
  - `--json`
  - `--status-file`
  - `--no-git-status`
  - `--max-items`
- Added git status integration so deleted worktree paths are included in the
  ecology table even when the file no longer exists.
- Added report self-noise controls.
  - Skips `ops/reports`.
  - Treats `learning/` as lab material.
  - Treats `data/` as stores boundary metadata.
  - Treats `pytest.ini` and `*.example` as ops metadata.
  - Excludes lab/learning/archive/project-plan/report references from live
    reference counts.
  - Avoids generic stem false positives such as `metadata`, `readme`, and
    `init`.
- Added tests for:
  - CLI report writing.
  - deleted git status paths entering the audit.
  - learning/data/metadata bucket classification.
  - generated reports and learning snapshots not inflating live references.
  - generic filename stem filtering.
- Generated full audit report:
  - `ops/reports/module_ecology_audit_2026-05-19.md`

## Report Summary

- item_count: 1515
- kept: 1041
- merged: 0
- archived: 227
- deleted: 247

Bucket counts:

- adapters: 70
- archive: 8
- core: 293
- delete: 247
- lab: 679
- ops: 189
- services: 8
- stores: 21

Decision counts:

- archive_candidate_lab_stale: 182
- archive_candidate_no_live_refs: 37
- archive_keep_historical: 8
- delete_candidate_requires_reference_audit: 247
- keep_active_niche: 544
- keep_lab_shadow: 497

## Validation

- `.\.venv\Scripts\python.exe -m py_compile xinyu_module_ecology_audit.py tests\test_module_ecology_audit.py`
  - pass
- `.\.venv\Scripts\python.exe -m pytest tests\test_module_ecology_audit.py -q`
  - 12 passed
- `.\.venv\Scripts\python.exe -m pytest tests\test_module_ecology_audit.py tests\test_archive_delete_reference_audit.py tests\test_boundary_readiness_audit.py -q`
  - 18 passed
- `.\.venv\Scripts\python.exe -m pytest tests -q`
  - 655 passed
- `.\.venv\Scripts\python.exe smoke_run.py --group quick --timeout-seconds 180 --json`
  - ok=true
- `git diff --check -- xinyu_module_ecology_audit.py tests/test_module_ecology_audit.py ops/reports/module_ecology_audit_2026-05-19.md`
  - pass

## Remaining

- No files were deleted or moved in this batch.
- 247 delete candidates still need archive/delete reference audit evidence
  before the current worktree deletions can be accepted as safe cleanup.
- 227 archive candidates are advisory. They need owner review or a follow-up
  archive batch before any move/delete action.
- `merged` is 0 in this report because no duplicate/canonical shim map was
  supplied to this full-field scan.
- Desktop typecheck/build was not rerun because this batch did not touch
  desktop source.

## Recovery Point

Start from:

`D:\XinYu\XinYu-Core\examples\agent-apps\xinyu`

Highest-value next batch:

Run archive/delete reference evidence over the 247 delete candidates, then
produce a compact accept/hold table. Do not delete or move anything without
that evidence.

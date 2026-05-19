# XinYu P72 Module Ecology Archive Candidate Filter Batch - 2026-05-19

## Scope

Batch: archive-candidate review surface after P70/P71.

Goal: make the 219 advisory archive candidates easy to review without scanning
the full 1515-item ecology report.

## Completed

- Added filtering support to `xinyu_module_ecology_audit.py`.
  - `--decision-prefix`, repeatable.
  - `--bucket`, repeatable.
  - `filter_module_ecology_audit(...)` for direct testable use.
- Added tests for:
  - decision-prefix filtering.
  - bucket filtering.
  - CLI filtered report generation.
- Regenerated the full module ecology report:
  - `ops/reports/module_ecology_audit_2026-05-19.md`
- Generated archive-candidate-only report:
  - `ops/reports/module_ecology_archive_candidates_2026-05-19.md`

## Archive Candidate Summary

- item_count: 219
- archived: 219
- kept: 0
- merged: 0
- deleted: 0

Bucket counts:

- core: 18
- lab: 182
- ops: 19

Decision counts:

- archive_candidate_lab_stale: 182
- archive_candidate_no_live_refs: 37

Direct effect:

- P70 full ecology table stays as the complete audit.
- P72 adds a compact review list for only the actionable archive candidates.
- No move/delete action was taken.

## Validation

- `.\.venv\Scripts\python.exe -m py_compile xinyu_module_ecology_audit.py tests\test_module_ecology_audit.py`
  - pass
- `.\.venv\Scripts\python.exe -m pytest tests\test_module_ecology_audit.py -q`
  - 14 passed
- `.\.venv\Scripts\python.exe -m pytest tests\test_module_ecology_audit.py tests\test_archive_delete_reference_audit.py tests\test_git_change_group_audit.py tests\test_boundary_readiness_audit.py -q`
  - 25 passed
- `.\.venv\Scripts\python.exe -m pytest tests -q`
  - 659 passed
- `.\.venv\Scripts\python.exe smoke_run.py --group quick --timeout-seconds 180 --json`
  - ok=true
- `git diff --check -- xinyu_module_ecology_audit.py tests/test_module_ecology_audit.py ops/reports/module_ecology_archive_candidates_2026-05-19.md ops/reports/module_ecology_audit_2026-05-19.md`
  - pass

## Remaining

- The archive-candidate report is advisory only.
- The 18 core candidates require more care than lab/doc candidates before any
  archive action.
- The 19 ops candidates are mostly old docs/manual wrappers and should be
  reviewed for current runbook value before archiving.
- Desktop typecheck/build was not rerun because no desktop source changed.

## Recovery Point

Start from:

`D:\XinYu\XinYu-Core\examples\agent-apps\xinyu`

Highest-value next batch:

Triage the 18 core archive candidates first. For each one, prove either
`false_positive_keep`, `compat_needed`, or `archive_ready`. Do not move files
until the core list is classified.

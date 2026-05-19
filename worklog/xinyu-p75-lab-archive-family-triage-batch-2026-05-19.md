# XinYu P75 Lab Archive Family Triage Batch - 2026-05-19

## Scope

Batch: lab archive candidate family triage after P74.

Goal: avoid one-by-one churn over lab artifacts, remove test-runner false
positives, and classify remaining lab archive candidates by family.

## Completed

- Improved `xinyu_module_ecology_audit.py`.
  - Treats pytest-collected `tests/test_*.py` files as active lab assets.
  - Treats `tests/conftest.py` as an active pytest support file.
- Added tests for pytest collection signals.
- Regenerated reports:
  - `ops/reports/module_ecology_audit_2026-05-19.md`
  - `ops/reports/module_ecology_archive_candidates_2026-05-19.md`
- Added lab family triage report:
  - `ops/reports/module_ecology_lab_archive_family_triage_2026-05-19.md`

## Latest Ecology Counts

Full ecology report:

- item_count: 1515
- kept: 1125
- archived: 143
- deleted: 247
- archive_candidate_lab_stale: 105
- archive_candidate_no_live_refs: 30
- keep_lab_shadow: 574

Archive-candidate-only report:

- item_count: 135
- core: 11
- lab: 105
- ops: 19

Lab family triage:

- learning/self_found: 33
- learning/owner_supplied: 2
- project-plans: 17
- tests/smoke: 53

## Direct Effect

- Normal pytest tests are no longer mislabeled as stale lab assets.
- Remaining lab candidates are grouped by cleanup strategy:
  - external snapshots can be archived by snapshot folder.
  - owner-supplied artifacts are held for boundary review.
  - stale plans need plan-index extraction.
  - smoke scripts need smoke inventory review.
- No files were moved or deleted.

## Validation

- `.\.venv\Scripts\python.exe -m py_compile xinyu_module_ecology_audit.py tests\test_module_ecology_audit.py`
  - pass
- `.\.venv\Scripts\python.exe -m pytest tests\test_module_ecology_audit.py -q`
  - 18 passed
- `.\.venv\Scripts\python.exe -m pytest tests\test_module_ecology_audit.py tests\test_archive_delete_reference_audit.py tests\test_git_change_group_audit.py tests\test_boundary_readiness_audit.py -q`
  - 29 passed
- `.\.venv\Scripts\python.exe -m pytest tests -q`
  - 663 passed
- `.\.venv\Scripts\python.exe smoke_run.py --group quick --timeout-seconds 180 --json`
  - ok=true
- `git diff --check -- xinyu_module_ecology_audit.py tests/test_module_ecology_audit.py ops/reports/module_ecology_audit_2026-05-19.md ops/reports/module_ecology_archive_candidates_2026-05-19.md ops/reports/module_ecology_lab_archive_family_triage_2026-05-19.md`
  - pass

## Remaining

- Archive candidates are classified but not moved.
- The remaining high-value cleanup work is now action-specific:
  - smoke inventory review for 53 stale smoke scripts.
  - plan-index extraction for 17 stale plans.
  - owner-supplied material boundary review for 2 files.
  - core/ops archive moves only after explicit keep/archive policy decisions.
- Desktop typecheck/build was not rerun because no desktop source changed.

## Recovery Point

Start from:

`D:\XinYu\XinYu-Core\examples\agent-apps\xinyu`

Highest-value next batch:

Build a smoke inventory review that compares `tests/smoke/**/*_smoke.py`
against `smoke_run.py` groups and marks each stale smoke as
`covered`, `manual_only`, or `archive_ready`.

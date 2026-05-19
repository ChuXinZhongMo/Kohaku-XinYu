# XinYu P73 Core Archive Candidate Triage Batch - 2026-05-19

## Scope

Batch: high-risk core archive candidate triage after P72.

Goal: reduce false positives in core archive candidates, then classify the
remaining core candidates without moving or deleting files.

## Completed

- Improved `xinyu_module_ecology_audit.py` reference detection.
  - Added AST import parsing for Python files.
  - Recognizes absolute dotted imports such as `xinyu_v1.types`.
  - Recognizes relative imports such as `from .models import ...` and
    `from ..types import ...`.
- Added tests for:
  - dotted imports to generic-stem modules such as `types.py`.
  - relative imports to generic-stem modules such as `models.py`.
- Regenerated reports:
  - `ops/reports/module_ecology_audit_2026-05-19.md`
  - `ops/reports/module_ecology_archive_candidates_2026-05-19.md`
- Added core triage report:
  - `ops/reports/module_ecology_core_archive_triage_2026-05-19.md`

## Latest Ecology Counts

Full ecology report:

- item_count: 1515
- kept: 1048
- merged: 0
- archived: 220
- deleted: 247
- archive_candidate_lab_stale: 182
- archive_candidate_no_live_refs: 30
- keep_active_niche: 551
- keep_lab_shadow: 497

Archive-candidate-only report:

- item_count: 212
- core: 11
- lab: 182
- ops: 19

Core triage:

- core_candidates_after_import_fix: 11
- false_positive_keep: 0
- compat_needed: 5
- archive_ready: 6

## Direct Effect

- `xinyu_v1/gateway/models.py`, `xinyu_v1/types.py`, and v1 model modules that
  are imported by tests or runtime source are no longer incorrectly listed as
  archive candidates.
- Remaining core candidates now have an explicit keep/archive classification
  surface before any move/delete action.
- No files were moved or deleted.

## Validation

- `.\.venv\Scripts\python.exe -m py_compile xinyu_module_ecology_audit.py tests\test_module_ecology_audit.py`
  - pass
- `.\.venv\Scripts\python.exe -m pytest tests\test_module_ecology_audit.py -q`
  - 16 passed
- `.\.venv\Scripts\python.exe -m pytest tests\test_module_ecology_audit.py tests\test_archive_delete_reference_audit.py tests\test_git_change_group_audit.py tests\test_boundary_readiness_audit.py -q`
  - 27 passed
- `.\.venv\Scripts\python.exe -m pytest tests -q`
  - 661 passed
- `.\.venv\Scripts\python.exe smoke_run.py --group quick --timeout-seconds 180 --json`
  - ok=true
- `git diff --check -- xinyu_module_ecology_audit.py tests/test_module_ecology_audit.py ops/reports/module_ecology_audit_2026-05-19.md ops/reports/module_ecology_archive_candidates_2026-05-19.md ops/reports/module_ecology_core_archive_triage_2026-05-19.md`
  - pass

## Remaining

- The 6 `archive_ready` core candidates are still only classified; they were not
  moved.
- The 5 `compat_needed` core candidates need explicit policy decisions before
  pruning.
- Lab and ops archive candidates still need their own lower-risk triage pass.
- Desktop typecheck/build was not rerun because no desktop source changed.

## Recovery Point

Start from:

`D:\XinYu\XinYu-Core\examples\agent-apps\xinyu`

Highest-value next batch:

Triage the 19 ops archive candidates. Most are old docs/manual wrappers; decide
`keep_doc`, `archive_doc`, or `merge_into_index` before moving anything.

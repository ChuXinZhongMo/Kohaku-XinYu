# XinYu P68 Module Ecology Audit Batch - 2026-05-19

## Scope

Plan: `project-plans/XINYU-CROSS-DOMAIN-SYNAESTHESIA-PLAN-2026-05-19.md`

Batch: F / ecology and gardening mapping.

Goal: add a module ecology audit provider that assigns modules to a bucket,
niche, activity signal, and retirement rule before merge/archive/delete
decisions. This is an advisory audit only; it does not move, delete, or rewrite
files.

## Changes Completed

- Added `xinyu_module_ecology_audit.py`.
  - Defines `ModuleEcologyItem`.
  - Classifies buckets:
    - core
    - adapters
    - stores
    - services
    - ops
    - lab
    - archive
    - delete
    - unknown
  - Produces decisions:
    - `keep_active_niche`
    - `merge_keep_compat_shim`
    - `archive_keep_historical`
    - `keep_lab_shadow`
    - `archive_candidate_lab_stale`
    - `archive_candidate_no_live_refs`
    - `delete_candidate_requires_reference_audit`
    - `classify_before_change`
  - Builds audits from module paths and source/doc reference counts while
    skipping memory/runtime/data/library/cases bodies.
  - Renders kept/merged/archived/deleted counts.
- Added `tests/test_module_ecology_audit.py`.
  - Covers active core keep.
  - Covers duplicate shim merge.
  - Covers deleted candidate requiring reference audit.
  - Covers stale lab archive candidate.
  - Covers private memory body skip.
  - Covers report summary counts.

## Validation

- `.\.venv\Scripts\python.exe -m py_compile xinyu_module_ecology_audit.py tests\test_module_ecology_audit.py`
  - pass
- `.\.venv\Scripts\python.exe -m pytest tests\test_module_ecology_audit.py tests\test_archive_delete_reference_audit.py tests\test_boundary_readiness_audit.py tests\test_cross_domain_synaesthesia_registry.py -q`
  - 16 passed
- `git diff --check -- xinyu_module_ecology_audit.py tests\test_module_ecology_audit.py`
  - pass

Full suite and desktop build were not run yet. A cross-domain focused matrix
should run next.

## Direct Effect

- XinYu now has a repeatable ecology-style method for deciding whether a module
  is kept, merged, archived, or delete-candidate.
- The audit gives every module a niche and retirement rule before cleanup.
- This supports subtractive cleanup without unsafe deletion in the current dirty
  worktree.

## Remaining

- Run cross-domain focused matrix across all A-F providers.
- Later integration batch: wire triage/error/immune/slow-state prompt blocks
  into runtime context in a narrow advisory pass.
- Optional later audit: run module ecology audit over the current app path and
  review top merge/archive candidates.

## Recovery Point

Start from:

`D:\XinYu\XinYu-Core\examples\agent-apps\xinyu`

Recently changed:

- `xinyu_module_ecology_audit.py`
- `tests/test_module_ecology_audit.py`

Recommended resume check:

`.\.venv\Scripts\python.exe -m pytest tests\test_module_ecology_audit.py tests\test_archive_delete_reference_audit.py tests\test_boundary_readiness_audit.py tests\test_cross_domain_synaesthesia_registry.py -q`

# XinYu P71 Archive/Delete Reference Evidence Batch - 2026-05-19

## Scope

Batch: archive/delete reference evidence after P70 module ecology audit.

Goal: take the P70 `delete` bucket and produce concrete relocation/reference
evidence before accepting the worktree deletions as cleanup.

## Completed

- Generated delete evidence report:
  - `ops/reports/archive_delete_reference_audit_2026-05-19.md`
- Updated `ops/validation/archive_delete_reference_audit.py`.
  - Treats `ops/archive/` as a valid relocation destination.
  - Treats `ops/validation/` as a valid relocation destination.
  - Ignores `ops/reports/` as generated report noise.
  - Adds `root_validator` and `root_probe` candidate kinds.
- Updated `ops/validation/git_change_group_audit.py`.
  - Includes the remaining deleted root validation/probe scripts in
    `archive/delete` when status is deleted:
    - `sync_memory_seeds.py`
    - `validate_inner_framework.py`
    - `validate_scaffold.py`
    - `xinyu_live_module_diagnostics.py`
    - `xinyu_research_loop_dry_run.py`
- Added regression tests for:
  - `ops/archive` relocation acceptance.
  - `ops/validation` relocation acceptance.
  - generated report references being ignored.
  - deleted root validators/probes being grouped as `archive/delete`.

## Evidence Summary

- total_candidates: 247
- accept_delete_relocated: 247
- hold_delete_referenced: 0

Kind counts:

- cleanup_candidate: 6
- custom_manifest: 7
- root_diagnostic: 3
- root_manual_runner: 14
- root_probe: 2
- root_smoke: 212
- root_validator: 3

Direct effect:

- P70 reported 247 delete-bucket paths.
- P71 now has relocation evidence for all 247.
- No delete candidate remains in hold state.

## Validation

- `.\.venv\Scripts\python.exe -m py_compile ops\validation\archive_delete_reference_audit.py ops\validation\git_change_group_audit.py tests\test_archive_delete_reference_audit.py tests\test_git_change_group_audit.py`
  - pass
- `.\.venv\Scripts\python.exe -m pytest tests\test_archive_delete_reference_audit.py tests\test_git_change_group_audit.py -q`
  - 8 passed
- `.\.venv\Scripts\python.exe -m pytest tests\test_archive_delete_reference_audit.py tests\test_git_change_group_audit.py tests\test_module_ecology_audit.py tests\test_boundary_readiness_audit.py -q`
  - 23 passed
- `.\.venv\Scripts\python.exe -m pytest tests -q`
  - 657 passed
- `.\.venv\Scripts\python.exe smoke_run.py --group quick --timeout-seconds 180 --json`
  - ok=true
- `git diff --check -- ops/validation/archive_delete_reference_audit.py ops/validation/git_change_group_audit.py tests/test_archive_delete_reference_audit.py tests/test_git_change_group_audit.py ops/reports/archive_delete_reference_audit_2026-05-19.md`
  - pass

## Remaining

- No files were deleted or moved in this batch.
- The current worktree still contains the deleted paths as git deletions; this
  batch only proves their same-name relocation evidence.
- P70 still lists 219 archive candidates plus 8 historical archive entries.
  The candidates need a separate archive-candidate review before any move/delete
  action.
- Desktop typecheck/build was not rerun because no desktop source changed.

## Recovery Point

Start from:

`D:\XinYu\XinYu-Core\examples\agent-apps\xinyu`

Highest-value next batch:

Review P70 `archive_candidate_*` rows and produce a compact archive-candidate
hold/accept table. Do not move files; first decide whether each candidate is
stale lab/doc, active ops documentation, or a false positive.

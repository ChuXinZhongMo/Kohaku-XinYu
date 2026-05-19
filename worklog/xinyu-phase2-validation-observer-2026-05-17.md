# XinYu Phase 2 Validation Observer - 2026-05-17

Scope: quick validation observation for maintenance bridge migration. No production code changes were made.

## Environment Notes

- Working directory used for validation: `D:\XinYu\XinYu-Core\examples\agent-apps\xinyu`
- Existing worktree state was already heavily dirty before validation, including modified, deleted, and untracked files.
- `custom/maintenance_bridge_utils.py` and `tests/test_maintenance_bridge_utils.py` were already untracked before this observer record was written.
- Validation output below intentionally omits raw memory/log content.

## Commands Run

1. Discovery/read-only checks:
   - `git status --short`
   - `rg --files custom tests | rg "(maintenance|bridge).*\.py$"`
   - `rg -n "argparse|--group|--timeout|restore-after|quick|memory|source|maintenance|bridge|SMOKE|GROUP" smoke_run.py`
   - Targeted reads of `smoke_run.py` group and argument handling.

2. Compile validation:
   - Environment: `PYTHONDONTWRITEBYTECODE=1`
   - Command shape: `.\.venv\Scripts\python.exe -B -m py_compile custom/maintenance_bridge_utils.py custom/*_bridge_plugin.py`
   - Result: PASS
   - Files compiled: 33

3. Maintenance bridge pytest:
   - Environment: `PYTHONDONTWRITEBYTECODE=1`
   - Command: `.\.venv\Scripts\python.exe -B -m pytest -q -p no:cacheprovider tests/test_maintenance_bridge_utils.py`
   - Result: PASS
   - Summary: 6 passed in 0.22s

## Quick Smoke Decision

`smoke_run.py --group quick --timeout-seconds 300` was not run.

Reason: `smoke_run.py` supports `--group`, `--json`, `--timeout-seconds`, and `--venv-path`, but it does not support `--restore-after` and does not append restore flags to child smokes. The quick group includes memory/source-related checks, so running the grouped quick smoke would not satisfy the requirement that state-writing source/memory smokes use `--restore-after`.

## Findings

- No syntax/import-compilation failures were observed for `custom/maintenance_bridge_utils.py` or the bridge plugin set compiled in this pass.
- The focused maintenance bridge utility tests passed.
- Current grouped smoke runner is not restore-safe for the requested policy.
- The dirty worktree makes this validation a snapshot of the current uncommitted state rather than a clean baseline signal.

## Improvement Suggestions

- Add a restore-safe grouped smoke mode, for example `smoke_run.py --group quick --restore-after`, and have the runner pass it only to child smokes that support it.
- Alternatively split quick into read-only and stateful subsets so validation can run `quick-readonly` safely in dirty worktrees.
- Add a dry-run/list mode for `smoke_run.py` that prints planned child commands and whether each is stateful.
- Keep `tests/test_maintenance_bridge_utils.py` as the first fast gate, then add targeted tests for each migrated maintenance/source bridge route if runtime behavior is not already covered elsewhere.

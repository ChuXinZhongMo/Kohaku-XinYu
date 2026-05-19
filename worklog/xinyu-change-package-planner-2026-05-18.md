# XinYu Change Package Planner - 2026-05-18

Status: complete as dirty-worktree packaging batch.

## Batch Scope

- Capability group: version/change management.
- Goal: turn the large dirty worktree into reviewable packages with handling rules and validation commands.
- Privacy boundary: use `git status --short` paths only; do not read or print secrets, raw QQ content, or private memory bodies.

## Completed

- Added `ops/validation/git_change_package_plan.py`.
  - Reuses `git_change_group_audit.py` classification.
  - Builds review packages `P00` through `P07`, plus `P99` for unknown paths.
  - Adds intent, risk, handling policy, status counts, group counts, examples, and validation commands per package.
- Added `tests/test_git_change_package_plan.py`.
- Generated package reports:
  - `D:\XinYu\worklog\xinyu-change-package-plan-2026-05-18.md`
  - `D:\XinYu\worklog\xinyu-change-package-plan-2026-05-18.json`

## Package Model

- `P00 docs-worklogs-plans`: low-risk planning and docs review.
- `P01 ops-validation-tools`: validation tools, smoke tooling, and worklogs.
- `P02 tests-smokes-regression`: tests and smoke coverage.
- `P03 core-runtime-services-stores`: live behavior, runtime, services, stores.
- `P04 adapters-bridges-io`: QQ, bridge, desktop action, and external I/O boundaries.
- `P05 desktop-shell`: Electron desktop main/preload/renderer changes.
- `P06 memory-data-review-only`: memory, library, cases, seeds, and legacy data.
- `P07 archive-delete-candidates`: deleted or archived smoke/manual/diagnostic files.
- `P99 unknown-triage`: paths that still need classification.

## Direct Impact

- The dirty worktree is no longer just a count. It now has a review order and per-package acceptance rules.
- Risky content packages are explicitly separated:
  - memory data is review-only and not auto-deleted;
  - adapter/I/O changes require privacy-conscious smoke validation;
  - core runtime changes require full pytest plus quick smoke.
- Compatibility with the previous group audit is preserved.

## Validation

Passed:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe -m py_compile ops\validation\git_change_package_plan.py
.\.venv\Scripts\python.exe -m pytest tests\test_git_change_group_audit.py tests\test_git_change_package_plan.py -q
.\.venv\Scripts\python.exe ops\validation\git_change_package_plan.py --repo-root D:\XinYu --json --max-examples 1

cd D:\XinYu
git diff --check
```

Result:

- Focused pytest: 6 passed.
- CLI json generation: passed.
- Diff check: exit code 0; CRLF normalization warnings only.

## Final Snapshot

- Current `git status --short` count after the source protocol shim-prune batch refreshed the report: 625.
- Generated markdown/json reports both show:
  - total_entries: 625
  - package_count: 9
  - review_order: `P00, P01, P02, P03, P04, P05, P06, P07, P99`

## Remaining After This Batch

- Use `P06 memory-data-review-only` as the next working package if continuing the cleanup sequence.
- Do not auto-delete memory/cases/library/runtime data; make per-file decisions from the boundary audit.

## Recovery Point

Resume from:

- `ops/validation/git_change_package_plan.py`
- `tests/test_git_change_package_plan.py`
- `D:\XinYu\worklog\xinyu-change-package-plan-2026-05-18.md`
- `D:\XinYu\worklog\xinyu-change-package-plan-2026-05-18.json`

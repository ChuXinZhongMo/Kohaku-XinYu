# XinYu P84 Project Plan Archive Batch - 2026-05-19

## Scope

Batch: stale project-plan archive after P83.

Goal: act on P77 plan classifications by moving safe superseded/historical
plans while preserving active, encoding-held, and currently modified plans.

## Completed

- Moved 13 stale project plans to:
  - `ops/archive/project-plans/2026-05-19/`
- Added archive README:
  - `ops/archive/project-plans/2026-05-19/README.md`
- Added policy review:
  - `ops/reports/module_ecology_project_plan_archive_policy_review_2026-05-19.md`
- Regenerated post-archive reports:
  - `ops/reports/module_ecology_audit_post_archive_2026-05-19.md`
  - `ops/reports/module_ecology_archive_candidates_post_archive_2026-05-19.md`
  - `ops/reports/archive_delete_reference_audit_post_archive_2026-05-19.md`
- Updated final audit:
  - `ops/reports/xinyu_long_autonomy_final_audit_2026-05-19.md`

## Latest Counts

Post-archive module ecology:

- item_count: 1534
- kept: 1127
- archived: 146
- delete candidates: 261

Post-archive archive candidates:

- total: 111
- core: 5
- lab: 92
- ops: 14

Archive/delete reference audit:

- total_candidates: 261
- accept_delete_relocated: 261

## Direct Effect

- Archive candidates reduced from 124 to 111 in this batch.
- Active `project-plans` surface is reduced by 13 stale plans.
- Current active cross-domain plan remains.
- Modified plan files remain in place.

## Validation

- Project-plan archive move check:
  - 13 active paths removed.
  - 13 archive paths exist.
  - active/held/modified plans still exist.
- Privacy/count check for updated reports:
  - pass
- `git diff --check -- ...`
  - pass
- `.\.venv\Scripts\python.exe -m pytest tests -q`
  - 666 passed
- Quick smoke was not rerun because only project-plan docs and reports changed;
  P82 quick smoke passed before P83/P84, and no runtime source changed after it.

## Remaining

- 53 manual smoke scripts need grouped-smoke/pytest/archive decisions.
- 5 merge-needed ops docs need active-index extraction before archive.
- `EXECUTION-ORDER.md` has local modifications and should not be moved until
  reviewed.
- `project-plans/XINYU-PROACTIVE-CONCRETE-REQUEST-LOOP-PLAN.md` and
  `project-plans/XINYU-SELF-THOUGHT-IDLE-LOOP-PLAN.md` have local modifications
  and remain in place.
- Chroma/Qdrant providers and v1 CLIs need explicit retirement policy before
  archive.
- Owner-supplied material needs a private/ignored archive lane before any move.

## Recovery Point

Start from:

`D:\XinYu\XinYu-Core\examples\agent-apps\xinyu`

Read first:

1. `D:\XinYu\worklog\xinyu-p84-project-plan-archive-batch-2026-05-19.md`
2. `ops/reports/xinyu_long_autonomy_final_audit_2026-05-19.md`
3. `ops/reports/module_ecology_archive_candidates_post_archive_2026-05-19.md`

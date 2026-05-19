# XinYu P77 Project Plan Index Review Batch - 2026-05-19

## Scope

Batch: stale `project-plans/*.md` archive-candidate review after P76.

Goal: identify which stale project plans remain active, which are historical,
and which are superseded by implementation or newer plans, without moving files.

## Completed

- Added plan index review report:
  - `ops/reports/module_ecology_plan_index_review_2026-05-19.md`
- Reviewed the 17 stale plan candidates from:
  - `ops/reports/module_ecology_archive_candidates_2026-05-19.md`
- Used local plan headings/status markers and current smoke/test evidence.

## Latest Counts

- stale plan candidates: 17
- keep active: 1
- hold for encoding/boundary review: 1
- archive candidate, superseded: 11
- archive candidate, historical: 4
- files moved: 0

Active:

- `project-plans/XINYU-CROSS-DOMAIN-SYNAESTHESIA-PLAN-2026-05-19.md`

Held:

- `project-plans/未完成事项-QQ接回后续接计划.md`
  - reason: renders as mojibake locally; keep until encoding is normalized or a
    clean replacement exists.

## Direct Effect

- The apparent active plan surface is reduced from 17 stale candidates to one
  current execution plan plus one held QQ-boundary/encoding review item.
- Old closeout/handoff/audit plans are separated from current work.
- Implemented design plans are marked as future archive candidates instead of
  active instructions.
- No files were moved or deleted.

## Validation

- Row-count/status check for `ops/reports/module_ecology_plan_index_review_2026-05-19.md`
  - 17 rows
  - 4 `archive_candidate_historical`
  - 11 `archive_candidate_superseded`
  - 1 `hold_review`
  - 1 `keep_active`
- `.\.venv\Scripts\python.exe -m pytest tests\test_module_ecology_audit.py -q`
  - 18 passed
- `git diff --check -- ops/reports/module_ecology_plan_index_review_2026-05-19.md`
  - pass
- `.\.venv\Scripts\python.exe smoke_run.py --group quick --timeout-seconds 180 --json`
  - ok=true

## Remaining

- Plan files are classified but not moved.
- Future archive move should add replacement notes or an archive manifest.
- `未完成事项-QQ接回后续接计划.md` needs encoding/boundary normalization before
  an archive decision.
- Remaining P75 lab cleanup families:
  - 33 `learning/self_found` files need snapshot-level archive review.
  - 2 `learning/owner_supplied` files need explicit owner-supplied material
    boundary handling.
- Core/ops archive candidates remain advisory until policy review.

## Recovery Point

Start from:

`D:\XinYu\XinYu-Core\examples\agent-apps\xinyu`

Highest-value next batch:

Review `learning/self_found` archive candidates at snapshot-folder level. Do
not read or print copied source bodies; use paths, folder metadata, and
reference checks only.

# XinYu P76 Smoke Inventory Review Batch - 2026-05-19

## Scope

Batch: stale smoke script inventory review after P75 lab-family triage.

Goal: compare the 53 stale `tests/smoke/**/*_smoke.py` candidates against
the canonical `smoke_run.py` grouped manifests before any archive/delete work.

## Completed

- Added smoke inventory report:
  - `ops/reports/module_ecology_smoke_inventory_review_2026-05-19.md`
- Compared stale smoke candidates from:
  - `ops/reports/module_ecology_archive_candidates_2026-05-19.md`
- Checked coverage against:
  - `smoke_run.SMOKE_GROUPS`

## Latest Counts

- stale smoke candidates: 53
- covered by `smoke_run.SMOKE_GROUPS`: 0
- uncovered by grouped smoke manifests: 53
- archive-ready now: 0

Family counts:

- bridge: 23
- codex: 1
- desktop: 2
- dialogue: 1
- initiative: 5
- life: 1
- qq: 16
- qq/integration: 1
- runtime: 1
- voice: 2

## Direct Effect

- Prevented accidental deletion of uncovered diagnostic smoke scripts.
- Converted the stale-smoke cleanup problem into a concrete 53-row decision
  list.
- Established that absence from `SMOKE_GROUPS` is not enough evidence to
  archive a smoke script.
- Runtime behavior is unchanged.

## Validation

- Row-count check for `ops/reports/module_ecology_smoke_inventory_review_2026-05-19.md`
  - 53 rows
  - all rows status `manual_only_or_archive_review`
- `.\.venv\Scripts\python.exe -m pytest tests\test_module_ecology_audit.py -q`
  - 18 passed
- `git diff --check -- ops/reports/module_ecology_smoke_inventory_review_2026-05-19.md`
  - pass
- `.\.venv\Scripts\python.exe smoke_run.py --group quick --timeout-seconds 180 --json`
  - ok=true

## Remaining

- Smoke scripts are classified but not moved.
- Next cleanup should pick one family and either:
  - add important scripts to a named smoke group,
  - convert their checks into pytest coverage,
  - or archive them with replacement evidence.
- Other P75 lab cleanup families remain:
  - 17 stale `project-plans/*.md` files need active-plan index extraction.
  - 33 `learning/self_found` files need snapshot-level archive review.
  - 2 `learning/owner_supplied` files need explicit owner-supplied material
    boundary handling.
- Core/ops archive candidates remain advisory until policy review.

## Recovery Point

Start from:

`D:\XinYu\XinYu-Core\examples\agent-apps\xinyu`

Highest-value next batch:

Build a plan-index review for the 17 stale `project-plans/*.md` candidates:
extract whether each plan is active, superseded, or historical; then generate
an archive decision report without moving files.

# XinYu P78 Self-Found Snapshot Review Batch - 2026-05-19

## Scope

Batch: `learning/self_found` stale lab candidate review after P77.

Goal: classify self-found learning candidates at snapshot-folder level without
reading or printing copied source bodies.

## Completed

- Added self-found snapshot report:
  - `ops/reports/module_ecology_self_found_snapshot_review_2026-05-19.md`
- Reviewed the 33 stale `learning/self_found` candidates from:
  - `ops/reports/module_ecology_archive_candidates_2026-05-19.md`
- Confirmed all 33 candidates belong to one imported GitHub snapshot:
  - `learning/self_found/20260506T065121+0800_github-ganeshnikhil-j-a-r-v-i-s-2-0_16811af8`
- Checked references outside `learning/self_found`, excluding memory/runtime/data/library/cases/log/report bodies.

## Latest Counts

- stale self-found file candidates: 33
- snapshot folders involved: 1
- archive candidate snapshots: 1
- files moved: 0

Candidate shape:

- `DATA`: 5
- `src`: 27
- `ui.py`: 1
- `.py`: 32
- `.md`: 1

## Direct Effect

- Converts 33 file-level archive candidates into one snapshot-level archive
  candidate.
- Prevents partial deletion of selected files while leaving metadata, extracted
  text, or original zip behind.
- Keeps the learning import boundary intact until an explicit archive move is
  performed.

## Validation

- Row-count/status check for `ops/reports/module_ecology_self_found_snapshot_review_2026-05-19.md`
  - 34 `learning/self_found` rows total
  - 1 snapshot row
  - 33 candidate file rows
  - all 33 file rows marked `archive_with_snapshot`
- `.\.venv\Scripts\python.exe -m pytest tests\test_module_ecology_audit.py -q`
  - 18 passed
- `git diff --check -- ops/reports/module_ecology_self_found_snapshot_review_2026-05-19.md`
  - pass
- Quick smoke was not rerun in this report-only batch; the P77 quick smoke ran
  immediately before this batch and passed, and no runtime code changed in P78.

## Remaining

- Snapshot is classified but not moved.
- Future move should move the whole snapshot intact with an archive manifest.
- `learning/owner_supplied` still needs stricter provenance/boundary review.
- Core/ops archive candidates remain advisory until policy review.

## Recovery Point

Start from:

`D:\XinYu\XinYu-Core\examples\agent-apps\xinyu`

Highest-value next batch:

Review `learning/owner_supplied` candidates. Treat owner-supplied material as
higher-trust but stricter-boundary input; do not print material bodies.

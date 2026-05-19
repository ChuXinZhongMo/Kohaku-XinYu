# XinYu P85 Manual Smoke Archive Batch - 2026-05-19

Scope: close the stale manual smoke surface identified by the module ecology
audit without changing active grouped smoke behavior.

Privacy note: this worklog records paths, counts, and validation results only.
It does not include private memory, runtime data, QQ payloads, owner-supplied
material bodies, raw prompts, raw replies, URLs, or tokens.

## Completed

- Moved 53 ungrouped manual smoke scripts from `tests/smoke/` to
  `ops/archive/manual-smokes/2026-05-19/`.
- Added archive notes in
  `ops/archive/manual-smokes/2026-05-19/README.md`.
- Added manual smoke archive policy report:
  `ops/reports/module_ecology_manual_smoke_archive_policy_review_2026-05-19.md`.
- Regenerated post-archive ecology reports:
  - `ops/reports/module_ecology_audit_post_archive_2026-05-19.md`
  - `ops/reports/module_ecology_archive_candidates_post_archive_2026-05-19.md`
  - `ops/reports/archive_delete_reference_audit_post_archive_2026-05-19.md`
- Fixed `ops/validation/queue_boundary_audit.py` so archived files under
  `ops/archive/` are not treated as live queue readers.
- Added coverage in `tests/test_queue_boundary_audit.py` for archived manual
  smoke exclusion.
- Updated final long-autonomy audit:
  `ops/reports/xinyu_long_autonomy_final_audit_2026-05-19.md`.

## Counts

- Post-archive item count: 1535
- Kept: 1127
- Archived: 147
- Deleted cleanup candidates accepted as relocated: 261
- Archive bucket: 89
- Lab bucket: 614
- Remaining archive candidates: 58
  - core: 5
  - lab: 39
  - ops: 14
- Archive candidates before P80/P81/P84/P85: 135
- Archive candidates after P80/P81/P84/P85: 58
- Candidate reduction: 77

## Validation

- Focused boundary tests:
  `pytest tests/test_queue_boundary_audit.py tests/test_boundary_readiness_audit.py -q`
  -> 7 passed.
- Full tests:
  `pytest tests -q`
  -> 667 passed.
- Quick smoke:
  `smoke_run.py --group quick --timeout-seconds 180 --json`
  -> ok=true.

## Remaining

- 33 self-found snapshot files remain represented as 1 snapshot-level archive
  candidate.
- 2 owner-supplied bundles remain held for private archive policy; use sanitized
  metadata only.
- 5 merge-needed ops docs still need summarization before archive.
- `EXECUTION-ORDER.md` is locally modified and should not be moved until
  reviewed.
- 2 modified stale plans remain in place:
  - `project-plans/XINYU-PROACTIVE-CONCRETE-REQUEST-LOOP-PLAN.md`
  - `project-plans/XINYU-SELF-THOUGHT-IDLE-LOOP-PLAN.md`
- 5 core compatibility/provider surfaces still need explicit retirement policy:
  - `xinyu_sticker_reference_index.py`
  - `xinyu_v1/cli/inspect_memory.py`
  - `xinyu_v1/cli/migrate_memory.py`
  - `xinyu_v1/memory/chroma_store.py`
  - `xinyu_v1/memory/qdrant_store.py`

## Recovery Point

Start from `D:\XinYu\XinYu-Core\examples\agent-apps\xinyu`.

Next batch should choose the highest-value remaining archive candidate family,
starting with merge-needed ops docs or core compatibility/provider retirement
policy. Do not move owner-supplied bundles until the private archive policy is
explicit.

# XinYu P86 Ops Docs Archive Batch - 2026-05-19

Scope: close the merge-needed root ops documentation archive candidates without
losing their useful operating rules.

Privacy note: this worklog records paths, counts, and validation results only.
It does not include private memory, runtime data, QQ payloads, owner-supplied
material bodies, raw prompts, raw replies, URLs, or tokens.

## Completed

- Reviewed five root-level ops/doc archive candidates:
  - `ACTION-LAYER-V1.md`
  - `PUBLIC-DATA-REPLAY.md`
  - `XINYU-DIRECTION.md`
  - `XINYU-SYSTEM-DIAGRAMS.md`
  - `XINYU-SYSTEM-UTILIZATION-AUDIT.md`
- Added their active conclusions to `INDEX.md`.
- Moved original docs to `ops/archive/ops-docs/2026-05-19/`.
- Added archive README:
  `ops/archive/ops-docs/2026-05-19/README.md`.
- Added archive policy report:
  `ops/reports/module_ecology_ops_docs_archive_policy_review_2026-05-19.md`.
- Regenerated ecology reports:
  - `ops/reports/module_ecology_audit_post_archive_2026-05-19.md`
  - `ops/reports/module_ecology_archive_candidates_post_archive_2026-05-19.md`
  - `ops/reports/archive_delete_reference_audit_post_archive_2026-05-19.md`
- Updated final long-autonomy audit:
  `ops/reports/xinyu_long_autonomy_final_audit_2026-05-19.md`.

## Counts

- Post-archive item count: 1540
- Kept: 1127
- Archived: 148
- Deleted cleanup candidates accepted as relocated: 265
- Archive bucket: 95
- Ops bucket: 180
- Remaining archive candidates: 53
  - core: 5
  - lab: 39
  - ops: 9
- Archive candidates before P80/P81/P84/P85/P86: 135
- Archive candidates after P80/P81/P84/P85/P86: 53
- Candidate reduction: 82

## Validation

- Focused ecology tests:
  `pytest tests/test_module_ecology_audit.py tests/test_archive_delete_reference_audit.py -q`
  -> 24 passed.
- Quick smoke:
  `smoke_run.py --group quick --timeout-seconds 180 --json`
  -> ok=true.
- Full tests were not rerun in this docs-only batch; last full run at P85 was
  667 passed.

## Remaining

- 33 self-found snapshot files remain represented as 1 snapshot-level archive
  candidate.
- 2 owner-supplied bundles remain held for private archive policy; use sanitized
  metadata only.
- 7 manual ops runners and 1 sticker manifest need explicit keep/archive policy.
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

Next batch should handle one remaining family only. The cleanest candidates are
the 7 manual ops runners plus `emotions/stickers/manifest.example.json`, or the
5 core compatibility/provider surfaces if the goal is to reduce core ambiguity.

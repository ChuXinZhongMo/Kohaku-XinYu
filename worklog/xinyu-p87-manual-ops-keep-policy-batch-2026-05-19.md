# XinYu P87 Manual Ops Keep Policy Batch - 2026-05-19

Scope: close the remaining no-reference ops manual/template candidates by
explicit keep policy, without moving live operator escape hatches.

Privacy note: this worklog records paths, counts, and validation results only.
It does not include private memory, runtime data, QQ payloads, owner-supplied
material bodies, raw prompts, raw replies, URLs, or tokens.

## Completed

- Registered all operator-only manual entrances in `ops/manual/README.md`.
- Registered `emotions/stickers/manifest.example.json` as a schema template in
  `emotions/stickers/README.md`.
- Added keep policy report:
  `ops/reports/module_ecology_manual_ops_keep_policy_review_2026-05-19.md`.
- Regenerated ecology reports:
  - `ops/reports/module_ecology_audit_post_archive_2026-05-19.md`
  - `ops/reports/module_ecology_archive_candidates_post_archive_2026-05-19.md`
  - `ops/reports/archive_delete_reference_audit_post_archive_2026-05-19.md`
- Updated final long-autonomy audit:
  `ops/reports/xinyu_long_autonomy_final_audit_2026-05-19.md`.

## Counts

- Post-policy item count: 1540
- Kept: 1135
- Archived: 140
- Deleted cleanup candidates accepted as relocated: 265
- Remaining archive candidates: 45
  - core: 5
  - lab: 39
  - ops: 1
- Archive candidates before P80/P81/P84/P85/P86/P87: 135
- Archive candidates after P80/P81/P84/P85/P86/P87: 45
- Candidate reduction: 90

## Validation

- Focused ecology tests:
  `pytest tests/test_module_ecology_audit.py -q`
  -> 18 passed.
- Quick smoke was not rerun in this README-only batch; P86 quick smoke was
  ok=true.
- Full tests were not rerun in this README-only batch; last full run at P85 was
  667 passed.

## Remaining

- 33 self-found snapshot files remain represented as 1 snapshot-level archive
  candidate.
- 2 owner-supplied bundles remain held for private archive policy; use sanitized
  metadata only.
- `EXECUTION-ORDER.md` is locally modified and remains the only ops archive
  candidate.
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

Next batch should handle the core compatibility/provider surfaces, because ops
is now reduced to one locally modified hold and lab includes private/snapshot
boundaries that need stricter policy.

# XinYu P88 Core Compat Keep Policy Batch - 2026-05-19

Scope: close five no-reference core compatibility/provider candidates by
explicit policy, without changing the canonical live recall path.

Privacy note: this worklog records paths, counts, and validation results only.
It does not include private memory, runtime data, QQ payloads, owner-supplied
material bodies, raw prompts, raw replies, URLs, or tokens.

## Completed

- Registered `xinyu_sticker_reference_index.py` as optional local sticker
  material maintenance in `emotions/stickers/README.md`.
- Added `xinyu_v1/cli/README.md` with keep/retire rules for:
  - `inspect_memory.py`
  - `migrate_memory.py`
  - `run_maintenance.py`
  - `smoke.py`
- Added `xinyu_v1/memory/README.md` with optional provider policy for:
  - `chroma_store.py`
  - `qdrant_store.py`
- Added core compatibility policy report:
  `ops/reports/module_ecology_core_compat_keep_policy_review_2026-05-19.md`.
- Regenerated ecology reports:
  - `ops/reports/module_ecology_audit_post_archive_2026-05-19.md`
  - `ops/reports/module_ecology_archive_candidates_post_archive_2026-05-19.md`
  - `ops/reports/archive_delete_reference_audit_post_archive_2026-05-19.md`
- Updated final long-autonomy audit:
  `ops/reports/xinyu_long_autonomy_final_audit_2026-05-19.md`.

## Counts

- Post-policy item count: 1542
- Kept: 1142
- Archived: 135
- Deleted cleanup candidates accepted as relocated: 265
- Remaining archive candidates: 40
  - core: 0
  - lab: 39
  - ops: 1
- Archive candidates before P80/P81/P84/P85/P86/P87/P88: 135
- Archive candidates after P80/P81/P84/P85/P86/P87/P88: 40
- Candidate reduction: 95

## Validation

- Focused ecology/v1 tests:
  `pytest tests/test_module_ecology_audit.py tests/v1/test_v1_smoke_contract.py -q`
  -> 21 passed.
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
- Active cross-domain plan and held QQ plan still appear as lab archive
  candidates by the generic scanner but are policy-held.

## Recovery Point

Start from `D:\XinYu\XinYu-Core\examples\agent-apps\xinyu`.

Next batch should handle lab candidate policy. Do not read or print
owner-supplied bundle bodies; use only sanitized metadata and path-level
decisions.

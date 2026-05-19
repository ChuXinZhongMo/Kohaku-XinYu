# XinYu P90 Project Plan Hold Policy Batch - 2026-05-19

Scope: close project-plan lab candidates by registering active/hold policy
without moving locally modified plans.

Privacy note: this worklog records paths, counts, and validation results only.
It does not include private memory, runtime data, QQ payloads, owner-supplied
material bodies, raw prompts, raw replies, URLs, or tokens.

## Completed

- Added `project-plans/README.md` with active/hold policy.
- Added top-level `INDEX.md` references for four active/hold plans because
  project-plan internal references are non-live for ecology scoring.
- Added hold policy report:
  `ops/reports/module_ecology_project_plan_hold_policy_review_2026-05-19.md`.
- Regenerated ecology reports:
  - `ops/reports/module_ecology_audit_post_archive_2026-05-19.md`
  - `ops/reports/module_ecology_archive_candidates_post_archive_2026-05-19.md`
  - `ops/reports/archive_delete_reference_audit_post_archive_2026-05-19.md`
- Updated final long-autonomy audit:
  `ops/reports/xinyu_long_autonomy_final_audit_2026-05-19.md`.

## Counts

- Post-policy item count: 1544
- Kept: 1139
- Archived: 140
- Deleted cleanup candidates accepted as relocated: 265
- Remaining archive candidates: 3
  - core: 0
  - lab: 2
  - ops: 1
- Archive candidates before P80/P81/P84/P85/P86/P87/P88/P89/P90: 135
- Archive candidates after P80/P81/P84/P85/P86/P87/P88/P89/P90: 3
- Candidate reduction: 132

## Validation

- Focused ecology tests:
  `pytest tests/test_module_ecology_audit.py -q`
  -> 18 passed.
- Quick smoke was not rerun in this docs-only batch; P86 quick smoke was
  ok=true.
- Full tests were not rerun in this batch; last full run at P85 was 667 passed.

## Remaining

- 2 owner-supplied bundles remain held for private archive policy; use sanitized
  metadata only.
- `EXECUTION-ORDER.md` is locally modified and remains the only ops archive
  candidate.

## Recovery Point

Start from `D:\XinYu\XinYu-Core\examples\agent-apps\xinyu`.

Next batch should handle owner-supplied archive policy by metadata only, or
`EXECUTION-ORDER.md` by explicit local-modification hold policy.

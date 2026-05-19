# XinYu Owner-Supplied Boundary Review - 2026-05-19

Scope: review the 2 stale `learning/owner_supplied` candidates from
`ops/reports/module_ecology_archive_candidates_2026-05-19.md`.

Privacy note: owner-supplied learning material can contain QQ file URLs, raw
owner instructions, and copied report bodies. This report records only paths,
counts, and boundary decisions. It intentionally does not print metadata values,
QQ URLs, raw prompts, raw replies, or material body content.

## Summary

- stale owner-supplied file candidates: 2
- owner-supplied bundles involved: 2
- archive-ready now: 0
- hold for sanitized boundary review: 2
- files moved: 0

## Decision

Both candidates are `hold_owner_supplied_boundary`.

Reason: owner-supplied files are higher-trust input than self-found public
snapshots, but they also carry stricter privacy and provenance requirements.
The local metadata shape is not safe to print directly, and future automation
must use a sanitized metadata reader before producing archive/delete evidence.

## Items

| Bundle | Candidate file | Decision | Evidence | Direct effect |
| --- | --- | --- | --- | --- |
| `learning/owner_supplied/20260506T192719+0800_codex-qq-20260506T191818-report.md_14a7a340` | `codex-qq-20260506T191818-report.md` | hold_owner_supplied_boundary | candidate report shows refs=0, but owner-supplied provenance requires sanitized metadata review | keep in place; do not archive/delete yet |
| `learning/owner_supplied/20260506T193342+0800_codex-qq-20260506T192321-report.md_8ae8715b` | `codex-qq-20260506T192321-report.md` | hold_owner_supplied_boundary | candidate report shows refs=0, but owner-supplied provenance requires sanitized metadata review | keep in place; do not archive/delete yet |

## Reference Check

Searched outside `learning/owner_supplied`, and excluded
memory/runtime/data/library/cases/log/report bodies.

Observed references were generic only:

- directory mentions in docs/runbooks
- structure inventory ignore patterns
- tests and smokes that use synthetic `learning/owner_supplied` paths
- learning library init helper for creating the directory

No active reference to these specific owner-supplied bundle names was found in
the checked active surface. That is useful signal, but not sufficient for
archive/delete because the privacy boundary is stricter.

## Required Before Archive

- Add or use a sanitized metadata reader that suppresses:
  - QQ URLs and temporary download tokens
  - raw owner instructions
  - raw prompt/reply/material text
  - copied report body excerpts
- Produce a replacement manifest with only:
  - bundle id
  - created time
  - origin
  - content type
  - stored path count
  - sanitized title or hash
  - archive decision
- Only after that manifest exists should these bundles become archive
  candidates.

## Direct Effect

- Prevents owner-supplied material from being treated like ordinary stale lab
  code.
- Creates a clear boundary: self-found snapshots can be archived by folder
  after reference checks; owner-supplied bundles need sanitized provenance first.
- Leaves runtime behavior unchanged.

## Next Batch

Review core archive candidates separately. Core candidates should not move until
compatibility/provider ownership is explicit.

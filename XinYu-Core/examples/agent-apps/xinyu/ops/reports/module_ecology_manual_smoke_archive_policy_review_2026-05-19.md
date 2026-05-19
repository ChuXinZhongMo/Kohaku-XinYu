# XinYu Manual Smoke Archive Policy Review - 2026-05-19

Scope: act on the 53 stale smoke candidates reviewed in
`ops/reports/module_ecology_smoke_inventory_review_2026-05-19.md`.

Privacy note: this report uses paths and smoke manifest coverage only. It does
not print private memory, runtime data, QQ payloads, owner-supplied material,
raw prompts, raw replies, URLs, or tokens.

## Summary

- stale smoke candidates: 53
- covered by `smoke_run.SMOKE_GROUPS`: 0
- archived in this batch: 53
- deleted: 0

## Archive Path

All files were moved to:

`ops/archive/manual-smokes/2026-05-19/`

Original relative paths were preserved.

## Family Counts

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

## Decision

The files are archived as `manual_smoke_unlisted`.

Reason:

- not listed in canonical `SMOKE_GROUPS`.
- untracked manual diagnostic files.
- active quick/core/full smoke coverage remains in `smoke_run.py`.
- recovery is available from `ops/archive/manual-smokes/2026-05-19/`.

## Direct Effect

- Removes 53 ungrouped manual smoke scripts from the active `tests/smoke`
  surface.
- Keeps active grouped smoke behavior unchanged.
- Makes future smoke work explicit: add a script to `SMOKE_GROUPS` or write a
  pytest test before treating it as active coverage.

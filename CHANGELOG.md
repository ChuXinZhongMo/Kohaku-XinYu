# Changelog

All notable public-source changes should be recorded here.

## v0.1.0 - Public Source Baseline

Status: **released** (2026-07-13)

First final public tag on the cut-over `main` line (includes work formerly on
`master`). Preceded by `v0.1.0-rc.2`.

### Highlights

- Python core runtime and active `xinyu` agent app.
- Native QQ/NapCat gateway path for normalized local messaging turns.
- Electron/Vite desktop shell for local operator visibility.
- Memory, learning, proactive behavior, and review boundaries.
- Unified `XinYu.ps1` operator entry point.
- Engineering maturity track: progressive CI gates, issue/PR templates,
  Dependabot, pre-commit, branch policy, OpenSSF self-assessment stub.
- Architecture debt payment: bridge store consolidation, gateway/status splits.
- Product surfaces landed through rc.2: kernel/experience adapters, TTS emotion
  mapping, persona/life-reply updates, private ecosystem stubs, desktop shell
  upgrades.

### Validation (blocking CI on release tip)

Re-check GitHub Actions on the exact tagged commit:

- Python tests (blocking): pass
- Python lint critical (blocking): pass
- Desktop typecheck (blocking): pass

Informational jobs (full ruff / smoke / npm audit) may still fail and are not
release blockers.

### Publication Boundary

Intentionally excludes private runtime state, local memory stores, credentials,
QQ payloads, owner-supplied material bodies, generated dependency folders, and
local machine artifacts.

### Branch / process

- Default branch: `main` (protected; required blocking checks).
- Backup tags: `backup/pre-main-cutover-20260713-main`,
  `backup/pre-main-cutover-20260713-master`.
- Dependabot: pywebview 6.2.1 merged; major Actions/npm bumps deferred.

## Unreleased

- Deferred Dependabot majors (Actions v6/v7, TypeScript 7, ESLint 10,
  electron-vite 5).
- Full ruff debt paydown; curated quick-smoke blocking job.
- Archive or delete remote `master` after one stable cycle.


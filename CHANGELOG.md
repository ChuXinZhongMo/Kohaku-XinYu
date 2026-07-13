# Changelog

All notable public-source changes should be recorded here.

## Unreleased - Engineering Maturity Track

Status: in progress (started 2026-07-13)

- Added engineering maturity plan and 30-day checklist under `docs/plans/`.
- Added Phase 2 architecture inventory for bridge/god-file debt.
- Added GitHub issue templates, PR template, CODEOWNERS, and Dependabot.
- Added `.editorconfig` and `.pre-commit-config.yaml`.
- Hardened CI with named blocking vs informational jobs, concurrency cancel,
  coverage artifact upload, and critical ruff gate on `XinYu-Core/src`.
- Documented branch policy (`main` canonical; `master` cutover checklist).
- Refreshed root README/CONTRIBUTING setup paths for fresh developers.
- Auto-fixed a batch of safe ruff issues under `XinYu-Core/src`.

## v0.1.0 - Public Source Baseline

Status: release candidate

This release candidate packages XinYu as a local, privacy-bound, long-running
personal AI runtime workspace.

### Highlights

- Python core runtime and active `xinyu` agent app.
- Native QQ/NapCat gateway path for normalized local messaging turns.
- Electron/Vite desktop shell for local operator visibility.
- Memory, learning, proactive behavior, and review boundaries.
- Unified `XinYu.ps1` operator entry point.
- Public documentation for setup, operations, open-source policy, security, and
  contribution expectations.
- Sanitized worklogs, audits, reports, tests, and smoke runners for release
  review.

### Validation Baseline

Latest checked local baseline, 2026-05-21:

- Python tests: `786 passed`
- runtime readiness smoke: `ok`
- QQ gateway smoke: `ok`
- desktop typecheck: passed
- desktop build: passed

### Publication Boundary

The release candidate intentionally excludes private runtime state, local
memory stores, credentials, QQ payloads, owner-supplied material bodies,
generated dependency folders, and local machine artifacts.

### Known Gaps Before A GitHub Release

- Publish a signed or annotated `v0.1.0` tag.
- Create a GitHub release using these notes.
- Re-run the validation baseline on the exact commit being tagged.
- Add issue templates after the first public feedback loop.

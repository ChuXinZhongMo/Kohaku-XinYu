# Changelog

All notable public-source changes should be recorded here.

## v0.1.0 - Public Source Baseline

Status: release candidate

This release candidate packages XinYu as a local, privacy-bound, long-running
personal AI runtime workspace.

### Highlights

- Python core runtime and active `xinyu` agent app.
- Native QQ/NapCat gateway path for normalized local messaging turns.
- Desktop shell for local operator visibility.
- Memory, learning, proactive behavior, and review boundaries.
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

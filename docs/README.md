# XinYu Docs

This directory keeps root-level planning and audit material out of the runtime
surface.

- `system/` - architecture notes and system-shape documents.
  - `system/FRESH-INSTALL.md` - stranger clone path (Python 3.12, Node 20, gates).
  - `system/BRANCH-POLICY.md` - `main` / `master` cutover policy.
  - `system/XINYU-SYSTEM.md` - system spine and component boundaries.
- `plans/` - active and historical work plans.
  - `plans/ENGINEERING-MATURITY-PLAN.md` - path from ~45 → top-tier OSS maturity.
  - `plans/ENGINEERING-30-DAY-CHECKLIST.md` - day-to-day execution board.
  - `plans/PHASE2-ARCHITECTURE-INVENTORY.md` - bridge/god-file debt inventory.
  - `plans/RELEASE-CHECKLIST.md` - pre-tag validation, privacy dry-run, GitHub release.
  - `plans/GOOD-FIRST-ISSUES.md` - curated starter issues with acceptance criteria.
  - `plans/OPENSSF-SELF-ASSESSMENT.md` - OpenSSF Best Practices Passing map (Phase 4 stub).
  - `plans/QUICK-SMOKE-SET.md` - curated offline smoke candidates for future CI blocking.
  - `plans/ENV-EXAMPLE-AUDIT.md` - env example inventory, gitignore coverage, secret-risk notes.
- `reports/` - validation, audit, operations, and refactor reports.

Related operator scripts (repo root, not under `docs/`):

- `scripts/Release-DryRun.ps1` - read-only privacy / release dry-run before tags.
- `.github/workflows/security.yml` - non-blocking pip-audit + npm audit.

Contributor policy links (repo root):

- `CONTRIBUTING.md`
- `SECURITY.md`
- `OPEN_SOURCE_POLICY.md`

Operational entry points stay at the workspace root. Use `..\XinYu.ps1 tree`
from this directory, or `.\XinYu.ps1 tree` from the repository root.

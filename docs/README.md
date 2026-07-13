# XinYu Docs

This directory keeps root-level planning and audit material out of the runtime
surface.

- `system/` - architecture notes and system-shape documents.
  - `system/BRANCH-POLICY.md` - `main` / `master` cutover policy.
  - `system/XINYU-SYSTEM.md` - system spine and component boundaries.
- `plans/` - active and historical work plans.
  - `plans/ENGINEERING-MATURITY-PLAN.md` - path from ~45 → top-tier OSS maturity.
  - `plans/ENGINEERING-30-DAY-CHECKLIST.md` - day-to-day execution board.
  - `plans/PHASE2-ARCHITECTURE-INVENTORY.md` - bridge/god-file debt inventory.
- `reports/` - validation, audit, operations, and refactor reports.

Operational entry points stay at the workspace root. Use `..\XinYu.ps1 tree`
from this directory, or `.\XinYu.ps1 tree` from the repository root.

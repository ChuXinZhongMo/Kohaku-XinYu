# XinYu P80 Core Orphan Archive Batch - 2026-05-19

## Scope

Batch: core archive candidates after P79.

Goal: act on the core candidates that already had archive-ready evidence while
leaving compatibility, operator CLI, and optional provider surfaces active.

## Completed

- Moved 6 archive-ready core orphan modules to:
  - `ops/archive/core-orphans/2026-05-19/`
- Added archive README:
  - `ops/archive/core-orphans/2026-05-19/README.md`
- Added policy review report:
  - `ops/reports/module_ecology_core_archive_policy_review_2026-05-19.md`

Archived with original relative paths preserved:

- `xinyu_v1/gateway/maintenance_gateway.py`
- `xinyu_v1/integrations/legacy_custom_engines.py`
- `xinyu_v1/integrations/napcat_contract.py`
- `xinyu_v1/observability/audit_log.py`
- `xinyu_v1/reasoning/conflict_resolver.py`
- `xinyu_v1/storage/sqlite_meta.py`

Kept active:

- `xinyu_sticker_reference_index.py`
- `xinyu_v1/cli/inspect_memory.py`
- `xinyu_v1/cli/migrate_memory.py`
- `xinyu_v1/memory/chroma_store.py`
- `xinyu_v1/memory/qdrant_store.py`

## Direct Effect

- Active core source surface is reduced by 6 unreferenced modules.
- Deleted nothing; recovery is available from `ops/archive`.
- Optional vector-store providers and operator/migration CLIs remain available
  until explicit policy retires them.

## Validation

- Archive move check:
  - 6 original active paths no longer exist.
  - 6 archived paths exist under `ops/archive/core-orphans/2026-05-19/`.
  - 5 kept compatibility/provider paths still exist.
- `git diff --check -- ...`
  - pass
- `.\.venv\Scripts\python.exe -m pytest tests -q`
  - 663 passed
- `.\.venv\Scripts\python.exe smoke_run.py --group quick --timeout-seconds 180 --json`
  - ok=true

## Remaining

- Core compatibility/provider surfaces remain:
  - move `xinyu_sticker_reference_index.py` only after ops/manual CLI coverage.
  - retire v1 inspect/migrate CLIs only after v1 migration policy is closed.
  - retire Chroma/Qdrant providers only after vector-store policy is explicit.
- Ops archive candidates remain advisory until ops/manual policy review.
- Lab holds remain:
  - owner-supplied bundles need sanitized metadata review.
  - stale smoke scripts need grouped-smoke/pytest replacement decisions.
  - stale plans are classified but not moved.

## Recovery Point

Start from:

`D:\XinYu\XinYu-Core\examples\agent-apps\xinyu`

Highest-value next batch:

Review ops archive candidates and move only documents/manual scripts that have
clear historical/operator status and no active references.

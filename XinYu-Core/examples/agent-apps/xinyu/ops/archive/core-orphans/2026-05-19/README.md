# Core Orphans Archive - 2026-05-19

This archive stores core-bucket modules that had no live references or tests in
the module ecology audit and were classified as archive-ready by the core triage
review.

Source evidence:

- `ops/reports/module_ecology_archive_candidates_2026-05-19.md`
- `ops/reports/module_ecology_core_archive_triage_2026-05-19.md`

Moved here:

- `xinyu_v1/gateway/maintenance_gateway.py`
- `xinyu_v1/integrations/legacy_custom_engines.py`
- `xinyu_v1/integrations/napcat_contract.py`
- `xinyu_v1/observability/audit_log.py`
- `xinyu_v1/reasoning/conflict_resolver.py`
- `xinyu_v1/storage/sqlite_meta.py`

Not moved:

- `xinyu_sticker_reference_index.py`
- `xinyu_v1/cli/inspect_memory.py`
- `xinyu_v1/cli/migrate_memory.py`
- `xinyu_v1/memory/chroma_store.py`
- `xinyu_v1/memory/qdrant_store.py`

Reason: the not-moved files are compatibility, operator CLI, or optional
provider surfaces and need explicit retirement/provider policy before archive.

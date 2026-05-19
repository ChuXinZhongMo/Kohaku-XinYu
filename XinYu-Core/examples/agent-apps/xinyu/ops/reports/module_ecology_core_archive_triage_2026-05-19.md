# XinYu Module Ecology Core Archive Triage

Generated from metadata-only module ecology output plus source/import reference
checks. It does not read or print memory, runtime, QQ payload, library, cases,
or data bodies.

## Summary

- source_report: `ops/reports/module_ecology_archive_candidates_2026-05-19.md`
- core_candidates_after_import_fix: 11
- false_positive_keep: 0
- compat_needed: 5
- archive_ready: 6

## Classifications

- `xinyu_sticker_reference_index.py` | classification=compat_needed | evidence=no live refs/tests; standalone CLIP reference-index CLI; keep until moved under ops/manual or covered by a smoke test
- `xinyu_v1/cli/inspect_memory.py` | classification=compat_needed | evidence=no live refs/tests; operator CLI for v1 memory inspection; keep until v1 CLI surface is explicitly retired
- `xinyu_v1/cli/migrate_memory.py` | classification=compat_needed | evidence=no live refs/tests; migration CLI with dry-run/apply mode; keep until legacy memory migration path is declared closed
- `xinyu_v1/memory/chroma_store.py` | classification=compat_needed | evidence=no live refs/tests; optional vector-store provider; keep until vector-store provider policy selects keep/archive
- `xinyu_v1/memory/qdrant_store.py` | classification=compat_needed | evidence=no live refs/tests; optional vector-store provider; keep until vector-store provider policy selects keep/archive
- `xinyu_v1/gateway/maintenance_gateway.py` | classification=archive_ready | evidence=no live refs/tests; no caller found for `build_maintenance_turn`
- `xinyu_v1/integrations/legacy_custom_engines.py` | classification=archive_ready | evidence=no live refs/tests; no caller found for `LegacyCustomEngineRegistry`
- `xinyu_v1/integrations/napcat_contract.py` | classification=archive_ready | evidence=no live refs/tests; no caller found for NapCat constants/helpers
- `xinyu_v1/observability/audit_log.py` | classification=archive_ready | evidence=no live refs/tests; no caller found for `JsonlAuditLog`
- `xinyu_v1/reasoning/conflict_resolver.py` | classification=archive_ready | evidence=no live refs/tests; no caller found for `inspect_conflict`
- `xinyu_v1/storage/sqlite_meta.py` | classification=archive_ready | evidence=no live refs/tests; no caller found for `SQLiteMetaStore`

## Notes

- `xinyu_v1/gateway/models.py`, `xinyu_v1/types.py`, and several v1 model
  modules were removed from the archive-candidate list after AST import parsing
  started recognizing dotted and relative Python imports.
- This report is classification only. It does not move, delete, or rewrite
  candidate files.

# XinYu Core Archive Policy Review - 2026-05-19

Scope: review and act on the 11 core archive candidates from
`ops/reports/module_ecology_archive_candidates_2026-05-19.md`.

Privacy note: this review uses code paths, import/reference search, and the
existing core triage report only. It does not read or print memory, runtime, QQ
payload, library, cases, or data bodies.

## Summary

- core candidates: 11
- archived in this batch: 6
- kept for compatibility/provider policy: 5
- deleted: 0

## Archived

The following files were moved to
`ops/archive/core-orphans/2026-05-19/` with their original relative paths
preserved.

| Original path | Archive path | Reason |
| --- | --- | --- |
| `xinyu_v1/gateway/maintenance_gateway.py` | `ops/archive/core-orphans/2026-05-19/xinyu_v1/gateway/maintenance_gateway.py` | no live refs/tests; no caller found for `build_maintenance_turn` |
| `xinyu_v1/integrations/legacy_custom_engines.py` | `ops/archive/core-orphans/2026-05-19/xinyu_v1/integrations/legacy_custom_engines.py` | no live refs/tests; no caller found for `LegacyCustomEngineRegistry` |
| `xinyu_v1/integrations/napcat_contract.py` | `ops/archive/core-orphans/2026-05-19/xinyu_v1/integrations/napcat_contract.py` | no live refs/tests; no caller found for NapCat constants/helpers |
| `xinyu_v1/observability/audit_log.py` | `ops/archive/core-orphans/2026-05-19/xinyu_v1/observability/audit_log.py` | no live refs/tests; no caller found for `JsonlAuditLog` |
| `xinyu_v1/reasoning/conflict_resolver.py` | `ops/archive/core-orphans/2026-05-19/xinyu_v1/reasoning/conflict_resolver.py` | no live refs/tests; no caller found for `inspect_conflict` |
| `xinyu_v1/storage/sqlite_meta.py` | `ops/archive/core-orphans/2026-05-19/xinyu_v1/storage/sqlite_meta.py` | no live refs/tests; no caller found for `SQLiteMetaStore` |

## Kept

| Path | Policy | Reason |
| --- | --- | --- |
| `xinyu_sticker_reference_index.py` | keep_compat_until_ops_move | standalone CLIP reference-index CLI; should move to ops/manual only after CLI coverage exists |
| `xinyu_v1/cli/inspect_memory.py` | keep_compat_until_v1_cli_retired | operator CLI for v1 memory inspection |
| `xinyu_v1/cli/migrate_memory.py` | keep_compat_until_migration_retired | migration CLI with dry-run/apply mode |
| `xinyu_v1/memory/chroma_store.py` | keep_provider_until_vector_policy | optional vector-store provider |
| `xinyu_v1/memory/qdrant_store.py` | keep_provider_until_vector_policy | optional vector-store provider |

## Direct Effect

- Removes 6 unreferenced core modules from the active source surface without
  deleting them.
- Leaves compatibility, operator CLI, and optional provider surfaces active
  until explicit retirement policy exists.
- Preserves recovery by keeping original relative paths under `ops/archive`.

## Validation Target

After this report, validation should confirm:

- archived source paths no longer exist at their active locations.
- archived files exist under `ops/archive/core-orphans/2026-05-19/`.
- focused tests still pass.
- quick smoke still passes because active runtime imports did not depend on the
  archived modules.

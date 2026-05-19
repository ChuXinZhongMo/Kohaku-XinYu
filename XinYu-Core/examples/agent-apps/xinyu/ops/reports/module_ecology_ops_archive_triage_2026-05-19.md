# XinYu Module Ecology Ops Archive Triage

Generated from metadata-only module ecology output. It does not read or print
memory, runtime, QQ payload, library, cases, or data bodies.

## Summary

- source_report: `ops/reports/module_ecology_archive_candidates_2026-05-19.md`
- ops_candidates: 19
- keep_doc: 8
- archive_doc: 6
- merge_into_index: 5

## Classifications

- `ACTION-LAYER-V1.md` | classification=merge_into_index | evidence=unreferenced ops doc; preserve useful action-layer summary in `INDEX.md` or `STATE-OF-XINYU.md` before archiving
- `DIALOGUE-OBSERVATION-WORKFLOW.md` | classification=archive_doc | evidence=unreferenced workflow doc; no active tests or source references found
- `EXECUTION-ORDER.md` | classification=archive_doc | evidence=unreferenced execution-order doc; likely superseded by worklogs/current plans
- `NAMING-CONVENTIONS.md` | classification=archive_doc | evidence=unreferenced naming doc; no active tests or source references found
- `PUBLIC-DATA-REPLAY.md` | classification=merge_into_index | evidence=unreferenced ops doc; preserve public-data replay rule summary before archiving
- `XINYU-DIRECTION.md` | classification=merge_into_index | evidence=unreferenced direction doc; preserve surviving direction statements before archiving
- `XINYU-SYSTEM-DIAGRAMS.md` | classification=merge_into_index | evidence=unreferenced system diagram doc; preserve still-current diagram links before archiving
- `XINYU-SYSTEM-UTILIZATION-AUDIT.md` | classification=merge_into_index | evidence=unreferenced system audit doc; preserve still-current audit conclusions before archiving
- `codex-qq-20260506T160933/codex-qq-20260506T160933-report.md` | classification=archive_doc | evidence=unreferenced generated report artifact
- `context/desktop_thoughts_state.md` | classification=archive_doc | evidence=unreferenced legacy context state artifact outside current memory/runtime boundary
- `emotions/stickers/manifest.example.json` | classification=keep_doc | evidence=unreferenced example/template; keep until sticker manifest docs point to a newer template
- `ops/manual/manual_archive_commit.py` | classification=keep_doc | evidence=manual operator runner; unreferenced by design
- `ops/manual/manual_archive_output.py` | classification=keep_doc | evidence=manual operator runner; unreferenced by design
- `ops/manual/manual_consolidation.py` | classification=keep_doc | evidence=manual operator runner; unreferenced by design
- `ops/manual/manual_maintenance_recommendation.py` | classification=keep_doc | evidence=manual operator runner; unreferenced by design
- `ops/manual/manual_retention_gate.py` | classification=keep_doc | evidence=manual operator runner; unreferenced by design
- `ops/manual/manual_source_integration_gate.py` | classification=keep_doc | evidence=manual operator runner; unreferenced by design
- `ops/manual/manual_source_reliability.py` | classification=keep_doc | evidence=manual operator runner; unreferenced by design
- `tools/structure_inventory.py` | classification=archive_doc | evidence=unreferenced one-off inventory tool; archive after confirming P70 ecology report replaces it

## Notes

- No files were moved or deleted.
- `keep_doc` here means keep the current file for now, but add an explicit
  docs/index reference later if it remains part of the supported operator
  surface.
- `merge_into_index` means extract the current useful summary first, then
  archive the standalone document in a later batch.

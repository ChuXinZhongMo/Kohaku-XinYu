# XinYu Ops Archive Policy Review - 2026-05-19

Scope: review and act on the 19 ops archive candidates from
`ops/reports/module_ecology_archive_candidates_2026-05-19.md`.

Privacy note: this review uses paths, git status, and the existing ops triage
report. It does not read or print memory, runtime, QQ payload, library, cases,
or data bodies.

## Summary

- ops candidates: 19
- archived in this batch: 5
- kept as manual/template/operator surface: 8
- held for merge into active index: 5
- held due current modification: 1
- deleted: 0

## Archived

The following files were moved to
`ops/archive/ops-orphans/2026-05-19/` with their original relative paths
preserved.

| Original path | Archive path | Reason |
| --- | --- | --- |
| `DIALOGUE-OBSERVATION-WORKFLOW.md` | `ops/archive/ops-orphans/2026-05-19/DIALOGUE-OBSERVATION-WORKFLOW.md` | unreferenced workflow doc; no active tests or source references found |
| `NAMING-CONVENTIONS.md` | `ops/archive/ops-orphans/2026-05-19/NAMING-CONVENTIONS.md` | unreferenced naming doc; no active tests or source references found |
| `codex-qq-20260506T160933/codex-qq-20260506T160933-report.md` | `ops/archive/ops-orphans/2026-05-19/codex-qq-20260506T160933/codex-qq-20260506T160933-report.md` | unreferenced generated report artifact |
| `context/desktop_thoughts_state.md` | `ops/archive/ops-orphans/2026-05-19/context/desktop_thoughts_state.md` | unreferenced legacy context state artifact outside current memory/runtime boundary |
| `tools/structure_inventory.py` | `ops/archive/ops-orphans/2026-05-19/tools/structure_inventory.py` | unreferenced one-off inventory tool; P70 ecology audit replaced the current inventory role |

## Held

| Path | Policy | Reason |
| --- | --- | --- |
| `EXECUTION-ORDER.md` | hold_current_modified | file currently has local modifications; do not move until reviewed |
| `ACTION-LAYER-V1.md` | hold_merge_into_index | preserve useful action-layer summary in active index first |
| `PUBLIC-DATA-REPLAY.md` | hold_merge_into_index | preserve public-data replay rule summary first |
| `XINYU-DIRECTION.md` | hold_merge_into_index | preserve surviving direction statements first |
| `XINYU-SYSTEM-DIAGRAMS.md` | hold_merge_into_index | preserve still-current diagram links first |
| `XINYU-SYSTEM-UTILIZATION-AUDIT.md` | hold_merge_into_index | preserve still-current audit conclusions first |

## Kept

| Path | Policy | Reason |
| --- | --- | --- |
| `emotions/stickers/manifest.example.json` | keep_template | example/template; keep until newer sticker manifest docs exist |
| `ops/manual/manual_archive_commit.py` | keep_manual_runner | manual operator runner; unreferenced by design |
| `ops/manual/manual_archive_output.py` | keep_manual_runner | manual operator runner; unreferenced by design |
| `ops/manual/manual_consolidation.py` | keep_manual_runner | manual operator runner; unreferenced by design |
| `ops/manual/manual_maintenance_recommendation.py` | keep_manual_runner | manual operator runner; unreferenced by design |
| `ops/manual/manual_retention_gate.py` | keep_manual_runner | manual operator runner; unreferenced by design |
| `ops/manual/manual_source_integration_gate.py` | keep_manual_runner | manual operator runner; unreferenced by design |
| `ops/manual/manual_source_reliability.py` | keep_manual_runner | manual operator runner; unreferenced by design |

## Direct Effect

- Removes 5 stale ops artifacts from the active root/tools/context surface.
- Keeps manual operator runners and templates available.
- Avoids moving a currently modified document.
- Leaves merge-needed documents in place until their still-current summaries are
  extracted.

## Validation Target

After this report, validation should confirm:

- 5 original active paths no longer exist.
- 5 archived paths exist under `ops/archive/ops-orphans/2026-05-19/`.
- held and kept paths still exist.
- focused tests and quick smoke pass.

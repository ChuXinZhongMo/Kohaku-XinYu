# XinYu Plan Next 2 Final Audit

Date: 2026-05-18
Plan: `plan-next-2.md`

## Completed Batches

1. P99 unknown path classification
   - P99 unknown package removed from the change package plan.
   - Worklog: `worklog/xinyu-p99-classification-batch-2026-05-18.md`

2. Runtime queue store boundary
   - Added `stores/self_action_queue.py`.
   - `self_action_gateway_approval_queue.jsonl` now has `target=stores/self_action_queue`.
   - Worklog: `worklog/xinyu-self-action-queue-store-boundary-batch-2026-05-18.md`

3. Source material parser consolidation
   - Added `custom/source_material_parser.py`.
   - Old engine function names remain compatibility shims.
   - Worklog: `worklog/xinyu-source-material-parser-consolidation-batch-2026-05-18.md`

4. Persona runtime overlay store boundary
   - Added `stores/persona_runtime_overlay.py`.
   - `goldmark_positive_overlay.json` now has `target=stores/persona_runtime_overlay`.
   - Worklog: `worklog/xinyu-persona-runtime-overlay-store-boundary-batch-2026-05-18.md`

5. Validation and reporting
   - Refreshed:
     - `worklog/xinyu-change-package-plan-2026-05-18.md`
     - `worklog/xinyu-change-package-plan-2026-05-18.json`
     - `worklog/xinyu-change-group-audit-2026-05-18.md`
     - `worklog/xinyu-change-group-audit-2026-05-18.json`

## Validation Evidence

- `git diff --check`
  - Result: passed; CRLF warnings only.
- `.\.venv\Scripts\python.exe -m pytest tests -q`
  - Result: 497 passed.
- `.\.venv\Scripts\python.exe smoke_run.py --group quick --restore-after --timeout-seconds 300`
  - Result: passed.
- Desktop:
  - `npm run typecheck`
  - `npm run build`
  - Result: both passed.

## Current Change Package Snapshot

- total_entries: 654
- package_count: 8
- P99 unknown: absent
- groups:
  - adapters: 27
  - archive/delete: 242
  - core: 140
  - desktop: 16
  - docs: 41
  - memory-data: 5
  - ops: 96
  - services: 4
  - stores: 3
  - tests: 80

## Store Boundary Progress

- `stores/review_state`: review cursor/decisions.
- `stores/self_action_queue`: self-action approval queue.
- `stores/persona_runtime_overlay`: Goldmark runtime expression overlay.

## Remaining Gaps

- `memory_structured_p0_triage.py` is functionally correct but slow on the current dirty tree because it invokes broad reference scans repeatedly.
- Some mutation-capable source learning smokes are safe only when `--restore-after` is supplied; this needs a stronger guard so manual runs do not pollute ignored `memory/**`.
- `learner_integration_engine.py` and `source_integration_gate_engine.py` still contain local I/O helper definitions that are immediately shadowed by `xinyu_state_io` imports.
- P0 structured memory still contains unowned durable runtime state candidates such as `daily_digest.json` and `impulse_soup_state.json`.
- `qq_outbox_queue.json` remains intentionally deferred because it has more callers and private/QQ payload risk.

## Recovery Note

- During Batch 3, source learning smokes were initially run without `--restore-after`; these scripts mutate ignored `memory/**` files by design and did not persist a pre-run restore snapshot.
- Subsequent mutation-capable smokes were run with `--restore-after --diff-lines 0`.
- Future plans should prioritize smoke mutation safety before more broad smoke execution.

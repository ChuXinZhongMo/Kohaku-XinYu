# XinYu Autonomous Continuation Plan 4

Date: 2026-05-18
Workspace: `D:\XinYu`

## Goal

`plan-next-3.md` is complete. This plan continues the same subtractive loop: close low-risk audit residue, move one more durable runtime state behind an explicit store boundary, and define event-log boundaries without exposing or migrating private data bodies.

## Execution Rules

- One capability group per batch.
- Scout first, patch narrowly, run focused tests, then update worklog.
- Do not commit git.
- Do not print secrets, tokens, raw QQ payloads, or private memory bodies.
- Do not use destructive git rollback commands.
- Mutation-capable smokes must use `--restore-after` and preferably `--diff-lines 0`.
- If this plan completes and useful low-risk work remains, write the next plan and continue.

## Batch 1: Archive/Delete Hold Cleanup

Goal: remove the false `hold_delete_referenced` residue from archive/delete audit outputs.

Tasks:
- Confirm `custom/source_gate_manifest.py` is only referenced by audit tests or audit implementation.
- Add focused coverage so self-test/audit references do not count as live references.
- Regenerate archive/delete audit reports.

Acceptance:
- `source_gate_manifest.py` is no longer held solely because of audit-test fixture text.
- `tests/test_archive_delete_reference_audit.py` passes.
- Refreshed audit report has no false hold for audit self-references.

## Batch 2: Impulse Soup Runtime State Store Boundary

Goal: move `memory/context/impulse_soup_state.json` behind an explicit store owner while preserving the compatibility storage path.

Tasks:
- Inspect `xinyu_impulse_soup.py` state read/write behavior.
- Add `stores/impulse_soup_state.py`.
- Update `xinyu_impulse_soup.py` to use the store boundary.
- Add focused store tests.
- Update `stores/README.md`.
- Update P0 triage classification to target `stores/impulse_soup_state`.

Acceptance:
- `memory/context/impulse_soup_state.json` becomes `compat_store_owner_exists`.
- Focused store tests pass.
- `tests/smoke/initiative/impulse_soup_smoke.py` passes.
- P0 triage report is refreshed.

## Batch 3: Event Log Boundary Manifest

Goal: make event-log ownership explicit without moving or printing event bodies.

Candidate paths:
- `memory/context/interaction_journal.jsonl`
- `memory/context/proactive_request_history.jsonl`
- `memory/relationships/owner_recent_events.jsonl`

Tasks:
- Use subagent/local scout results to identify owner modules.
- Add a lightweight manifest or validation table that records owner, kind, privacy level, and migration status.
- Add focused tests for the manifest/boundary classification.
- Do not migrate or display private event content.

Acceptance:
- Event logs are no longer ambiguous in docs/audit tooling.
- Tests validate the boundary metadata without reading event bodies.

## Batch 4: Validation and Next Plan Decision

Tasks:
- `git diff --check`
- Focused pytest for changed areas.
- Full app pytest if runtime behavior changed.
- Quick smoke with `--restore-after`.
- Desktop typecheck/build only if desktop files are touched.
- Refresh change package plan/group audit.
- Write final audit for this plan.
- If useful low-risk work remains, create `plan-next-5.md` and continue.

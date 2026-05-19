# XinYu Autonomous Continuation Plan 7

Date: 2026-05-18
Workspace: `D:\XinYu`

## Goal

`plan-next-6.md` is complete. This plan handles the remaining P0 structured-memory ambiguity without reading, moving, deleting, or printing private state bodies.

## Execution Rules

- One capability group per batch.
- Scout first, patch narrowly, run focused tests, then update worklog.
- Do not commit git.
- Do not print secrets, tokens, raw QQ payloads, or private memory bodies.
- Do not use destructive git rollback commands.
- Mutation-capable smokes must use `--restore-after`.
- If only manual-review content remains after metadata boundaries are defined, stop with a recovery point.

## Batch 1: QQ Queue Boundary

Goal: resolve `memory/context/qq_outbox_queue.json` from generic migration candidate into an explicit metadata-only queue boundary.

Tasks:

- Scout live producer/consumer references without reading queue bodies.
- Add a queue boundary manifest and validation/audit tooling.
- Update P0 triage decision for `qq_outbox_queue.json`.
- Add focused tests.

Acceptance:

- `qq_outbox_queue.json` no longer reports `migrate_candidate_after_caller_update`.
- Queue bodies are not read, migrated, or printed.
- Reference audit declares all live producer/consumer paths.

## Batch 2: Orphan Runtime State Hold Boundary

Goal: make the nine zero-reference runtime JSON files explicitly review-only instead of generic migration candidates.

Tasks:

- Add a metadata-only orphan runtime state hold manifest.
- Update orphan audit/P0 triage to classify those files as held review items.
- Add focused tests.

Acceptance:

- The nine zero-reference runtime JSON files are no longer generic `migrate_candidate` items.
- Deletion remains blocked with `delete_allowed=False`.
- State bodies are not read, moved, or printed.

## Batch 3: Reports and Hold Audit

Tasks:

- Refresh P0 triage.
- Refresh queue boundary audit.
- Refresh orphan runtime state audit.
- Write a hold audit for anything still unsafe.

Acceptance:

- Remaining work is explicitly manual/high-risk, not hidden as generic migration debt.

## Batch 4: Validation and Final Decision

Tasks:

- `git diff --check`
- Focused pytest for changed areas.
- Full app pytest if runtime behavior or shared validation behavior changed.
- Quick smoke with `--restore-after`.
- Desktop typecheck/build only if desktop files are touched or final closeout requires it.
- Refresh change package plan/group audit.
- Write final audit for this plan.
- If no safe low-risk improvement remains, stop with a recovery point.

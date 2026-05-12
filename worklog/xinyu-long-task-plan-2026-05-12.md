# XinYu Long Task Plan - 2026-05-12

## Purpose

Run XinYu engineering work as a repeatable loop until the safe plan below is complete.

This plan continues after the 2026-05-11 integration closeout. It does not add broad product behavior by default. The work is focused on shrinking monolithic files, improving state governance, strengthening validation, and keeping the live runtime observable.

## Current State

- Branch: `master`.
- Last closeout commit: `0c0cbce docs: record integration closeout`.
- Completed post-Loop-144 integration slices:
  - `a52541b refactor: gate stale runtime failure signals`
  - `9eb0f6c feat: add live turn coherence sidecars`
  - `8f5459f feat: add emotion council shadow guardrails`
  - `6fbe6f8 refactor: connect proactive feedback state`
  - `c3d64c9 fix: bypass proxy for local XinYu health checks`
  - `a18567e fix: lazily initialize plugin model patterns`
- Current uncommitted code slice:
  - Continue QQ reply bubble helper extraction in:
    - `XinYu-Core/examples/agent-apps/xinyu/xinyu_qq_gateway.py`
    - `XinYu-Core/examples/agent-apps/xinyu/xinyu_qq_gateway_smoke.py`
    - `XinYu-Core/examples/agent-apps/xinyu/xinyu_qq_reply_bubbles.py`
- Current untracked plan files:
  - `XINYU-24H-WORK-PLAN.md`
  - `worklog/integration-closeout-plan-2026-05-11.md`

## Hard Rules

- Do not edit persona semantics.
- Do not edit long-term memory body text.
- Do not run real QQ outbound tests unless the owner explicitly approves.
- Do not widen v1 real traffic unless the owner explicitly approves.
- Do not delete runtime, memory, Autonomy, or Local-Scope directories.
- Do not use destructive git commands such as `git reset --hard` or broad checkout.
- Do not hide validation failures. If a command fails, record it and either fix narrowly or stop if the failure crosses a red line.
- Keep every successful code slice separately revertible with `git revert <commit>`.
- Do not collapse unrelated slices into one commit.

## Automatic Loop Instruction

Repeat this loop until every item in "Safe Execution Queue" is complete or a stop condition is hit.

1. Sync:
   - Run `git status --short --branch`.
   - Run `git log --oneline -5`.
   - Confirm dirty files are either the current slice or known untracked plan files.
2. Pick one slice:
   - Choose the first unchecked item in the Safe Execution Queue.
   - The slice must have a narrow owner file set and a validation command set.
3. Inspect:
   - Read only the files needed for the current slice.
   - Use `rg` for search and local reads for exact edit points.
4. Patch:
   - Preserve external behavior, routes, payload shapes, config names, and visible text semantics.
   - Prefer alias/extraction patterns already used in the repository.
5. Validate:
   - Run `git diff --check`.
   - Compile changed Python files.
   - Run the focused smoke or pytest commands listed for the slice.
   - Run broader gateway/bridge smoke only when the touched files affect those surfaces.
6. Record:
   - Append a loop entry to `worklog/24h-refactor-progress.md`.
   - Mark the queue item complete in this plan and, when mirrored there, in `worklog/24h-next-task-queue.md`.
7. Commit:
   - Stage only files belonging to the current slice.
   - Commit with a focused message.
8. Continue:
   - Start the next unchecked safe item immediately.
   - Every 4-6 loops, run a health checkpoint and record it.

## Stop Conditions

Stop and report before continuing if any of these occur:

- Live core status fails after a code slice.
- QQ gateway logs new repeated `core bridge HTTP 502` after the latest gateway start.
- A slice requires changing persona, prompt semantics, or long-term memory body text.
- A slice requires real QQ outbound testing.
- A slice requires widening v1 real traffic.
- Validation fails twice for the same slice after one narrow fix.
- The dirty worktree contains unexpected user edits in the same files needed by the current slice.
- A planned change becomes a broad rewrite instead of a reversible slice.

## Safe Execution Queue

### P0 - Close Current Dirty Slice

- [x] Loop 145: Finish QQ visible reply bubble split extraction.
  - Goal: Move split decision and visible bubble chunking ownership into `xinyu_qq_reply_bubbles.py`; keep gateway methods as compatibility aliases.
  - Files:
    - `XinYu-Core/examples/agent-apps/xinyu/xinyu_qq_gateway.py`
    - `XinYu-Core/examples/agent-apps/xinyu/xinyu_qq_reply_bubbles.py`
    - `XinYu-Core/examples/agent-apps/xinyu/xinyu_qq_gateway_smoke.py`
    - `worklog/24h-refactor-progress.md`
    - `worklog/24h-next-task-queue.md`
  - Validation:
    - `D:\XinYu\Python312\python.exe -m py_compile xinyu_qq_gateway.py xinyu_qq_gateway_smoke.py xinyu_qq_reply_bubbles.py`
    - `D:\XinYu\Python312\python.exe xinyu_qq_gateway_smoke.py`
    - `D:\XinYu\Python312\python.exe xinyu_qq_review_smoke.py`
    - `git diff --check`
  - Commit: `refactor: extract qq reply bubble split helpers`

### P1 - Continue QQ Gateway Decomposition

- [ ] Extract the next isolated QQ reply bubble/outbox helper if gateway still owns pure reply bubble logic.
- [x] Audit remaining `NativeQQGateway` pure methods and classify them into owner modules.
- [x] Extract one low-risk QQ runtime/outbox helper from `xinyu_qq_gateway.py` into the existing flat helper modules.
- [x] Add or extend one focused QQ smoke that pins the extracted helper alias.
- [ ] Update `XINYU-VALIDATION-MATRIX.md` for any new QQ slice gate.

### P1 - Continue Core Bridge Decomposition

- [x] Audit remaining pure helper/static wrapper methods in `xinyu_core_bridge.py`.
- [x] Extract one low-risk core bridge helper into an existing `xinyu_bridge_*` module.
- [x] Replace one compatibility wrapper with a direct alias where behavior is already covered.
- [x] Add or extend one focused bridge smoke for the boundary.
- [ ] Update `XINYU-VALIDATION-MATRIX.md` for any new bridge slice gate.

### P1 - State Governance

- [ ] Audit direct runtime/projection writes that still bypass `state_service.py`.
- [ ] Pick one low-risk runtime/projection writer and migrate it to `state_service.py`.
- [ ] Add a focused smoke for the migrated caller if none exists.
- [ ] Update `XINYU-STATE-WRITE-AUDIT.md`.
- [ ] Update `XINYU-VALIDATION-MATRIX.md`.

### P2 - Validation And Operations

- [ ] Run a long-run health checkpoint after every 4-6 successful loops.
- [ ] Keep `recent_exceptions` from regressing due to stale log windows.
- [ ] Add a validation inventory entry for any smoke added during this plan.
- [ ] Re-run final local gates after all safe P0/P1/P2 items complete:
  - `xinyu_status.py --json`
  - `deployment_status_smoke.py`
  - `bridge_probe_smoke.py`
  - `xinyu_qq_gateway_smoke.py`
  - `xinyu_qq_review_smoke.py`
  - `diagnostics/check_xinyu_health.py --json --workspace D:\XinYu`

## Deferred / Owner-Approval Queue

These are real remaining gaps, but this automatic loop must not execute them without explicit owner approval:

- Full long-term memory body migration.
- Full event/projection conversion.
- Full chat pipeline rewrite.
- Desktop UI large refactor.
- v1 real traffic expansion.
- Real QQ outbound tests.
- Productized deployment or installer work.

## Completion Criteria

The long task is complete when:

- All Safe Execution Queue items are checked or explicitly recorded as no-op after inspection.
- Every completed slice has a loop entry and a separate commit.
- Final local gates pass, or any warning is documented as non-blocking and not caused by new work.
- Deferred / Owner-Approval Queue remains untouched unless the owner explicitly approves a specific item.

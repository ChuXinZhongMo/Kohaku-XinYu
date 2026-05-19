# XinYu Autonomous Continuation Plan 5

Date: 2026-05-18
Workspace: `D:\XinYu`

## Goal

`plan-next-4.md` is complete. This plan continues the subtractive cleanup loop by closing small boundary mismatches that are now visible in the refreshed audits.

## Execution Rules

- One capability group per batch.
- Scout first, patch narrowly, run focused tests, then update worklog.
- Do not commit git.
- Do not print secrets, tokens, raw QQ payloads, or private memory bodies.
- Do not use destructive git rollback commands.
- Mutation-capable smokes must use `--restore-after` and preferably `--diff-lines 0`.
- If this plan completes and useful low-risk work remains, write the next plan and continue.

## Batch 1: Review State Triage Closure

Goal: align P0 triage with the existing `stores/review_state.py` boundary.

Tasks:
- Confirm review cursor/decision files are owned by `stores/review_state.py`.
- Update P0 triage decisions for `review_inbox_cursor.json` and `review_inbox_decisions.json`.
- Add or update tests for this classification.
- Regenerate P0 triage report.

Acceptance:
- Both review state files report `compat_store_owner_exists`.
- Focused triage tests pass.
- No review body content is printed.

## Batch 2: Sticker Send State Boundary Decision

Goal: resolve `memory/context/sticker_send_state.generated.json` from manual review into an explicit low-risk boundary.

Tasks:
- Scout `xinyu_sticker_pack.py` and existing sticker tests without printing sticker/private payload bodies.
- If the state is runtime/generated cache, add a small store owner and tests while keeping the legacy physical path.
- Otherwise, add a manifest-only decision and leave migration deferred.
- Update P0 triage accordingly.

Acceptance:
- `sticker_send_state.generated.json` no longer reports generic `manual_review`.
- Focused sticker state tests pass.

## Batch 3: No-Reference Durable Runtime State Audit

Goal: make no-reference durable runtime state files reviewable without deleting or reading bodies.

Tasks:
- Add an ops audit that lists P0 durable runtime state files with zero source references.
- Classify them as `orphan_runtime_state_review` rather than delete instructions.
- Add focused tests proving the audit reports paths/counts only.

Acceptance:
- No-reference runtime state files are listed in a privacy-safe report.
- The report is explicitly non-destructive.

## Batch 4: Validation and Next Plan Decision

Tasks:
- `git diff --check`
- Focused pytest for changed areas.
- Full app pytest if runtime behavior changed.
- Quick smoke with `--restore-after`.
- Desktop typecheck/build only if desktop files are touched or final closeout requires it.
- Refresh change package plan/group audit.
- Write final audit for this plan.
- If useful low-risk work remains, create `plan-next-6.md` and continue.

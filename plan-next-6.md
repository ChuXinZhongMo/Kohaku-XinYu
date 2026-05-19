# XinYu Autonomous Continuation Plan 6

Date: 2026-05-18
Workspace: `D:\XinYu`

## Goal

`plan-next-5.md` is complete. This plan handles the remaining low-risk P0 boundary items that still have live callers but do not require moving private/QQ payloads.

## Execution Rules

- One capability group per batch.
- Scout first, patch narrowly, run focused tests, then update worklog.
- Do not commit git.
- Do not print secrets, tokens, raw QQ payloads, or private memory bodies.
- Do not use destructive git rollback commands.
- Mutation-capable smokes must use `--restore-after` and preferably `--diff-lines 0`.
- If this plan completes and only high-risk/manual-review work remains, write a stop/hold audit instead of inventing low-value churn.

## Batch 1: Source Extract Boundary

Goal: resolve `memory/creative/planning/inspiration/safe_extracts.jsonl` from generic migration candidate into an explicit compatibility boundary.

Tasks:
- Scout `xinyu_creative_writing.py` source extract path usage without printing row bodies.
- Add a metadata/store boundary if the caller can remain on the legacy physical path.
- Update P0 triage target/decision.
- Add focused tests.

Acceptance:
- `safe_extracts.jsonl` no longer reports `migrate_candidate_after_caller_update`.
- No JSONL bodies are printed or migrated.

## Batch 2: Runtime Trace Boundary

Goal: resolve `memory/context/impulse_soup_trace.jsonl` from archive candidate into a manifest-defined runtime trace boundary.

Tasks:
- Scout `xinyu_impulse_soup.py` and `xinyu_runtime_presence.py` references without reading trace bodies.
- Add metadata-only runtime trace manifest or audit.
- Update P0 triage decision for `impulse_soup_trace.jsonl`.
- Add focused tests.

Acceptance:
- `impulse_soup_trace.jsonl` no longer reports `archive_candidate_after_caller_update`.
- No trace bodies are printed or migrated.

## Batch 3: Hold/Stop Audit for Remaining Risk

Goal: identify what remains after low-risk work and explicitly separate high-risk/manual-review items from actionable low-risk work.

Tasks:
- Refresh P0 triage and orphan runtime state audit.
- Write a hold audit listing remaining high-risk items and why they are not safe for autonomous mutation.

Acceptance:
- Remaining work is clearly classified as high-risk, manual-review, or not worth further churn.

## Batch 4: Validation and Final Decision

Tasks:
- `git diff --check`
- Focused pytest for changed areas.
- Full app pytest if runtime behavior changed.
- Quick smoke with `--restore-after`.
- Desktop typecheck/build only if desktop files are touched or final closeout requires it.
- Refresh change package plan/group audit.
- Write final audit for this plan.
- If only high-risk/manual-review work remains, stop with a recovery point instead of continuing automatically.

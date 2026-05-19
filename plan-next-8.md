# XinYu Autonomous Continuation Plan 8

Date: 2026-05-18
Workspace: `D:\XinYu`

## Goal

`plan-next-7.md` is complete and all P0 structured-memory items now have explicit boundaries or holds. This plan adds one final non-invasive review layer: a single boundary readiness audit that aggregates the existing manifests and reference audits without reading private data bodies.

## Execution Rules

- One capability group per batch.
- Scout first, patch narrowly, run focused tests, then update worklog.
- Do not commit git.
- Do not print secrets, tokens, raw QQ payloads, or private memory bodies.
- Do not use destructive git rollback commands.
- Mutation-capable smokes must use `--restore-after`.
- If this plan passes and no generic P0 migration/archive decisions remain, stop with a recovery point.

## Batch 1: Boundary Readiness Audit

Goal: provide one command/report that answers whether all current memory/store/queue/event/trace/orphan boundaries are declared and validated.

Tasks:

- Aggregate existing validators:
  - memory library manifest
  - event boundary manifest
  - runtime trace manifest
  - queue boundary manifest
  - orphan runtime state hold manifest
- Aggregate existing reference audits:
  - event log boundary audit
  - runtime trace boundary audit
  - queue boundary audit
  - orphan runtime state audit
- Include P0 generic-decision status.
- Add focused tests.

Acceptance:

- One CLI writes markdown/json readiness reports.
- Report status is `pass` only when all manifests/audits pass and no generic P0 migration/archive/manual-review decisions remain.
- No private JSON/JSONL bodies are read or printed.

## Batch 2: Final Validation and Stop Decision

Tasks:

- Run focused tests for readiness audit.
- Run full app pytest if validation behavior changed.
- Run quick smoke with `--restore-after`.
- Refresh change package/group audit.
- Write final audit.
- Stop if no low-risk autonomous work remains.

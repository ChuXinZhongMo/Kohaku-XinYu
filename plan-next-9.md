# Plan Next 9: Commit Readiness Audit

Date: 2026-05-18
Workspace: `D:\XinYu`

## Goal

Turn the large dirty XinYu worktree into reviewable, commit-ready packages without committing.

This plan is metadata-only:

- read `git status --short` paths
- reuse existing boundary and cleanup audits
- do not read or print private memory bodies, QQ payload bodies, tokens, or secrets
- do not run destructive git commands

## Batch 1: Commit Readiness Aggregator

1. Add `ops/validation/commit_readiness_audit.py`.
2. Aggregate:
   - change package plan
   - change group audit
   - archive/delete reference audit
   - boundary readiness audit
3. Report:
   - total dirty entries
   - package counts and risk counts
   - unknown/P99 count
   - archive/delete decision counts
   - boundary readiness status
   - recommended review order
   - kept/merged/archived/deleted/hold/risk summary
4. Add focused tests for deterministic status input.

## Batch 2: Refresh Reports

1. Refresh change package plan markdown/json.
2. Refresh change group audit markdown/json.
3. Refresh archive/delete reference audit markdown/json.
4. Refresh boundary readiness audit markdown/json.
5. Generate commit readiness audit markdown/json.

## Batch 3: Validation

1. Run focused compile and pytest for validation tooling.
2. Run `git diff --check`.
3. Run full app pytest if the validation tooling changes pass focused tests.
4. Run quick smoke with `--restore-after`.
5. Run desktop `npm run typecheck` and `npm run build`.

## Batch 4: Worklog And Stop Decision

1. Write `worklog/xinyu-commit-readiness-audit-batch-2026-05-18.md`.
2. Write `worklog/xinyu-plan-next-9-final-audit-2026-05-18.md`.
3. Decide whether another autonomous plan is still useful.

## Done

- `commit_readiness_audit.py` exists and is tested.
- Reports are refreshed under `worklog/`.
- Unknown package count is visible.
- Archive/delete holds are visible.
- Boundary readiness is visible.
- Final worklog lists kept, merged, archived, deleted, remaining risks, and validation evidence.
- No git commit is made.

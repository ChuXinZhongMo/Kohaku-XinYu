# Branch Policy

Status: active as of 2026-07-13  
Related: `docs/plans/ENGINEERING-MATURITY-PLAN.md`

## Canonical branch

- **Remote default:** `main` (`origin/HEAD` → `origin/main`)
- **Historical dual branch:** `master` has been used as a long-lived integration
  branch and may be ahead of `main` during the engineering hardening window.

Until cutover is complete:

| Branch | Role |
|--------|------|
| `main` | Canonical public default; protect once CI is green on it |
| `master` | May hold newer local integration work; do not treat as second product line |

## Contributor rule

1. Open pull requests against **`main`** once cutover is done.
2. During transition, maintainers may accept PRs to `master` only if `main` is
   still lagging; every such PR must note the follow-up merge into `main`.
3. Do not commit directly to either protected branch once GitHub protection is
   enabled.

## Cutover checklist (maintainer)

1. Ensure CI is green on the tip that will become the single line of history.
2. Create a backup tag: `backup/pre-main-cutover-YYYYMMDD`.
3. Fast-forward or merge `master` into `main` (prefer a merge commit if histories
   diverged non-trivially; document the choice in the merge PR).
4. Push `main`, set it as the only default branch in GitHub settings.
5. Enable branch protection on `main`:
   - require pull request
   - require status checks: `Python tests (blocking)`,
     `Python lint critical (blocking)`, `Desktop typecheck (blocking)`
   - dismiss stale reviews on new commits
6. Update local clones: `git checkout main && git pull`.
7. Stop pushing to `master`. After one stable release cycle, delete `origin/master`
   or archive it as `archive/master`.

## CI branches

`.github/workflows/ci.yml` listens to both `main` and `master` until cutover
completes, then `master` should be removed from the trigger list.

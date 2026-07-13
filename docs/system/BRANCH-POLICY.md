# Branch Policy

Status: **cutover completed 2026-07-13**  
Related: `docs/plans/ENGINEERING-MATURITY-PLAN.md`

## Canonical branch

- **Canonical branch:** `main`
- **Active integration tip (cutover source):** was `master` at `3833d2f`
- **Old public `main` tip (pre-cutover):** `2461020` — preserved as tag
  `backup/pre-main-cutover-20260713-main`
- **Pre-cutover `master` tip:** also tagged
  `backup/pre-main-cutover-20260713-master` (same commit as the new `main`)

### Why not a normal merge?

Local `main` and `master` had **unrelated histories** (`git merge` refused without
`--allow-unrelated-histories`). The long-running product/engineering line lived
on `master`. Cutover therefore **retargeted `main` to the `master` tip** after
backup tags, rather than inventing a synthetic dual-root merge.

## Contributor rule

1. Open pull requests against **`main`**.
2. Do not open new long-lived work on `master`.
3. After remote default is confirmed as `main` and CI is green, stop pushing to
   `master`. Optionally rename remote `master` to `archive/master` after one
   stable release cycle.

## Cutover record

| Step | Status |
|------|--------|
| Backup tag `backup/pre-main-cutover-20260713-main` | done |
| Backup tag `backup/pre-main-cutover-20260713-master` | done |
| Point local `main` at `master` tip | done |
| Push `main` (force-with-lease; non-ff vs old main) | in progress |
| Push backup tags | in progress |
| GitHub default branch = `main` | **maintainer UI / `gh`** |
| Branch protection on `main` | **maintainer UI** |
| Archive/delete remote `master` | deferred one release cycle |

### Branch protection (recommended)

On `main`:

- require pull request
- require status checks:
  - `Python tests (blocking)`
  - `Python lint critical (blocking)`
  - `Desktop typecheck (blocking)`
- dismiss stale reviews on new commits

## CI branches

`.github/workflows/ci.yml` may still list `master` briefly for compatibility;
new work should target `main` only.

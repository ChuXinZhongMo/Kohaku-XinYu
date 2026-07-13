# Branch Protection — Maintainer Setup

Status: active after main cutover (2026-07-13)  
Audience: repository admin (`ChuXinZhongMo`)  
Related: `docs/system/BRANCH-POLICY.md`

GitHub **cannot** fully enable branch protection from a normal `git push`.
Do this once in the UI (or via `gh api` with admin rights).

## 1. Confirm default branch

Repo → **Settings** → **General** → **Default branch** = **`main`**.

Current cutover tip should match `origin/main` (engineering + product line).

## 2. Protect `main`

Repo → **Settings** → **Branches** → **Add branch protection rule**

| Field | Recommended value |
|-------|-------------------|
| Branch name pattern | `main` |
| Require a pull request before merging | **On** (1 approval optional while solo; can set 0 reviewers if you allow admin bypass carefully) |
| Dismiss stale pull request approvals when new commits are pushed | **On** |
| Require status checks to pass before merging | **On** |
| Require branches to be up to date before merging | **On** (once CI is reliable) |
| Status checks that are required | see list below |
| Require conversation resolution before merging | optional |
| Do not allow bypassing the above settings | On for non-admins; admins may keep bypass while solo |
| Restrict who can push to matching branches | optional |
| Allow force pushes | **Off** |
| Allow deletions | **Off** |

### Required status checks (exact job names from `.github/workflows/ci.yml`)

After the rule exists, open a draft PR or wait for a run so checks appear, then tick:

1. **`Python tests (blocking)`**
2. **`Python lint critical (blocking)`**
3. **`Desktop typecheck (blocking)`**
4. **`Python smoke offline (blocking)`** — curated hermetic smokes only

Do **not** require (informational only):

- `Python lint core full (informational)`
- `Python lint app full (informational)`
- `Python smoke (informational)` — full corpus / live-ish
- jobs from `security.yml` (pip-audit / npm audit)

API (admin) sketch to set the four required checks:

```bash
gh api -X PATCH repos/ChuXinZhongMo/Kohaku-XinYu/branches/main/protection/required_status_checks \
  --input - <<'EOF'
{
  "strict": true,
  "checks": [
    {"context": "Python tests (blocking)"},
    {"context": "Python lint critical (blocking)"},
    {"context": "Desktop typecheck (blocking)"},
    {"context": "Python smoke offline (blocking)"}
  ]
}
EOF
```

## 3. Optional `gh` sketch (admin)

```bash
# Inspect current protection (may 404 if none)
gh api repos/ChuXinZhongMo/Kohaku-XinYu/branches/main/protection

# Example PUT (adjust JSON to taste; requires admin)
# Prefer UI if unsure — a wrong payload can lock the branch.
```

If you use the API, always keep an admin bypass until the first green PR merges successfully.

## 4. What about `master`?

- Remote `master` archived after `v0.1.0` (see `docs/system/BRANCH-POLICY.md`).
- Tip preserved as `archive/master` + cutover backup tags.
- Do **not** protect `master` as a second product line.

## 5. Labels (community hygiene)

Settings → Labels (or Issues → Labels). Suggested:

`bug` `enhancement` `documentation` `gateway` `good first issue` `engineering` `privacy` `dependencies`

## 6. After protection is on

1. Open PRs against **`main`** only.
2. Local: `git checkout main && git pull`.
3. Do not commit release tags from a dirty tree; see `docs/plans/RELEASE-CHECKLIST.md`.

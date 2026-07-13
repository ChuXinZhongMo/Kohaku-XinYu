# Release Checklist

Status: active as of 2026-07-13  
Audience: maintainers preparing a public tag / GitHub Release  
Related: `CHANGELOG.md`, `OPEN_SOURCE_POLICY.md`, `docs/system/BRANCH-POLICY.md`, `docs/system/FRESH-INSTALL.md`

Use this before every annotated public tag (`v0.1.0`, RC tags, or later semver).
Do **not** invent pass counts—record the actual numbers from the commit you tag.

---

## 0. Decide the release shape

- [ ] Semver choice: `v0.1.0` final vs `v0.1.0-rc.N` then final
- [ ] Target commit identified (SHA) and on the intended branch line
- [ ] Branch policy understood: remote default is **`main`**; see `docs/system/BRANCH-POLICY.md`
- [ ] No dual-product-line confusion: if tagging from `master` during cutover, document the follow-up merge into `main`

---

## 1. Pre-tag validation matrix

Run on the **exact commit** to be tagged. Prefer a clean worktree or CI green on that SHA.

### 1.1 Blocking gates (must pass)

| Gate | How | Record |
|------|-----|--------|
| Python tests (blocking) | `make test` or `cd XinYu-Core/examples/agent-apps/xinyu && python -m pytest -q -m "not smoke"` | pass count / date / SHA |
| Python lint critical (blocking) | `make lint` or `ruff check XinYu-Core/src --select F,E9,F63,F7,F82` | exit 0 |
| Desktop typecheck (blocking) | `cd XinYu_Desktop && npm ci && npm run typecheck` (+ lint if present) | exit 0 |
| CI on target ref | GitHub Actions: jobs named `Python tests (blocking)`, `Python lint critical (blocking)`, `Desktop typecheck (blocking)` | green |

### 1.2 Informational / optional (record, do not pretend they block)

| Check | How | Notes |
|-------|-----|--------|
| Full ruff core | `ruff check XinYu-Core/src` | residual debt allowed until cleaned |
| App ruff | critical + full under xinyu app (see CI) | informational |
| Smoke marker suite | `pytest -q -m smoke` | often needs live local env; CI is `continue-on-error` |
| Quick operator smoke (Windows) | `.\XinYu.ps1 smoke` or app `smoke_run.py --group quick` | provisioned machine only |
| QQ verify | `.\XinYu.ps1 verify qq` | live stack; not a public CI gate |
| Coverage artifact | CI uploads `coverage.xml`; no floor enforced yet | optional local `make test-cov` |

### 1.3 Validation log template (paste into release notes or worklog)

```text
Release candidate SHA: ____________
Date (local): ____________
Python tests (-m "not smoke"): ____ passed / ____ failed / ____ skipped
Ruff critical (XinYu-Core/src): pass | fail
Desktop typecheck: pass | fail
CI URL: ____________
Optional smoke notes: ____________
```

Historical baseline in `CHANGELOG.md` / root `README.md` (2026-05-21: 786 passed, etc.) is **not** a substitute for re-running on the tag commit.

---

## 2. Privacy dry-run

Goal: prove the distributable tree has no private runtime state.

### 2.1 Ignore and example audit

- [ ] Only env **examples** are tracked (`xinyu.local.env.example`, any other `*.env.example`)
- [ ] No tracked `*.env`, `*.local.env`, keys, or PEMs (`git ls-files` / search)
- [ ] No accidental add of `memory/`, `runtime/`, `logs/`, owner-supplied bodies
- [ ] `.gitignore` still covers `runtime/deps/`, app `.venv`, desktop `node_modules/`, private trees

### 2.2 Automated helper (Windows)

If present, run the read-only helper from repo root:

```powershell
.\scripts\Release-DryRun.ps1
.\scripts\Release-DryRun.ps1 -Archive -Strict   # optional stricter export scan
```

Treat script output as a signal, not a substitute for the manual checks below.
Record the script version/date and any findings in the release log.

### 2.3 Clean export inspection

From a clean clone or archive of the tag commit:

```bash
# example: inspect what would ship without local untracked junk
git archive --format=tar HEAD | tar -t | head   # spot-check paths
# or full list redirected to a file and grepped for risky names:
# git archive --format=tar HEAD | tar -t > /tmp/xinyu-export.list
```

Search the export list (or a fresh clone with no private mounts) for:

- `.env` (except `*.example`)
- `memory/`, `owner_supplied`, private replay paths
- `runtime/deps`, NapCat bundles, venvs
- tokens, cookies, real QQ IDs in fixtures

Also:

```bash
git status --ignored   # local only; ensure ignored private dirs are not force-added
git check-ignore -v path/to/suspicious/file
```

### 2.4 Content spot-checks

- [ ] No secrets in docs, worklogs, or “sanitized” reports
- [ ] Gateway fixtures are synthetic / redacted
- [ ] `OPEN_SOURCE_POLICY.md` and `SECURITY.md` still describe the real boundary
- [ ] `THIRD-PARTY-NOTICES.md` updated if dependencies were added for this release

---

## 3. CHANGELOG, tag, and GitHub Release

### 3.1 CHANGELOG

- [ ] `CHANGELOG.md` has a section for this version (not only “Unreleased”)
- [ ] Highlights, validation baseline for **this** SHA, publication boundary, known gaps
- [ ] App-local changelogs (if any) do not contradict the root release story

### 3.2 Tag

```bash
# after privacy + validation on the exact commit
git tag -a v0.1.0 -m "XinYu v0.1.0 public source baseline"
git push origin v0.1.0
```

- [ ] Annotated tag (not lightweight) preferred
- [ ] Tag points at the validated SHA
- [ ] Do not force-move a published tag without a documented incident process

### 3.3 GitHub Release

- [ ] Create GitHub Release from the tag
- [ ] Body includes CHANGELOG section + validation log + privacy statement
- [ ] No private attachments (logs, memory dumps, real screenshots with PII)
- [ ] Link `OPEN_SOURCE_POLICY.md` / license notes (KohakuTerrarium License 1.0)

---

## 4. Branch policy reminder

- Canonical remote default: **`main`**
- During cutover, `master` may still hold integration work; do not treat it as a second product line
- Prefer tagging from the line that will become (or already is) protected `main`
- If cutover is part of this release:
  1. Backup tag: `backup/pre-main-cutover-YYYYMMDD`
  2. Merge/ff into `main` per `docs/system/BRANCH-POLICY.md`
  3. Protect `main` with required checks:
     - `Python tests (blocking)`
     - `Python lint critical (blocking)`
     - `Desktop typecheck (blocking)`
  4. Stop pushing to `master`; archive after one stable cycle

---

## 5. Post-release

- [ ] Update root `README.md` “Current Validation Baseline” if numbers changed
- [ ] Mark completed items in `docs/plans/ENGINEERING-30-DAY-CHECKLIST.md` only when true
- [ ] File follow-ups as issues (good first issues, residual ruff, smoke curation)
- [ ] Dependabot / security advisories: no action required for the tag itself unless a CVE ships in deps

---

## 6. Explicit non-goals for v0.1.x tags

These are **not** release blockers unless you choose them to be:

- Full mypy strictness
- Full app-tree ruff clean
- Dockerized full QQ/NapCat stack
- Coverage floor enforcement
- Multi-maintainer governance formalization

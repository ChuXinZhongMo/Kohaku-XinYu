# Release Dry-Run — Final gate for v0.1.0 (2026-07-13)

**Tag decision:** proceed with `v0.1.0` after this report + green blocking CI on tip.  
**Related:** `docs/plans/RELEASE-CHECKLIST.md`, `docs/system/BRANCH-PROTECTION.md`

## Git / branch

| Item | Value |
|------|--------|
| Default branch | `main` (protected) |
| Tip at dry-run | see git log after merge of pywebview + dry-run tar fix |
| Untracked local only | `memory/`, `runtime/*`, `terminals/`, `oct_tmp.txt` (not in archive) |
| Tracked denylist | **PASS** |
| Content scan HIGH | 2× test fixture Bearer strings (`secretsecretsecret123`) — **false positives** |
| Archive | Windows `tar.exe` listing; no denylist hits after tar fix |

## Blocking CI (required)

On `main` tip used for tag:

| Check | Result |
|-------|--------|
| Python tests (blocking) | **pass** (verified on 07f3759 and pywebview PR rebased to main) |
| Python lint critical (blocking) | **pass** |
| Desktop typecheck (blocking) | **pass** |

Informational full ruff / smoke / npm audit may fail — non-blocking by design.

## Branch protection

Enabled via API on `main`:

- required checks: the three blocking jobs above (`strict: true`)
- dismiss stale reviews: true
- force push / delete: **off**
- enforce_admins: **false** (solo maintainer escape hatch)

## Dependabot

| PR | Decision |
|----|----------|
| #5 pywebview 6.1→6.2.1 | **merged** (patch, blocking green) |
| #1–4 Actions major bumps | **deferred** post-v0.1.0 |
| #6–10 npm major (TS7/ESLint10/electron-vite5) | **deferred** post-v0.1.0 |

## Final tag readiness

- [x] main protected  
- [x] blocking CI green on release line  
- [x] denylist clean  
- [x] archive no private paths  
- [x] CHANGELOG section for v0.1.0 updated  
- [x] prerelease rc.2 already exists  

**Ship `v0.1.0` as first public final from this line.**

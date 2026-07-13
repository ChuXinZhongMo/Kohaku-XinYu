# Release Dry-Run Report — 2026-07-13

**Scope:** pre-tag readiness only. **No tag created.**  
**HEAD at report time:** `7b5853c` (then advanced by architecture commit)  
**Branch:** cutover complete — GitHub default branch is **`main`** (aligned with former `master` tip).

## Commands

```powershell
.\scripts\Release-DryRun.ps1 -Archive
```

Also reviewed: `docs/plans/RELEASE-CHECKLIST.md`, `CHANGELOG.md` Unreleased section.

## Results summary

| Check | Result | Notes |
|-------|--------|-------|
| Git context | WARN | Working tree dirty (expected: WIP + architecture in flight) |
| Tracked denylist | HIGH (noise) | Matches `xinyu_v1/memory/*.py` — **source package**, not private runtime memory dumps |
| Heuristic secret scan | partial fail | Script choked on a path with non-ASCII characters (`Test-Path : Illegal characters in path`) — tool bug to fix |
| Archive scan | not completed cleanly | Blocked by content-scan path bug |
| Backup tags | OK | `backup/pre-main-cutover-20260713-main`, `backup/pre-main-cutover-20260713-master` on origin |
| Default branch | OK | `origin/HEAD` → `main` |

## Interpretation

### Real blockers before `v0.1.0` tag

1. **Clean tree** for the exact tag commit (no unstaged product WIP).
2. **Re-run validation baseline** on that commit (pytest non-smoke + desktop typecheck at minimum).
3. **Fix Release-DryRun.ps1** path handling for Unicode paths and tighten denylist so `**/xinyu_v1/memory/**` code is not treated as private data.
4. **Decide tag name:** recommend `v0.1.0-rc.2` first (engineering + cutover just landed), then `v0.1.0` after one green CI cycle on `main`.
5. **Branch protection on `main`** (maintainer GitHub UI) still recommended before advertising the release.

### Not blockers (false positives)

- Tracked files under `xinyu_v1/memory/` are **implementation modules** for the memory subsystem, not live owner memory stores (those remain gitignored under app `memory/` / `runtime/`).

## Recommendation

| Option | When |
|--------|------|
| **`v0.1.0-rc.2`** | After architecture follow-up commits land and CI on `main` is green |
| **`v0.1.0`** | After clean dry-run on a clean tree + validation matrix re-run |

**Do not tag from a dirty working tree.**

## Follow-ups (tracked)

- [ ] Fix `scripts/Release-DryRun.ps1` Unicode path bug
- [ ] Denylist: exclude package paths like `xinyu_v1/memory/` source; keep ignoring live `memory/` runtime dirs
- [ ] Clean commit product WIP or stash before tag
- [ ] CI green on `main` for tip
- [ ] Maintainer: enable branch protection

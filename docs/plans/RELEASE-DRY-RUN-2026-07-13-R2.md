# Release Dry-Run Report R2 — 2026-07-13

**Intent:** prepare `v0.1.0-rc.2`  
**Tag created:** **NO**  
**HEAD evaluated:** `bda33b6` (`main` / `master`)

## Branch protection

See `docs/system/BRANCH-PROTECTION.md` (UI steps). Not automatable without admin API risk.

## Dry-run automation

```powershell
.\scripts\Release-DryRun.ps1 -Archive
```

| Check | Result |
|-------|--------|
| Dirty tree | **WARN** — local untracked `memory/`, `runtime/`, `terminals/`, `oct_tmp.txt` + one diagnostics worklog (not for tag tree) |
| Tracked denylist | **PASS** after denylist tightening (no live memory/env paths) |
| Content scan | Script previously aborted on quoted/Unicode path entries; further hardened to skip bad paths instead of dying |
| Archive | Re-run after script fix on next commit |

## CI on `main` @ `bda33b6` (run `29221797270`)

| Job | Conclusion | Notes |
|-----|------------|-------|
| Python tests (blocking) | **FAIL** | ~58 collection `ImportError`s — missing re-exports after facade/ruff cleanup (e.g. `SEMANTIC_FAST_ALLOWED_INTENTS`, `append_codex_delegate_background_trace`, `*_REL` constants) |
| Python lint critical (blocking) | **FAIL** | 2× F401 facade imports (fix prepared locally) |
| Desktop typecheck (blocking) | **FAIL** | `tsc` OK; **eslint** `no-extra-boolean-cast` errors in renderer/main |
| Full ruff / smoke | FAIL informational | expected residual debt / collection errors |

## Validation log (local, partial)

```text
Release candidate SHA: bda33b6 (not tagged)
Date (local): 2026-07-13
Ruff critical XinYu-Core/src: pass
Ruff critical xinyu app: fail (2 F401) → fix in flight
Desktop tsc: pass locally
Desktop eslint: fail (no-extra-boolean-cast) on CI
Python tests (-m "not smoke"): not green on CI (import collection)
```

## Decision

**Do not tag `v0.1.0-rc.2` until:**

1. Critical ruff app = 0 on the tag SHA  
2. Desktop job green (`tsc` + eslint, or eslint demoted deliberately with docs)  
3. Python tests (blocking) collect/pass on CI for the tag SHA  
4. Working tree clean for the tag commit  
5. Dry-run archive completes without HIGH secret findings  

## Recommended next engineering slice

1. Restore missing public re-exports on bridge facades / store modules (import map from CI errors).  
2. Fix `Boolean(...)` eslint errors in `XinYu_Desktop`.  
3. Re-run CI on `main`; only then annotated tag + GitHub pre-release.

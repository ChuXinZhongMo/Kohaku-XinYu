# Desktop toolchain major bumps (deferred)

Status: deferred post-v0.1.0  
Date: 2026-07-13  
Related: Dependabot PRs #6–#10 (closed), `XinYu_Desktop/package.json`

## Why deferred

Lone major bumps of TypeScript 7 / ESLint 10 / electron-vite 5 failed Desktop typecheck on the release line. They must land as **one coordinated migration PR**, not separate Dependabot merges.

| Package | From (approx) | To (Dependabot) | Risk |
|---------|---------------|-----------------|------|
| `typescript` | 5.x | 7.x | TS config + type-breaking changes |
| `eslint` + `@eslint/js` | 9.x | 10.x | flat config / rule renames |
| `eslint-plugin-react-hooks` | 5.x | 7.x | paired with ESLint 10 |
| `electron-vite` | 2.x | 5.x | Vite/Electron bundler pipeline |

## Migration PR checklist (when scheduled)

1. Branch from green `main`; keep product code freezes out of the PR.
2. Bump packages together; regenerate lockfile with `npm install` in `XinYu_Desktop`.
3. `npm run typecheck` + `npm run lint` green locally.
4. Fix only toolchain-driven breaks (types, eslint config, vite config).
5. CI: **Desktop typecheck (blocking)** must pass; do not weaken the gate.
6. Optional: pin Actions SHAs in a separate supply-chain PR (OpenSSF).

## Explicit non-goals

- Do not merge individual Dependabot majors for these packages.
- Do not upgrade Electron runtime major in the same PR unless required by electron-vite.

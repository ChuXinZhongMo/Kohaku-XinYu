# Progressive lint & smoke gates

Status: active 2026-07-14  
Related: `.github/workflows/ci.yml`, `docs/plans/QUICK-SMOKE-SET.md`

## Policy

| Gate | Mode | Rule set / set |
|------|------|----------------|
| Critical lint (core + app) | **blocking** | `F,E9,F63,F7,F82` |
| Progressive style (extracted modules only) | **blocking** | same + `E7,W6` on a small allowlist of new pure modules |
| Full ruff (core / app) | informational | full project config; debt remains |
| Offline smoke | **blocking** | curated hermetic scripts only |
| Full `pytest -m smoke` | informational | live/mixed corpus |

## Why not block full ruff yet

The app tree still has large historical style debt. Blocking full ruff would freeze product work. Progressive path:

1. Keep critical import/syntax rules green on the whole app (done).
2. Apply slightly wider rules only to **new extracted modules** (prepare_policy, presence_text/io/markdown, outbox_summary).
3. Expand the allowlist as more pure modules land.
4. Never promote full-tree ruff until the allowlist covers the hot paths and residual debt is inventory'd.

## Offline smoke growth

Promote only scripts that are:

- hermetic (no NapCat / LLM / local secrets)
- exit 0 on clean CI checkout
- listed in `QUICK-SMOKE-SET.md`

2026-07-14 additions: `state_io_smoke`, `summary_coverage_smoke`.

## Coverage floor

- Unit suite (`not smoke`): **`--cov-fail-under=50`** (blocking).
- Baseline observed ~78% total lines locally with full tree.
- Stretch target 70% is reported in the job summary but not enforced yet.

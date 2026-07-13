# XinYu Engineering — 30-Day Execution Checklist

Companion to `ENGINEERING-MATURITY-PLAN.md`.  
Use this as the day-to-day board. Check items off as they land on the default branch.

Baseline date: **2026-07-13**  
Target date: **2026-08-12**  
Target score: **~60 / 100**

---

## Day 0–3 — Foundation (Phase 0)

### Docs & plan

- [x] `docs/plans/ENGINEERING-MATURITY-PLAN.md`
- [x] `docs/plans/ENGINEERING-30-DAY-CHECKLIST.md`
- [x] Link from `docs/README.md`
- [x] Link from root `ROADMAP.md` (engineering track)
- [x] Mention in root `README.md` (short pointer only)

### GitHub community surface

- [x] `.github/ISSUE_TEMPLATE/bug_report.yml`
- [x] `.github/ISSUE_TEMPLATE/gateway_failure.yml`
- [x] `.github/ISSUE_TEMPLATE/documentation.yml`
- [x] `.github/ISSUE_TEMPLATE/feature_request.yml`
- [x] `.github/ISSUE_TEMPLATE/config.yml`
- [x] `.github/pull_request_template.md`
- [x] `.github/CODEOWNERS`
- [x] `.github/dependabot.yml`

### Local engineering hygiene

- [x] `.editorconfig`
- [x] `.pre-commit-config.yaml`
- [x] Document pre-commit install in `CONTRIBUTING.md`
- [x] `make check` documented as local gate

### CI

- [x] CI job names clarify blocking vs informational
- [x] Ruff job split or scoped so core can become blocking soon
- [x] Coverage report retained (floor deferred)
- [x] No secrets required for default unit-test job

### Branch policy

- [x] Document: canonical remote default is `main`; active work may still be on `master` until cutover
- [x] Write cutover steps in plan (no force-push without backup tag)

---

## Day 4–7 — Hardening kickoff (Phase 1)

- [x] Ruff **blocking** critical rules on `XinYu-Core/src` (app remains informational)
- [x] CONTRIBUTING uses relative paths + Makefile, not only `D:\XinYu\...`
- [x] README Setup includes fresh-dev install (`pip install -e "./XinYu-Core[dev]"`)
- [ ] Label set on GitHub: `bug`, `docs`, `gateway`, `good first issue`, `engineering`, `privacy`
- [x] Inventory markdown: `docs/plans/PHASE2-ARCHITECTURE-INVENTORY.md`

---

## Day 8–14 — First debt payment

- [x] Bridge/store cluster #1 consolidated (thin stores → `xinyu_bridge_stores.py`; 21 thin done, 2 thick remain)
- [x] Shim count recorded before/after (see PHASE2 inventory / agent report)
- [x] God-file split: `xinyu_qq_gateway.py` helpers extracted; `xinyu_status.py` facade + collect/render/models
- [x] Targeted store/status suites exercised (full suite still owner-run before tag)
- [ ] Architecture note touch-up if import paths changed (optional follow-up)

---

## Day 15–21 — Contributor path

- [x] Fresh-install draft in `docs/` or root README section (`docs/system/FRESH-INSTALL.md` + root README pointer)
- [x] `*.env.example` audit (only examples tracked) — `docs/plans/ENV-EXAMPLE-AUDIT.md`
- [x] Curated quick smoke list identified for future blocking job — `docs/plans/QUICK-SMOKE-SET.md`
- [x] At least 3 `good first issue` tickets written (`docs/plans/GOOD-FIRST-ISSUES.md` backlog; file on GitHub next)
- [ ] Dependabot first batch reviewed (merge safe patches after push)

---

## Day 22–30 — Release prep

- [ ] Re-run validation baseline on intended commit
- [x] CHANGELOG engineering track section present (Unreleased)
- [x] Release dry-run procedure: `docs/plans/RELEASE-CHECKLIST.md` + `scripts/Release-DryRun.ps1`
- [ ] Decide: tag `v0.1.0` now or `v0.1.0-rc.2` then final
- [ ] main/master cutover dry-run completed or scheduled with date
- [x] Scorecard notes updated in maturity plan changelog

---

## Metrics to record at day 30

| Metric | Day 0 | Day 30 |
|--------|-------|--------|
| Overall score (self) | ~45 | |
| Bridge `*bridge*.py` count | ~1390 (noisy; refine) | |
| `xinyu_bridge_*_store.py` count | record | |
| CI blocking jobs | tests + desktop | |
| God files >2500 LOC | ≥3 | |
| Public release tagged? | no | |
| Issue templates live? | no | yes (target) |

---

## Parking lot (do not steal focus in 30 days)

- Full mypy strictness
- Full app ruff clean
- Docker full QQ stack
- Relicense
- Multi-maintainer governance formalization (start notes only)

# XinYu Engineering Maturity Plan

Status: active  
Owner: ChuXinZhongMo  
Created: 2026-07-13  
Baseline score (self-assessed vs top-tier OSS): **~45 / 100**  
Near-term target (30 days): **~60 / 100**  
Mid-term target (90 days): **~70 / 100**  
Long-term target (6–12 months): **~85 / 100**

This plan turns the gap analysis into an executable program: what to change,
in what order, how to measure progress, and what “done” means for each phase.

Related:

- Root roadmap: `ROADMAP.md`
- Open-source policy: `OPEN_SOURCE_POLICY.md`
- Privacy / security: `SECURITY.md`, `.gitignore`
- Bridge consolidation context: existing bridge-store pilot work under
  `XinYu-Core/examples/agent-apps/xinyu/`

---

## 0. Guiding Principles

1. ** Harden without freezing product velocity.** Prefer progressive gates
   (informational → warn → block) over big-bang “make everything red”.
2. **Public surface first, private runtime never.** Engineering maturity must
   strengthen the privacy boundary, not weaken it for convenience.
3. **Stranger clone path > owner machine path.** Every process that only works
   on the maintainer’s Windows box is unfinished product engineering.
4. **One logical change per PR/commit.** Large refactors land behind tests and
   small slices, not multi-week mega-diffs.
5. **Measure.** Each phase has exit criteria. “Feels better” is not an exit.

---

## 1. Scorecard (track monthly)

| Dimension | Baseline | 30d | 90d | Top-tier |
|-----------|----------|-----|-----|----------|
| Docs / community facade | 72 | 85 | 90 | 95 |
| Privacy / release boundary | 85 | 88 | 90 | 90 |
| Packaging / toolchains | 65 | 75 | 85 | 95 |
| CI/CD quality gates | 40 | 65 | 80 | 95 |
| Test maturity | 60 | 68 | 78 | 90 |
| Architecture modularity | 35 | 42 | 60 | 90 |
| Release / supply chain | 35 | 50 | 70 | 95 |
| Contributor UX | 40 | 65 | 80 | 95 |
| Governance / bus factor | 25 | 35 | 50 | 90 |
| **Overall** | **~45** | **~60** | **~70** | **100** |

---

## 2. Phase Map

```text
Phase 0  Foundation (this sprint)     → community + CI skeleton + plan
Phase 1  Hardening (weeks 1–2)        → blocking gates, branch policy, quickstart
Phase 2  Architecture (weeks 2–8)     → bridge/store convergence, god-file splits
Phase 3  Productize OSS (weeks 4–10)  → fresh install, release, demos
Phase 4  Supply chain + scale (90d+)  → SBOM, signed release, multi-maintainer
```

Phases overlap intentionally: Phase 0/1 unblock contributors while Phase 2
pays down the real modularity debt.

---

## 3. Phase 0 — Foundation (in progress now)

**Goal:** Look and behave like a project that *expects* external collaboration.

### Deliverables

| # | Item | Exit criteria |
|---|------|---------------|
| 0.1 | This plan + checklist | File exists, linked from `docs/README.md` and `ROADMAP.md` |
| 0.2 | Issue templates | Bug / gateway / docs / feature templates under `.github/ISSUE_TEMPLATE/` |
| 0.3 | PR template | `.github/pull_request_template.md` |
| 0.4 | Dependabot | Weekly pip + npm + actions updates |
| 0.5 | CODEOWNERS | Maintainer ownership for critical paths |
| 0.6 | pre-commit config | Ruff + basic hygiene hooks (local opt-in first) |
| 0.7 | `.editorconfig` | Consistent basics across editors |
| 0.8 | CI progressive structure | Named gates; clear blocking vs informational |
| 0.9 | CONTRIBUTING refresh | Makefile path, pre-commit, PR checklist |

### Non-goals (Phase 0)

- No large bridge refactors.
- No forced ruff-clean of the entire tree.
- No license change.
- No force-merge of `main`/`master` without an explicit branch decision.

---

## 4. Phase 1 — Hardening (target: 2 weeks)

**Goal:** Make the default contribution path enforceable and reproducible.

### 1.1 Branch policy

| Decision | Recommendation |
|----------|----------------|
| Canonical branch | **`main`** (already `origin/HEAD`) |
| Working branch today | `master` is ahead; treat as active integration until cutover |
| Cutover plan | After Phase 0 lands: merge/rebase `master` → `main`, protect `main`, stop pushing to `master`, delete or archive `master` after one stable release cycle |
| Protection rules (GitHub UI) | Require PR, require CI `python-tests` + `desktop-typecheck`, dismiss stale reviews |

**Exit:** One documented default branch; no dual-branch confusion in README/CI.

### 1.2 CI gates (progressive)

| Job | Phase 0 | Phase 1 | Phase 2+ |
|-----|---------|---------|----------|
| python-tests (ubuntu) | block | block | block + coverage floor |
| desktop-typecheck | block | block | block |
| ruff (core subset) | info | **block on `XinYu-Core/src`** | block + app packages |
| ruff (app) | info | info / warn | block per cleaned package |
| smoke | info | curated **quick smoke block** | expanded |
| windows-tests | — | optional / manual | scheduled or PR-labeled |
| mypy | — | info on core | gradual package strictness |

### 1.3 Contributor quickstart

- Document `pip install -e "./XinYu-Core[dev]"` + `make test` / `make check`
- Document desktop `npm install && npm run typecheck`
- Keep Windows operator path (`XinYu.ps1`) as first-class, not only path
- Add “fresh machine assumptions” section (Python 3.12, Node 20, no private deps required for unit tests)

### 1.4 Exit criteria

- [ ] Issue + PR templates live
- [ ] Dependabot PRs can open
- [ ] `make check` documented as pre-push gate
- [ ] CI blocks on tests + desktop typecheck
- [ ] Ruff blocking at least on `XinYu-Core/src` **or** documented residual debt with owner
- [ ] Branch policy written and linked

---

## 5. Phase 2 — Architecture Convergence (target: 8 weeks)

**Goal:** Raise modularity score without stopping product work.

### 5.1 Reality check (baseline debt)

- xinyu app: ~1.8k Python files / ~290k lines (including tests/tools)
- `*bridge*.py`: ~1k+ files (historical shim explosion)
- God files: `xinyu_qq_gateway.py` (~4k), `xinyu_creative_writing.py` (~4k),
  `xinyu_status.py` (~3k), several 1.5k–3k modules/tests
- Existing pilot: bridge stores consolidation → `xinyu_bridge_stores.py` pattern

### 5.2 Workstreams

#### A. Bridge / store consolidation (continue proven playbook)

1. Inventory remaining `xinyu_bridge_*_store.py` and thin shims.
2. Cluster by domain (state, proactive, desktop, codex, autonomy, …).
3. Per cluster:
   - merge pure store I/O into a domain module
   - keep thin re-export shims **only if** public import paths require them
   - delete dead shims once tests prove no callers
4. Every cluster PR: tests green + import map note in PR body.

**Metric:** bridge shim count trend down each week; no new store-per-file without review.

#### B. God-file splits (one vertical at a time)

Priority order:

1. `xinyu_qq_gateway.py` — protocol / session / send / normalize
2. `xinyu_status.py` — collect vs render vs CLI
3. `xinyu_creative_writing.py` — generation vs policy vs storage
4. Next offenders >1500 lines with high change frequency

Rules:

- No behavior change in pure split PRs.
- Keep public entrypoints stable; move helpers first.
- Add or move tests with the split, never “later”.

#### C. Package layout (target shape)

Move from flat app root toward:

```text
XinYu-Core/examples/agent-apps/xinyu/
  xinyu_app/                 # optional long-term package root
    bridge/
    gateway/
    memory/
    proactive/
    desktop/
    autonomy/
  tests/
  prompts/
  ops/
```

Do **not** big-bang rename the tree. Introduce packages incrementally;
re-export from old paths until one release cycle passes.

#### D. Test hygiene

- Keep unit tests fast and default (`-m "not smoke"`).
- Tag integration needs clearly (`smoke`, later `live`, `windows`).
- Cap new test files that are 2k+ lines; prefer focused modules.
- Track flaky tests; quarantine with issue links rather than silent skip.

### 5.3 Exit criteria

- [ ] Bridge shim count reduced ≥30% from Phase 0 baseline (document numbers)
- [ ] At least 2 god files split with green tests
- [ ] No new flat `xinyu_bridge_*_store.py` without ADR-style note
- [ ] Architecture note updated (`docs/system/` + app `ARCHITECTURE.md`)

---

## 6. Phase 3 — Productize Open Source (target: weeks 4–10)

**Goal:** A stranger can validate the public surface without your machine state.

### Deliverables

1. **Fresh-install guide** (Windows primary, Linux secondary for unit tests)
2. **Sanitized demo scenarios** (non-private, no real QQ payloads)
3. **v0.1.0 GitHub Release** with tag, notes, validation baseline re-run
4. **Issue labels** + first “good first issue” set
5. **Env contract**: only `*.example` committed; validate ignore rules with a
   release dry-run script
6. **Optional**: minimal Docker for *unit-test / core API* path (not full NapCat)

### Exit criteria

- [ ] Tagged `v0.1.0` (or next semver) with CHANGELOG section
- [ ] Fresh checkout path documented and exercised on a clean profile/VM
- [ ] Release dry-run confirms no secrets / memory / runtime private paths
- [ ] At least 5 good-first-issues filed

---

## 7. Phase 4 — Supply Chain & Scale (90 days+)

**Goal:** Approach OpenSSF Silver-ish engineering posture for a small team.

1. Dependency scanning (Dependabot + optional OSV/pip-audit job)
2. SBOM generation on release
3. Pin GitHub Actions to SHAs for critical workflows
4. Coverage floor on critical packages (start low, raise)
5. Signed or attested releases when practical
6. Second maintainer / triage rotation plan (bus factor)
7. Consider SPDX-friendly dual presentation if license remains custom
   (keep KohakuTerrarium terms; improve discoverability)

### Early Phase 4 stubs (landed)

| Item | Path | Notes |
|------|------|-------|
| Informational security CI | `.github/workflows/security.yml` | `pip-audit` + `npm audit`; `continue-on-error: true` |
| OpenSSF Passing map | `docs/plans/OPENSSF-SELF-ASSESSMENT.md` | Living stub; not a formal badge submission |
| Privacy release dry-run | `scripts/Release-DryRun.ps1` | Read-only; optional `-Archive` / `-Strict` |

### Exit criteria

- [ ] Release checklist automated or semi-automated
- [ ] Security reporting path exercised once (tabletop)
- [x] OpenSSF Best Practices self-assessment started (`docs/plans/OPENSSF-SELF-ASSESSMENT.md`)
- [ ] Documented maintainer succession notes
- [x] Non-blocking dependency audit workflow present
- [x] Release privacy dry-run script present

---

## 8. 30-Day Checklist (execution board)

### Week 1 — Foundation + policy

- [x] Engineering maturity plan written
- [ ] Issue templates
- [ ] PR template
- [ ] Dependabot
- [ ] CODEOWNERS
- [ ] pre-commit + editorconfig
- [ ] CI structure pass
- [ ] CONTRIBUTING / ROADMAP / docs index links
- [ ] Branch policy note

### Week 2 — Hardening

- [ ] Make ruff block on `XinYu-Core/src` (or split job)
- [ ] Add curated quick-smoke blocking job if stable
- [ ] Document `make check` as required local gate
- [ ] Start main/master cutover discussion and dry-run
- [ ] Inventory bridge clusters for Phase 2 sprint 1

### Week 3 — First architecture slice

- [ ] One store/bridge cluster consolidation PR
- [ ] One god-file split PR (gateway or status)
- [ ] Update architecture notes

### Week 4 — Release readiness prep

- [ ] Fresh-install draft
- [ ] Validation baseline re-run on intended tag commit
- [ ] CHANGELOG + release notes draft
- [ ] Good first issues

---

## 9. 90-Day Outcomes (definition of better)

If this plan is followed, XinYu should be able to say:

1. **Contributors** open issues/PRs with templates and pass CI without asking
   the maintainer for tribal knowledge.
2. **CI** enforces tests and core lint; informational jobs are clearly labeled.
3. **Bridge debt** is measurably shrinking, not growing.
4. **At least one public release** exists with validation evidence.
5. **Architecture docs** match the tree people actually edit.
6. **Privacy boundary** remains intact under release dry-runs.

---

## 10. Explicit Non-Goals (do not distract)

- Rewriting the whole agent in another framework
- Changing persona / TTS product direction under “engineering” work
- Full type-strict mypy on 300k+ LOC in one pass
- Multi-cloud deploy automation (product is local-first)
- Relicensing debates unless they block a concrete adoption goal

---

## 11. Operating Cadence

| Cadence | Action |
|---------|--------|
| Every PR | Tests for touched behavior; no private artifacts |
| Weekly | Update scorecard notes; merge Dependabot; one debt PR |
| Biweekly | Architecture cluster review |
| Monthly | Scorecard numbers; roadmap status flip |
| Per release | Validation matrix + privacy dry-run + CHANGELOG |

---

## 12. Immediate Next Actions (ordered)

1. Land Phase 0 files in-tree (templates, Dependabot, CODEOWNERS, pre-commit, CI, docs).
2. Decide branch cutover date; until then document dual-branch reality.
3. Open Phase 2 inventory issue: bridge clusters + god files.
4. Schedule v0.1.0 release dry-run after CI hardens.

---

## 13. Change Log For This Plan

| Date | Change |
|------|--------|
| 2026-07-13 | Initial plan from engineering maturity assessment; Phase 0 execution starts |
| 2026-07-13 | Phase 0 landed: issue/PR templates, Dependabot, CODEOWNERS, pre-commit, editorconfig, branch policy, maturity checklist |
| 2026-07-13 | CI progressive gates: blocking tests + critical ruff + desktop; full ruff/smoke informational |
| 2026-07-13 | `ruff check --fix` on `XinYu-Core/src` auto-fixed 135 issues (219 residual under full ruleset) |
| 2026-07-13 | Phase 2 inventory draft: `docs/plans/PHASE2-ARCHITECTURE-INVENTORY.md` |
| 2026-07-13 | Phase 4 stubs: informational `security.yml` (pip-audit + npm audit), OpenSSF self-assessment map, `scripts/Release-DryRun.ps1` |
| 2026-07-13 | App critical ruff cleaned 885→0; CI blocking critical lint now covers core **and** app |
| 2026-07-13 | Thin bridge stores consolidated into `xinyu_bridge_stores.py` (21 thin modules; 2 thick remain) |
| 2026-07-13 | God-file splits: `xinyu_qq_gateway.py` ~4279→3465 + helper modules; `xinyu_status.py` → models/collect/render facade |
| 2026-07-13 | Phase 3 docs: FRESH-INSTALL, RELEASE-CHECKLIST, GOOD-FIRST-ISSUES, QUICK-SMOKE-SET, ENV-EXAMPLE-AUDIT |

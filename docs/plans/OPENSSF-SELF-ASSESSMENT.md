# OpenSSF Best Practices — Self-Assessment (stub)

Status: living document (updated 2026-07-13)  
Created: 2026-07-13  
Scope: XinYu public repository (privacy-bound personal AI runtime)  
Target badge level: **Passing** first; Silver later if team capacity allows  
Related: `docs/plans/ENGINEERING-MATURITY-PLAN.md` Phase 4, `SECURITY.md`, `docs/system/BRANCH-PROTECTION.md`

This is an internal mapping against the [OpenSSF Best Practices](https://www.bestpractices.dev/)
**Passing** criteria. It is **not** a formal badge submission. Revisit quarterly.

Legend: **met** | **partial** | **missing** | **n/a**

---

## Summary

| Area | Status | Notes |
|------|--------|-------|
| Basics (license, docs, VCS) | **met** / partial | Docs + LICENSE strong; default branch is `main` (master archived) |
| Change control | **met** / partial | CI + PR templates + protected `main`; still solo maintainer |
| Reporting | partial | `SECURITY.md` exists; path not tabletop-exercised |
| Quality | **met** / partial | Blocking tests + critical lint + offline smoke; no coverage floor |
| Security | partial | Dependabot + informational audits; no SBOM/signed release |
| Analysis | partial | Ruff/CI; dependency scan non-blocking |

Estimated distance to formal **Passing**: medium-low after v0.1.0 + protection + offline smoke (remaining: coverage floor, SBOM, multi-maintainer).

---

## Passing criteria map (selected)

### Basics

| Criterion | Status | Evidence / gap |
|-----------|--------|----------------|
| Project has a LICENSE | **met** | Root `LICENSE` (KohakuTerrarium 1.0, Apache-derived custom) |
| LICENSE discoverable | **met** | Root + `XinYu-Core/LICENSE` |
| Documentation basics | **met** | Root README, `docs/README.md`, CONTRIBUTING, ROADMAP |
| Project site / repo public | **partial** | Public source intent; some URLs still local placeholders in package metadata |
| Discussion / contribution path | **met** | `CONTRIBUTING.md`, issue templates, PR template |
| Code of conduct | **met** | `CODE_OF_CONDUCT.md` |

### Change control

| Criterion | Status | Evidence / gap |
|-----------|--------|----------------|
| Version control (git) | **met** | GitHub-hosted git |
| Public VCS | **met** | Public collaboration surface |
| Unique versioning | **met** | `CHANGELOG.md` + tags `v0.1.0` / `v0.1.0-rc.2` on GitHub |
| Changelog / release notes | **met** | `CHANGELOG.md` section for v0.1.0 released 2026-07-13 |
| Working bug reporting | **met** | Issue templates (bug / gateway / docs / feature) |
| Working enhancement reporting | **met** | Feature request template |

### Reporting (security)

| Criterion | Status | Evidence / gap |
|-----------|--------|----------------|
| Process for reporting vulnerabilities | **met** | `SECURITY.md` (private advisory / owner contact) |
| Vulnerability response process documented | **partial** | Reporting path yes; SLA / response roles thin (single maintainer) |
| Private disclosure preference clear | **met** | Explicit ban on secrets/private payloads in public issues |

### Quality

| Criterion | Status | Evidence / gap |
|-----------|--------|----------------|
| Automated build / test in CI | **met** | Blocking: python tests, critical lint, desktop typecheck, **offline smoke** |
| Test suite exists | **met** | pytest under xinyu app; curated offline smoke blocking; full smoke informational |
| New code generally tested | **partial** | Policy in CONTRIBUTING/PR template; uneven historical coverage |
| Warning-free compile / critical lint | **met** | Critical ruff blocking on core **and** app (`F,E9,...`); full ruff informational |
| Static analysis | **partial** | Ruff; no mypy gate yet |
| Coverage floor | **missing** | Coverage XML uploaded; no enforced minimum |
| Flaky test policy | **partial** | Maturity plan mentions quarantine; not fully operationalized |

### Security / supply chain

| Criterion | Status | Evidence / gap |
|-----------|--------|----------------|
| Secure development knowledge | **partial** | Privacy boundary + SECURITY policy; formal secure-coding checklist light |
| Cryptographic practices | **partial** | Local-first product; no formal crypto review checklist |
| Dependency update automation | **met** | Dependabot (pip / npm / actions) weekly |
| Dependency vulnerability scan | **partial** | Informational `security.yml` (`pip-audit`, `npm audit`); not blocking |
| SBOM on release | **missing** | Planned Phase 4 |
| Signed / attested releases | **missing** | No signed tags/artifacts yet |
| Pinned GitHub Actions SHAs | **missing** | Floating majors (`@v6`/`@v7` after Dependabot batch); pin-SHA is a follow-up |
| Secrets out of VCS | **met** / **partial** | Strong `.gitignore` + privacy dry-run; continuous vigilance required |
| Release dry-run / privacy check | **met** / partial | `scripts/Release-DryRun.ps1` used for v0.1.0; not yet CI-automated |

## Next OpenSSF actions (ordered)

1. Optional coverage floor (e.g. fail under 40% on app unit suite) behind a flag first.
2. Pin GitHub Actions to full commit SHAs in `ci.yml` / `security.yml`.
3. Generate SBOM on tag (CycloneDX or SPDX) and attach to GitHub Release.
4. Tabletop: run one private vulnerability report drill; document SLA in `SECURITY.md`.
5. Formal badge submission only after (2)+(3) and maintainer bandwidth.

### Analysis & governance

| Criterion | Status | Evidence / gap |
|-----------|--------|----------------|
| Continuous integration | **met** | CI on push/PR; concurrency cancel |
| Security CI job | **partial** | Non-blocking security workflow |
| Bus factor / multi-maintainer | **missing** | CODEOWNERS single owner (`@ChuXinZhongMo`) |
| Maintainer succession notes | **missing** | Phase 4 exit item |
| OpenSSF badge published | **missing** | Self-assessment only |

---

## Explicit non-goals for Passing (product constraints)

- Full multi-cloud deploy pipelines (local-first product).
- Publishing private runtime memory or QQ payloads for “realism”.
- Relicensing away from KohakuTerrarium solely for SPDX convenience (may add clearer SPDX presentation later).

---

## Near-term actions toward Passing

1. Keep `security.yml` informational until triage baseline exists; then promote selected severity to warn/block.
2. Run `scripts/Release-DryRun.ps1` before every public tag; attach summary to release notes.
3. Land first public GitHub Release with CHANGELOG section and validation evidence.
4. Document vulnerability response target times (even if single-maintainer “best effort”).
5. Add SBOM generation + consider action SHA pins for release-critical workflows.
6. Second maintainer / triage rotation plan when collaboration volume justifies it.

---

## Change log

| Date | Change |
|------|--------|
| 2026-07-13 | Initial stub from Phase 4 supply-chain hardening |

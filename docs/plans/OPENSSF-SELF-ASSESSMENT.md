# OpenSSF Best Practices — Self-Assessment (stub)

Status: draft / living document  
Created: 2026-07-13  
Scope: XinYu public repository (privacy-bound personal AI runtime)  
Target badge level: **Passing** first; Silver later if team capacity allows  
Related: `docs/plans/ENGINEERING-MATURITY-PLAN.md` Phase 4, `SECURITY.md`

This is an internal mapping against the [OpenSSF Best Practices](https://www.bestpractices.dev/)
**Passing** criteria. It is **not** a formal badge submission. Revisit quarterly.

Legend: **met** | **partial** | **missing** | **n/a**

---

## Summary

| Area | Status | Notes |
|------|--------|-------|
| Basics (license, docs, VCS) | partial | Strong privacy/docs facade; custom license; dual branch residual |
| Change control | partial | CI + PR templates; single maintainer; limited review depth |
| Reporting | partial | `SECURITY.md` exists; path not tabletop-exercised |
| Quality | partial | Blocking tests + critical lint; no coverage floor yet |
| Security | partial | Dependabot + informational audits; no SBOM/signed release |
| Analysis | partial | Ruff/CI; dependency scan non-blocking |

Estimated distance to formal **Passing**: medium (process + release hygiene more than missing docs).

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
| Unique versioning | **partial** | `CHANGELOG.md` + package versions; public GitHub Release cadence still forming |
| Changelog / release notes | **partial** | `CHANGELOG.md` present; first tagged public release still RC-oriented |
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
| Automated build / test in CI | **met** | `.github/workflows/ci.yml` — blocking python tests + desktop typecheck |
| Test suite exists | **met** | pytest under xinyu app; smoke informational |
| New code generally tested | **partial** | Policy in CONTRIBUTING/PR template; uneven historical coverage |
| Warning-free compile / critical lint | **partial** | Critical ruff blocking on `XinYu-Core/src`; app lint still informational |
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
| Pinned GitHub Actions SHAs | **missing** | Currently floating major tags (`@v4` / `@v5`) |
| Secrets out of VCS | **met** / **partial** | Strong `.gitignore` + privacy dry-run script; continuous vigilance required |
| Release dry-run / privacy check | **partial** | `scripts/Release-DryRun.ps1` added; not yet release-gate automated |

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

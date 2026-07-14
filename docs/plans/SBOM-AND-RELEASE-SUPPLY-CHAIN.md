# SBOM & release supply-chain notes

Status: active plan (2026-07-13)  
Related: `OPENSSF-SELF-ASSESSMENT.md`, `RELEASE-CHECKLIST.md`, `scripts/Release-DryRun.ps1`

## Current state

| Control | Status |
|---------|--------|
| Privacy dry-run before tag | **met** (operator script) |
| Dependabot (pip/npm/actions) | **met** |
| Informational pip-audit / npm audit | **met** (`security.yml`) |
| Actions pinned to full SHAs | **met** as of this engineering pass |
| Coverage soft summary | **met** (informational floor in CI summary) |
| SBOM attached to GitHub Release | **missing** (manual recipe below) |
| Signed tags / attestations | **missing** |

## Generate an SBOM for a release tag (operator)

From a clean checkout of the tag:

```bash
# Python (CycloneDX)
python -m pip install cyclonedx-bom
cd XinYu-Core
cyclonedx-py environment -o ../sbom-xinyu-core.cdx.json

# Optional desktop
cd ../XinYu_Desktop
npx --yes @cyclonedx/cyclonedx-npm --output-file ../sbom-xinyu-desktop.cdx.json
```

Attach both JSON files to the GitHub Release for that tag. Do **not** include private runtime trees.

## Coverage floor policy

- CI prints total line coverage from `coverage.xml` with a **35% informational floor**.
- Do not fail PRs on the floor until the baseline is stable for two release cycles.
- Next step: set `fail_under` only on a narrow package allowlist (not the whole app tree).

## CI automation

- Workflow: `.github/workflows/sbom-release.yml` (tags `v*` + `workflow_dispatch`).
- Produces `sbom-xinyu-core.cdx.json` from the installed XinYu-Core env.
- Uploads workflow artifact **and** attaches the file to the GitHub Release on tag pushes
  (`softprops/action-gh-release`, continue-on-error so tagging is never bricked).

## Next supply-chain steps

1. Auto-attach SBOM artifact to GitHub Releases on tag.
2. Pin remaining third-party Actions if any float tags reappear.
3. Document cosign/sigstore only if multi-maintainer releases start.

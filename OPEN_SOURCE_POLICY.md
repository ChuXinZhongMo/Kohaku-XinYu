# Open Source Policy

This repository is prepared for source-code publication, not for publishing
private runtime state.

## License

XinYu follows the KohakuTerrarium License Version 1.0 used by the embedded
KohakuTerrarium/XinYuTerrariumRuntime source tree. See `LICENSE` and `NOTICE`.

The license is based on Apache License 2.0 with additional naming and
attribution requirements. Downstream forks, services, packages, and products
must keep the required KohakuTerrarium attribution.

## Publication Scope

Included:

- source code
- tests and smoke runners
- public documentation
- sanitized audit/worklog reports
- examples and templates that do not contain real credentials

Excluded:

- `.env`, tokens, keys, local credentials
- runtime state, logs, memory stores, private QQ payloads
- owner-supplied material bodies
- self-found external source snapshots with unclear redistribution terms
- generated desktop build output and dependency folders

## Third-Party Material

Third-party package dependencies are not vendored unless explicitly noted.
Install them from their package managers and follow their own licenses.

Unknown-license copied source snapshots are not part of the distributable open
source surface. If a future batch wants to publish such material, first verify
its upstream license and add an attribution entry.

## Contributor Rule

Before accepting a contribution:

- no secrets or private runtime artifacts
- no raw owner-supplied bodies
- no copied third-party source without license evidence
- tests or smoke coverage for runtime behavior changes
- update `THIRD-PARTY-NOTICES.md` when adding a dependency or vendored asset

# XinYu

XinYu is a local long-running personal AI runtime workspace. It combines a
Python core runtime, QQ/NapCat gateway integration, a desktop shell, memory and
learning boundaries, and validation tooling.

This repository is prepared for source-code publication. It is not intended to
publish private runtime state, owner-supplied materials, QQ payloads, local
memory, or credentials.

## Repository Layout

- `XinYu-Core/` - core Python runtime and the active `xinyu` agent app.
- `XinYu_Desktop/` - Electron/Vite desktop shell.
- `XinYu-TinyKernel/` - local tiny-kernel experiments and training scaffolding.
- `XinYu-Autonomy/` - owner-visible autonomy notes; private contents are
  ignored except the README.
- `XinYu-Local-Scope/` - local request/material staging; private contents are
  ignored except the README.
- `worklog/` - sanitized engineering worklogs and recovery points.

## Privacy Boundary

The following are intentionally excluded from publication:

- `.env`, token, key, and local credential files
- runtime logs and process state
- live memory stores
- private QQ payloads
- owner-supplied material bodies
- self-found external source snapshots with unclear redistribution terms
- generated build output and dependency directories

See `.gitignore`, `OPEN_SOURCE_POLICY.md`, and `SECURITY.md`.

## License

XinYu follows the KohakuTerrarium License Version 1.0 used by the embedded
KohakuTerrarium/XinYuTerrariumRuntime source tree.

See:

- `LICENSE`
- `NOTICE`
- `THIRD-PARTY-NOTICES.md`

## Setup

Python runtime:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe smoke_run.py --group quick --timeout-seconds 180 --json
```

Desktop shell:

```powershell
cd D:\XinYu\XinYu_Desktop
npm install
npm run typecheck
npm run build
```

## Daily Entry Points

Root launch scripts are provided for local Windows use:

- `Start-XinYu-Desktop.ps1`
- `Stop-XinYu-Desktop.ps1`
- `Start-XinYu-TinyKernel.ps1`
- `Stop-XinYu-TinyKernel.ps1`

These scripts assume the local machine has the required runtime configuration.
Do not commit local credentials or machine-specific secrets.

## Current Validation Baseline

Latest checked local baseline, 2026-05-21:

- Python tests: `772 passed`
- runtime readiness smoke: `ok`
- QQ gateway smoke: `ok`
- desktop typecheck: passed
- desktop build: not rerun in this closeout pass

Detailed audit and recovery notes live in `worklog/` and
`XinYu-Core/examples/agent-apps/xinyu/ops/reports/`.

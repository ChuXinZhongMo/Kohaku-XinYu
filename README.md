# XinYu

XinYu is a local long-running personal AI runtime workspace. It combines a
Python core runtime, QQ/NapCat gateway integration, a desktop shell, memory and
learning boundaries, and validation tooling.

This repository is prepared for source-code publication. It is not intended to
publish private runtime state, owner-supplied materials, QQ payloads, local
memory, or credentials.

## Why This Project Matters

XinYu is a reusable reference implementation for local, privacy-bound,
long-running personal AI agents. It is not a hosted chatbot wrapper: the
project focuses on the operating surfaces needed to keep an agent running,
observable, reviewable, and bounded on a local machine.

Core technical themes:

- durable memory, event, and review boundaries that keep private state out of
  the public source tree
- controlled proactive behavior with explicit lifecycle, claim, delivery, and
  acknowledgement paths
- native QQ/NapCat gateway integration for real local messaging loops
- desktop and command-line operator workflows for local inspection and control
- smoke tests, pytest coverage, audits, and runbooks for long-run maintenance
- tiny-kernel experiments for local behavior, persona, and routing research

The intended open-source value is a practical, inspectable foundation for
Chinese-language personal companion agents and other privacy-aware local agent
runtimes.

## Open Source And Maintainer Status

- Primary maintainer: `ChuXinZhongMo`.
- Current stage: early public source baseline with working local runtime,
  desktop shell, QQ gateway path, tests, and operations documentation.
- Contribution path: issues and pull requests are welcome for public source,
  tests, docs, operator tooling, gateway reliability, and privacy-boundary
  hardening.
- Roadmap: see `ROADMAP.md` and `XinYu-Core/ROADMAP.md`.
- Release notes: see `CHANGELOG.md` for the `v0.1.0` public-source release
  candidate.

## Goal Anchor

Required first reading for project direction:

- `docs/system/心玉最终目标.md` - Chinese final goal anchor for XinYu's
  bounded, verifiable self-generating autonomy loop.

## Repository Layout

- `XinYu.ps1` - unified local operator entry point for status, start/stop,
  tests, smoke checks, cleanup, and the system tree.
- `XinYu-Core/` - core Python runtime and the active `xinyu` agent app.
- `XinYu_Desktop/` - Electron/Vite desktop shell.
- `XinYu-TinyKernel/` - local tiny-kernel experiments and training scaffolding.
- `XinYu-Autonomy/` - owner-visible autonomy notes; private contents are
  ignored except the README.
- `XinYu-Local-Scope/` - local request/material staging; private contents are
  ignored except the README.
- `docs/` - system notes, work plans, audits, reports, and operations docs.
- `scripts/` - startup, shutdown, and local operator helper scripts.
- `assets/` - cases, reference library, icons, OCR fixtures, and material library.
- `artifacts/` - local archives, protection snapshots, and generated package artifacts.
- `runtime/deps/` - local machine dependencies such as Python, OCR, vision,
  and NapCat runtimes. This directory is ignored.
- `worklog/` - sanitized engineering worklogs and recovery points.

See `docs/system/XINYU-SYSTEM.md` for the current system spine and component
boundaries.

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

This is a custom Apache-2.0-derived license with additional naming and
attribution requirements. Treat `LICENSE` as the canonical license text; do not
assume the project is MIT-licensed or plain Apache-2.0.

See:

- `LICENSE`
- `NOTICE`
- `THIRD-PARTY-NOTICES.md`

## Setup

### Fresh developer install (tests / contribution)

```bash
python -m pip install -U pip
pip install -e "./XinYu-Core[dev]"

# from repo root (Git Bash / WSL / Linux / macOS)
make test
make check

# optional local hooks
pip install pre-commit && pre-commit install
```

Desktop shell:

```bash
cd XinYu_Desktop
npm install
npm run typecheck
npm run build
```

### Windows operator path (local runtime already provisioned)

```powershell
cd XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe smoke_run.py --group quick --timeout-seconds 180 --json
```

Engineering maturity plan (how we close the gap to top-tier OSS practice):

- `docs/plans/ENGINEERING-MATURITY-PLAN.md`
- `docs/plans/ENGINEERING-30-DAY-CHECKLIST.md`
- `docs/system/BRANCH-POLICY.md`

## Daily Entry Points

Use the unified local operator entry point:

```powershell
.\XinYu.ps1 tree
.\XinYu.ps1 status
.\XinYu.ps1 start desktop
.\XinYu.ps1 stop all
.\XinYu.ps1 test core
.\XinYu.ps1 verify qq
.\XinYu.ps1 clean
```

For a one-click QQ live-loop verification on Windows, run or double-click:

```powershell
.\Verify-XinYu-QQ.cmd
```

Compatibility launch scripts are still provided for local Windows use:

- `scripts/Start-XinYu-Desktop.ps1`
- `scripts/Stop-XinYu-Desktop.ps1`
- `scripts/Start-XinYu-TinyKernel.ps1`
- `scripts/Stop-XinYu-TinyKernel.ps1`

These scripts assume the local machine has the required runtime configuration.
Do not commit local credentials or machine-specific secrets.

## Current Validation Baseline

Latest checked local baseline, 2026-05-21:

- Python tests: `786 passed`
- runtime readiness smoke: `ok`
- QQ gateway smoke: `ok`
- desktop typecheck: passed
- desktop build: passed

Detailed audit and recovery notes live in `worklog/` and
`XinYu-Core/examples/agent-apps/xinyu/ops/reports/`.

This baseline is the public release-readiness signal for the current source
tree. New runtime behavior should keep the relevant tests, smoke checks, and
privacy-boundary checks green before publication.

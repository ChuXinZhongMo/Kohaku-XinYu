# Contributing

Use small, reviewable commits and keep private runtime state out of the repo.

The primary maintainer is `ChuXinZhongMo`. Public contributions are welcome for
source code, tests, smoke coverage, documentation, operator tooling, gateway
reliability, engineering hygiene, and privacy-boundary hardening.

## Good First Areas

- clarify setup and troubleshooting docs
- add or tighten tests around public runtime behavior
- improve QQ/NapCat gateway diagnostics with sanitized fixtures
- improve `XinYu.ps1` operator ergonomics
- strengthen release, security, and privacy-boundary checks
- engineering maturity items in `docs/plans/ENGINEERING-MATURITY-PLAN.md`

## Engineering Plan

We are actively raising repo maturity toward top-tier open-source practice:

- Plan: `docs/plans/ENGINEERING-MATURITY-PLAN.md`
- 30-day board: `docs/plans/ENGINEERING-30-DAY-CHECKLIST.md`
- Branch policy: `docs/system/BRANCH-POLICY.md`

## Development Setup

### Python (core + xinyu app tests)

```bash
python -m pip install -U pip
pip install -e "./XinYu-Core[dev]"

# optional local hooks
pip install pre-commit
pre-commit install
```

From repo root:

```bash
make test          # app tests, smoke excluded
make lint          # ruff on core + app
make check         # tests + lint (pre-push gate)
make test-cov      # coverage report
```

Or without Make:

```bash
cd XinYu-Core/examples/agent-apps/xinyu
python -m pytest -q -m "not smoke"
```

On Windows with the project venv already provisioned:

```powershell
cd XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe smoke_run.py --group quick --timeout-seconds 180 --json
```

### Desktop shell

```bash
cd XinYu_Desktop
npm install
npm run typecheck
npm run build
```

### Operator entry (local machine)

```powershell
.\XinYu.ps1 tree
.\XinYu.ps1 status
.\XinYu.ps1 test core
```

## Commit Style

Use conventional, scoped subjects:

- `feat: ...`
- `fix: ...`
- `refactor: ...`
- `test: ...`
- `docs: ...`
- `chore: ...`

Prefer commits that each answer one question:

- what behavior changed
- what boundary was tightened
- what files moved or were archived
- what validation proves it

## Before A Pull Request

1. Run the relevant checks (`make check` when possible).
2. Fill the PR template (validation + privacy checkboxes).
3. Keep the diff reviewable; large refactors should be behavior-preserving and
   tested.

Do not include:

- secrets or `.env` files
- private memory/runtime/log files
- owner-supplied material bodies
- unknown-license third-party source snapshots

For behavior changes, include the smallest relevant pytest, smoke check, or
manual verification note so the maintainer can review the change without
reconstructing local private state.

## CI Expectations

Blocking checks (must pass):

- Python tests (`not smoke`)
- Python **critical** lint on `XinYu-Core/src` **and** the xinyu app
  (`ruff` select `F,E9,F63,F7,F82`; app excludes learning/runtime/venv/archive)
- Desktop typecheck

Informational (may fail while debt is paid down):

- Full expanded ruff on `XinYu-Core/src`
- Full expanded ruff on the xinyu app tree
- Full smoke marker suite (often needs a live local env; see
  `docs/plans/QUICK-SMOKE-SET.md`)

Local equivalent of the CI pre-push gate:

```bash
make check   # tests + lint-critical
```

See `.github/workflows/ci.yml` and the engineering maturity plan for the
progressive gate schedule.

## Privacy And Security

- Public issues must be sanitized. Use `SECURITY.md` for sensitive reports.
- Gateway bugs: use the **Gateway failure** issue template; never paste raw QQ
  payloads.
- Policy: `OPEN_SOURCE_POLICY.md`.

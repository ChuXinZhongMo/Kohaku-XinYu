# Fresh Install Guide

Status: active as of 2026-07-13  
Audience: contributors and maintainers cloning a clean public tree  
Related: `CONTRIBUTING.md`, `SECURITY.md`, `OPEN_SOURCE_POLICY.md`, `docs/system/BRANCH-POLICY.md`

This guide is the **stranger clone path**: validate the public surface without the
maintainer’s private Windows runtime. Full QQ/NapCat live loops, TTS adapters,
and local memory stores are **out of scope** for a fresh contribution install.

---

## 1. Assumptions

| Tool | Version | Notes |
|------|---------|--------|
| Python | **3.12** | Matches CI (`actions/setup-python` 3.12) |
| Node.js | **20** | Matches CI desktop job |
| npm | comes with Node 20 | Prefer `npm ci` when `package-lock.json` is present |
| Git | any recent | |
| Make | optional | Linux / macOS / Git Bash / WSL; Windows can copy `Makefile` targets |

**Not required for unit tests / typecheck:**

- `runtime/deps/` (local Python/OCR/NapCat bundles)
- app `.venv` under `XinYu-Core/examples/agent-apps/xinyu/`
- real `.env` / `xinyu.local.env`
- live QQ / NapCat / LLM credentials
- owner memory, logs, or learning bodies

Those belong to the **operator path** (Section 5), not the contributor path.

---

## 2. Clone and branch

```bash
git clone <your-fork-or-upstream-url> XinYu
cd XinYu
git checkout main   # preferred after cutover; see BRANCH-POLICY.md
```

During the dual-branch window, `master` may hold newer integration work. Open PRs
against **`main`** when cutover is complete; see `docs/system/BRANCH-POLICY.md`.

---

## 3. Python: core + app tests

From the repository root:

```bash
python -m pip install -U pip
pip install -e "./XinYu-Core[dev]"
```

Optional local hooks:

```bash
pip install pre-commit
pre-commit install
```

### Run the default gates

With Make (Git Bash / WSL / Linux / macOS):

```bash
make test          # pytest -m "not smoke" in the xinyu app
make lint          # critical ruff on XinYu-Core/src
make check         # tests + critical lint (pre-push gate)
make test-cov      # coverage report (optional locally)
```

Without Make:

```bash
cd XinYu-Core/examples/agent-apps/xinyu
python -m pytest -q -m "not smoke"

# from repo root:
ruff check XinYu-Core/src --select F,E9,F63,F7,F82
```

### What “green” means today

CI blocking jobs (must pass on PRs):

| Job | What it runs |
|-----|----------------|
| `Python tests (blocking)` | `pytest -q -m "not smoke"` under the xinyu app (+ coverage artifact) |
| `Python lint critical (blocking)` | `ruff check XinYu-Core/src --select F,E9,F63,F7,F82` |
| `Desktop typecheck (blocking)` | `npm run typecheck` (+ lint if present) |

Informational (may fail while debt is paid down):

- Full ruff on `XinYu-Core/src`
- Critical + full ruff on the xinyu app tree
- Full `pytest -m smoke` suite (often needs a live local env)

Do **not** claim smoke or full-app ruff are currently blocking gates.

Env template only (never commit filled values):

- `XinYu-Core/examples/agent-apps/xinyu/xinyu.local.env.example`  
  Copy to `xinyu.local.env` for operator runs; that real file is gitignored.

---

## 4. Desktop shell (Node 20)

```bash
cd XinYu_Desktop
if [ -f package-lock.json ]; then npm ci; else npm install; fi
npm run typecheck
npm run lint --if-present
npm run build    # optional locally; CI currently blocks on typecheck/lint
```

Windows PowerShell:

```powershell
cd XinYu_Desktop
if (Test-Path package-lock.json) { npm ci } else { npm install }
npm run typecheck
npm run lint --if-present
npm run build
```

---

## 5. Windows operator path (`XinYu.ps1`)

The unified operator entry point is **Windows-oriented** and expects a
**provisioned local machine**, not a bare clone.

```powershell
.\XinYu.ps1 tree      # layout + component presence
.\XinYu.ps1 status    # needs resolvable Python + app scripts
.\XinYu.ps1 test core
.\XinYu.ps1 smoke     # quick smoke group; may need local runtime
.\XinYu.ps1 verify qq # live-loop oriented; needs gateway stack
.\XinYu.ps1 start desktop
.\XinYu.ps1 stop all
.\XinYu.ps1 clean
```

### What requires local runtime / deps

| Capability | Typical local needs |
|------------|---------------------|
| `tree` | mostly filesystem layout only |
| `test core` | Python (app `.venv`, `runtime\deps\Python312`, or system `python`) + `pip install -e "./XinYu-Core[dev]"` |
| `status` / bridge scripts | app tree + often local env / process state |
| `start desktop` / QQ / TinyKernel | scripts under `scripts/`, Node deps, and frequently `runtime/deps/` (NapCat, bundled Python, adapters) |
| `verify qq` / live smoke | NapCat/QQ gateway config, credentials, and running services |
| TTS / OCR / vision | adapters and models under ignored `runtime/deps/` paths |

Python resolution order in `XinYu.ps1` (simplified):

1. `XinYu-Core/examples/agent-apps/xinyu/.venv/Scripts/python.exe`
2. `runtime/deps/Python312/python.exe`
3. `Python312/python.exe` (legacy root layout)
4. system `python` on `PATH`

Contributor unit tests do **not** require items 2–3. Full operator start/stop
does.

If you only want tests on Windows without Make:

```powershell
cd XinYu-Core\examples\agent-apps\xinyu
# after: pip install -e ".\..\..\..\XinYu-Core[dev]" from repo root
python -m pytest tests -q -m "not smoke"
```

With a provisioned app venv:

```powershell
cd XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe smoke_run.py --group quick --timeout-seconds 180 --json
```

---

## 6. Privacy boundary (never commit)

Public source only. Before every commit and PR:

**Never commit:**

- `.env`, `*.local.env`, tokens, keys, PEM material
- live memory stores (`.../xinyu/memory/`, core memory trees)
- runtime process state and logs (`.../xinyu/runtime/`, `logs/`)
- private QQ payloads and gateway config with real identities
- owner-supplied learning bodies (`learning/owner_supplied/`, etc.)
- unclear-license external source snapshots
- generated `node_modules/`, `dist/`, `out/`, venvs
- machine bundles under `runtime/deps/`

**Safe to commit:**

- source, tests, smoke **runners**, public docs
- `*.env.example` / `xinyu.local.env.example` only
- sanitized fixtures and redacted reports

Authoritative policy:

- `OPEN_SOURCE_POLICY.md` — publication scope
- `SECURITY.md` — how to report sensitive issues (not public issue bodies)
- `.gitignore` — ignore rules for private/local paths
- `CONTRIBUTING.md` — PR hygiene

If a bug needs gateway or memory context, sanitize first. Use the **Gateway
failure** issue template; never paste raw QQ payloads.

---

## 7. Suggested first hour for a new contributor

1. Install Python 3.12 + Node 20.
2. `pip install -e "./XinYu-Core[dev]"` and `make check` (or equivalent).
3. Desktop: `npm ci` / `npm install` + `npm run typecheck`.
4. Skim `docs/system/XINYU-SYSTEM.md` and `docs/plans/ENGINEERING-MATURITY-PLAN.md`.
5. Pick a ticket from `docs/plans/GOOD-FIRST-ISSUES.md` or a labeled GitHub issue.
6. Open a small PR against the current contribution branch policy.

---

## 8. Related docs

| Doc | Why |
|-----|-----|
| `CONTRIBUTING.md` | setup, commit style, CI expectations |
| `SECURITY.md` | private reporting surface |
| `OPEN_SOURCE_POLICY.md` | what may ship publicly |
| `docs/system/BRANCH-POLICY.md` | `main` / `master` cutover |
| `docs/plans/RELEASE-CHECKLIST.md` | pre-tag validation |
| `docs/plans/GOOD-FIRST-ISSUES.md` | concrete starter tasks |
| `docs/plans/ENGINEERING-30-DAY-CHECKLIST.md` | execution board |
| `scripts/Release-DryRun.ps1` | read-only privacy / release dry-run helper |
| `Makefile` | local gate aliases matching CI intent |
| `.github/workflows/ci.yml` | exact job names and commands |

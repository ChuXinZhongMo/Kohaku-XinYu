# Env example audit

Date: 2026-07-13  
Scope: repository-wide `*.env.example` / `*.local.env.example` and related secret gitignore rules  
Constraint: this document does **not** print secret values.

## Summary

| Finding | Detail |
|---|---|
| Tracked env **examples** (app surface) | **One**: `XinYu-Core/examples/agent-apps/xinyu/xinyu.local.env.example` |
| Tracked real secret env files | **None** found via `git ls-files` for `*.env` / `xinyu.local.env` |
| Real local env file (untracked / ignored) | `XinYu-Core/examples/agent-apps/xinyu/xinyu.local.env` (present on developer machines; gitignored) |
| Risk of tracked secrets in examples | **Low** — example uses placeholders (`your-api-key`, empty keys, example.com URLs). No `sk-…` live tokens detected in the example file |
| Nested third-party examples | May exist under ignored trees (`runtime/deps/`, Local-Scope study copies); not part of the published app surface |

## Tracked examples

### Primary (owner app)

| File | Tracked? | Purpose |
|---|---|---|
| `XinYu-Core/examples/agent-apps/xinyu/xinyu.local.env.example` | Yes | Canonical template: copy to `xinyu.local.env` and fill secrets. Documents LLM, v1 shadow, serviceization backends, OCR, STT/TTS, Genie TTS, owner QQ, search, etc. |

Header of the example explicitly says: copy to `xinyu.local.env` and do not commit the real file.

### Other env-ish tracked files (not `*.env.example`)

These are **not** dotenv templates but appear in env-related searches:

| File | Role |
|---|---|
| `XinYu-Core/examples/agent-apps/xinyu/bootstrap_minimal_env.ps1` | Bootstrap helper (script, not a secret store) |
| `XinYu-Core/examples/agent-apps/xinyu/ops/diagnostics/check_runtime_env.py` | Diagnostics |
| Bridge/env store modules & tests | Code that **reads** local env; not credential files |

### Excluded / ignored trees (do not treat as product templates)

| Location | Notes |
|---|---|
| `runtime/deps/**` (e.g. CosyVoice third_party `.env.example`) | Vendored/deps; root `.gitignore` ignores `runtime/deps/` |
| `XinYu-Local-Scope/**` study checkouts (`.env`, `.env.dist`, `.env_template`) | Entire tree ignored except README |
| `**/node_modules/**`, `**/.venv/**`, `runtime/voice-training/**` venvs | Dependency noise; out of audit scope |

## Real env files and gitignore coverage

### Explicit ignore rules (good)

Root `.gitignore`:

- `.xinyu_bridge_token`
- `*.env`
- `*.local.env`
- `*.key` / `*.pem`
- `XinYu-Core/examples/agent-apps/xinyu/xinyu.local.env`
- `XinYu-Core/examples/agent-apps/xinyu/xinyu_qq_gateway.config.json`
- Runtime/memory/logs/data trees under the xinyu app

`XinYu-Core/.gitignore`:

- `.env`, `.env.local`, `.env.*.local`
- `examples/agent-apps/xinyu/xinyu.local.env`
- `examples/agent-apps/xinyu/xinyu_qq_gateway.config.json`
- `examples/agent-apps/xinyu/config/external_plugins.json`
- memory/runtime/logs under the app

Verified: `git check-ignore` reports `xinyu.local.env` ignored; the `.example` file is **not** ignored (correct).

### Files that must stay untracked

| File / pattern | Reason |
|---|---|
| `xinyu.local.env` | API keys, bridge-related secrets, owner IDs |
| `.xinyu_bridge_token` | Bridge auth token |
| `xinyu_qq_gateway.config.json` | Gateway tokens / QQ IDs |
| `config/external_plugins.json` (when present with secrets) | Plugin endpoints/credentials |
| Any `*.env` / `*.local.env` outside examples | Catch-all |

## Secret risk assessment

| Risk | Assessment |
|---|---|
| Example file commits live API keys | **Not observed** — placeholders only (`your-api-key`, blank `OPENAI_API_KEY`, empty TTS keys) |
| Example documents real private endpoints | Uses example.com / `127.0.0.1` local defaults; provider/model **names** are configuration hints, not credentials |
| Real `xinyu.local.env` accidentally tracked | **Mitigated** by layered gitignore; re-check with `git ls-files '*env*'` before releases |
| Tokens in CI logs from smokes | Offline smokes use fake keys (`test-key`, `smoke-token`); live readiness smokes must remain non-blocking and must not echo tokens (existing readiness smoke has redaction patterns) |
| History leak | This audit is snapshot-only; if a secret was ever committed historically, rotate keys (out of scope here) |

## Gaps / follow-ups (non-blocking)

1. **Single example file** is good for the app, but there is no root-level `.env.example` for multi-package contributors — optional if `docs/system/FRESH-INSTALL.md` remains the install path.
2. **Stale comments vs runtime**: example may lag flag renames (e.g. TTS sample-rate comments/defaults). Treat example as documentation; keep it aligned when shipping voice changes.
3. **Gateway config** has no `*.example` sibling in-tree from this audit — if operators need a template, add `xinyu_qq_gateway.config.example.json` with fake IDs only (do not copy real config).
4. Before each release, run a privacy dry-run (`scripts/Release-DryRun.ps1` per `docs/README.md`) rather than relying only on this static list.

## Operator recipe

```text
# Create local secrets file (never commit)
copy XinYu-Core\examples\agent-apps\xinyu\xinyu.local.env.example `
     XinYu-Core\examples\agent-apps\xinyu\xinyu.local.env

# Confirm ignore
git check-ignore -v XinYu-Core/examples/agent-apps/xinyu/xinyu.local.env

# Confirm nothing secret is tracked
git ls-files | rg -i '\.env|local\.env|bridge_token|gateway\.config'
```

Expected: only `xinyu.local.env.example` (and non-secret code) appears for env-like paths.

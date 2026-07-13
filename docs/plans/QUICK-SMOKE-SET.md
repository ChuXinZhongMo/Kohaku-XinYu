# Quick smoke set (CI-blocking candidate)

Date: 2026-07-13 (updated)  
Scope: `XinYu-Core/examples/agent-apps/xinyu`  
Status: **blocking CI job live** — `Python smoke offline (blocking)` in `.github/workflows/ci.yml`; also a required check on `main`

## How smokes work today

| Surface | Path / command | Role |
|---|---|---|
| Manual runner | `smoke_run.py` | Groups: `quick`, `core`, `full`, `deployment`, `runtime`, `memory`, `voice`, `learning`, `privacy`, `replay` |
| Default group | `QUICK_SMOKES` in `smoke_run.py` | ~39 steps: one large `py_compile` batch + many `tests/smoke/**/*_smoke.py` scripts |
| Pytest marker | `pytest.ini` → `markers.smoke` | Standalone `*_smoke.py` scripts collected via `tests/test_smoke_scripts.py` |
| Default pytest | `addopts = -m "not smoke"` | Unit/bridge tests only; smokes **excluded** |
| CI blocking | `.github/workflows/ci.yml` job `python-smoke-offline` | Curated hermetic scripts (fail PR); required on `main` |
| CI informational | `.github/workflows/ci.yml` job `python-smoke` | `pytest -q -m smoke`, **`continue-on-error: true`** |

There are on the order of **~180** `tests/smoke/**/*_smoke.py` scripts. Almost all are `main()`-style subprocess programs, not pure pytest unit tests. Many are fine offline (tempdirs + in-process stubs). A large tail still assumes local memory trees, optional bridge tokens, live HTTP to a running bridge, QQ/NapCat, LLM/TTS, or owner machine state.

**Honest summary:** most of the full smoke corpus is **not** a safe blocking CI gate. `smoke_run.py --group quick` is already too large and mixed for a green-required PR check. Prefer a **small curated offline set** for blocking, keep full `pytest -m smoke` / `smoke_run` groups as non-blocking or operator-only.

## Recommended CI-blocking set (offline / hermetic)

Run from app root:

`XinYu-Core/examples/agent-apps/xinyu`

Suggested command shape (future):

```text
python -m py_compile <core modules…>
python tests/smoke/<script>.py   # each of the list below
```

Or a thin wrapper group (not implemented here) e.g. `smoke_run.py --group ci-quick`.

### A. Syntax / import surface (cheap, high signal)

| Item | Path / args | Why | Live env? |
|---|---|---|---|
| Compile core surface | `python -m py_compile` over the first entry of `QUICK_SMOKES` in `smoke_run.py` (state/chat services, bridge routes, custom bridge plugins, key life/voice modules) | Catches syntax/import breakage on the always-touched surface without executing runtime | No |

Keep this list synced with `QUICK_SMOKES[0]` rather than forking a second long list forever.

### B. Offline logic / contract smokes (stable candidates)

These were sampled as tempdir-based, static-marker, or local-stub tests and are the best near-term blocking candidates:

| Name | Path | Why included | Live env? |
|---|---|---|---|
| Mojibake guard | `tests/smoke/runtime/mojibake_guard_smoke.py` | Encoding / prompt-card corruption is a recurring regression class | No (repo file scan) |
| Runtime presence | `tests/smoke/runtime/runtime_presence_smoke.py` | Heartbeat / turn presence + secret redaction in prompt blocks | No (tempdir) |
| Runtime security | `tests/smoke/runtime/runtime_security_smoke.py` | Bridge token / API key guard rails | No (in-process env fixtures) |
| Memory braid | `tests/smoke/memory/memory_braid_smoke.py` | Core memory orchestration prompt block | No (tempdir) |
| Codex delegation reality | `tests/smoke/codex/codex_delegation_reality_smoke.py` | Static policy/prompt/bridge marker contract (no Codex CLI) | No (repo text markers) |
| Bridge renderer guards | `tests/smoke/bridge/bridge_renderer_guard_flags_smoke.py` | Output-guard flag wiring | No (logic-level) |
| Speech controller | `tests/smoke/voice/xinyu_speech_controller_smoke.py` | Voice pipeline controller without requiring TTS hardware | Typically no (confirm before gating) |
| Persona realism eval | `tests/smoke/voice/persona_realism_eval_smoke.py` | Persona eval harness smoke | Typically no |
| Self-code approval | `tests/smoke/codex/self_code_approval_smoke.py` | Self-action approval gates | No (tempdir/logic) |
| Self-code watchdog | `tests/smoke/codex/self_code_watchdog_smoke.py` | Watchdog snapshot path | No (tempdir) |
| Environment sensor | `tests/smoke/life/environment_sensor_smoke.py` | Life env sensing without external APIs | No / local only |
| Life kernel family | `tests/smoke/life/life_kernel_smoke.py`, `life_kernel_entropy_smoke.py`, `life_kernel_self_choice_bias_smoke.py`, `xinyu_self_choice_store_smoke.py`, `xinyu_dream_engine_smoke.py` | Life-kernel contracts used heavily in autonomy work | No (in-process) |
| QQ gateway unit-style | `tests/smoke/qq/integration/xinyu_qq_gateway_smoke.py` | Gateway config + error normalization; stubs ConnectionReset; does **not** need NapCat | No live QQ (uses mocks / local temp) |

### C. Local-HTTP stub smokes (OK offline if loopback is allowed)

| Name | Path | Why | Live env? |
|---|---|---|---|
| Metabolism HTTP | `tests/smoke/life/metabolism_http_smoke.py` | Spins its own `127.0.0.1:0` server | Loopback only |
| GitHub autonomous learning | `tests/smoke/learning/github_autonomous_learning_smoke.py` | Stub HTTP server + tempdir | Loopback only |
| External plugins | `tests/smoke/tools/xinyu_external_plugins_smoke.py` | Kohaku-style stub server | Loopback only |

Safe in CI runners that allow binding localhost; still not “pure unit”. Put these in a second tier if loopback policies are strict.

## Explicitly **not** for blocking CI (need live / owner env)

| Area | Examples | Needs |
|---|---|---|
| Runtime readiness / deployment | `tests/smoke/runtime/integration/runtime_readiness_smoke.py`, `deployment_status_smoke.py` | Running bridge, token discovery, status scripts; `--offline` only softens part of readiness |
| Live dialogue / relationship | `tests/smoke/dialogue/integration/*`, `owner_relationship_lived_stress_smoke.py`, multi-person live | LLM + long session state |
| Live voice quality | `tests/smoke/voice/integration/*` (real conversation, calibration, continuity) | Brain model + TTS stack |
| Privacy group pieces that still touch policy files only are fine; full privacy group mixes offline + operator checks | `smoke_run.py --group privacy` | Mixed |
| Learning ingest / bridge probe against a live process | `tests/smoke/bridge/integration/bridge_probe_smoke.py`, `bridge_learning_ingest_smoke.py` | Live bridge |
| Codex **execution** worker lifecycle | `tests/smoke/codex/codex_execution_*` | Worker process / backend flags |
| Full groups | `smoke_run.py --group core|full|voice|learning|runtime` | Too broad; core embeds full pytest + privacy + voice |

## Relationship to existing `QUICK_SMOKES`

`QUICK_SMOKES` is a useful **operator** default (`python smoke_run.py --group quick`) but is **not** identical to the CI-blocking set above:

- Includes many good offline scripts (life kernel, initiative spine, memory self-review, sticker pack, etc.).
- Also includes items that are heavier or environment-sensitive (e.g. integration-ish learning/github paths, QQ gateway under `integration/`, full compile list that can lag deleted modules).
- Does **not** include several strong offline contracts (e.g. `runtime_security_smoke`, `codex_delegation_reality_smoke` lives under privacy group instead).

Recommendation:

1. Keep `quick` for humans / long-running local validation.
2. Add a future `ci-quick` (or CI job steps) = section A + B only (~15–20 scripts).
3. Leave `pytest -m smoke` informational until the corpus is partitioned (`@pytest.mark.smoke_offline` vs `smoke_live`) or until failure rate is known green.

## What still needs live env (operator checklist)

Before promoting any additional smoke into the blocking set, verify it does **not** require:

- `xinyu.local.env` secrets (`XINYU_API_KEY`, bridge token, OpenAI keys)
- A running `xinyu_core_bridge.py` on `:8765` (or desktop/QQ processes)
- NapCat / real QQ accounts
- Local Genie/Higgs TTS on `:8000`/`:8001`
- Network egress to LLM vendors or GitHub (unless fully stubbed)
- Writable production `memory/` or `runtime/` trees (prefer tempdir + `--restore-after`)

## Current blocking list (CI job, 2026-07-13)

Verified green offline on the release line and wired in `python-smoke-offline`:

| Script |
|---|
| `tests/smoke/runtime/runtime_security_smoke.py` |
| `tests/smoke/memory/memory_braid_smoke.py` |
| `tests/smoke/bridge/bridge_renderer_guard_flags_smoke.py` |
| `tests/smoke/bridge/bridge_auth_smoke.py` |
| `tests/smoke/bridge/bridge_values_smoke.py` |
| `tests/smoke/bridge/bridge_session_cleanup_smoke.py` |
| `tests/smoke/codex/self_code_approval_smoke.py` |
| `tests/smoke/voice/xinyu_speech_controller_smoke.py` |
| `tests/smoke/voice/persona_realism_eval_smoke.py` |
| `tests/smoke/life/environment_sensor_smoke.py` |
| `tests/smoke/life/life_kernel_smoke.py` |
| `tests/smoke/life/life_kernel_entropy_smoke.py` |
| `tests/smoke/life/life_kernel_self_choice_bias_smoke.py` |
| `tests/smoke/life/xinyu_self_choice_store_smoke.py` |
| `tests/smoke/life/xinyu_dream_engine_smoke.py` |

### Known red (do not promote yet)

| Script | Why red |
|---|---|
| `mojibake_guard_smoke.py` | Intentional/legacy U+FFFD and mojibake fragments still in tree |
| `runtime_presence_smoke.py` | Marker drift vs current bridge API |
| `codex_delegation_reality_smoke.py` | Missing policy path markers after refactor |
| `self_code_watchdog_smoke.py` | Watchdog alias/marker drift |
| `qq/integration/xinyu_qq_gateway_smoke.py` | `_trace_qq_inbound` signature drift (`delivery_kind`) |

## Suggested next engineering steps

1. Clean marker-drift smokes above, then promote one at a time into the CI list.
2. Optional: `CI_QUICK_SMOKES` list in `smoke_run.py` so local operators share the same set.
3. Keep `pytest -m smoke` informational until the corpus is partitioned.
4. Periodically re-audit `QUICK_SMOKES` for dead paths after bridge consolidations.

# Phase 2 Architecture Inventory

Status: draft baseline (2026-07-13)  
Related: `docs/plans/ENGINEERING-MATURITY-PLAN.md`

This file is the working inventory for modularity work. Update numbers when a
cluster lands.

## 1. Size snapshot (approximate, local tree)

| Area | Signal | Notes |
|------|--------|-------|
| xinyu app `*.py` | ~1850 files / ~290k lines | includes tests/tools; exclude venv/self_found |
| core `XinYu-Core/src` | ~320 files / ~57k lines | package root `xinyu_runtime` |
| `*bridge*.py` under app | ~1k+ paths | noisy glob; prefer store/shim counts |
| app `tests/` | ~660 test modules | unit default; smoke marked |
| smoke scripts | ~180 | many need live env |

Re-measure before/after each consolidation PR:

```bash
# from repo root (adjust excludes as needed)
find XinYu-Core/examples/agent-apps/xinyu -name 'xinyu_bridge_*_store.py' | wc -l
find XinYu-Core/examples/agent-apps/xinyu -name 'xinyu_bridge_*.py' | wc -l
```

## 2. God files (split priority)

Priority = size × change frequency × operator criticality.

| Priority | Path | ~LOC | Split strategy |
|----------|------|------|----------------|
| P0 | `.../xinyu_qq_gateway.py` | ~4000 | protocol / session / send / normalize / CLI |
| P0 | `.../xinyu_status.py` | ~2900 | collect / render / CLI |
| P1 | `.../xinyu_creative_writing.py` | ~4000 | generation / policy / storage |
| P1 | `.../xinyu_runtime_presence.py` | ~2400 | presence model / IO / API |
| P1 | `.../xinyu_learning_library.py` | ~1900 | index / retrieve / write gates |
| P2 | `.../xinyu_speech_controller.py` | ~1800 | TTS pipeline vs policy |
| P2 | `.../xinyu_codex_delegate.py` | ~1600 | retire/legacy paths vs native coding |
| P2 | other >1500 LOC hot modules | … | same rules |

### Split rules

1. Behavior-preserving PRs only for pure moves.
2. Keep public import paths stable (shim re-exports OK for one release cycle).
3. Move tests with the code or add focused unit tests in the same PR.
4. No drive-by feature work inside split PRs.

## 3. Bridge / store clusters

Use the proven pilot playbook (stores → domain module, thin shims only if needed).

| Cluster | Example name patterns | Target module (proposed) | Status |
|---------|----------------------|--------------------------|--------|
| Generic stores | `xinyu_bridge_*_store.py` (pilot set) | `xinyu_bridge_stores.py` | pilot done / continue |
| Bootstrap / CLI env | `*_bootstrap*`, `*_cli_env*` | `bridge/bootstrap.py` | todo |
| Autonomous maintenance | `*_autonomous_maintenance*` | `bridge/autonomous_maintenance.py` | todo |
| Proactive / promise | `*_proactive*`, `*_promise*` | `bridge/proactive_state.py` | todo |
| Desktop private frame | `*_private_desktop*`, `*_desktop_proactive*` | `bridge/desktop_state.py` | todo |
| Codex / coding | `*_codex*` | `bridge/codex_runtime.py` | todo (legacy retire) |
| Learning sidecars | `*_learning_sidecar*` | `bridge/learning_sidecars.py` | todo |
| Observation reports | `*_observation_report*` | `bridge/observation.py` | todo |

### Per-cluster PR checklist

- [ ] Inventory callers (`rg` import map)
- [ ] Move pure IO/helpers
- [ ] Keep or delete shims deliberately
- [ ] Tests green (`pytest -q -m "not smoke"` for touched area)
- [ ] Record before/after file counts in PR body

## 4. Target package shape (incremental)

Do **not** rename the whole tree in one PR.

```text
XinYu-Core/examples/agent-apps/xinyu/
  # near-term: keep flat entrypoints
  xinyu_qq_gateway.py          # thin facade
  xinyu_status.py              # thin facade

  # grow packages underneath
  xinyu_gateway/
  xinyu_bridge/
  xinyu_memory/
  xinyu_proactive/
  xinyu_desktop/
  xinyu_autonomy/
  tests/
  prompts/
  ops/
```

## 5. Sprint 1 recommendation (next engineering PRs)

1. **Inventory commit** — this file + measured counts in PR description.
2. **Gateway split slice 1** — extract pure helpers from `xinyu_qq_gateway.py`
   with zero behavior change.
3. **Store cluster #2** — next remaining `*_store.py` family after pilot.
4. **Stop-the-bleeding rule** — new store modules require a one-line rationale
   in the PR linking to this inventory.

## 6. Progress log

| Date | Change |
|------|--------|
| 2026-07-13 | Thin bridge stores: 21 modules folded into `xinyu_bridge_stores.py`; remaining thick: `desktop_surface_state_store`, `proactive_delivery_state_store` |
| 2026-07-13 | Gateway split: `xinyu_qq_owner_private_intent.py`, `xinyu_qq_sticker_context.py`, `xinyu_qq_payload_builders.py`; facade ~3465 LOC |
| 2026-07-13 | Status split: `xinyu_status_models.py`, `xinyu_status_collect.py`, `xinyu_status_render.py`; facade ~72 LOC |
| 2026-07-13 | App critical ruff (`F,E9,...`) 885 → 0; CI blocks on app critical |
| 2026-07-13 | Gateway pure helpers: `message_ids_from_action_response` → `xinyu_qq_gateway_utils`; sticker question heuristic → `xinyu_qq_sticker_context`; group/file-learning policy → `xinyu_qq_group_policy.py` (+ unit tests). Thick store facades already thin re-exports (`desktop_surface` / `proactive_delivery` live under `stores/`). |

## 7. Stop-ship / do-not

- No new 2k-line modules without an explicit exception.
- No “fix + refactor + feature” mega-PRs.
- No deleting shims without an import map.
- No weakening privacy boundary for cleaner packages.
- Do not blind-`ruff --fix` F401 on bridge injection facades without `__all__`.

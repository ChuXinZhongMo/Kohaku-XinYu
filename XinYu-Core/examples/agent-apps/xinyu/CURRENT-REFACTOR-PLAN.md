# XinYu Current Refactor Plan

Date: 2026-05-07

This plan describes the current-stage refactor for XinYu. It is not a rewrite plan. The current runtime is healthy, so the goal is to reduce structural risk while preserving the running QQ/Core/Desktop behavior.

## 0. Current Judgment

XinYu needs refactoring, but not an emergency rewrite.

Current facts:

- The live path is still `NapCat -> xinyu_qq_gateway.py -> xinyu_core_bridge.py -> XinYu Core`.
- `xinyu_core_bridge.py` and `xinyu_qq_gateway.py` are large enough to create maintenance risk.
- `xinyu_v1/` and Action Layer v1 already exist and should receive new structured work.
- Runtime readiness, action experience smoke, v1 canary smoke, pytest, and desktop typecheck are currently green.

Therefore:

- Do not stop the system for a broad rewrite.
- Do not keep adding new large behavior blocks to the old bridge/gateway files.
- Move one bounded responsibility at a time into smaller modules.
- Keep every step reversible and covered by smoke tests.

## 1. Non-Goals

This refactor must not:

- rewrite the whole Core bridge in one pass;
- switch v1 to full production automatically;
- change XinYu's visible personality, memory policy, or QQ behavior as a side effect;
- mix behavior tuning, UI redesign, and structural refactor in the same batch;
- open arbitrary shell or filesystem authority through the action layer;
- delete legacy code before the replacement has real smoke and runtime evidence.

## 2. Baseline Gate

Before and after each refactor slice, run the smallest relevant gate.

Full baseline:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe xinyu_status.py --json
.\.venv\Scripts\python.exe runtime_readiness_smoke.py
.\.venv\Scripts\python.exe -m pytest tests -q

cd D:\XinYu\XinYu_Desktop
npm run typecheck
```

Focused bridge/gateway baseline:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe -m py_compile xinyu_core_bridge.py xinyu_qq_gateway.py
.\.venv\Scripts\python.exe runtime_readiness_smoke.py
```

Focused v1 baseline:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe -m pytest tests\v1 -q
.\.venv\Scripts\python.exe xinyu_v1_owner_simple_canary_smoke.py
```

Focused action-layer baseline:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe xinyu_action_experience_smoke.py
```

## 3. Stage 1: Documentation And Boundaries

Goal: make the current architecture and refactor direction explicit.

Tasks:

- Keep this file updated as the current refactor source of truth.
- Fix stale README references when they point to missing plans.
- State clearly that v1 is still shadow/canary unless owner approval explicitly enables a narrow canary.
- State clearly that `xinyu_core_bridge.py` should become thinner and should not receive new large feature blocks.
- State clearly that `xinyu_qq_gateway.py` is a transport adapter, not a personality, memory, or action-decision layer.

Acceptance:

- A new Codex window can read this file and understand what to refactor next.
- README and plan references match files that actually exist.
- No runtime behavior changes.

## 4. Stage 2: Thin The Core Bridge

Goal: reduce `xinyu_core_bridge.py` risk by extracting orchestration slices without changing behavior.

First extraction targets:

- action-layer turn path;
- recent action follow-up path;
- action digest follow-up path;
- v1 shadow/canary path;
- turn sidecar preflight order.

Suggested modules:

- `xinyu_bridge_action_routes.py`
- `xinyu_bridge_v1_routes.py`
- `xinyu_bridge_turn_sidecars.py`
- `xinyu_bridge_turn_pipeline.py`

Rules:

- Move code first; avoid logic changes in the same patch.
- Preserve response payload shape.
- Preserve existing notes where possible, because tests and runtime diagnostics depend on them.
- Keep `XinYuBridgeRuntime.chat()` as the observable behavior contract until a new pipeline has enough coverage.

Acceptance:

- `chat()` is shorter and easier to scan.
- Runtime readiness remains green.
- Existing action-layer and v1 smoke tests pass.
- No QQ visible behavior changes.

## 5. Stage 3: Narrow v1 Canary Ownership

Goal: let v1 take responsibility for a tiny, reversible class of turns after explicit owner approval.

Allowed scope:

- owner private chat only;
- simple text only;
- no attachments;
- no group messages;
- no learning ingest;
- no Codex delegation;
- no action-layer tool execution;
- automatic fallback to the old main path on error, timeout, missing reply, or unexpected route.

Rules:

- v1 canary must remain observable through readiness state and trace files.
- v1 must not auto-switch to full production.
- Owner approval remains required.

Acceptance:

- `tests\v1` passes.
- v1 canary smoke passes.
- v1 errors are visible in status/readiness.
- Disabling v1 returns all traffic to the old path.

## 6. Stage 4: Split QQ Gateway Responsibilities

Goal: reduce `xinyu_qq_gateway.py` into a connection and dispatch layer.

Extraction targets:

- OneBot event normalization;
- command prefix routing;
- attachment and file enrichment;
- outbox claim/ack client;
- send retry and ack tracking.

Suggested modules:

- `xinyu_qq_normalizer.py`
- `xinyu_qq_command_router.py`
- `xinyu_qq_attachment_resolver.py`
- `xinyu_qq_outbox_client.py`

Rules:

- Keep QQ visible behavior unchanged.
- Do not move personality, memory, or action decisions into gateway modules.
- Gateway modules should produce normalized transport facts and call Core routes.

Acceptance:

- Gateway smoke passes.
- Gateway main class becomes mostly connection, queue, and dispatch logic.
- Core remains the only owner of action routing and memory-affecting decisions.

## 7. Stage 5: Desktop Shell File Split

Goal: split large renderer files without redesigning the product.

Targets:

- `src/renderer/src/main.tsx`
- `src/renderer/src/style.css`

Suggested slices:

- chat surface;
- environment/status panel;
- proactive inbox;
- action/report view;
- shared state hooks;
- panel-specific CSS files.

Rules:

- Do not change visual design and component split in the same patch unless the visual change is necessary.
- Keep text and controls stable.
- Run typecheck after every slice.

Acceptance:

- `npm run typecheck` passes.
- Existing UI behavior remains intact.
- New files make the main renderer easier to navigate.

## 8. Stage 6: Retire Old Paths Only After Evidence

Goal: remove or demote legacy code only when the replacement is proven.

Requirements before removal:

- replacement module has focused smoke or pytest coverage;
- runtime readiness has stayed green after the replacement was active;
- status output or traces show the replacement is actually used;
- rollback path is clear.

Allowed cleanup:

- mark compatibility helpers as legacy;
- delete truly unreachable files;
- move stale plans into archive;
- remove stale README references.

Not allowed yet:

- delete the old bridge path;
- delete the old QQ gateway path;
- make v1 full production by default;
- remove action-layer safety checks.

## 9. Priority Order

Recommended next sequence:

1. Fix stale plan references in README.
2. Extract action-layer route handling from `xinyu_core_bridge.py`.
3. Extract v1 shadow/canary route handling from `xinyu_core_bridge.py`.
4. Extract recent-action follow-up handling.
5. Add a small diagnostics command or panel showing which live modules influenced a turn.
6. Split QQ gateway transport helpers.
7. Split desktop renderer files.

## 10. Working Rule

Every refactor slice should answer one question:

```text
Did this make XinYu easier to change next time without changing who she is today?
```

If the answer is not clear, keep the slice smaller.

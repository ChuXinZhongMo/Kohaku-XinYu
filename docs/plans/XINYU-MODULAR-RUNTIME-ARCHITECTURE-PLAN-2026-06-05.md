# XinYu Modular Runtime Architecture Plan

Date: 2026-06-05
Workspace: `D:\XinYu`

## 1. Direction

XinYu should stay a working local runtime while its architecture boundaries are
rebuilt. The target is a layer-first modular runtime architecture, not an
immediate microservice rewrite and not a framework replacement. The
implementation should keep the current flat-module layout unless the owner
explicitly approves package-directory migration later.

Terminology:

```text
Architecture layer decoupling:
  Enforce layer ownership and dependency direction so gateway, API, runtime,
  services, contracts, execution, and persistence stop leaking into each other.
  This comes first.

Functional relocation:
  Move existing code into the layer it actually belongs to. This is still
  architecture work, not service/process splitting.

Local service owner:
  After a capability's layer is clear, give it an explicit local module owner
  such as chat/proactive/codex/learning/state. This stays in the same process.

Process/service split:
  Run a boundary as a separate service/process. This is deferred until the local
  boundary is already stable.
```

Order:

```text
1. Define the layer contract.
2. Cut architecture seams in fat entrypoints.
3. Relocate functions into the correct layer.
4. Promote stable capabilities into local service owners.
5. Only then consider process-level service splits for stable boundaries.
```

Core rule:

```text
Keep external behavior stable.
Architecture boundaries first.
Functional ownership second.
Process/service splitting last.
Thin fat entrypoints only by moving code to the correct layer.
Move side effects behind execution and persistence boundaries.
```

## 2. Target Architecture

```text
Access / gateway layer
  QQ / NapCat / Desktop / HTTP / CLI / private browser / private desktop
  Only exposes entrypoints, normalizes external payloads, forwards calls, and
  returns responses. It does not own memory, runtime policy, or service logic.

API layer
  Stable internal callable API for gateway, UI, tools, and external adapters.
  Owns request contracts, auth checks, route registration, sessions, and
  request/response wiring.

Runtime layer
  Replaceable core runtime capability: model calls, prompt/runtime execution,
  renderer, sidecars, session engine, and runtime adapters. API calls runtime;
  runtime does not call back into gateway.

UI/UX layer
  Desktop shell, dashboards, operator panels, and owner-visible controls. UI/UX
  consumes API contracts and presents state; it does not call runtime internals
  or own persistence rules.

Application service layer
  chat, proactive, codex, learning, desktop, qq outbox, actions, state. Each
  service owns one business capability and exposes narrow functions to API.

Contract / policy layer
  turn routing, trust, approval, proactive policy, outbox semantics,
  memory-candidate rules, owner-private rules, DTO/schema helpers.

Execution layer
  concrete task execution: Codex runner, tool calls, package install, private
  browser/desktop actions, background maintenance, async jobs.

Persistence layer
  events, projections, runtime queues, traces, review stores, memory gates,
  JSON/JSONL/text stores, cache, logs.
```

Implementation layout rule:

```text
Use existing flat modules by default:
  xinyu_bridge_*.py
  xinyu_qq_*.py
  xinyu_*_service.py
  state_service.py / xinyu_*_store.py

Do not create new package folders such as xinyu_bridge/ or xinyu_qq/ during
this plan unless the owner explicitly asks for that migration.
```

Allowed dependency direction:

```text
access/gateway -> API -> application service -> contract/policy
                  UI/UX -> API
                  API -> runtime
                  application service -> execution
                  application service -> persistence
```

Forbidden dependency direction:

```text
runtime -> gateway
runtime -> UI/UX service
gateway -> stable memory body writes
gateway -> runtime internals
API route handler -> raw NapCat protocol details
contract/policy -> API route handler
persistence helper -> business policy
execution module -> owner-private policy decisions
```

Layer independence rule:

```text
Runtime should be swappable without breaking gateway/UI/API contracts.
Gateway should be swappable without changing runtime behavior.
UI/UX services should consume API contracts, not runtime internals.
Persistence should store facts/state, not decide business policy.
Execution should perform approved work, not decide approval.
```

Current flat-module anchors:

```text
Access / gateway:
  xinyu_qq_gateway.py
  xinyu_qq_server.py
  xinyu_qq_sender.py
  xinyu_qq_normalizer.py
  xinyu_qq_outbox_dispatcher.py

API:
  xinyu_core_bridge.py
  xinyu_bridge_app.py
  xinyu_bridge_http.py
  xinyu_bridge_auth.py
  xinyu_bridge_session.py
  xinyu_bridge_*_routes.py

Runtime:
  xinyu_runtime package
  xinyu_bridge_null_input.py
  xinyu_bridge_turn_pipeline.py
  xinyu_bridge_slow_live_turn.py
  renderer/session/sidecar adapters used by Bridge

UI/UX:
  XinYu_Desktop/*
  runtime/local_inspector_dashboard.html
  desktop REST/WS presentation state helpers

Application service:
  xinyu_chat_service.py
  xinyu_desktop_service.py
  xinyu_codex_service.py
  xinyu_learning_service.py
  future xinyu_proactive_service.py / xinyu_qq_outbox_service.py

Contract / policy:
  xinyu_bridge_payload_policy.py
  xinyu_bridge_trusted_search.py
  xinyu_qq_trust_policy.py
  v1_canary_gate.py
  approval/trust/owner-private DTO helpers

Execution:
  xinyu_codex_delegate.py
  xinyu_package_installer.py
  xinyu_private_desktop_control.py
  xinyu_private_ecosystem.py
  tool/plugin runners

Persistence:
  state_service.py
  xinyu_*_store.py
  xinyu_qq_outbox.py
  xinyu_review_inbox.py
  JSON/JSONL/text store helpers
```

Ambiguous modules must be classified before they are edited. If one module
contains multiple layers, the first slice should expose the seam instead of
moving the whole module.

## 3. Non-Negotiables

- Do not change public HTTP/WS routes unless a compatibility shim remains.
- Do not change QQ/OneBot payload shape during refactors.
- Do not batch-migrate or rewrite stable memory/persona bodies.
- Do not expand v1 real traffic while decomposing legacy boundaries.
- Do not turn local coupling into distributed coupling before modules are clean.
- Do not create package directories during this plan.
- Every code slice must have a compile check, smoke, or focused pytest.
- User/runtime/private ecosystem data bodies are not inspected or moved unless
  the task explicitly requires it.

## 4. Migration Phases

### Phase 0: Architecture Contract And Guardrails

Goal: make the intended boundaries visible and reviewable.

Deliverables:

- This architecture plan.
- A short boundary checklist in future worklog entries.
- Focused smoke/pytest commands attached to each slice.
- Optional boundary audit scripts for forbidden imports/writes once enough flat
  modules exist to enforce the rules.

Exit criteria:

- The team can point to one plan for layer names, dependency direction, and
  red lines.

### Phase 1: Split Bridge Into API And Runtime Seams

Goal: split the current Bridge into an API layer plus runtime adapter seam
before moving large business workflows. The Bridge remains a compatibility
entrypoint, but route/API contracts, runtime calls, execution calls, and
persistence calls become visibly separate.

Slices:

1. Extract Bridge startup/server/shutdown orchestration.
2. Extract route registration maps where routes are still implicit, using
   flat modules such as `xinyu_bridge_route_registry.py`.
3. Separate route/API contract handling from runtime execution calls.
4. Keep runtime access behind a replaceable runtime adapter boundary.
5. Separate persistence/file writes from API and runtime path code.
6. Extract session lifecycle and cleanup ownership beyond helper shims.
7. Split UI/UX-facing desktop/dashboard presentation helpers away from runtime
   and persistence internals.
8. Only after the seams are clear, relocate chat/proactive/Codex blocks into
   their correct local owners.
9. Keep old method names as compatibility wrappers until tests prove callers
   are migrated.

Exit criteria:

- `xinyu_core_bridge.py` contains startup, dependency wiring, and thin
  wrappers, not long business workflows.
- Route/API, runtime, execution, and persistence responsibilities are visible
  as separate flat modules or helpers.
- Existing bridge, desktop, proactive, codex, and state smokes still pass.

### Phase 2: Split QQ Gateway Into Access And API Client Seams

Goal: make QQ Gateway an access layer only. It normalizes OneBot/NapCat events,
checks access rules, calls API contracts, and sends OneBot actions. It does not
own runtime internals, persistence, learning strategy, or memory policy.

Slices:

1. Move WebSocket server lifecycle into flat modules such as
   `xinyu_qq_server.py`.
2. Move OneBot payload normalization into flat modules such as
   `xinyu_qq_normalizer.py`.
3. Move send/action construction into flat modules such as `xinyu_qq_sender.py`.
4. Move owner/group access and trigger rules into contract/policy helpers.
5. Keep outbox claim/send/ack isolated behind the existing dispatcher/client
   boundary.
6. Ensure QQ Gateway calls API contracts, not runtime internals or persistence
   files directly.
7. Keep real QQ outbound validation disabled unless explicitly approved.

Exit criteria:

- `xinyu_qq_gateway.py` does not own learning, sticker, Codex, or self-action
  strategy directly; it delegates through API contracts and layer-specific
  helpers.
- QQ gateway and outbox smokes pass.

### Phase 3: Relocate Functions Into Local Owners

Goal: after Bridge/Gateway seams are visible, move feature code into the local
owner that matches its layer. This is local modularization, not process-level
service splitting.

Target owners:

- `ChatService`: request preparation, turn metadata, finish-sidecar contract.
- `ProactiveService`: candidates, claim/ack lifecycle, owner reply feedback.
- `CodexService`: delegation payloads, completion summary, completion outbox.
- `LearningService`: ingest wrapper and closed-loop follow-up contract.
- `DesktopService`: REST/WS/event state surface.
- `QQOutboxService`: Core-side outbox semantics.
- `StateService`: atomic JSON/text writes, JSONL append, projection/runtime queue
  stores, privacy-safe state classification.

Exit criteria:

- New feature work attaches to a service owner rather than a fat entrypoint.
- Service-boundary smokes cover the extracted contracts.

### Phase 4: State Boundary Consolidation

Goal: reduce scattered runtime writes after the API/runtime/execution seams are
clear, without touching protected memory bodies.

Directory semantics:

```text
events/       append-only facts
projections/  derived current views
runtime/      temporary state, queues, traces, sessions
memory/       protected long-term material and reviewed memory
logs/         diagnostics
cache/        rebuildable artifacts
```

Slices:

1. Move low-risk projection writes behind `StateService`.
2. Move runtime queues behind store owners.
3. Keep stable memory writes gated and review-first.
4. Add metadata-only audits for orphan/runtime/private state.

Exit criteria:

- New runtime/projection writes do not directly hand-roll file IO.
- Protected memory body content remains untouched.

### Phase 5: Service-Split Stable Boundaries

Goal: only split processes where the local boundary is already stable.

Good candidates:

- QQ/NapCat gateway.
- Desktop event stream.
- Private browser/private desktop engines.
- Codex/tool runner.
- Health/diagnostics runner.
- Model provider adapter.

Deferred candidates:

- Main chat runtime.
- Persona and stable memory writes.
- Proactive core policy.
- v1 takeover path.

Exit criteria:

- Split services have explicit request/response contracts, health checks,
  retry behavior, and state ownership.

## 5. Per-Slice Workflow

Every slice follows:

```text
1. Inspect current callers and dirty worktree.
2. Pick one boundary.
3. Classify it by layer: access, API, runtime, service, contract, execution, or
   persistence.
4. Add or extend the flat target module for that layer.
5. Replace only the minimal legacy code.
6. Keep compatibility wrappers.
7. Run focused validation.
8. Record what moved, which layer owns it, and what remains coupled.
```

Boundary checklist before editing:

```text
1. Which layer owns this code today?
2. Which layer should own it after this slice?
3. Does it expose an external route/payload shape?
4. Does it touch runtime internals?
5. Does it write state or memory?
6. Does it execute tools/actions?
7. Does it make owner-private or approval decisions?
8. What compatibility wrapper keeps existing callers working?
9. What focused validation proves behavior is unchanged?
```

Layer-specific rule of thumb:

```text
Gateway/access code may normalize and forward.
API code may validate contracts, auth, session, and route calls.
Runtime code may compute/model/render, but not expose itself to gateways.
UI/UX code may present and request through API, but not decide persistence.
Application service code may orchestrate one capability.
Contract/policy code may decide rules, but should avoid side effects.
Execution code may perform approved work.
Persistence code may read/write state, but not decide policy.
```

## 6. Validation Matrix

Use the smallest relevant set for each slice:

```text
python -m py_compile <changed .py files>
python tests/smoke/bridge/bridge_probe_smoke.py
python xinyu_desktop_rest_smoke.py
python xinyu_desktop_ws_smoke.py
python xinyu_qq_gateway_smoke.py
python qq_outbox_smoke.py
python codex_delegate_smoke.py
python codex_completion_outbox_smoke.py
python bridge_learning_ingest_smoke.py
python state_io_smoke.py
python service_boundary_smoke.py
python -m pytest <focused tests> -q
```

If a smoke path has moved, prefer the repo's current equivalent and record the
actual command used.

Validation selection:

```text
Architecture seam only:
  py_compile + focused unit test + diff check.

Bridge route/API seam:
  py_compile + focused route/helper test + bridge_probe_smoke.py when practical.

Runtime seam:
  py_compile + focused runtime/turn test + relevant chat/session smoke.

Gateway/access seam:
  py_compile + xinyu_qq_gateway_smoke.py + no real outbound.

Persistence seam:
  py_compile + state_io_smoke.py + feature-specific smoke.

UI/UX seam:
  Desktop typecheck/build only if Desktop files are touched.
```

## 7. First Execution Queue

1. Extract Bridge app startup/server/shutdown orchestration.
2. Add a small compile/focused import validation for the new Bridge app module.
3. Extract a low-risk Bridge route/API seam into a flat `xinyu_bridge_*`
   module without moving the whole chat flow.
4. Add a small boundary-classification comment or test for that seam when it
   is not obvious from the module name.
5. Extract a low-risk runtime adapter seam only after route/API ownership is
   clear.
6. Extract a low-risk persistence seam, such as one runtime/projection writer,
   behind `StateService`.
7. Extract one QQ Gateway access-only slice.
8. Add or extend focused smoke coverage for the extracted contract.
9. Re-check architecture plan against the current project diagram.
10. Audit whether the touched slice respects the access/API/runtime/service/
   contract/execution/persistence layer split.

## 8. Success Definition

The refactor is succeeding when:

- Fat entrypoint line count trends down.
- New modules have clear ownership and tests.
- Route and QQ compatibility stay stable.
- State writes are easier to audit.
- There are fewer fallback-heavy compatibility blocks in active paths.
- Future service-splitting becomes an operational choice, not a rescue plan.

## 9. Compatibility And Rollback

Compatibility pattern:

```text
1. Add a flat target module.
2. Move only one cohesive seam.
3. Keep old function/method names in the legacy file as wrappers.
4. Keep old route/payload/state shapes.
5. Migrate callers only after focused tests pass.
6. Delete wrappers only in a later explicit cleanup slice.
```

Rollback pattern:

```text
1. Revert the latest slice only, not unrelated dirty worktree changes.
2. Prefer restoring the legacy wrapper body over deleting new modules mid-run.
3. Do not reset or checkout user changes.
4. Re-run the focused validation that failed.
```

## 10. Known Gaps To Track

- `xinyu_core_bridge.py` still mixes API routes, runtime calls, execution calls,
  UI/desktop presentation state, and persistence helpers.
- `xinyu_qq_gateway.py` is reduced but still mixes access, command routing,
  attachment/sticker semantics, core API calls, and transport lifecycle.
- `state_service.py` is still too thin for broad persistence ownership.
- Some existing `*_service.py` modules are helper-shaped, not full local owners.
- The current architecture diagram still shows `Core -> Runtime -> Gateway`;
  future diagrams should show `Gateway -> API -> Runtime` and no runtime-to-
  gateway dependency.
- Validation is strong for many existing slices, but every new seam still needs
  a focused test or smoke.

## 11. Execution Log

### 2026-06-05 Plan Completeness Review

Added after review:

- UI/UX layer, because Desktop/dashboard presentation should be separate from
  gateway, API, runtime, and persistence.
- Current flat-module anchors, so each layer maps to existing files without
  creating package directories.
- Boundary checklist before editing.
- Layer-specific rule of thumb.
- Validation selection by slice type.
- Compatibility and rollback pattern.
- Known gaps to track.

Result:

- The document now covers direction, terminology, target layers, dependency
  rules, current-file mapping, non-negotiables, migration phases, workflow,
  validation, first queue, success definition, compatibility, rollback, known
  gaps, and execution history.
- The remaining documentation gap is the visual architecture diagram, which
  should later be updated from `Core -> Runtime -> Gateway` to the intended
  `Gateway -> API -> Runtime` direction.

### 2026-06-05 Slice 1: Bridge App Startup Boundary

Moved:

- Extracted Bridge startup/server/shutdown orchestration into
  `xinyu_bridge_app.py`.
- Reduced `xinyu_core_bridge.py` `main()` to stdio setup, argument parsing,
  dependency wiring, and `run_bridge_app(...)`.
- Added `tests/test_bridge_app.py` to prove lifecycle wiring with fake runtime,
  desktop service, and HTTP server.

Preserved:

- CLI arguments.
- HTTP server class and request handler.
- Bridge token guard behavior.
- Desktop event stream startup/shutdown behavior.
- Existing log prefix.
- Runtime constructor arguments.

Validation:

```powershell
python -m py_compile xinyu_bridge_app.py xinyu_core_bridge.py tests\test_bridge_app.py
python -m pytest tests\test_bridge_app.py -q
git diff --check -- XinYu-Core\examples\agent-apps\xinyu\xinyu_core_bridge.py XinYu-Core\examples\agent-apps\xinyu\xinyu_bridge_app.py XinYu-Core\examples\agent-apps\xinyu\tests\test_bridge_app.py docs\plans\XINYU-MODULAR-RUNTIME-ARCHITECTURE-PLAN-2026-06-05.md
```

Result:

- Compile passed.
- Focused pytest passed: `1 passed`.
- Diff check passed; Git only reported the existing line-ending warning for
  `xinyu_core_bridge.py`.

Next slice:

- Continue thinning Bridge by extracting another low-risk wrapper group or
  route registration boundary before touching chat turn internals.

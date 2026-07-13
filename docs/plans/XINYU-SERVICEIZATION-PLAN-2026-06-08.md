# XinYu Serviceization Plan

Date: 2026-06-08
Workspace: `D:\XinYu\XinYu-Core\examples\agent-apps\xinyu`

## 1. Current State

The runtime/bridge decoupling loop reached Loop 408 with the expanded bridge
regression passing at `526 passed` and the runtime digest check returning
`missing_count 0`. The safe line-count-oriented decomposition stage is treated
as complete.

The next target is serviceization, but this does not mean immediate
microservice/process splitting. The required order remains:

```text
1. Freeze facade and compatibility contracts.
2. Define explicit local service boundaries.
3. Run service owners in-process behind narrow contracts.
4. Add health, lifecycle, retry, and rollback contracts.
5. Split processes only for boundaries that are stable locally.
```

The current bridge must continue to work as a compatibility entrypoint while
service ownership becomes visible.

## 2. Non-Negotiable Rules

- Keep public HTTP routes, QQ/OneBot payloads, and desktop DTO shapes stable.
- Preserve `XinYuBridgeRuntime` facade method names and alias object identity.
- Preserve monkeypatch seams used by focused tests.
- Keep `BRIDGE_RUNTIME_SOURCE_RELS` complete; digest checks must return
  `missing_count 0`.
- Do not inspect, rewrite, or relocate protected memory/persona bodies unless a
  task explicitly requires it.
- Do not expand v1 real traffic during serviceization.
- Do not create package-directory migrations during this plan.
- Do not split the main chat runtime, persona/memory write path, proactive core
  policy, or marker/policy modules into separate processes in the first phase.

Protected process-split modules:

```text
xinyu_bridge_slow_live_turn.py
xinyu_bridge_codex_runtime.py
xinyu_bridge_codex_policy_markers.py
xinyu_bridge_semantic_fast_pipeline.py
```

## 3. Service Domains

The executable contract manifest lives in:

```text
xinyu_serviceization_contracts.py
```

Initial local service domains:

| Service ID | Local owner | Process split status |
| --- | --- | --- |
| `chat_turn` | `ChatService + BridgeRuntimeAdapter` | Not a first-wave split candidate |
| `proactive_delivery` | `ProactiveService + QQOutboxService` | Candidate, not ready |
| `desktop_surface` | `DesktopService` | Candidate, not ready |
| `codex_execution` | `CodexService + CodexRunner` | Candidate, not ready |
| `learning_ingest` | `LearningService` | Local only for now |
| `external_action` | `ActionService + ExternalPluginService + PrivateDesktopService` | Candidate, not ready |
| `life_metabolism` | `LifeMetabolismService` | Local only for now |
| `health_diagnostics` | `HealthDiagnosticsService` | Candidate, not ready |
| `state_persistence` | `StateService` | Local consolidation only |

No contract is marked process-split-ready at plan start.

## 4. Phases

### Phase S0: Facade Freeze And Contract Manifest

Goal: make the service boundary map executable and testable without changing
runtime behavior.

Deliverables:

- `xinyu_serviceization_contracts.py`
- `tests/test_serviceization_contracts.py`
- This plan document
- Worklog entry for Loop 409

Exit criteria:

- Contract validation passes.
- Runtime digest includes the contract manifest.
- No service contract is accidentally marked split-ready.
- Current HTTP route classification covers contract API routes.

### Phase S1: Local Service Adapters

Goal: add in-process adapters for candidate domains while keeping existing
facades and route functions as wrappers.

Priority order:

1. `health_diagnostics`: lowest behavior risk, can define service health DTOs.
2. `codex_execution`: execution worker candidate, but keep runtime facade.
3. `external_action`: private desktop/browser/external plugin execution seams.
4. `proactive_delivery`: claim/ack/outbox lifecycle after idempotency is explicit.
5. `desktop_surface`: event stream can be split later; snapshot DTOs stay stable.
6. `chat_turn`: adapter only, no process split.

Exit criteria per slice:

- Service adapter has a narrow request/response contract.
- Old facade/wrapper names still exist.
- Focused tests pass.
- Worklog records owner layer, validation, risk, rollback, and remaining coupling.

### Phase S2: Health, Lifecycle, And Fallback Harness

Goal: every candidate service can be started, stopped, health-checked, and
fallen back to the current in-process path.

The executable readiness audit lives in `xinyu_serviceization_readiness.py`.

Required before any process split:

- Request/response DTO contract.
- Error taxonomy.
- Health/readiness contract.
- Lifecycle start/stop contract.
- State owner declaration.
- In-process fallback adapter.
- Single-slice rollback plan.

### Phase S3: Process Split Pilot

Goal: split exactly one low-risk execution-side service after S2 gates pass.

Preferred pilot:

```text
codex_execution or external_action
```

Deferred:

```text
QQ/NapCat gateway
main chat runtime
persona and stable memory writes
proactive core policy
v1 takeover path
```

### Phase S4: Gateway/Transport Split

Goal: make QQ/NapCat access transport independent only after the core API
contract and outbox lifecycle are stable.

Hard rules:

- No real QQ outbound is required or used as validation.
- Gateway calls API contracts, not runtime internals or raw persistence.
- Ack/claim/retry semantics must have local smoke coverage.

### Phase S5: Runtime Split

Goal: split main runtime only after service ownership, state boundaries,
health checks, and fallback adapters are proven.

This is intentionally last.

## 5. Validation Gates

Every serviceization slice uses the smallest relevant focused gate plus the
contract gate:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_serviceization_contracts.py -q
.\.venv\Scripts\python.exe -m compileall -q <changed modules>
.\.venv\Scripts\python.exe -c "from pathlib import Path; from xinyu_runtime_security import runtime_source_paths; missing=[str(p) for p in runtime_source_paths(Path('.')) if not p.exists()]; print('missing_count', len(missing)); [print(p) for p in missing]"
```

Runtime-facing or route-facing slices also run the relevant focused tests. If a
slice touches broad bridge behavior, run the expanded bridge regression used in
Loop 408.

Hard stop conditions:

- Protected memory/persona body changes.
- HTTP route payload or QQ payload shape changes without a compatibility shim.
- Facade alias identity changes unexpectedly.
- Monkeypatch seam disappears.
- Runtime digest reports a missing source.
- A process split is proposed before S2 gates exist.
- Tests fail repeatedly and the failure is not isolated to the current slice.

## 6. Automatic Execution Loop

Use this loop until serviceization is complete:

```text
1. Read the latest worklog entry.
2. Select one service boundary from xinyu_serviceization_contracts.py.
3. State layer owner, contract, state owner, validation, and rollback.
4. Implement one in-process slice only.
5. Preserve facade/wrapper/route/payload compatibility.
6. Run compile/focused tests/service contract tests.
7. Run runtime digest check.
8. Run expanded bridge regression for broad runtime or route-facing changes.
9. Append a worklog entry with result, risk, rollback, and next slice.
10. Continue only after all gates pass.
```

## 7. Rollback Pattern

- Revert only the latest serviceization slice.
- Do not touch unrelated dirty worktree changes.
- Prefer restoring old wrapper bodies over deleting new helpers mid-run.
- If a helper was added to `BRIDGE_RUNTIME_SOURCE_RELS`, remove it during
  rollback only when the helper is removed.
- For process split failures, disable the service flag and route back to the
  in-process adapter.

## 8. First Execution Queue

1. Land S0 manifest and tests.
2. Add health-diagnostics adapter contract without changing `/health` output.
3. Add Codex execution request/result contract around the existing runner.
4. Add external-action execution contract for private desktop/browser/plugin
   calls.
5. Add proactive delivery idempotency contract around claim/ack.
6. Add desktop event-stream readiness contract.
7. Reassess whether any candidate is S2-ready before process split.

## 8.1 Current Queue After Loop 420

S0/S1/S2 status:

- `health_diagnostics`, `codex_execution`, `external_action`,
  `proactive_delivery`, and `desktop_surface` now have S2 in-process
  lifecycle/readiness/fallback metadata.
- Public readiness marks those five first-wave candidates as having the generic
  S2 entry gates satisfied, while still keeping every candidate
  `process_split_ready=False`.
- `chat_turn` has local-only harness metadata and remains protected from
  first-wave process splitting.

Next execution order:

1. Harden `codex_execution` as the first S3 pilot candidate by freezing job,
   cancellation, timeout, completion outbox, and health semantics. Keep
   `/codex/execute`, `XinYuBridgeRuntime.codex_execute`, marker policy, and
   runtime facades in-process.
2. Harden `external_action` by freezing the approval/execution boundary: API
   and policy own approval; any future execution adapter performs only already
   approved work.
3. Add local-only service harnesses for `learning_ingest` and
   `life_metabolism` so surrounding modules attach to explicit owners without
   becoming process-split candidates.
4. Defer `proactive_delivery` transport work to S4. Before any QQ/NapCat split,
   freeze claim/ack DTOs, retry/dead/suppressed semantics, and the
   `proactive:*` virtual message-id branch.
5. Reassess readiness after the S3 preflight contracts pass focused and
   expanded bridge regression. Do not start a real worker process until a
   single boundary has explicit job, cancellation, health, fallback, and
   rollback coverage.

## 8.2 Current Queue After Loop 631

Status on 2026-06-12:

- The executable manifest still has 12 service contracts.
- The fixed split-ready set is:
  `codex_execution`, `desktop_event_stream`, `desktop_surface`,
  `external_action`, `health_diagnostics`, `proactive_delivery`.
- The fixed local/not-ready set is:
  `chat_turn`, `learning_ingest`, `life_metabolism`, `diagnostic_reports`,
  `memory_governance_reports`, `state_persistence`.
- `state_persistence` remains local-only and must not overlap split-ready
  module ownership.
- Adapter kind metadata is now explicit:
  - `codex_execution`: `worker_client`
  - `external_action`: `execution_backend`
  - `proactive_delivery`: `route_backend`
  - `desktop_surface`: `route_backend`
  - `health_diagnostics`: `provider_registry`
  - `desktop_event_stream`: `ws_contract_only`
- Optional adapter scaffolds exist for every non-WS split-ready seam and are
  disabled by default in `xinyu.local.env.example`.
- `health_diagnostics` additionally has a dry-run provider registry service
  harness for `/health/services/{service_id}`. It remains a
  `provider_registry` adapter, uses existing service IDs only, and does not
  replace the bridge `/health` route.
- `desktop_event_stream` is not an HTTP/backend adapter. Its websocket
  lifecycle remains app-owned; route dispatch and health/readiness metadata
  are contract guarded, but no runtime-owned websocket starter/stopper should
  be introduced implicitly.

Next execution order:

1. Treat `codex_execution` or `external_action` as the first real deployment
   pilot only through explicit env configuration and endpoint health checks.
2. Keep `proactive_delivery` and `desktop_surface` route-backend adapters
   optional and disabled by default until an external worker/server process is
   provided.
3. Keep `health_diagnostics` provider-registry split behind explicit runtime
   injection or a deliberate config wiring slice.
4. Do not split `desktop_event_stream` until there is a separate websocket
   service design covering lifecycle ownership, replay cursors, auth, and
   rollback.
5. Continue to defer QQ/NapCat gateway, main chat runtime, persona/memory
   writes, and state persistence process splits.

## 9. Success Definition

Serviceization is succeeding when new feature work attaches to a named local
service owner, route facades stay thin, state writes are easier to audit,
facade compatibility tests remain stable, and a future process split becomes an
operational deployment choice instead of a rescue refactor.

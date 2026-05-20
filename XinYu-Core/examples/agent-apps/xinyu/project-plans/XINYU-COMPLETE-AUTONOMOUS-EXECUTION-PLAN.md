# XinYu Complete Autonomous Execution Plan

Date: 2026-05-20

Purpose: this document is the execution contract for Codex to keep working on XinYu until the project reaches the defined completion criteria. It is not a brainstorming note. A future Codex session should be able to open this file, pick the next unchecked item, implement it, verify it, update this file, and continue.

## 0. Completion Definition

XinYu is "done" for this plan when it is a reliable local long-running personal AI agent system with:

- stable QQ/NapCat -> gateway -> core message handling;
- observable turn lifecycle from message receipt to route, memory, model, reply, archive, and failure;
- owner intervention controls for stale or running turns;
- bounded memory writes with reviewable provenance;
- stable expression behavior for core owner-private scenarios;
- controlled and auditable proactive behavior;
- reproducible failure scenarios and regression tests;
- a local inspector/dashboard or CLI sufficient for operation;
- public documentation that explains the architecture, privacy boundary, and research artifacts.

This plan does not require XinYu to become a public SaaS product, a hosted multi-user bot, or a fully autonomous system without owner control.

## 1. Codex Autonomous Work Loop

Every Codex session must follow this loop.

### 1.1 Start Loop

1. Read this file first.
2. Run a quick status check:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
git status --short
```

3. Identify the first unchecked task in the highest-priority phase that is not blocked.
4. Inspect only the files needed for that task.
5. Implement the smallest coherent slice.
6. Add or update focused tests for that slice.
7. Run the smallest relevant verification gate.
8. If verification passes, update this file:
   - mark the task complete;
   - add a one-line evidence note with command/result;
   - add any new follow-up task discovered.
9. Continue to the next unchecked task in the same session until one of the stop conditions is reached.

### 1.2 Stop Conditions

Do not stop after analysis only. Stop only when:

- all tasks in this plan are complete;
- a required secret, account, credential, or owner decision is needed;
- a verification failure cannot be resolved without risking unrelated user changes;
- the live runtime must be manually checked by the owner;
- the current turn is interrupted by a newer user request.

If stopped, leave a short handoff note in the final response naming the next unchecked task and current verification state.

### 1.3 Safety Rules

- Do not revert user changes or unrelated dirty files.
- Do not add canned visible replies as a substitute for root-cause fixes.
- Keep QQ gateway as transport only; personality, memory, and action decisions belong in core.
- Do not expose private QQ ids, private memory, tokens, or raw owner chat in public artifacts.
- Prefer structured trace/state over ad hoc log-only diagnostics.
- Preserve visible behavior unless a task explicitly changes it.
- Use focused tests for each slice; broaden tests only when shared contracts change.

### 1.4 Verification Gates

Use the smallest relevant gate first.

Core bridge focused gate:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
python -m py_compile xinyu_core_bridge.py xinyu_bridge_turn_pipeline.py xinyu_bridge_semantic_fast_routes.py xinyu_turn_route_trace.py
.\.venv\Scripts\python.exe -m pytest tests\test_dialogue_curiosity_bridge_injection.py -k "semantic_fast or pre_model_routes_timeout or turn_finish_sidecars" -q
```

QQ focused gate:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe tests\smoke\qq\integration\xinyu_qq_gateway_smoke.py
```

v1 focused gate:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe -m pytest tests\v1 -q
```

Runtime health gate:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe xinyu_status.py --json
```

Full gate, used before major handoff or release:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe tests\smoke\runtime\integration\runtime_readiness_smoke.py
.\.venv\Scripts\python.exe tests\smoke\qq\integration\xinyu_qq_gateway_smoke.py
```

## 2. Phase A: Runtime Observability And Timeout Containment

Goal: no turn should disappear behind "replying" without a precise route/stage state.

### Tasks

- [x] Add turn route trace files and health summary.
  - Evidence: `xinyu_turn_route_trace.py`, health `turn_route`; focused tests passed in prior session.
- [x] Move owner-private low-risk semantic fast route before heavy pre-model routes.
  - Evidence: semantic fast greeting test prevents `run_pre_model_routes` from being called first.
- [x] Add pre-model route timeout containment.
  - Evidence: `pre_model_routes_timeout` test passes; health exposes `pre_model_routes_timeout_seconds`.
- [x] Add trace stages around slow live memory recall:
  - `memory_recall_started`
  - `memory_recall_finished`
  - `memory_recall_timeout`
  - `memory_recall_error`
  - Evidence: `python -m py_compile ...` passed; `pytest tests\test_dialogue_curiosity_bridge_injection.py -k "semantic_fast or pre_model_routes_timeout or turn_finish_sidecars or memory_recall" -q` passed with 8 selected tests.
- [x] Add trace stages around model event injection:
  - `model_inject_started`
  - `model_inject_finished`
  - `model_inject_timeout`
  - `model_inject_error`
  - Evidence: `python -m py_compile ...` passed; `pytest tests\test_dialogue_curiosity_bridge_injection.py -k "semantic_fast or pre_model_routes_timeout or turn_finish_sidecars or memory_recall or model_inject" -q` passed with 10 selected tests.
- [x] Add trace stages around outward renderer:
  - `outward_renderer_started`
  - `outward_renderer_finished`
  - `outward_renderer_timeout`
  - `outward_renderer_error`
  - Evidence: `python -m py_compile ...` passed; `pytest tests\test_dialogue_curiosity_bridge_injection.py -k "semantic_fast or pre_model_routes_timeout or turn_finish_sidecars or memory_recall or model_inject or outward_renderer" -q` passed with 13 selected tests.
- [x] Add trace stages around slow turn finish sidecars:
  - `finish_sidecars_started`
  - `finish_sidecars_finished`
  - `finish_sidecars_timeout`
  - `finish_sidecars_error`
  - Evidence: `python -m py_compile ...` passed; `pytest tests\test_dialogue_curiosity_bridge_injection.py -k "semantic_fast or pre_model_routes_timeout or turn_finish_sidecars or memory_recall or model_inject or outward_renderer or finish_sidecars" -q` passed with 15 selected tests.
- [x] Add health fields for current turn age, route stage, route status, stale age, and last timeout reason in one compact operator section.
  - Evidence: `health_snapshot()["operator"]` covers current turn age, route stage/status, stale age, and last timeout reason; focused health operator test passed.
- [x] Add focused tests that a simulated slow live timeout records route trace before returning or raising.
  - Evidence: model injection timeout test asserts `model_inject_timeout` trace and health operator timeout fields before the bridge raises 504; focused gate passed with 16 selected tests.

### Acceptance

- For any stalled turn, `/health` and `runtime/turn_route_trace.jsonl` show the last reached stage.
- No observed live turn remains only at `turn_started` unless it is truly before the first traced step.
- Timeout is recorded in trace/state before gateway fallback.

## 3. Phase B: Thin `xinyu_core_bridge.py`

Goal: reduce core bridge risk by moving bounded responsibilities into modules without changing behavior.

### Tasks

- [x] Extract semantic fast route into `xinyu_bridge_semantic_fast_routes.py`.
- [x] Extract slow turn finish sidecars into `xinyu_bridge_turn_finish_sidecars.py`.
- [x] Extract slow live turn orchestration into `xinyu_bridge_slow_live_turn.py`.
  - Evidence: slow-live memory recall, model context preparation, model event injection, and finish sidecar trace wrapper moved into `xinyu_bridge_slow_live_turn.py`; focused gate passed with 43 selected tests.
- [x] Extract route tracing helper/wrapper into `xinyu_bridge_route_observer.py`.
  - Evidence: `xinyu_bridge_route_observer.py` added and `chat()` uses `TurnRouteObserver`; `pytest tests\test_bridge_route_observer.py tests\test_dialogue_curiosity_bridge_injection.py -k "route_observer or semantic_fast or pre_model_routes_timeout or turn_finish_sidecars or memory_recall or model_inject or outward_renderer or finish_sidecars or health_operator" -q` passed with 17 selected tests.
- [x] Extract pre-model timeout wrapper into `xinyu_bridge_pre_model_runtime.py` or fold cleanly into `xinyu_bridge_turn_pipeline.py`.
  - Evidence: `run_pre_model_routes_with_timeout` folded into `xinyu_bridge_turn_pipeline.py`; `pytest tests\test_bridge_route_observer.py tests\test_bridge_turn_pipeline_pre_model_runtime.py tests\test_dialogue_curiosity_bridge_injection.py -k "route_observer or pre_model or semantic_fast or turn_finish_sidecars or memory_recall or model_inject or outward_renderer or finish_sidecars or health_operator" -q` passed with 20 selected tests.
- [x] Extract reply rendering/recovery path into `xinyu_bridge_reply_pipeline.py`.
  - Evidence: `xinyu_bridge_reply_pipeline.py` owns renderer trace wrapper and empty visible reply recovery; `pytest tests\test_bridge_reply_pipeline.py tests\test_bridge_route_observer.py tests\test_bridge_turn_pipeline_pre_model_runtime.py tests\test_dialogue_curiosity_bridge_injection.py -k "reply_pipeline or empty_visible_reply or route_observer or pre_model or semantic_fast or turn_finish_sidecars or memory_recall or model_inject or outward_renderer or finish_sidecars or health_operator" -q` passed with 28 selected tests.
- [x] Remove now-unused imports from `xinyu_core_bridge.py` after each extraction.
  - Evidence: removed imports superseded by sidecar/reply/slow-live modules; `python -m py_compile ...` and focused bridge/module tests passed.
- [x] Add module-level tests for each extracted module.
  - Evidence: added/kept module-focused tests for semantic fast routes, route observer, pre-model runtime wrapper, reply pipeline, slow-live helpers, and finish sidecars; focused gate passed with 43 selected tests.

### Acceptance

- `XinYuBridgeRuntime.chat()` becomes a readable top-level orchestration function.
- Extracted modules own their tests.
- Existing QQ visible behavior remains unchanged.
- Focused bridge and QQ smoke gates pass after every extraction.

## 4. Phase C: Owner Intervention API

Goal: owner can inspect and recover stale/running turns without restarting the whole runtime.

### Tasks

- [x] Add read-only `GET /turn/current`.
- [x] Add `POST /turn/cancel` for stale/running turn cancellation.
- [x] Add `POST /turn/retry-lightweight` for semantic fast retry when safe.
- [x] Add `POST /turn/skip-sidecar` for timed-out optional sidecars.
- [x] Add `POST /turn/continue` to continue slow live after contained timeout.
- [x] Add `POST /turn/status-message` that emits safe operational status without chain-of-thought.
- [x] Add `xinyu_bridge_intervention_routes.py`.
- [x] Add `tests/test_turn_intervention_routes.py`.
- [x] Add trace events for every intervention:
  - `intervention_requested`
  - `intervention_applied`
  - `intervention_rejected`
  - Evidence: intervention module and HTTP routes added; `pytest tests\test_turn_intervention_routes.py ... -q` passed in focused gate with 53 selected tests.

### Acceptance

- A stale turn can be inspected and marked canceled.
- Intervention actions never expose private message content or hidden reasoning.
- Intervention actions do not write false long-term memory.
- Tests cover allowed, rejected, and stale/no-current-turn cases.

## 5. Phase D: Failure Scenario Harness

Goal: regressions are caught through reproducible scenarios, not manual log reading.

### Tasks

- [x] Create `failure-scenarios/README.md`.
- [x] Define scenario schema:
  - input payload
  - expected trace stages
  - expected health state
  - expected visible behavior
  - expected memory impact
  - recovery action
- [x] Add scenario: owner private greeting fast route.
- [x] Add scenario: stuck before route decision.
- [x] Add scenario: pre-model timeout containment.
- [x] Add scenario: model injection timeout.
- [x] Add scenario: renderer empty reply recovery.
- [x] Add scenario: stale running cancellation.
- [x] Add scenario: proactive conflict with live reply.
- [x] Implement `tests/failure_scenarios/test_failure_scenarios.py` or smoke runner.
- [x] Generate sanitized trace examples from scenarios for public evidence.
  - Evidence: `failure-scenarios/scenarios/*.json`, sanitized trace examples, and schema/privacy runner added; focused gate passed with 57 selected tests.

### Acceptance

- Scenario runner can run without private QQ account data.
- Each scenario asserts trace, response, health, and memory side effects.
- Grant/research artifacts can cite sanitized scenario outputs.

## 6. Phase E: Memory Write Boundary And Review

Goal: XinYu remembers deliberately, not just frequently.

### Tasks

- [x] Document memory layers in `MEMORY-LAYERS.md`:
  - runtime trace
  - dialogue tail
  - event sourcing
  - candidate memory
  - approved long-term memory
  - seed memory
- [x] Add candidate provenance fields where missing:
  - source turn id
  - source message ids
  - extraction reason
  - risk flags
- [x] Add memory candidate review CLI:
  - list
  - show
  - approve
  - reject
  - explain
- [x] Add tests that runtime traces and temporary timeout notes cannot become approved memory directly.
- [x] Add high-risk memory gate for relationship/personality-changing candidates.
- [x] Add public `PRIVACY-BOUNDARY.md`.
  - Evidence: `MEMORY-LAYERS.md`, `PRIVACY-BOUNDARY.md`, provenance columns, `xinyu_memory_candidate_review_cli.py`, and focused tests added; focused gate passed with 61 selected tests.

### Acceptance

- Every durable memory candidate can explain where it came from.
- Owner can reject or approve high-risk memory.
- Temporary operational failures do not become long-term memory.

## 7. Phase F: Expression Stability

Goal: stable owner-private expression without template patching.

### Tasks

- [x] Define expression scenario set:
  - greeting
  - acknowledgement
  - fatigue
  - anger/blame
  - technical request
  - uncertainty/waiting
  - proactive response
- [x] Add tests for no canned fallback in ordinary owner-private chat.
- [x] Add tests for empty visible reply recovery through renderer/retry path only.
- [x] Separate intent, stance, and surface expression in docs or code where practical.
- [x] Add final reply guard trace notes for major rewrites.
- [x] Add English/Japanese runtime intent recognition only after Chinese stability tests are green.
  - Evidence: `expression-scenarios/scenarios.json`, `EXPRESSION-STABILITY.md`, `final_reply_guard_rewrite` trace, and English/Japanese classifier tests added; focused gate passed with 70 selected tests.

### Acceptance

- Common owner-private turns do not regress to customer-service tone.
- Empty reply is recovered by model/rendering path, not template.
- Expression changes are testable and traceable.

## 8. Phase G: Controlled Proactivity

Goal: XinYu may initiate contact only with clear reason, risk, and owner control.

### Tasks

- [x] Audit proactive candidate schema for:
  - reason
  - urgency
  - risk
  - owner relevance
  - channel
  - expiration
- [x] Add proactive cooldown checks where missing.
- [x] Ensure owner reply closes proactive state correctly.
- [x] Add trace for proactive candidate lifecycle.
- [x] Add scenario: proactive candidate collides with live owner reply.
- [x] Add tests for claim/ack failure and retry behavior.

### Evidence

- Added `xinyu_proactive_lifecycle_trace.py`.
- Added controlled proactive lifecycle tests in `tests/test_proactive_controlled_lifecycle.py`.
- Verified: `python -m py_compile xinyu_proactive_lifecycle_trace.py xinyu_proactive_request_loop.py xinyu_proactive_presence.py xinyu_core_bridge.py tests\test_proactive_controlled_lifecycle.py`.
- Verified: `.\.venv\Scripts\python.exe -m pytest tests\test_proactive_controlled_lifecycle.py -q`.
- Verified: `.\.venv\Scripts\python.exe -m pytest tests\test_proactive_controlled_lifecycle.py tests\test_initiative_orchestrator.py tests\test_dialogue_curiosity_bridge_injection.py -k "proactive or initiative or owner_reply or failed_proactive or retry or lifecycle" -q`.
- Verified: `.\.venv\Scripts\python.exe tests\smoke\initiative\proactive_presence_smoke.py`.
- Verified: `.\.venv\Scripts\python.exe tests\smoke\initiative\proactive_request_loop_smoke.py`.
- Verified: `.\.venv\Scripts\python.exe tests\smoke\desktop\xinyu_desktop_proactive_smoke.py`.

### Acceptance

- Proactive messages are explainable and auditable.
- Failed proactive sends do not pollute live turn state.
- Owner can see why a proactive message exists.

## 9. Phase H: Local Inspector / Dashboard

Goal: owner should not need to read raw JSONL for normal operation.

### Tasks

- [x] Build CLI inspector first:
  - current turn
  - route timeline
  - gateway connection
  - proactive state
  - memory candidate count
  - stale warnings
- [x] Add CLI intervention commands after Phase C exists.
- [x] Add minimal local dashboard only after CLI is stable.
- [x] Ensure default view hides private message content.
- [x] Add screenshot/demo notes for public grant evidence.

### Evidence

- Added `xinyu_local_inspector.py` with local summary, route timeline, gateway/proactive/memory counts, stale warnings, dashboard generation, and `/turn/*` intervention commands.
- Added `LOCAL-INSPECTOR-DEMO.md`.
- Added privacy-focused tests in `tests/test_xinyu_local_inspector.py`.
- Verified: `python -m py_compile xinyu_local_inspector.py tests\test_xinyu_local_inspector.py`.
- Verified: `.\.venv\Scripts\python.exe -m pytest tests\test_xinyu_local_inspector.py -q`.
- Verified: `.\.venv\Scripts\python.exe -m pytest tests\test_xinyu_local_inspector.py tests\test_turn_intervention_routes.py tests\test_proactive_controlled_lifecycle.py tests\test_dialogue_curiosity_bridge_injection.py -k "local_inspector or turn_ or proactive or health_operator or owner_reply" -q`.
- Verified real local read: `.\.venv\Scripts\python.exe xinyu_local_inspector.py --no-network --json`.

### Acceptance

- Owner can answer "why is it not replying?" from inspector output.
- Owner can trigger safe intervention without editing files.
- Public demo can show status without private data.

## 10. Phase I: Public Research Package

Goal: make XinYu understandable and reproducible as an interactivity research artifact.

### Tasks

- [x] Add `INTERACTIVITY-RESEARCH.md`.
- [x] Add `TRACE-SCHEMA.md`.
- [x] Add `FAILURE-SCENARIOS.md` or link to scenario folder.
- [x] Update architecture diagram after intervention API exists.
- [x] Keep README language links synchronized.
- [x] Add sanitized trace example generated from scenario runner.
- [x] Add final grant progress report template.

### Evidence

- Added `INTERACTIVITY-RESEARCH.md`, `TRACE-SCHEMA.md`, `FAILURE-SCENARIOS.md`, `ARCHITECTURE.md`, and `GRANT-PROGRESS-REPORT-TEMPLATE.md`.
- Added `README.en.md`, `README.ja.md`, and README language/research links.
- Added `failure-scenarios/generate_sanitized_trace_examples.py` and regenerated `failure-scenarios/examples/sanitized_trace_examples.jsonl`.
- Added `tests/test_public_research_package.py`.
- Verified: `python -m py_compile failure-scenarios\generate_sanitized_trace_examples.py tests\test_public_research_package.py`.
- Verified: `.\.venv\Scripts\python.exe failure-scenarios\generate_sanitized_trace_examples.py --check`.
- Verified: `.\.venv\Scripts\python.exe -m pytest tests\test_public_research_package.py tests\failure_scenarios\test_failure_scenarios.py -q`.

### Acceptance

- External reviewer can understand XinYu in 10 minutes.
- Research artifacts do not leak private owner data.
- Repo clearly separates runtime product code from research evidence.

## 11. Current Next Task

Autonomous execution status: all tasks in this plan are checked and have focused evidence above.

Current next task: none inside this plan. Treat future work as a new iteration plan unless a regression is found.

Final closure update, 2026-05-21:

- Supplemental regression commits after the original plan closure:
  - `7446b0a fix(xinyu): keep personal state chat out of runtime context`
  - `2edb7e2 fix(xinyu): replace stale failover replies in private chat`
  - `6c87a6a fix(xinyu): retry transient core chat disconnects`
  - `69b98ef chore(xinyu): ignore local external plugin control`
  - `e128c6a fix(xinyu): avoid bare ack in owner life chat`
- Current worktree before this note: clean.
- Runtime status after restart: `xinyu_status.py --json` reported `ok=true`, `bridge_restart_required=false`, `runtime_restart_required=false`, `gateway_restart_may_be_needed=false`.

Final focused gate:

- `python -m py_compile xinyu_proactive_lifecycle_trace.py xinyu_proactive_request_loop.py xinyu_proactive_presence.py xinyu_core_bridge.py xinyu_local_inspector.py failure-scenarios\generate_sanitized_trace_examples.py tests\test_proactive_controlled_lifecycle.py tests\test_xinyu_local_inspector.py tests\test_public_research_package.py`
- `.\.venv\Scripts\python.exe -m pytest tests\test_public_research_package.py tests\test_xinyu_local_inspector.py tests\test_proactive_controlled_lifecycle.py tests\test_expression_scenarios.py tests\v1\test_hybrid_router.py tests\test_memory_candidate_review_cli.py tests\failure_scenarios\test_failure_scenarios.py tests\test_turn_intervention_routes.py tests\test_bridge_semantic_fast_routes.py tests\test_bridge_slow_live_turn.py tests\test_bridge_reply_pipeline.py tests\test_bridge_route_observer.py tests\test_bridge_turn_pipeline_pre_model_runtime.py tests\test_dialogue_curiosity_bridge_injection.py -k "public_research or local_inspector or proactive or expression or greeting or relationship_pressure or memory_candidate or failure_scenario or turn_ or semantic_fast or slow_live_turn or memory_recall or model_inject or reply_pipeline or empty_visible_reply or route_observer or pre_model or turn_finish_sidecars or outward_renderer or finish_sidecars or health_operator or final_reply_guard or owner_reply" -q`

Result: `86 passed, 39 deselected`.

Extended closure gate:

- `git diff --check`
  - Result: no whitespace errors.
- `.\.venv\Scripts\python.exe -m pytest tests -q`
  - Result: `759 passed`.
- `.\.venv\Scripts\python.exe tests\smoke\runtime\integration\runtime_readiness_smoke.py --timeout-seconds 240 --json`
  - Result: `ok=true`; all subcommands exited `0`.
- `.\.venv\Scripts\python.exe tests\smoke\qq\integration\xinyu_qq_gateway_smoke.py`
  - Result: `xinyu_qq_gateway_smoke: ok`.

# Claude Execution Dossier: XinYu Autonomy Recovery And Desktop Excellence

created_at: 2026-05-31
owner: Atimea
director: Codex
executor: Claude
repository: D:\XinYu
primary_app: D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
desktop_app: D:\XinYu\XinYu_Desktop
mode: execution-grade engineering dossier

## 0. Executive Mandate

This dossier is for Claude. Treat it as the execution contract for the next autonomy and desktop-quality pass.

The final target is not performative personality, random unsolicited messages, or a claim of consciousness. The target is a bounded, owner-authorized, auditable self-generating autonomy loop that can eventually initiate external exploration and proactive outbound messages when the system has a real internal gap, a valid reason, an explicit gate decision, an allowed channel, and a feedback path:

```text
external/internal input
-> importance and anomaly judgment
-> internal state, need, and gap
-> candidate intentions and candidate actions
-> gates, boundaries, and priority arbitration
-> bounded action, including external exploration or proactive outbound messaging when authorized
-> action result and environmental feedback
-> memory, scoring, strategy, and expression update
-> measurably different future behavior
```

The autonomy end-state must include:

1. Self-initiated external exploration: XinYu can notice a concrete knowledge gap, propose or run a bounded search/local probe/tool action, retain source/evidence anchors, and convert results into strategy or future behavior without inventing facts.
2. Self-initiated proactive messaging: XinYu can decide that a message should be surfaced to the owner, explain why it should be sent or held, pass channel/risk/cooldown/owner-authorization gates, deliver through Desktop or QQ outbox when allowed, observe ack or non-response, and update future scoring.
3. Self-restraint: XinYu can decide not to explore and not to send, with an auditable reason, rather than failing silently or pretending autonomy.

Every change must strengthen one segment of this loop or improve the operator's ability to inspect and govern that loop. If a change only makes XinYu "sound autonomous", reject it.

## 1. Non-Negotiable Constraints

1. Do not bypass owner authorization, QQ outbox claim/ack semantics, stable-memory review, local safety boundaries, or explicit runtime gates.
2. Do not promote runtime trial bias into stable memory without explicit owner apply.
3. Do not write raw private owner text, raw visible reply text, raw local paths, tokens, cookies, API keys, or QQ payload bodies into reports, worklogs, or UI-visible state.
4. Do not claim consciousness, biological embodiment, fake sensors, fake physiology, or unbounded agency.
5. Do not use destructive Git commands. The worktree is dirty and contains user/Codex work in progress.
6. Do not broadly reformat, rename, or relocate files unless the operation is part of a narrowly scoped fix.
7. Do not weaken a gate to make a report green. Fix the underlying state, test fixture, runtime service, or report interpretation.
8. Do not add a new frontend framework or design system. Use the existing Electron, React, TypeScript, Vite, and lucide-react stack.

## 2. Current Verified State

Codex inspection on 2026-05-31 found the following.

### 2.1 Runtime Status

`python xinyu_status.py --json` returned `ok=false` because the live runtime stack was not online:

- `core_bridge`: failed, connection refused.
- `xinyu_qq_gateway_6199`: failed, TCP connect refused.
- `napcat_webui_6099`: failed, TCP connect refused.
- `napcat_to_xinyu_qq_gateway_ws`: failed, no established local connection.

Many autonomy subreports are green from local state, but the live autonomy claim must be evaluated from freshly rerun reports, not stale status fields.

### 2.2 Autonomy Evidence Already Exists

The project already has substantial autonomy-loop infrastructure:

- `xinyu_perception_event_layer.py`
- `xinyu_perception_importance.py`
- `xinyu_attention_posture.py`
- `xinyu_relation_posture.py`
- `xinyu_intention_ecology.py`
- `xinyu_decision_chain_latest.py`
- `xinyu_action_feedback_surface.py`
- `xinyu_action_feedback_coverage.py`
- `xinyu_owner_feedback_effects.py`
- `xinyu_feedback_consumption_diagnostics.py`
- `xinyu_autonomy_loop_report.py`
- `xinyu_stage8_memory_review_packet.py`
- `xinyu_stage9_self_state_model.py`
- `xinyu_stage10_proactive_life_loop.py`
- `xinyu_stage11_multisensory_extension.py`
- `xinyu_stage12_long_term_evaluation.py`
- `xinyu_stage13_self_narrative.py`

The key design is already present: candidates are scored, gates are explicit, feedback is consumed, silence can be represented as a decision, and stable memory is gated.

### 2.3 Fresh Stage Reports

Fresh reruns during Codex inspection produced this state:

- `xinyu_feedback_consumption_diagnostics.py --json`: `status=pass`, `199/199` auditable feedback samples consumed, `stage7_ready_for_stage8=true`.
- `xinyu_stage8_memory_review_packet.py --json`: `packet_status=ready_for_owner_review`, `owner_review_required_count=2`, `duplicate_cluster_count=1`, stable memory blocked.
- `xinyu_stage12_long_term_evaluation.py --json --no-live-status`: `status=active_needs_check`, `ready_for_stage13=false`, because live-loop required checks did not all pass.
- `xinyu_stage13_self_narrative.py --json`: `status=waiting_for_stage12`, `available=false`.

Therefore, the current engineering truth is:

```text
Core loop mechanics: substantially implemented.
Live long-running autonomy: not currently green.
Stage 13 evidence narrative: blocked by Stage 12.
Stable memory governance: intentionally blocked pending owner review and duplicate consolidation.
```

### 2.4 Focused Test Result

Codex ran the focused autonomy suite:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe -m pytest -q tests/test_intention_ecology.py tests/test_autonomy_loop_report.py tests/test_feedback_consumption_diagnostics.py tests/test_stage8_memory_review_packet.py tests/test_stage8_learning_trial_validation_packet.py tests/test_stage9_self_state_model.py tests/test_stage10_proactive_life_loop.py tests/test_stage11_multisensory_extension.py tests/test_stage12_long_term_evaluation.py tests/test_stage13_self_narrative.py tests/test_owner_feedback_effects.py tests/test_proactive_direct_sender.py
```

Result:

```text
92 passed in 4.43s
```

The code path is not trivially broken. The blocking issues are primarily runtime availability, governance state, backlog resolution, and UI/operator quality.

### 2.5 Repository Governance State

The repository is currently not governance-clean.

- Git branch: `master...origin/master`, ahead by 2 commits.
- Worktree: 332 changed entries.
- Modified: 119.
- Deleted: 50.
- Untracked: 163.
- Understand graph: missing.
- Repowise state: missing; `repowise init` failed because it detected nested repositories and required interactive selection.
- Sentrux rules: missing.
- Sentrux baseline: missing.
- Code-intel hospital status: red, primarily due local tool / graph / governance failures.

Do not treat the repository as release-ready until the worktree and governance baseline are stabilized.

## 3. Autonomy Distance Assessment

Use this as the working estimate:

```text
Autonomy-loop implementation maturity: 75-80%.
Operational long-running autonomy readiness: 60-65%.
Remaining distance: 25-35%, concentrated in runtime availability, Stage8 governance, Stage12/13 live gates, frontend observability, and repository governance.
```

This is not a "build a personality" gap. It is an engineering closure gap.

## 4. Primary Problem Taxonomy

### P0-A: Live Runtime Is Not Currently Online

Problem:

The status command reports the core bridge, QQ gateway, NapCat web UI, and gateway WebSocket connection as unavailable. Stage12 cannot be considered ready while live-loop runtime checks fail.

Required outcome:

`xinyu_status.py --json` must return `ok=true`, or every failed runtime check must be intentionally accepted as a documented offline-mode exception. For autonomy readiness, prefer the real online stack.

Execution approach:

1. Start the stack using the repository-owned launchers.
2. Verify ports and health.
3. Rerun status and Stage12.
4. Confirm fresh reports, not stale state files.

Commands:

```powershell
cd D:\XinYu
powershell -NoProfile -ExecutionPolicy Bypass -File .\XinYu.ps1 status
powershell -NoProfile -ExecutionPolicy Bypass -File .\XinYu.ps1 start desktop
powershell -NoProfile -ExecutionPolicy Bypass -File .\XinYu.ps1 verify qq
```

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe xinyu_status.py --json
.\.venv\Scripts\python.exe xinyu_autonomy_loop_report.py --root . --json
.\.venv\Scripts\python.exe xinyu_stage12_long_term_evaluation.py --root . --json
.\.venv\Scripts\python.exe xinyu_stage13_self_narrative.py --root . --json
```

Acceptance criteria:

- Core bridge reachable.
- QQ gateway reachable.
- NapCat reachable or explicitly documented as intentionally offline.
- Gateway WebSocket connected when QQ live loop is in scope.
- Latest private input, dispatch, visible reply, QQ ack, and shadow guard are all coherent in `xinyu_autonomy_loop_report.py`.
- Stage12 fresh rerun reports `ready_for_stage13=true`.
- Stage13 fresh rerun reports `active_available_for_self_narrative`.

### P0-B: Stage12/Stage13 Must Be Freshly Truthful

Problem:

Some aggregate status fields can look green from prior state, while fresh Stage12 and Stage13 reruns show the actual gate is not currently satisfied. This creates a stale-readiness risk.

Required outcome:

Stage12 and Stage13 must derive readiness from current live-loop evidence and current diagnostics, not stale status-field optimism.

Execution approach:

1. Compare `xinyu_status.py --json` fields with fresh direct Stage12/13 report output.
2. If inconsistent, fix the status aggregation path so it does not overstate readiness.
3. Add or update regression tests for stale readiness.
4. Ensure status explains which specific gate is failing.

Likely files:

- `xinyu_status.py`
- `xinyu_stage12_long_term_evaluation.py`
- `xinyu_stage13_self_narrative.py`
- `xinyu_autonomy_loop_report.py`
- `tests/test_stage12_long_term_evaluation.py`
- `tests/test_stage13_self_narrative.py`

Acceptance criteria:

- `xinyu_status.py`, Stage12 direct report, and Stage13 direct report agree on readiness.
- If live loop is offline, Stage12 must not present as ready.
- Stage13 must remain `waiting_for_stage12` unless Stage12 is freshly ready.
- Failure details must name the failing gate, not only say `needs_check`.

### P0-C: Stage8 Memory Governance Backlog Blocks Stable Autonomy

Problem:

Stage8 currently has owner-review memory candidates and a duplicate cluster. Stable memory is correctly blocked, but this means the system is still in guarded governance rather than stable long-term self-update.

Current observed state:

- Owner review required: 2.
- Duplicate cluster backlog: 1.
- Candidate inventory: 399.
- Stable memory write: blocked.
- Stable identity profile apply: blocked.

Required outcome:

Resolve or explicitly defer the Stage8 backlog without weakening gates.

Execution approach:

1. Generate a fresh Stage8 memory review packet.
2. Present owner-review items without raw private text.
3. Record owner decisions as review decisions only.
4. Consolidate duplicate clusters after owner review is clear.
5. Rerun Stage8, Stage9, Stage12, and Stage13.

Commands:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe xinyu_stage8_memory_review_packet.py --root . --json
.\.venv\Scripts\python.exe xinyu_stage8_learning_trial_validation_packet.py --root . --json
.\.venv\Scripts\python.exe xinyu_memory_health_report.py --root . --json
```

Acceptance criteria:

- Owner-review queue is either cleared or explicitly documented as a remaining owner decision.
- Duplicate candidate cluster is consolidated or explicitly deferred.
- No raw owner text appears in packets, state, trace, or desktop UI.
- Stable memory remains blocked unless the owner explicitly applies a reviewed candidate.
- Stage8 state explains the next action in operator-readable language.

### P1-A: Code Intelligence Governance Is Missing

Problem:

The repository lacks a current architecture graph, Repowise state, and Sentrux governance baseline/rules. This makes future refactors harder to trust.

Required outcome:

Create a stable local governance surface for future Claude/Codex work.

Execution approach:

1. Refresh the Understand graph from Claude-side tooling.
2. Initialize Repowise in a scoped way that avoids nested third-party repositories.
3. Create Sentrux rules for the governed scope.
4. Create an intentional Sentrux baseline only after confirming it does not hide real regressions.

Commands:

```text
/understand D:\XinYu --language zh
```

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File D:\projects\_tools\code-intel-pipeline\invoke-code-intel.ps1 -RepoPath D:\XinYu -Mode normal
```

Recommended governance scope:

```text
D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
D:\XinYu\XinYu_Desktop
D:\XinYu\docs
```

Avoid indexing or governing vendored/runtime dependency directories as first-class source.

Acceptance criteria:

- Understand graph exists and is fresh.
- Repowise is initialized without prompting for nested repos.
- `.sentrux/rules.toml` exists for the chosen scope.
- `.sentrux/baseline.json` exists only after review.
- Code-intel summary has zero failure-category counters or documented accepted exceptions.

### P1-B: Worktree Hygiene Is Unsafe For Large Changes

Problem:

The worktree has 332 changed entries. This increases merge risk, hides ownership, and makes regression attribution difficult.

Required outcome:

Before large implementation work, separate active owner work from the new Claude task.

Execution approach:

1. Do not revert anything.
2. Produce a worktree inventory grouped by subsystem.
3. Identify files required for this task.
4. Avoid touching unrelated dirty files.
5. If a required file is already modified, inspect before editing and preserve user changes.

Commands:

```powershell
cd D:\XinYu
git status --short --branch
git diff --stat
```

Acceptance criteria:

- Claude reports which dirty files it touched.
- No unrelated deletions are restored or committed.
- No broad formatting churn.
- Verification commands are run after the scoped changes.

### P0-D: Active External Exploration And Proactive Messaging Are Not Yet A Fully Proven Live Capability

Problem:

The repository has the building blocks for initiative, proactive presence, QQ outbox delivery, action feedback, owner response diagnostics, and bounded local actions. However, the current inspected state does not yet prove a complete live cycle where XinYu independently forms an external-exploration need or proactive-message need, passes gates, performs or queues the action, receives ack/non-response, and updates future scoring from that outcome.

This is the owner's intended meaning of autonomy. Treat it as a first-class target, not a cosmetic extension.

Required outcome:

XinYu must be able to perform two governed initiative loops:

1. External exploration loop.
2. Proactive outbound-message loop.

External exploration loop:

```text
perceived gap or curiosity pressure
-> candidate exploration objective
-> source/tool/channel risk classification
-> owner/local permission gate
-> bounded search, local probe, code/status probe, or approved tool action
-> result capture with source anchors
-> hallucination/privacy/source-license guard
-> memory candidate, strategy update, or next-action bias
```

Proactive outbound-message loop:

```text
internal gap, owner-relevant event, or completed task residue
-> candidate message
-> value/risk/cooldown/channel gate
-> Desktop inbox preview or QQ outbox queue
-> claim/ack or explicit hold/dismiss/reply
-> owner response or non-response diagnostic
-> future scoring and expression strategy update
```

Execution approach:

1. Inventory current initiative and proactive surfaces.
2. Identify the exact gate that converts internal pressure into external exploration or owner-visible proactive message.
3. Preserve the distinction between `candidate`, `preview`, `queued`, `sent`, `acked`, `dismissed`, `timed_out`, and `blocked`.
4. Add or repair tests that prove the cycle end to end without using fake success.
5. Surface this loop in the desktop cockpit.

Likely files:

- `xinyu_initiative_orchestrator.py`
- `xinyu_initiative_spine.py`
- `xinyu_intention_ecology.py`
- `xinyu_proactive_presence.py`
- `xinyu_proactive_request_loop.py`
- `xinyu_proactive_direct_sender.py`
- `xinyu_proactive_response_diagnostics.py`
- `xinyu_qq_outbox.py`
- `xinyu_action_feedback_coverage.py`
- `xinyu_feedback_consumption_diagnostics.py`
- `xinyu_trusted_search.py` or the current trusted-search bridge if present.
- `xinyu_bridge_trusted_search.py`
- `xinyu_stage10_proactive_life_loop.py`
- `xinyu_autonomy_loop_report.py`
- `xinyu_status.py`

Required tests:

- A test where XinYu forms an exploration candidate from a real internal gap and keeps source anchors.
- A test where exploration is blocked because the source/channel/privacy boundary fails.
- A test where a proactive message is previewed but not sent because owner authorization is absent.
- A test where a proactive message is queued/sent through the allowed outbox path and ack is consumed.
- A test where owner non-response or dismissal reduces future proactive pressure.
- A test where silence is written as a decision when exploration or messaging is not justified.

Acceptance criteria:

- The system can show at least one fresh external-exploration candidate with objective, gate, allowed tool/source, result/hold reason, and future effect.
- The system can show at least one fresh proactive-message candidate with candidate text hidden or sanitized as appropriate, gate, channel, lifecycle, ack/non-response, and future effect.
- No proactive message bypasses Desktop preview, QQ outbox claim/ack, cooldown, owner authorization, or privacy guards.
- No external exploration writes unverified claims as stable facts.
- Stage10 and the desktop cockpit both expose whether the next autonomous action is `explore`, `message`, `wait`, or `hold`.

## 5. Recommended Technical Stack

### 5.1 Core Runtime

Use the existing stack.

- Language: Python 3.12.
- Test runner: pytest.
- Runtime style: local files, JSONL traces, Markdown state surfaces, explicit privacy boundaries.
- IPC/HTTP boundary: existing core bridge and QQ gateway.
- Diagnostics: existing report modules plus `xinyu_status.py`.
- Do not add a new backend framework.
- Do not add a database for this pass unless a specific state-store bottleneck is proven.

### 5.2 Desktop Frontend

Use the existing stack.

- Electron 31.
- electron-vite.
- React 18.
- TypeScript 5.5.
- Vite 5.
- lucide-react.
- CSS modules are not currently used; continue with source-owned CSS unless a clear local pattern exists.
- Use the existing preload bridge, `window.xinyu`, and main-process IPC handlers.

Do not introduce:

- Next.js.
- Tailwind.
- Material UI.
- shadcn/ui.
- Remote webfont dependencies.
- Browser-only routing abstractions that do not fit Electron.

Optional only after the core pass:

- Playwright for screenshot regression, if the owner accepts the new dev dependency.
- A small renderer-level visual test harness, if Playwright is not added.

### 5.3 Code Intelligence And Governance

Use:

- `rg` for exact search.
- `pytest` for behavioral verification.
- `code-intel-pipeline` for local reports.
- Understand Anything for architecture graph.
- Repowise for semantic memory, scoped to source-owned paths.
- Sentrux for structural gates and regression baselines.

Do not add Sourcegraph, Archon, or a second RAG stack for this pass.

## 6. Desktop Frontend Excellence Track

The current desktop has useful operational surfaces, but it reads as an accreted control panel rather than a professional autonomy operations cockpit. The next frontend pass must improve information architecture, density, visual hierarchy, interaction clarity, and gate visibility.

### 6.1 Product Goal

Turn `XinYu_Desktop` into a local autonomy operations cockpit:

```text
What is alive?
What did XinYu perceive?
What gap did it form?
What does XinYu want to explore?
What does XinYu want to proactively tell the owner?
What candidate did it choose?
What did it block or hold?
What feedback changed future behavior?
What owner decision is required?
What action is safe right now?
```

The first screen must be the usable control surface, not a landing page.

### 6.2 Information Architecture

Use four persistent regions:

1. Runtime command rail.
2. Autonomy loop dashboard.
3. Intervention and review queue.
4. Evidence drawer / detail inspector.

Recommended primary views:

- `Runtime`: Core, QQ gateway, NapCat, WebSocket, recent health transitions.
- `Autonomy Loop`: input anchor, perception gap, selected candidate, gate, action result, feedback, next bias.
- `Exploration`: curiosity gap, source/tool gate, search/probe lifecycle, evidence anchors, result confidence, future effect.
- `Memory Governance`: Stage8 owner-review queue, duplicate clusters, stable-write boundary, apply status.
- `Proactive Control`: candidate inbox, lifecycle, claimability, owner approval, response diagnostics.
- `Stage Gates`: Stage7 through Stage13 readiness and exact blockers.
- `Configuration`: API profiles, QQ runtime configuration, plugin controls.

### 6.3 Visual System

The UI should feel like a high-trust local operations console, not a generic chat app.

Recommended visual direction:

- Base: near-white porcelain surface, graphite text, deep ink panels.
- Status accents: green for verified, amber for gated, red for failed, cyan for live transport.
- Avoid purple-dominant gradients, decorative blobs, excessive rounded cards, and marketing-style hero layouts.
- Use consistent 4/8 px spacing increments.
- Cards may exist for repeated items, modals, and bounded tools only. Do not nest cards inside cards.
- Use stable dimensions for toolbars, status cells, counters, and queue rows.
- Text must not overlap or resize containers on hover.

Typography:

- Prefer a purposeful local stack such as `IBM Plex Sans`, `Noto Sans`, `Noto Sans SC`, with a separate mono stack for hashes, trace IDs, and command output.
- Do not rely on generic default UI typography as the primary design language.
- Keep compact operational headings small and scannable. Avoid hero-scale type inside dashboard panels.

### 6.4 Component Refactor Plan

Refactor toward these renderer components while preserving existing behavior:

- `RuntimeStatusStrip`: always-visible service health and last-refresh signal.
- `AutonomyLoopTimeline`: horizontal or vertical loop representation with one cell per autonomy stage.
- `GateProofMatrix`: Stage7-13 gate proof booleans with exact blockers.
- `DecisionChainInspector`: selected intent, runner-up, score margin, gate pressure, feedback consumed.
- `ExplorationQueuePanel`: exploration candidates, source/tool gates, confidence, evidence anchors, blocked reasons.
- `MemoryGovernanceQueue`: owner-review candidates, duplicate clusters, stable-memory boundary.
- `ProactiveLifecyclePanel`: candidate lifecycle, claimability, approval, ack, timeout.
- `EvidenceDrawer`: trace refs, report paths, sanitized evidence, command output.
- `CommandDeck`: safe actions only, with disabled states and explicit consequences.

Keep components source-owned under:

```text
D:\XinYu\XinYu_Desktop\src\renderer\src
```

Avoid a giant `main.tsx` expansion. Extract cohesive components from `DesktopPanels.tsx` only when it reduces complexity and clarifies ownership.

### 6.5 Renderer State And IPC

Current renderer polling is distributed across multiple effects and timers. Consolidate only if it reduces complexity.

Preferred approach:

- Keep main-process IPC as the backend boundary.
- Do not scatter direct `fetch` calls in renderer components.
- Add one typed normalization layer in `desktopModel.ts` for any new status/report shape.
- Use a single refresh coordinator for related runtime/autonomy surfaces where practical.
- Preserve explicit loading, stale, error, and disabled states.
- Every button that mutates runtime state must expose pending state and prevent duplicate submission.

Potential IPC additions:

- `xinyu:get-autonomy-stage-status`
- `xinyu:get-autonomy-loop-report`
- `xinyu:get-exploration-queue`
- `xinyu:get-stage12-report`
- `xinyu:get-stage13-report`
- `xinyu:get-memory-review-packet`

Only add these if the current IPC set cannot express the cockpit cleanly.

### 6.6 Frontend Acceptance Criteria

The desktop pass is complete only when:

- The first viewport answers the runtime/autonomy health question without scrolling.
- Stage12 and Stage13 readiness are visible and cannot be confused with stale cached state.
- Stage8 owner-review blockers are visible without exposing private text.
- Active external-exploration candidates are visible with source/tool gates, confidence, evidence anchors, and hold/send/run status.
- Proactive approval makes claimability and owner authorization obvious.
- Runtime services show live/offline/stale states distinctly.
- Destructive or outward actions are visually secondary and guarded.
- Buttons use lucide icons where a standard symbol exists.
- Dense panels remain readable at common laptop widths.
- No text overlaps, truncation hides critical status, or hover state shifts layout.
- `npm run typecheck` passes.
- `npm run build` passes.

### 6.7 Frontend Verification Commands

```powershell
cd D:\XinYu\XinYu_Desktop
npm run typecheck
npm run build
```

If a dev session is needed:

```powershell
cd D:\XinYu\XinYu_Desktop
npm run dev
```

If adding screenshot verification, document the tool and exact viewport sizes. At minimum verify:

- 1440 x 900.
- 1280 x 800.
- 1024 x 768.
- Narrow responsive width if the shell supports it.

## 7. Execution Plan

### Phase 1: Establish Truth

Run the current status and direct reports. Capture results in a handoff-back file.

Required commands:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe xinyu_status.py --json
.\.venv\Scripts\python.exe xinyu_autonomy_loop_report.py --root . --json
.\.venv\Scripts\python.exe xinyu_feedback_consumption_diagnostics.py --root . --json
.\.venv\Scripts\python.exe xinyu_stage8_memory_review_packet.py --root . --json
.\.venv\Scripts\python.exe xinyu_stage12_long_term_evaluation.py --root . --json
.\.venv\Scripts\python.exe xinyu_stage13_self_narrative.py --root . --json
```

Deliverable:

- A short truth table: report, status, ready flag, blocker, next action.

### Phase 2: Bring Live Runtime Back

Start or repair the local runtime chain.

Required result:

- `xinyu_status.py --json` reports `ok=true`, or an explicitly accepted offline-mode exception is documented.

Do not fake runtime success by editing state files.

### Phase 3: Repair Fresh Stage12/13 Consistency

Make Stage12, Stage13, and status aggregation agree.

Required result:

- Fresh Stage12 direct report controls Stage13 availability.
- `xinyu_status.py` cannot report Stage13 available when direct Stage13 says waiting.
- Tests cover the mismatch.

### Phase 4: Resolve Stage8 Governance Backlog

Handle owner-review candidates and duplicate cluster.

Required result:

- Stable memory remains blocked unless explicitly applied.
- Owner decisions are recorded without raw private text.
- Duplicate cluster has a resolution path.

### Phase 5: Prove Active Exploration And Proactive Messaging

Implement or repair the governed initiative loops that let XinYu actively explore external information and proactively message the owner.

Required result:

- At least one external-exploration candidate can be generated from a real internal gap and shown with objective, gate, source/tool, lifecycle, result or hold reason, and future effect.
- At least one proactive-message candidate can be generated, previewed, gated, delivered or held, acked or timed out, and consumed as future behavior feedback.
- The system can explain both action and restraint.
- The desktop cockpit exposes exploration and proactive-message state without raw private content.

Do not implement free-form autonomous browsing, unbounded external messaging, or owner-bypassing direct sends.

### Phase 6: Desktop Cockpit Pass

Improve the Electron desktop into a professional autonomy operations cockpit.

Required result:

- The operator can inspect the autonomy loop, Stage8 blockers, Stage12/13 gates, and runtime service health from the first screen.
- UI is dense, stable, readable, and visually intentional.
- Typecheck and build pass.

### Phase 7: Governance Baseline

Refresh local code intelligence and structural governance.

Required result:

- Understand graph exists.
- Scoped Repowise state exists.
- Sentrux rules and baseline exist for the chosen source scope.
- Code-intel run is clean or has accepted exceptions.

## 8. Test Matrix

Run focused tests after backend/autonomy changes:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe -m pytest -q tests/test_intention_ecology.py tests/test_autonomy_loop_report.py tests/test_feedback_consumption_diagnostics.py tests/test_stage8_memory_review_packet.py tests/test_stage8_learning_trial_validation_packet.py tests/test_stage9_self_state_model.py tests/test_stage10_proactive_life_loop.py tests/test_stage11_multisensory_extension.py tests/test_stage12_long_term_evaluation.py tests/test_stage13_self_narrative.py tests/test_owner_feedback_effects.py tests/test_proactive_direct_sender.py
```

Run broader smoke if runtime is online:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe smoke_run.py --group quick --timeout-seconds 180 --json
```

Run desktop checks after UI changes:

```powershell
cd D:\XinYu\XinYu_Desktop
npm run typecheck
npm run build
```

Run root operator verification:

```powershell
cd D:\XinYu
powershell -NoProfile -ExecutionPolicy Bypass -File .\XinYu.ps1 status
powershell -NoProfile -ExecutionPolicy Bypass -File .\XinYu.ps1 test core
```

## 9. Definition Of Done

This dossier is complete only when all of the following are true:

1. Live runtime status is green or explicitly documented as accepted offline mode.
2. Fresh Stage12 reports `ready_for_stage13=true`.
3. Fresh Stage13 reports `active_available_for_self_narrative`.
4. Stage8 owner-review backlog is resolved or explicitly parked with owner-visible next actions.
5. Stable memory remains blocked unless the owner explicitly applies reviewed candidates.
6. Feedback consumption remains clean and auditable.
7. Action feedback coverage remains clean across QQ, desktop, Codex, local tools, code probe, patch executor, and runtime probe surfaces.
8. A bounded external-exploration loop is demonstrated or explicitly blocked with a truthful gate reason.
9. A proactive outbound-message loop is demonstrated or explicitly blocked with a truthful gate reason.
10. The desktop first screen shows runtime health, autonomy-loop status, exploration candidates, proactive-message candidates, Stage8 blockers, Stage12/13 gates, and safe actions.
11. Frontend typecheck and build pass.
12. Focused autonomy pytest suite passes.
13. Code-intel governance either runs clean or documents accepted exceptions.
14. Handoff-back states exactly what changed, what was verified, and what remains blocked.

## 10. Handoff-Back Template

Claude must write a handoff-back document after execution:

```text
title: Claude Handoff-Back: XinYu Autonomy Recovery And Desktop Excellence
date:
executor:
scope:

1. Summary
2. Files changed
3. Runtime status before/after
4. Stage8 before/after
5. Stage12 before/after
6. Stage13 before/after
7. Desktop changes
8. External exploration loop status
9. Proactive outbound-message loop status
10. Privacy and boundary verification
11. Tests and commands run
12. Remaining blockers
13. Exact next action
```

Do not claim completion if Stage12/13 readiness is based on stale files or if desktop build verification was skipped.

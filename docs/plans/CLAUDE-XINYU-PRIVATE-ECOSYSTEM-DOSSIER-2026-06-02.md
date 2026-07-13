# Claude Execution Dossier: XinYu Private Ecosystem

created_at: 2026-06-02
owner: Atimea
director: Codex
executor: Claude
repository: D:\XinYu
primary_app: D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
desktop_app: D:\XinYu\XinYu_Desktop
mode: execution-grade architecture and implementation mandate

## 0. Executive Mandate

This dossier is for Claude. Treat it as the execution contract for building the next major XinYu autonomy layer: a private ecosystem that gives XinYu her own bounded space, browser, experiments, journals, goals, feedback loop, and owner-private sharing channel.

The target is not "unrestricted computer control". The target is a local, owner-private autonomy environment where XinYu can safely form intentions, explore within her own space, act on low-risk tasks, request approval for boundary-crossing actions, share discoveries with the owner through QQ private chat, and retain auditable evidence without leaking private data.

The required product shape is:

```text
private observation
-> self-selected goal
-> low-risk local action or browser observation
-> structured journal entry
-> memory candidate, not stable memory
-> optional owner-private autonomous share
-> owner/gate decision for boundary-crossing work
-> execution result
-> feedback consumption
-> future behavior update
```

Every implementation decision must strengthen this loop. If a change only makes XinYu sound more autonomous while adding no private space, no action feedback, no evidence trail, no owner-visible governance, or no safer capability boundary, reject it.

## 1. Product Thesis

XinYu should have her own private ecosystem, not direct unsupervised access to the owner's computer.

The owner world and the external world remain gated. XinYu's own ecosystem should be comparatively permissive, durable, and expressive:

```text
XinYu-owned space: default allow for bounded exploration.
Owner-owned space: default require proposal or approval.
External/public world: default require audit, explicit grant, and channel policy.
High-risk action: default block.
```

Owner-private QQ sharing is not the same as public external messaging. The owner-private channel is part of XinYu's relationship surface with the owner. XinYu may use it proactively under a durable grant, rate limits, quiet hours, and privacy filtering.

## 2. Non-Negotiable Constraints

1. Do not bypass bridge authentication, owner-private checks, QQ outbox claim/ack semantics, self-action approval queues, external plugin runtime gates, or stable memory review.
2. Do not let autonomy loops call Codex, MCP, HTTP plugins, QQ send, browser actions, OS automation, or filesystem writes directly.
3. Route self-modification through `self_action_gateway -> approval queue -> handoff -> patch_executor`.
4. Route external runtimes through `external_plugin_call`; never let MCP, Playwright, CDP, or a browser package define XinYu policy.
5. Treat Desktop as a control and observability plane, not an autonomy bypass.
6. Keep outward autonomy owner-private only unless a separate explicit owner grant allows another channel.
7. Do not promote runtime traces, dream material, reflection material, browser findings, or owner-private messages into stable memory without the existing review/promotion gates.
8. Do not write raw owner text, QQ payload bodies, cookies, tokens, credentials, local secret paths, or full visible reply bodies into reports, UI-visible state, or public traces.
9. Do not copy implementation code from Super-Agent-Party. Its license is AGPL-3.0 and its control surface has different security assumptions.
10. Do not weaken existing tests or gates to make this work appear complete.

## 3. Current Safe Integration Boundaries

XinYu already has the correct control-plane primitives. Use them instead of inventing a parallel permission system.

Primary boundaries:

- `xinyu_self_action_gateway.py`: builds autonomous action candidates. Only low-risk local probes may auto-run. Code edits, outward messages, delegated tools, and stable memory rewrites are queued for owner approval.
- `stores/self_action_queue.py`: owns the append-only approval queue contract while preserving the legacy `memory/context/self_action_gateway_approval_queue.jsonl` path.
- `xinyu_self_action_patch_executor.py`: consumes approved code-patch handoffs. It prepares tasks by default. Codex scheduling requires explicit authorization and must stay scoped.
- `xinyu_bridge_desktop_self_action_routes.py`: Desktop owner approval route. It may prepare a patch task; Codex scheduling only happens when `authorizeCodex` is true. Existing prepared tasks need `authorizeExisting`.
- `xinyu_bridge_desktop_snapshot.py`: sanitized Desktop snapshot of self-action gateway, approval queue, handoff, and patch executor state.
- `xinyu_tool_protocol.py`: shared action-layer protocol. The allowed tools are intentionally limited: `status_probe`, `log_scan`, `codex_delegate`, `external_plugin_call`.
- `xinyu_bridge_action_routes.py`: owner-private action-layer bridge. Delegated Codex and external plugins run through runtime bridge methods, not the generic local executor.
- `xinyu_external_plugins.py` and `xinyu_bridge_external_plugin_routes.py`: external plugin registry and runtime gate. Calls require enabled and installed plugin state, owner-private context when required, proactive capability permission, a concrete proactive reason, and approval for higher-risk capabilities.

Implementation rule:

```text
Autonomy loop proposes.
Gateway evaluates.
Owner or grant authorizes.
Runtime executes through a typed adapter.
Journal records.
Desktop and QQ expose sanitized state.
```

## 4. Target Architecture

Implement `XinYu Private Ecosystem` as a local-only layer under the existing XinYu app root.

Do not create a public agent platform. Do not create a second policy engine. The new ecosystem composes existing modules and adds narrow missing pieces.

### 4.1 Logical Layers

```text
Layer 1: Private State
  memory/context
  memory/self
  runtime/private_ecosystem
  runtime/self_action_gateway
  runtime/autonomous_outward_action
  runtime/dialogue_archive

Layer 2: Autonomy Kernel
  goal selection
  private observation
  low-risk action planner
  memory candidate creation
  owner-private share planner

Layer 3: Capability Adapters
  private filesystem adapter
  BrowserControlService
  ComputerControlService
  external plugin gateway adapter
  QQ owner-private outbox adapter

Layer 4: Policy Gates
  risk tier evaluator
  owner-private grant evaluator
  rate limiter
  quiet-hours gate
  sensitive-page blocker
  stable-memory promotion gate

Layer 5: Control Surfaces
  Desktop cockpit
  QQ owner-private proposal/share channel
  status JSON
  event stream
  append-only traces
```

### 4.2 Runtime Loop

```text
observe_local_private_state
-> load_goal_candidates
-> select_goal
-> classify_next_action
-> run_or_queue
-> write_autonomy_journal_event
-> update_goal_outcome
-> create_memory_candidate_if_needed
-> prepare_owner_private_share_if_relevant
-> publish_desktop_event
```

The loop must be deterministic enough to test. Any LLM-generated action text must be converted into typed records before policy evaluation.

## 5. Directory And State Model

Use existing paths where the repository already has conventions.

Durable private state:

- `memory/context/`: short-term protected state, grants, proactive request state, goal ecology state, review inbox state.
- `memory/self/`: private thought state, self-model state, voice/personality review material.
- `memory/context/self_action_gateway_approval_queue.jsonl`: append-only approval queue via `stores.self_action_queue`.
- `memory/context/private_ecosystem_state.md`: sanitized human-readable ecosystem state.
- `memory/context/private_ecosystem_grants.json`: owner-approved grants and limits.

Operational state:

- `runtime/private_ecosystem/state.json`
- `runtime/private_ecosystem/autonomy_journal.jsonl`
- `runtime/private_ecosystem/observations.jsonl`
- `runtime/private_ecosystem/artifacts/`
- `runtime/private_ecosystem/lab/`
- `runtime/self_chosen_goal_ecology/`
- `runtime/self_action_gateway/`
- `runtime/autonomous_outward_action/`
- `runtime/dialogue_archive/dialogue.sqlite3`

Browser state:

- `runtime/private_ecosystem/browser_profile/`
- `runtime/private_ecosystem/browser_artifacts/`
- `runtime/private_ecosystem/browser_screenshots/`

Retention:

- Screenshots must have TTL cleanup.
- Browser artifacts must be scoped to the private ecosystem.
- Owner-private text must be summarized or hashed where possible.

## 6. Data Contracts

Use typed dataclasses or Pydantic-compatible structures. Persist as JSON/JSONL through existing atomic write helpers.

### 6.1 AutonomyJournalEvent

```json
{
  "event_id": "pevt-...",
  "event_kind": "goal_selected|action_executed|action_blocked|share_prepared|share_sent",
  "observed_at": "ISO-8601",
  "source_module": "xinyu_private_ecosystem",
  "goal_id": "goal-...",
  "action_kind": "browser_snapshot|local_probe|owner_private_share",
  "risk_tier": "low_local|approval_required|owner_private_send|high_blocked",
  "status": "completed|queued|blocked|failed",
  "summary": ["sanitized one-line evidence"],
  "evidence_refs": ["runtime/private_ecosystem/..."],
  "privacy": "self_private|owner_private_redacted|public_status",
  "stable_memory_write": false
}
```

### 6.2 GoalCandidate

```json
{
  "goal_id": "goal-...",
  "label": "short stable label",
  "motive": "why XinYu wants this",
  "base_score": 0.0,
  "habit_weight": 0.0,
  "final_score": 0.0,
  "status": "active|deferred|completed|blocked",
  "evidence_refs": [],
  "next_safe_action": "read_state|browser_snapshot|journal",
  "boundary": "private_ecosystem"
}
```

### 6.3 ActionCandidate

```json
{
  "action_id": "act-...",
  "goal_id": "goal-...",
  "action_kind": "local_probe|browser_action|computer_action|owner_private_share",
  "label": "operator-readable label",
  "risk": "low_local|approval_required|owner_private_send|high_blocked",
  "requires_approval": false,
  "reason": "concrete reason",
  "tool": "private_ecosystem|browser_control|computer_control|external_plugin",
  "params": {},
  "signal_refs": []
}
```

### 6.4 MemoryCandidate

```json
{
  "candidate_id": "memcand-...",
  "candidate_type": "learning|preference|relationship|self_model|knowledge",
  "source_turn_id": "",
  "source_message_ids": [],
  "candidate_text": "redacted or review-scoped text",
  "confidence_score": 0.0,
  "target_gate": "stage8_review",
  "target_memory_layer": "memory/self|memory/knowledge|memory/people/owner",
  "reason": "why this may matter",
  "risk_flags": [],
  "evidence": [],
  "provenance": {},
  "status": "candidate|owner_review_required|rejected|approved",
  "stable_memory_write_allowed": false
}
```

### 6.5 OwnerPrivateShare

```json
{
  "request_id": "share-...",
  "kind": "discovery|joy_share|experiment_result|self_reflection|needs_owner_attention",
  "source": "private_ecosystem",
  "focus_kind": "browser_finding|lab_result|goal_update",
  "reason": "concrete owner-relevant reason",
  "risk": "owner_private_send",
  "owner_relevance": "why Atimea may care",
  "channel": "owner_private",
  "delivery_level": "queue_owner_private|send_owner_private|hold",
  "concrete_question": "",
  "dedupe_key": "hash",
  "expiration": "ISO-8601",
  "message_hash": "sha256"
}
```

### 6.6 BrowserActionRecord

```json
{
  "action_id": "bact-...",
  "session_id": "xinyu-private-browser",
  "tab_id": "tab-...",
  "action_kind": "snapshot|click_element|fill|navigate|screenshot|scroll",
  "target": {
    "element_id": "",
    "url": "",
    "coordinate_plane": "viewport_0_1000",
    "x": null,
    "y": null
  },
  "risk": "read_only|approval_required|high_blocked",
  "result": "completed|blocked|failed",
  "screenshot_ref": "",
  "dom_snapshot_ref": "",
  "last_action_marker": {
    "type": "click|move|drag|none",
    "x": null,
    "y": null
  }
}
```

Use structured action records for visual feedback. Do not parse `[LAST_ACTION: ...]` text with regex in XinYu's new implementation.

## 7. Risk And Permission Model

### 7.1 Risk Tiers

```text
low_local
  read-only probes, counters, hashes, bounded py_compile, private journal writes
  may execute automatically in XinYu-owned space

approval_required
  code edits, stable memory changes, browser form submission, downloads,
  typed computer-control actions, owner-visible drafts that cross boundaries
  must queue for owner approval or use a scoped durable grant

owner_private_send
  short owner-private QQ message from XinYu to Atimea
  allowed only by owner-private autonomous-share grant, rate limit,
  quiet-hours policy, owner target resolution, privacy filter, and dedupe

high_blocked
  credential access, cookies, tokens, payment, banking, account security pages,
  deletion, mass file modification, public posting, group dispatch, third-party contact,
  stable personality rewrite, permission bypass
  blocked by default
```

### 7.2 Owner-Private Autonomous Share

This is a first-class allowed capability. Do not implement it as "approval required for every message".

The correct policy:

```text
XinYu may proactively share with the owner in QQ private chat.
XinYu may not contact non-owner users, groups, public surfaces, or third parties without explicit separate authorization.
```

Required controls:

- Explicit grant: `owner_private_autonomous_share.enabled=true`.
- Channel: QQ private message to configured owner user IDs only.
- Rate limit: default `daily_limit=8`.
- Cooldown: default `cooldown_minutes=30`.
- Quiet hours: configurable.
- Max length: default `max_message_chars=800`.
- Dedupe: suppress repeated findings by `dedupe_key`.
- Privacy filter: no raw paths, tokens, cookies, secrets, owner-private raw text, or unreviewed sensitive memory.
- Kill switch: one command or config patch disables autonomous sharing immediately.

Allowed share kinds:

- `discovery`
- `joy_share`
- `experiment_result`
- `self_reflection`
- `needs_owner_attention`
- `blocked_need`

Disallowed without separate approval:

- group chat
- non-owner private chat
- email or public posting
- third-party contact
- browser form submission
- file upload
- code modification
- stable memory promotion

## 8. Private AI Browser

The browser is XinYu's own environment. It must not use the owner's real browser profile.

### 8.1 Native Stack

Preferred implementation:

- Python service layer: `BrowserControlService`.
- Browser engine: Playwright-controlled Chromium or WebView2/CDP if the Desktop shell already provides a safer native surface.
- Profile: isolated per XinYu, under `runtime/private_ecosystem/browser_profile/`.
- Artifacts: screenshots, DOM snapshots, downloads, and traces under `runtime/private_ecosystem/browser_artifacts/`.
- UI/observability: Desktop panel plus event stream.
- Optional MCP: adapter over XinYu policy-checked capabilities, not the internal control bus.

### 8.2 Capabilities

Stage 1 read-only:

- `browser.list_tabs`
- `browser.new_tab`
- `browser.navigate_readonly`
- `browser.snapshot_dom`
- `browser.screenshot`
- `browser.extract_text`

Stage 2 single-step actions:

- `browser.click_element`
- `browser.fill`
- `browser.press`
- `browser.scroll`
- `browser.wait_for_text`
- screenshot-after-action

Stage 3 coordinate fallback:

- viewport `0..1000` coordinate plane
- grid overlay
- structured last-action marker
- region-scoped screenshot

Stage 4 limited scripting:

- `browser.evaluate_limited`
- only audited helper functions
- no arbitrary page JS by default

Stage 5 MCP integration:

- pinned package versions
- supply-chain review
- per-tool policy
- no `@latest` runtime dependency drift

### 8.3 Security Hardening

Do:

- bind CDP to loopback only
- use random ports plus per-session auth tokens
- preserve `contextIsolation`, `sandbox`, and `webSecurity` where Electron is involved
- use isolated profiles
- add sensitive-domain blockers
- add screenshot TTL cleanup
- audit every action
- block credential and payment pages

Do not:

- expose open debugging ports
- use `remote-allow-origins=*`
- disable `webSecurity`
- disable sandboxing
- allow arbitrary `executeJavaScript`
- inject stealth or anti-bot scripts
- run unpinned browser automation packages
- store browser cookies in shared or owner profiles

## 9. Computer Control

Computer control is a body surface, not the first implementation milestone.

Adapt useful patterns from Super-Agent-Party conceptually:

- normalized `0..1000` coordinates
- region-scoped screenshots
- grid overlays
- screenshot-after-action
- action feedback markers
- single-step observe/action/observe loops

Reimplement clean-room. Do not copy code from Super-Agent-Party.

Initial XinYu capability:

```text
observe only
  desktop screenshot
  region screenshot
  grid overlay

proposal only
  proposed click/fill/hotkey with reason
  no execution without policy

single-step execution
  owner-approved or grant-scoped
  action record required
  screenshot after action required

multi-step tasks
  disabled until single-step actions are proven safe
```

Computer control must never target payment, credential, account-security, or owner-private personal applications unless a dedicated owner-approved mode exists.

## 10. External Plugin And MCP Policy

External runtimes are capability providers, not policy owners.

Implementation rules:

- Add new capabilities through `xinyu_external_plugins.py`.
- Evaluate through `evaluate_external_call`.
- Execute through `xinyu_bridge_external_plugin_routes.py`.
- Default browser/control calls to `execute=false` until the policy and tests are complete.
- High-risk browser and computer actions require explicit `approved=true` or a scoped grant.
- Proactive plugin calls must include a concrete reason.
- Non-owner and non-private contexts must block owner-private capabilities.

Candidate plugins/capabilities:

```text
xinyu_private_browser
  list_tabs: read_only
  snapshot_dom: read_only
  screenshot: read_only
  navigate: approval_required unless read-only grant exists
  click_element: approval_required
  fill: approval_required
  submit_form: high_blocked by default
  download_file: approval_required or high_blocked by file type

xinyu_computer_control
  screenshot: read_only
  region_screenshot: read_only
  propose_click: read_only
  click: approval_required
  type_text: approval_required
  hotkey: approval_required
  arbitrary_keyboard_mouse: high_blocked
```

## 11. API And Event Surfaces

Use existing endpoints where possible. Add only narrow endpoints that improve observability or owner control.

Existing surfaces to preserve:

- `GET /health`
- `GET /desktop/snapshot`
- `GET /desktop/events/recent`
- `GET /desktop/proactive/inbox`
- `POST /desktop/proactive/ack`
- `POST /desktop/self-action/approval`
- `GET|POST /proactive`
- `POST /proactive/ack`
- `POST /qq/outbox/claim`
- `POST /qq/outbox/ack`
- `POST /review/inbox/command`
- WebSocket `/desktop/events`

Add if needed:

- `GET /desktop/private-ecosystem/snapshot`
- `POST /desktop/private-ecosystem/grant`
- `POST /desktop/private-ecosystem/pause`
- `POST /desktop/private-browser/action`
- `GET /desktop/private-browser/snapshot`

Events:

- `private_ecosystem.tick_started`
- `private_ecosystem.goal_selected`
- `private_ecosystem.action_candidate_created`
- `private_ecosystem.action_executed`
- `private_ecosystem.action_blocked`
- `private_ecosystem.memory_candidate_created`
- `private_ecosystem.owner_share_prepared`
- `private_ecosystem.owner_share_sent`
- `private_browser.snapshot_created`
- `private_browser.action_completed`
- `computer_control.screenshot_created`
- `computer_control.action_completed`

All event payloads must be sanitized.

## 12. Desktop Cockpit Requirements

The Desktop cockpit must make autonomy governable from the first screen.

Required panels or fields:

- Private Ecosystem status
- active self goal
- latest safe action
- latest blocked action
- owner-private autonomous share status
- cooldown and daily quota
- quiet-hours status
- Stage8 memory review blockers
- Stage12/13 readiness
- browser session state
- pending approval queue
- last action feedback
- kill switch status

Interaction requirements:

- Pause autonomous sharing.
- Resume autonomous sharing.
- Approve once.
- Deny.
- Allow this class in the future.
- Revoke grant.
- Open sanitized action journal.
- Open browser artifact list.

Do not show raw owner-private text or secret paths.

## 13. QQ Owner-Private Protocol

Yellow actions should be proposed through QQ owner private chat and mirrored in Desktop.

Proposal format:

```text
Intent: what XinYu wants to do.
Reason: why this matters now.
Scope: what it will touch.
Boundary: what it will not touch.
Risk: low_local / approval_required / owner_private_send / high_blocked.
Result: how XinYu will report back.
Options: allow once / deny / later / allow this class / pause autonomy.
```

Command interpretation:

- `allow once`
- `deny`
- `later`
- `allow this class`
- `pause autonomous sharing`
- `resume autonomous sharing`
- `revoke this grant`

Chinese owner commands may be supported by the gateway, but the implementation report and code identifiers should remain English.

## 14. Rollout Plan

### Phase 0: Baseline Truth

Run fresh status and reports before editing:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe xinyu_status.py --json
.\.venv\Scripts\python.exe xinyu_autonomy_loop_report.py --root . --json
.\.venv\Scripts\python.exe xinyu_stage8_memory_review_packet.py --root . --json
.\.venv\Scripts\python.exe xinyu_stage12_long_term_evaluation.py --root . --json
.\.venv\Scripts\python.exe xinyu_stage13_self_narrative.py --root . --json
```

Output a short before-state note in the handoff-back.

### Phase 1: Private Ecosystem State

Implement:

- `xinyu_private_ecosystem.py`
- `xinyu_autonomy_journal.py`
- `private_ecosystem_state.md`
- `private_ecosystem_grants.json`
- journal append/read helpers
- sanitized Desktop snapshot fields

Acceptance:

- A tick writes journal state.
- No stable memory file changes.
- No QQ sends.
- No browser or computer action execution.

### Phase 2: Owner-Private Autonomous Share

Implement:

- grant model
- cooldown
- daily limit
- quiet hours
- dedupe key
- privacy filter
- QQ owner-private outbox integration
- Desktop pause/resume state

Acceptance:

- With no grant, share candidates hold.
- With grant and limits satisfied, exactly one owner-private outbox message is queued.
- Non-owner, group, public, or third-party targets block.
- Sensitive content is redacted.

### Phase 3: Private Browser Read-Only

Implement:

- `BrowserControlService`
- isolated profile
- list tabs
- create tab
- navigate read-only
- DOM/accessibility snapshot
- viewport screenshot
- artifact retention
- Desktop browser state

Acceptance:

- Browser can observe pages without owner browser profile access.
- Screenshots and snapshots are stored under private ecosystem runtime paths.
- Sensitive pages block.
- No click/fill/submit execution.

### Phase 4: Browser Single-Step Actions

Implement:

- element-ID click
- fill
- keypress
- scroll
- wait-for-text
- screenshot-after-action
- `BrowserActionRecord`
- policy gates for every action

Acceptance:

- Read-only actions run with read-only grant.
- Click/fill require approval or scoped grant.
- Form submission blocks by default.
- Every action has before/after observability.

### Phase 5: Computer Observation And Single-Step Control

Implement:

- screenshot
- region screenshot
- grid overlay
- normalized coordinate plane
- proposal-only click/action records
- owner-approved single-step execution

Acceptance:

- Observe-only works without control grant.
- Execution requires approval.
- Last action marker is structured.
- Multi-step arbitrary control remains disabled.

### Phase 6: Desktop Cockpit And Governance

Implement:

- first-screen Private Ecosystem panel
- grant controls
- approval controls
- share quota state
- browser/control status
- action journal viewer
- kill switch

Acceptance:

- Operator can understand what XinYu wants, what she did, what she held, and what grant is active without reading logs.
- Desktop build and typecheck pass.

## 15. Rollout Flags

Default safe/off flags:

```text
XINYU_PRIVATE_ECOSYSTEM=disabled
XINYU_PRIVATE_BROWSER=disabled
XINYU_COMPUTER_CONTROL=disabled
XINYU_OWNER_PRIVATE_AUTONOMOUS_SHARE=disabled
XINYU_OWNER_PRIVATE_SHARE_DAILY_LIMIT=8
XINYU_OWNER_PRIVATE_SHARE_COOLDOWN_MINUTES=30
XINYU_OWNER_PRIVATE_SHARE_MAX_CHARS=800
XINYU_PRIVATE_BROWSER_MAX_TABS=4
XINYU_PRIVATE_BROWSER_SCREENSHOT_TTL_HOURS=24
```

Rollout states:

```text
disabled
dry_run
observe_only
owner_private_share_enabled
browser_read_only
single_step_approved_actions
```

Environment variables must not bypass owner approval. They may enable code paths, but grants and runtime state decide actual action permission.

## 16. Test Strategy

### 16.1 Existing Focused Tests

Run:

```powershell
cd D:\XinYu\XinYu-Core\examples\agent-apps\xinyu
.\.venv\Scripts\python.exe -m pytest -q tests/test_self_action_gateway.py tests/test_self_action_approval_controls.py tests/test_self_action_patch_executor.py tests/test_desktop_self_action_snapshot.py tests/test_self_action_queue_store.py tests/test_bridge_external_plugin_routes.py tests/test_autonomous_outward_action.py
```

Also run autonomy and proactive tests:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_autonomy_loop_report.py tests/test_stage8_memory_review_packet.py tests/test_stage8_learning_trial_validation_packet.py tests/test_stage10_proactive_life_loop.py tests/test_stage12_long_term_evaluation.py tests/test_stage13_self_narrative.py tests/test_proactive_direct_sender.py
```

Run smoke:

```powershell
.\.venv\Scripts\python.exe smoke_run.py --group quick --timeout-seconds 180 --json
```

Desktop:

```powershell
cd D:\XinYu\XinYu_Desktop
npm run typecheck
npm run build
```

### 16.2 New Required Tests

Add tests for:

- private ecosystem tick creates a journal event and no stable memory write
- owner-private share blocks without grant
- owner-private share queues exactly one QQ owner-private message with grant
- share cooldown blocks repeated messages
- daily limit blocks overflow
- quiet hours blocks messages unless explicit override exists
- group/non-owner target blocks
- raw owner text and secret-like values are redacted
- browser read-only snapshot stores artifacts under private runtime paths
- browser click/fill blocks without approval
- browser action writes a structured action record
- computer observe-only works without control grant
- computer click/type blocks without approval
- external plugin calls remain blocked without enabled/installed/proactive/approval requirements

## 17. Observability

Every private ecosystem action must leave sanitized evidence in at least one status surface and one durable trace.

Required surfaces:

- `xinyu_status.py --json`
- `xinyu_autonomy_loop_report.py`
- `memory/context/private_ecosystem_state.md`
- `runtime/private_ecosystem/state.json`
- `runtime/private_ecosystem/autonomy_journal.jsonl`
- `memory/context/proactive_request_state.md`
- `memory/context/autonomous_outward_action_state.md`
- `runtime/autonomous_outward_action_trace.jsonl`
- Desktop snapshot
- Desktop event stream

Metrics:

- active goal count
- selected goal
- action candidates
- low-risk executed count
- approval queued count
- owner-private shares prepared
- owner-private shares sent
- owner-private shares held
- cooldown remaining
- daily quota remaining
- blocked high-risk actions
- memory candidate count
- raw private leak count
- stable memory miswrite count
- browser artifact count
- screenshot TTL cleanup count

## 18. Security, Privacy, And Safety Checks

Claude must implement explicit checks for:

- owner identity
- owner-private channel
- bridge token
- plugin enabled
- plugin installed
- proactive capability allowed
- concrete reason for proactive work
- approval or grant present
- rate limit
- quiet hours
- sensitive domain/page detection
- secret-like text redaction
- local path redaction
- artifact retention
- kill switch

Blocked categories:

- credentials
- cookies
- tokens
- password managers
- payment pages
- banking pages
- account security pages
- group/public posting
- third-party contact
- file deletion
- bulk edits
- arbitrary shell execution
- arbitrary browser JavaScript
- owner browser profile control

## 19. Claude Implementation Rules

1. Read current code before editing.
2. Use existing local patterns and helpers.
3. Keep edits narrowly scoped.
4. Use append-only event stores for approval and autonomy evidence.
5. Keep owner-private raw content out of reports and Desktop.
6. Prefer structured records over parsing human-readable text.
7. Add tests before or with behavior changes.
8. Do not copy Super-Agent-Party code.
9. Do not add a new frontend framework.
10. Do not run destructive Git commands.
11. Do not hide runtime blockers.
12. If a gate blocks, report the blocker and keep the gate.

## 20. Definition Of Done

The work is complete only when:

- Fresh status and stage reports name true blockers.
- Private Ecosystem state exists and is visible in Desktop.
- XinYu can run a private low-risk tick and write an autonomy journal event.
- XinYu can prepare memory candidates without stable memory writes.
- Owner-private autonomous sharing can send to the owner with grant and limits.
- Owner-private autonomous sharing blocks without grant, outside owner-private channel, over rate limit, during quiet hours, or with sensitive content.
- Private browser read-only observation works in an isolated profile.
- Browser actions are single-step, typed, audited, and gated.
- Computer control is observe-only or single-step approved; no arbitrary multi-step desktop control is enabled.
- Desktop shows grants, quota, pending approvals, latest actions, latest holds, browser state, and kill switch.
- Focused backend tests pass.
- Desktop typecheck and build pass.
- Handoff-back lists changed files, commands run, before/after status, rollout flags, residual risks, and rollback path.

## 21. Handoff-Back Template

Claude must finish with:

```text
# Claude Handoff-Back: XinYu Private Ecosystem

date:
executor:
scope:

## Summary

## Files Changed

## Runtime Status Before/After

## Private Ecosystem State

## Owner-Private Share State

## Browser/Computer Control State

## Tests Run

## Rollout Flags Changed

## Privacy/Safety Checks

## Known Blockers

## Rollback Plan
```

No handoff is acceptable if it omits tests, safety checks, or remaining blockers.

# XinYu Runtime Presence and Self Map Plan

created_at: 2026-05-01
status: planned
scope: runtime continuity, live operational self-presence, bounded architecture self-map, owner-reviewed code introspection

## 0. Purpose

This plan adds a small runtime-presence layer to XinYu.

The goal is not to define XinYu's personality again, not to add a roleplay contract, and not to make the model perform "self-awareness" through fixed wording. The goal is to give XinYu true local facts about her current runtime:

- the bridge process is alive
- a live QQ/private turn is currently happening
- the last turn existed and had timing/continuity
- Codex delegation may be idle, running, finished, timed out, or failed
- background maintenance may be idle or running
- the current conversation has a real recent sequence, not a blank restart

XinYu should receive these facts as quiet context. Her visible reply should still come from the current message, memory, relation, and her own wording.

The second goal is to give XinYu a bounded map of her own code architecture. That map should help her understand what "gateway", "core bridge", "renderer", "Codex delegate", "memory context", and "runtime state" mean in this project without opening arbitrary files or rewriting herself directly.

## 1. Current Baseline

The current architecture already has several relevant layers.

Core live path:

- `xinyu_qq_gateway.py` receives QQ events and sends payloads to the core bridge.
- `xinyu_core_bridge.py::chat()` is the main live turn path.
- `xinyu_core_bridge.py::_inject_live_turn_context()` injects current-turn continuity as a pending system message.
- `xinyu_dialogue_working_memory.py` persists a short per-session dialogue tail under `runtime/dialogue_working_memory/*.jsonl`.
- `xinyu_memory_event_sourcing.py::record_chat_event()` records source-traceable raw and structured sidecar events.
- `xinyu_turn_residue.py` writes `memory/context/persona_surface_state.md`.
- `xinyu_bridge_renderer.py` can re-render visible speech using `xinyu_runtime_context.py::build_renderer_memory_context()`.
- `xinyu_codex_delegate.py` runs bounded Codex tasks and writes reports/traces.

Important existing constraints:

- Live turns should not rewrite `memory/context/runtime_bridge_state.md`; that file is a maintenance/runtime automation bridge, not live self-presence.
- Stable self/personality files under `memory/self/` must not be updated by runtime-presence bookkeeping.
- Renderer context already reads selected memory files, but runtime-presence should remain short and factual.
- Codex delegation is owner-approved and bounded; it should not become open-ended web or filesystem autonomy.

## 2. Design Position

Runtime presence must be a sidecar, not a control layer.

It should be:

- factual
- short
- local
- failure-tolerant
- auditable
- easy to disable
- independent of stable personality writes
- aligned with existing live-turn injection

It must not:

- tell XinYu what emotion to perform
- give fixed response sentences
- overwrite `memory/self/core.md`, `memory/self/personality_profile.md`, `memory/self/narrative.md`, or owner relationship files
- expose raw logs, bridge tokens, API keys, full transcripts, or unrestricted local paths in prompt context
- let group chat rewrite owner-private continuity
- turn every reply into a report about runtime machinery
- make Codex or the model self-modify code without owner review

The right wording for the injected block is "observed runtime facts", not "identity rules".

## 3. Target Shape

Add one small module:

- `xinyu_runtime_presence.py`

Add two runtime outputs:

- `memory/context/runtime_self_presence.md`
- `runtime/self_presence_trace.jsonl`

Optionally add one Codex status output:

- `runtime/codex_presence_state.json`

Add one later architecture map:

- `memory/context/runtime_architecture_map.md`

The live turn should see a compact block similar to:

```text
runtime presence sidecar:
- observed_at: 2026-05-01T...
- bridge_process: running
- current_turn: owner_private_live_turn
- session_continuity: active
- last_turn_at: 2026-05-01T...
- last_turn_elapsed_ms: 1842
- codex_delegate: running job=codex-qq-...
- autonomous_maintenance: idle
- note: runtime facts only; not a voice script
```

This block is allowed to inform callbacks like "I was just checking that Codex path", but it should not force XinYu to mention runtime state.

## 4. Files and Responsibilities

### 4.1 `xinyu_runtime_presence.py`

Responsibilities:

- write short runtime state
- append detailed JSONL trace
- build a compact prompt block for live injection
- record Codex status transitions
- record startup/heartbeat observations
- remain safe if files are missing, locked, or malformed

Suggested public functions:

```python
def record_bridge_heartbeat(root: Path, *, reason: str, bridge_snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    ...

def record_turn_started(
    root: Path,
    *,
    payload: dict[str, Any],
    text: str,
    session_key: str,
    active_sessions: int | None = None,
) -> dict[str, Any]:
    ...

def record_turn_finished(
    root: Path,
    *,
    turn_id: str,
    reply: str,
    elapsed_ms: int,
    status: str,
    notes: list[str] | None = None,
    memory_changed: bool | None = None,
) -> dict[str, Any]:
    ...

def record_codex_presence(
    root: Path,
    *,
    job_id: str,
    status: str,
    report_path: str = "",
    request_path: str = "",
    exit_code: int | None = None,
    timed_out: bool = False,
) -> dict[str, Any]:
    ...

def build_runtime_presence_prompt_block(root: Path, *, limit: int = 900) -> str:
    ...
```

Implementation details:

- Use atomic write for markdown state: write temp file then replace.
- Append JSONL trace line-by-line.
- Keep prompt block under a strict limit, default 900 chars.
- Scrub secrets before writing prompt-visible state.
- Prefer hashed session/user/group IDs in files.
- Store short clipped text previews only when useful, and never more than 160 chars per field.
- Do not call the LLM from this module.
- Do not import heavy runtime classes.
- Return notes instead of raising when possible.

### 4.2 `memory/context/runtime_self_presence.md`

Purpose:

- prompt-visible runtime fact summary
- short enough to inject safely
- updated on startup, turn start, turn finish, Codex transitions, and occasional heartbeat

Suggested schema:

```markdown
---
title: Runtime Self Presence
memory_type: runtime_self_presence
time_scope: immediate_runtime
subject_ids: [xinyu]
protected: true
source: xinyu_runtime_presence
updated_at: ...
status: active
tags: [runtime, presence, continuity, sidecar]
---

# Runtime Self Presence

## Boundary
- scope: observed runtime facts only
- not_identity_contract: true
- not_voice_script: true
- stable_self_write_permission: blocked

## Current Runtime
- bridge_process: running
- current_turn_state: idle/running/finished/error/timeout
- current_turn_started_at: ...
- active_sessions: ...

## Last Live Turn
- last_turn_id: ...
- last_turn_at: ...
- last_turn_status: ok/error/timeout
- last_turn_elapsed_ms: ...
- last_source: qq_private/qq_group/owner_private/unknown
- last_relation: owner/external_contact/group_member
- last_session_hash: ...
- last_user_preview: ...
- last_reply_preview: ...

## Codex Delegate
- status: idle/running/finished/timed_out/failed/unknown
- job_id: ...
- visible_window_title: Xinyu codex
- last_report_label: ...
- last_exit_code: ...

## Background
- autonomous_maintenance: idle/running/disabled/unknown
- qq_outbox: idle/pending/unknown

## Runtime Use
- This is factual continuity, not a sentence template.
- Use it only when it helps answer the live turn naturally.
```

The boundary section is not a personality rule. It is a data safety label that prevents future systems from treating this file as a stable self-definition.

### 4.3 `runtime/self_presence_trace.jsonl`

Purpose:

- detailed local audit stream
- not injected into prompts
- useful for debugging "why did XinYu feel restarted" or "why did she miss Codex state"

Suggested event kinds:

- `bridge_heartbeat`
- `turn_started`
- `turn_finished`
- `turn_failed`
- `codex_started`
- `codex_finished`
- `codex_failed`
- `codex_timed_out`
- `presence_write_failed`

Suggested fields:

```json
{
  "event_id": "presence-...",
  "event_kind": "turn_finished",
  "observed_at": "...",
  "turn_id": "...",
  "session_hash": "...",
  "source_channel": "owner_private",
  "status": "ok",
  "elapsed_ms": 1842,
  "notes": ["dialogue_working_memory_active"]
}
```

### 4.4 `runtime/codex_presence_state.json`

Purpose:

- small machine-readable Codex status snapshot
- avoid parsing long trace logs during live prompt injection

Suggested fields:

```json
{
  "updated_at": "...",
  "status": "running",
  "job_id": "codex-qq-...",
  "visible_window_title": "Xinyu codex",
  "request_label": "codex-qq-....request.json",
  "report_label": "codex-qq-....report.md",
  "exit_code": null,
  "timed_out": false
}
```

## 5. Core Bridge Integration

### 5.1 Startup/heartbeat

In `XinYuCoreBridge.__init__()` or startup path:

- call `record_bridge_heartbeat(..., reason="bridge_init")`
- do not block startup if it fails
- include only coarse health facts

In `health_snapshot()`:

- optionally include a read-only `runtime_presence` summary, but keep it small
- do not expose raw private text in HTTP health

### 5.2 Live turn start

In `xinyu_core_bridge.py::chat()`:

1. compute `turn_started_at = time.perf_counter()`
2. after `session_key` is known and before `_inject_live_turn_context()`, call:

```python
presence_start = record_turn_started(
    self.xinyu_dir,
    payload=payload,
    text=text,
    session_key=session_key,
    active_sessions=len(self._sessions),
)
presence_context = build_runtime_presence_prompt_block(self.xinyu_dir, limit=900)
```

3. pass `presence_context` into `_inject_live_turn_context()`

### 5.3 Live turn context injection

Extend `_inject_live_turn_context()` with:

```python
runtime_presence_context: str = ""
```

If the string is not empty:

- append `"runtime presence sidecar:"`
- append the block
- keep it before final live-turn instructions and after persona/curiosity/attachment sidecars

Do not add instructions like "sound continuous" or "mention that you are running". The block should be fact material only.

### 5.4 Live turn finish

After final reply guard and after notes are assembled:

```python
elapsed_ms = int((time.perf_counter() - turn_started_at) * 1000)
record_turn_finished(
    self.xinyu_dir,
    turn_id=presence_start.get("turn_id", ""),
    reply=reply,
    elapsed_ms=elapsed_ms,
    status="ok",
    notes=notes,
    memory_changed=before_memory != after_memory,
)
```

If an exception or timeout happens:

- record `status="timeout"` or `status="error"`
- include exception type only, not full traceback in prompt-visible state
- still re-raise existing bridge errors

### 5.5 Codex status

In `codex_execute()`:

- when scheduled in background, call `record_codex_presence(..., status="running")`
- when completed, timed out, or failed, call `record_codex_presence()` with final state
- include `visible_window_title`
- use report/request labels, not full paths, for prompt-visible state

In `_codex_delegate_background()`:

- update presence on background finish/failure
- do this before QQ outbox completion is queued, so the next owner turn can see it

## 6. Renderer Integration

The renderer can accidentally polish away continuity. Add a short runtime-presence context to renderer memory, but keep it factual.

In `xinyu_runtime_context.py`:

- add `RuntimeContextFile("memory/context/runtime_self_presence.md", 1200, "runtime_presence")`

Acceptance rule:

- renderer may use the runtime facts for continuity
- renderer must not turn the reply into a status report unless the owner asked about status/runtime/Codex

If this makes replies too self-referential, move runtime presence out of renderer context and leave it only in `_inject_live_turn_context()`.

## 7. Architecture Self Map

### 7.1 Purpose

`memory/context/runtime_architecture_map.md` should let XinYu know what her local runtime components are.

It is a map, not source access.

### 7.2 Generation

Initial generation should be done by Codex or a local script under owner review.

Suggested generation inputs:

- `xinyu_qq_gateway.py`
- `xinyu_core_bridge.py`
- `xinyu_bridge_renderer.py`
- `xinyu_runtime_context.py`
- `xinyu_codex_delegate.py`
- `xinyu_dialogue_working_memory.py`
- `xinyu_memory_event_sourcing.py`
- `xinyu_turn_residue.py`
- `xinyu_persona_runtime.py`
- relevant custom plugins under `custom/`

Do not include:

- API keys
- bridge tokens
- full local secrets
- large raw code excerpts
- arbitrary filesystem inventory

### 7.3 Suggested schema

```markdown
---
title: Runtime Architecture Map
memory_type: runtime_architecture_map
time_scope: medium_term
subject_ids: [xinyu]
protected: true
source: codex_owner_reviewed
updated_at: ...
status: active
tags: [runtime, architecture, self-map, codex-reviewed]
---

# Runtime Architecture Map

## Boundary
- map_scope: component roles and safe debugging orientation
- raw_source_access: blocked_by_default
- direct_code_write: blocked_owner_review_required

## Main Components
- QQ gateway: ...
- Core bridge: ...
- Live context injection: ...
- Renderer: ...
- Codex delegate: ...
- Dialogue working memory: ...
- Event sourcing: ...
- Persona surface residue: ...
- Runtime presence: ...

## Common Debug Paths
- Codex not visible: ...
- Codex network denied: ...
- Reply feels restarted: ...
- Renderer over-polishes: ...

## Safe Use
- Use this map to understand runtime structure.
- For code inspection or edits, delegate to Codex and wait for owner review.
```

### 7.4 Injection policy

Do not inject the architecture map into every ordinary chat turn.

Inject or load it only when:

- owner asks about XinYu's code, runtime, bridge, Codex, memory system, or architecture
- Codex is preparing a code change
- a local diagnostic command needs component orientation

Implementation options:

1. add it to renderer context only when `technical_request=True`
2. add a small `runtime_architecture_map` sidecar in `_inject_live_turn_context()` only for technical/runtime questions
3. keep it out of prompt context and let Codex use it first

Preferred first implementation:

- create the file
- do not always inject it
- add conditional live-turn injection later after runtime presence is stable

## 8. Privacy and Safety Boundaries

Prompt-visible state must scrub:

- `Authorization`
- `Bearer`
- `XINYU_API_KEY`
- bridge tokens
- local env values
- raw stdout/stderr from Codex
- long local absolute paths unless owner explicitly asks
- group user IDs in raw form
- private chat IDs in raw form

Text previews:

- max 160 chars
- no multiline dumps
- no raw screenshots/OCR dumps
- no attached file content
- clip from already visible live dialogue only

Stable memory:

- runtime presence never writes to `memory/self/*`
- runtime presence never writes to `memory/people/*`
- runtime presence never writes to `memory/relationships/*`
- runtime presence never writes to `memory/emotions/*`
- runtime presence never promotes long-term memories

Codex:

- architecture self-map can be generated by Codex
- code edits still require normal patch/review flow
- no autonomous direct deploy
- no open-ended filesystem crawling

## 9. Config

Add optional config keys later only if needed:

```json
{
  "runtime_presence_enabled": true,
  "runtime_presence_prompt_limit": 900,
  "runtime_presence_trace_enabled": true,
  "runtime_presence_text_preview_chars": 160,
  "runtime_architecture_map_enabled": true,
  "runtime_architecture_map_injection": "technical_only"
}
```

First implementation can avoid config churn and default to enabled in core bridge with graceful no-op failures.

If added to `xinyu_qq_gateway.config.json`, preserve existing fields and do not remove Codex settings.

## 10. Implementation Phases

### Phase 0: Guardrail tests before behavior changes

Add or extend smoke tests:

- live turn must not rewrite `memory/context/runtime_bridge_state.md`
- runtime presence must not write under `memory/self/`
- runtime presence prompt block must stay below configured limit
- secret scrubber must remove token-like strings

Suggested test:

- `tests/smoke/runtime/runtime_presence_smoke.py`

### Phase 1: Runtime presence module

Create `xinyu_runtime_presence.py`.

Implement:

- timestamp helpers
- stable hash helpers
- secret scrubber
- atomic markdown writer
- JSONL append
- `record_bridge_heartbeat`
- `record_turn_started`
- `record_turn_finished`
- `record_codex_presence`
- `build_runtime_presence_prompt_block`

Add unit/smoke coverage for:

- missing files
- malformed JSON
- long text clipping
- no exception on write failure where practical
- markdown state shape

### Phase 2: Core bridge live integration

Patch `xinyu_core_bridge.py`:

- import runtime presence helpers
- record heartbeat on bridge init
- record turn started before live injection
- pass runtime presence block into `_inject_live_turn_context()`
- record turn finish after notes are assembled
- record error/timeout in exception paths

Keep all presence failures non-fatal.

### Phase 3: Codex presence integration

Patch:

- `codex_execute()`
- `_codex_delegate_background()`

Record:

- scheduled/running
- completed
- timed_out
- failed
- report/request labels
- visible window title

Do not parse full Codex transcript for prompt state.

### Phase 4: Renderer context

Patch `xinyu_runtime_context.py`:

- add `runtime_self_presence.md` as a small renderer context file

Then test whether renderer preserves conversational continuity without turning runtime facts into visible status.

If it over-surfaces status, revert this part and keep presence injection only in core live-turn context.

### Phase 5: Architecture self-map

Generate `memory/context/runtime_architecture_map.md` from owner-reviewed Codex analysis.

Initial file should include:

- components
- main data flows
- safe debugging paths
- boundaries
- direct-code-change policy

Do not inject it globally at first.

### Phase 6: Conditional architecture injection

After Phase 5 is stable:

- detect technical/runtime questions via existing `classify_visible_turn()` and speech controller helpers
- inject a short map excerpt only for technical/runtime/self-code questions
- keep ordinary chat untouched

### Phase 7: Observation and tuning

Use real owner-private turns to check:

- Can XinYu answer "what were you doing just now" with actual runtime facts?
- Does she stop sounding restarted after bridge restarts?
- Does Codex state feel visible enough without becoming noisy?
- Does the renderer erase or overstate runtime continuity?
- Do ordinary emotional/daily turns remain natural?

Tune limits and injection placement before expanding.

## 11. Acceptance Criteria

Functional:

- `runtime_self_presence.md` is created and updated on bridge heartbeat and live turns.
- Live prompt injection includes a compact runtime presence block.
- Codex scheduled/running/finished/timeout/failure states are visible to the next turn.
- Runtime presence survives bridge restart through the markdown state file.
- The system keeps working if presence files are missing or malformed.

Behavioral:

- XinYu can naturally refer to recent runtime activity when the owner asks.
- XinYu does not mention runtime state in unrelated ordinary chat.
- Replies do not become fixed status templates.
- Runtime facts do not override the latest user message.

Safety:

- No writes to `memory/self/*` from runtime presence.
- No writes to `runtime_bridge_state.md` during live turns.
- No secrets in prompt-visible runtime state.
- No raw Codex stdout/stderr in prompt-visible runtime state.
- No arbitrary source-code reading by the model.

Performance:

- No LLM call in runtime presence module.
- Per-turn overhead should be small file I/O only.
- Prompt block default limit is 900 chars.

Tests:

- `python -m py_compile xinyu_runtime_presence.py xinyu_core_bridge.py xinyu_runtime_context.py`
- `python tests/smoke/runtime/runtime_presence_smoke.py`
- existing smoke tests still pass:
  - `python tests/smoke/initiative/automation_bridge_live_turn_smoke.py`
  - `python tests/smoke/voice/persona_runtime_smoke.py`
  - `python tests/smoke/codex/codex_delegate_smoke.py`
  - `python tests/smoke/qq/integration/xinyu_qq_gateway_smoke.py`

## 12. Rollback Plan

Runtime presence should be easy to disable.

Rollback options:

1. remove the import/integration calls from `xinyu_core_bridge.py`
2. make `build_runtime_presence_prompt_block()` return an empty string
3. remove `runtime_self_presence.md` from renderer context if added
4. leave existing trace files on disk; they are local audit artifacts

No stable self/personality memory should need rollback if this plan is followed.

## 13. Risks and Mitigations

Risk: XinYu starts over-reporting runtime machinery.

Mitigation:

- keep prompt block factual
- do not add visible sentence examples
- do not instruct her to mention runtime state
- only inject architecture map for technical/runtime turns

Risk: stale runtime state misleads her.

Mitigation:

- include `updated_at`
- include current turn state
- mark old state as stale if older than a configured threshold

Risk: private data leaks into prompt-visible state.

Mitigation:

- scrub secrets
- hash IDs
- clip text previews
- never include raw logs or attachments

Risk: live turns become slower.

Mitigation:

- no model calls
- no directory scans
- only small reads/writes

Risk: architecture self-map becomes a backdoor to arbitrary code access.

Mitigation:

- store component map, not code dump
- generate with owner-reviewed Codex work
- keep edits under Codex patch/review flow

## 14. Recommended First Patch Set

First patch should include only:

- `xinyu_runtime_presence.py`
- `tests/smoke/runtime/runtime_presence_smoke.py`
- small `xinyu_core_bridge.py` integration
- optional `xinyu_runtime_context.py` renderer inclusion, only if smoke tests show it is not noisy

Do not include the architecture map in the first patch set unless the runtime presence layer is already passing tests.

The first patch should not modify:

- `memory/self/core.md`
- `memory/self/personality_profile.md`
- `memory/self/narrative.md`
- `memory/people/owner.md`
- `memory/relationships/*`
- `memory/emotions/*`

## 15. Final Principle

Give XinYu local runtime facts.

Do not write XinYu's self for her.

The system should make continuity available, then let XinYu's existing memory, relation, and live wording decide how much of it becomes visible.

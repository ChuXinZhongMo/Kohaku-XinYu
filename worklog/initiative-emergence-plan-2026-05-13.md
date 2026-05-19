# XinYu Initiative Emergence Plan

Date: 2026-05-13

## Purpose

Design a behavior-preserving path for XinYu to develop credible initiative: not random proactive messages, not fixed reminders, and not uncontrolled automation, but a traceable loop where internal pressure becomes candidate action, candidate action competes with other priorities, gates decide whether it deserves owner attention, and feedback changes future behavior.

The first implementation goal is not to prove consciousness or agency. The goal is to build the engineering substrate for observable, bounded, feedback-sensitive initiative.

## Current Ground Truth

Existing modules already cover most parts of the loop:

- `xinyu_self_thought_loop.py`: private thought source and candidate pressure.
- `xinyu_proactive_request_loop.py`: proactive request formation.
- `xinyu_proactivity_scorer.py`: candidate collection, scoring, recommendation, traces.
- `xinyu_initiative_spine.py`: synthesis across self-thought, emotion, impulse, proactive choice, action permission, and feedback.
- `xinyu_runtime_presence.py`: program-aware status surface and sidecar health.
- `xinyu_proactive_presence.py`: proactive candidate, claim, ack, and desktop/QQ-facing delivery.
- `xinyu_qq_outbox.py`: queue, claim, ack, retry, dispatch state.
- `xinyu_learning_closed_loop.py`: feedback-sensitive adjustment path.
- `xinyu_runtime_context.py`: prompt-safe context injection, including initiative spine.
- `XinYu_Desktop/src/main/xinyu_gateway.ts`: desktop proactive inbox and ack bridge.
- `XinYu_Desktop/src/renderer/src/main.tsx`: owner-facing proactive inbox actions.

Current risk: these modules already form partial initiative behavior, but the causal chain is still spread across Markdown state, JSONL traces, bridge code, desktop ack paths, and QQ outbox state. The missing piece is a single initiative lifecycle record that ties source, score, gate, delivery, and feedback together.

## Definition Of Initiative

XinYu initiative is a lifecycle, not a message.

Required lifecycle:

```text
source pressure
  -> candidate
  -> score
  -> gate
  -> delivery decision
  -> owner/system feedback
  -> future tendency update
```

An initiative event is valid only if it can answer:

- Why did this candidate exist?
- What else could have been chosen?
- Why was it selected, held, blocked, or sent?
- What happened after delivery?
- Did that outcome alter future scoring or gating?

## Non-Goals

- Do not create a new autonomous sender that bypasses existing proactive request, desktop inbox, QQ outbox, or claim/ack gates.
- Do not let self-thought directly send QQ messages.
- Do not treat a candidate as stable memory or personality change.
- Do not rewrite `xinyu_core_bridge.py` broadly.
- Do not move private runtime data into tracked source files.
- Do not increase owner interruption frequency until feedback metrics prove it is warranted.

## Architecture

### 1. Source Layer

Sources produce raw initiative pressure. They do not decide delivery.

Initial source types:

- `self_thought`: private thought loop found something worth surfacing.
- `proactive_request`: existing proactive request state is ready or candidate-only.
- `promise_followup`: a prior commitment needs follow-up.
- `owner_idle`: long owner silence with relevant grounded context.
- `learning_update`: owner-supplied or self-found learning has a meaningful result.
- `runtime_program_awareness`: code/runtime state creates a useful owner-facing update.
- `dream_or_reflection`: dream/reflection material is shareable and not too private.
- `qq_outbox`: queued outward message needs lifecycle tracking.

Implementation should initially reuse `collect_proactive_candidates()` in `xinyu_proactivity_scorer.py` instead of inventing a second candidate collector.

### 2. Candidate Layer

Canonical candidate shape:

```json
{
  "candidate_id": "procand-...",
  "source_type": "self_thought",
  "source_ref": "self_thought:...",
  "intent_type": "share_reflection",
  "content_preview": "short private-safe preview",
  "owner_visible_text": "text that could be shown to owner",
  "private_reason": "why XinYu wants to act",
  "confidence": 74,
  "emotional_weight": 35,
  "utility_hint": "owner/open_loop",
  "novelty_hint": "fresh",
  "risk_flags": [],
  "created_at": "2026-05-13T00:00:00+08:00",
  "expires_at": "2026-05-13T12:00:00+08:00"
}
```

This should map directly to or extend `ProactiveCandidate` from `xinyu_proactivity_scorer.py`.

### 3. Competition Layer

Every candidate competes against the others. A selected candidate is not necessarily delivered.

Scoring inputs:

- Utility to owner.
- Urgency.
- Owner relevance.
- Novelty.
- Internal pressure.
- Confidence.
- Repetition penalty.
- Staleness penalty.
- Uncertainty penalty.
- Interruption penalty.
- Safety and privacy hard blocks.

Recommendation values:

- `hold_private`: useful internally, not worth surfacing.
- `show_desktop`: show in Desktop proactive inbox only.
- `ask_owner`: show as a consent/request candidate.
- `queue_qq`: may enter QQ outbox after explicit owner or policy gate.
- `send_now_allowed`: only for narrow, already-approved cases.
- `blocked`: do not surface.

### 4. Gate Layer

Gates enforce restraint. They must be stronger than the score.

Required gates:

- Cooldown gate: prevents repeated interruptions.
- Duplicate gate: blocks semantically repeated candidates.
- Open-loop gate: prefers resolving existing initiative threads before new ones.
- Privacy gate: blocks sensitive local state or private memory leakage.
- Owner-consent gate: blocks local writes, code execution, external sends, or QQ messages without proper approval.
- Context gate: blocks candidates that cannot cite a grounded source.
- Mood-noise gate: blocks vague emotional bids with no owner utility.
- Delivery gate: determines `private_bias`, `desktop_inbox`, or `qq_outbox`.

### 5. Delivery Layer

Delivery levels:

```text
private_bias
desktop_inbox
qq_outbox
```

Rules:

- `private_bias` can influence the next prompt but is not visible.
- `desktop_inbox` appears in owner-facing proactive inbox and needs owner ack.
- `qq_outbox` must use existing queue, claim, ack, and retry logic.
- Direct QQ send should stay disabled unless a candidate passed explicit narrow gates.

### 6. Feedback Layer

Feedback must update future initiative behavior.

Feedback events:

- `ignored`
- `dismissed`
- `read_locally`
- `replied`
- `approved_qq`
- `sent`
- `failed`
- `owner_positive`
- `owner_negative`
- `expired`
- `blocked_by_gate`

Feedback effects:

- Dismissed candidates reduce similar future score.
- Replied candidates increase related source confidence.
- Failed sends increase delivery penalty.
- Repeated ignored desktop candidates increase interruption penalty.
- Owner-positive feedback can promote the source type, but not directly modify stable personality.
- Owner-negative feedback should create a repair lane before future promotion.

## New Orchestrator

Add a small coordinating module:

```text
XinYu-Core/examples/agent-apps/xinyu/xinyu_initiative_orchestrator.py
```

Responsibilities:

- Read candidates from existing scorer sources.
- Run scoring and gate decisions.
- Write canonical lifecycle events.
- Update Markdown summary state for prompt-safe context.
- Optionally hand selected candidate to existing proactive presence or QQ outbox.
- Never send directly.

Initial public functions:

```python
def run_initiative_orchestrator(
    root: Path,
    *,
    checked_at: str | None = None,
    trigger: str = "manual",
    delivery_level: str = "desktop_inbox",
    dry_run: bool = False,
) -> dict[str, Any]:
    ...

def record_initiative_feedback(
    root: Path,
    *,
    candidate_id: str,
    action: str,
    feedback_at: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ...
```

## State Files

New files:

```text
memory/context/initiative_lifecycle_state.md
memory/context/initiative_feedback_state.md
runtime/initiative_lifecycle_events.jsonl
runtime/initiative_metrics.json
```

Do not store raw private memory text in lifecycle JSONL. Store short previews, hashes, source refs, score parts, and reason labels.

### Lifecycle Event Schema

```json
{
  "event_id": "init-20260513T010203-abc123",
  "ts": "2026-05-13T01:02:03+08:00",
  "stage": "decision",
  "trigger": "autonomous_maintenance",
  "candidate_id": "procand-...",
  "source_type": "self_thought",
  "source_ref": "self_thought:...",
  "intent_type": "share_reflection",
  "candidate_signature": "sha256:...",
  "content_preview": "private-safe preview",
  "score": {
    "total_score": 136,
    "utility_score": 48,
    "urgency_score": 12,
    "owner_relevance": 40,
    "novelty_score": 22,
    "inner_pressure": 34,
    "penalties": 20
  },
  "gate": {
    "decision": "desktop_inbox",
    "blocked_by": [],
    "held_by": [],
    "positive_reasons": ["owner_relevant", "open_loop"],
    "negative_reasons": ["recent_contact_penalty"]
  },
  "delivery": {
    "level": "desktop_inbox",
    "outbox_message_id": "",
    "desktop_candidate_id": "..."
  },
  "feedback": {
    "status": "pending",
    "feedback_event_id": ""
  }
}
```

### Prompt-Safe State

`initiative_lifecycle_state.md` should be compact:

```text
# Initiative Lifecycle State

- checked_at: ...
- last_trigger: autonomous_maintenance
- candidate_count: 5
- selected_candidate_id: ...
- selected_source: self_thought
- selected_intent: share_reflection
- selected_decision: desktop_inbox
- selected_score: 136
- blocked_count: 2
- held_count: 2
- pending_feedback_count: 1
- interruption_posture: restrained
- next_step: wait for owner ack before promoting similar candidates
```

## Integration Points

### Autonomous Maintenance

Current tests show `_run_autonomous_self_thought_sidecars()` already runs self-thought and proactive sidecars. Add orchestrator after existing self-thought/proactive scoring, not before.

Target:

```text
xinyu_core_bridge.py
  -> _run_autonomous_self_thought_sidecars()
     -> run_self_thought_loop()
     -> run_proactive_request_loop()
     -> run_proactivity_scorer_shadow()
     -> run_initiative_orchestrator()
```

Keep the bridge change tiny: import and call only.

### Desktop Ack

Current path:

```text
renderer main.tsx
  -> window.xinyu.ackProactive()
  -> xinyu_gateway.ts
  -> /desktop/proactive/ack
```

Add feedback recording inside the Core endpoint that handles `/desktop/proactive/ack`, not in the renderer.

### QQ Outbox Ack

Current path:

```text
xinyu_qq_outbox.py
  -> claim_next_qq_outbox_message()
  -> ack_qq_outbox_message()
```

When outbox item has initiative metadata, ack should call `record_initiative_feedback()` with `sent` or `failed`.

### Runtime Context

`xinyu_runtime_context.py` already injects initiative spine. Add one compact block from `initiative_lifecycle_state.md`, but keep it lower priority than current owner message and stable memory.

## Implementation Phases

### Phase 0: Baseline And Safety

Goal: no behavior change.

Tasks:

- Add `xinyu_initiative_orchestrator.py` in dry-run mode only.
- Add state writers for lifecycle state and JSONL trace.
- Add unit tests with temp directories only.
- Do not connect to desktop or QQ delivery.

Acceptance:

- `python -m py_compile xinyu_initiative_orchestrator.py`
- Tests prove lifecycle events contain source, score, gate, and pending feedback.
- No production state files are written unless called manually.

### Phase 1: Shadow Orchestration

Goal: observe candidate competition without changing delivery.

Tasks:

- Call orchestrator from autonomous maintenance with `dry_run=True`.
- Read existing candidates from `xinyu_proactivity_scorer.py`.
- Write `runtime/initiative_lifecycle_events.jsonl`.
- Write `memory/context/initiative_lifecycle_state.md`.
- Add health/status summary field.

Acceptance:

- Existing proactive behavior unchanged.
- Lifecycle state shows candidate count, selected candidate, decision, and blocked/held reasons.
- Repeated runs apply duplicate and cooldown gates.

### Phase 2: Desktop Inbox Control

Goal: let orchestrator decide which candidate reaches Desktop inbox.

Tasks:

- Add delivery decision `desktop_inbox`.
- Attach initiative metadata to proactive candidate payloads.
- Record desktop ack feedback: `read_locally`, `dismissed`, `reply`, `approve_qq`.
- Keep QQ send manual/approved.

Acceptance:

- Desktop can show selected candidate.
- Dismiss lowers future similar score.
- Reply/positive ack raises source confidence.
- Pending candidate is not duplicated.

### Phase 3: Feedback Learning

Goal: make outcomes alter future initiative.

Tasks:

- Add feedback summary to `initiative_feedback_state.md`.
- Feed feedback penalties into candidate scoring.
- Add per-source tendency modifiers.
- Integrate with `xinyu_learning_closed_loop.py` only through explicit records, not hidden prompt hacks.

Acceptance:

- A dismissed candidate produces measurable penalty for same signature/source.
- A replied candidate produces measurable confidence bump for same source type.
- Failed QQ delivery reduces future QQ delivery recommendation.
- Owner-negative feedback creates repair posture.

### Phase 4: QQ Outbox Metadata

Goal: track QQ delivery as part of initiative lifecycle.

Tasks:

- Add optional initiative metadata to queued QQ outbox items.
- On claim, update lifecycle delivery state.
- On ack, record `sent` or `failed`.
- Preserve current outbox retry/dead behavior.

Acceptance:

- Outbox tests pass.
- Initiative event links to outbox message id and claim id.
- Failed delivery does not erase candidate history.

### Phase 5: Emergence Metrics

Goal: measure whether initiative is improving.

Metrics:

- `candidate_count_24h`
- `selected_count_24h`
- `desktop_shown_count_24h`
- `qq_queued_count_24h`
- `dismiss_rate`
- `reply_rate`
- `positive_feedback_rate`
- `repeat_block_count`
- `held_private_count`
- `cooldown_block_count`
- `average_time_to_feedback`

Acceptance:

- `runtime/initiative_metrics.json` updates from lifecycle events.
- Status page can report initiative posture without exposing private content.

## Test Matrix

Core orchestrator tests:

- candidate with high score becomes `desktop_inbox`.
- repeated signature becomes `hold_private` or `blocked`.
- recent owner interruption triggers cooldown.
- risky candidate is blocked even with high score.
- no candidates writes `no_candidates` state.
- dry-run writes trace but does not enqueue delivery.

Feedback tests:

- dismiss creates future penalty.
- reply creates future confidence bump.
- approve_qq records approval but does not directly send unless outbox path is used.
- failed QQ ack creates delivery penalty.
- stale pending feedback expires.

Integration tests:

- autonomous maintenance invokes orchestrator after self-thought.
- desktop ack endpoint records initiative feedback.
- QQ outbox ack records initiative feedback when metadata exists.
- runtime context includes compact lifecycle block.
- status summary exposes counts, not private text.

Regression tests to keep:

- `test_learning_closed_loop.py`
- `test_dialogue_curiosity_bridge_injection.py`
- `test_gateway_ack_spool.py`
- `xinyu_qq_gateway_smoke.py`
- `proactive_request_loop_smoke.py` if present
- `proactivity_scorer_smoke.py` if present

## Safety Rules

- No direct network sending from orchestrator.
- No stable personality writes from initiative feedback.
- No raw private memory text in lifecycle JSONL.
- No QQ delivery without existing outbox claim/ack.
- No owner-local file/code action without explicit owner approval.
- No new candidate can supersede an unresolved active owner thread unless it is safety-related.
- No broad bridge rewrite.

## Rollback

Each phase must be independently disableable.

Suggested flags:

```text
XINYU_INITIATIVE_ORCHESTRATOR=0
XINYU_INITIATIVE_DRY_RUN=1
XINYU_INITIATIVE_DESKTOP_DELIVERY=0
XINYU_INITIATIVE_QQ_METADATA=0
```

Rollback should require only disabling the flags and leaving trace files unused.

## First Concrete Patch Set

Patch set 1 should include only:

- `xinyu_initiative_orchestrator.py`
- `tests/test_initiative_orchestrator.py`
- a tiny optional import/call in `xinyu_core_bridge.py`, guarded by dry-run flag

No desktop changes, no QQ changes, no delivery behavior change.

## Definition Of Done

The system is ready to leave shadow mode when:

- It records full lifecycle traces for at least candidate -> score -> gate.
- It can explain why it stayed silent.
- Duplicate and cooldown gates demonstrably work.
- Desktop delivery can be enabled without QQ sending.
- Feedback changes future score in tests.
- Status surfaces expose counts and posture without private content.


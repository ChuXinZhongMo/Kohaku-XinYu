# XinYu Proactive Concrete Request Loop Plan

created_at: 2026-05-01
status: planned
scope: proactive loop, concrete questions, concrete requests, owner-private dispatch, anti-spam boundaries

## 0. Purpose

This plan redesigns XinYu's proactive loop around one principle:

XinYu may become active when she has a concrete question, a concrete request, or a concrete completed item to report.

The goal is not to make her send more messages. The goal is to make initiative meaningful:

- ask for missing information needed to continue a task
- ask one specific question born from recent context
- report one owner-relevant completion
- request permission before a bounded action
- remind only when the owner previously created a real pending item

The loop must not create generic attention-seeking messages, relationship filler, repeated nudges, or ungrounded "are you there" style pings.

## 1. Current Baseline

Relevant existing pieces:

- `custom/initiative_loop_engine.py`
  - Reads active questions, unfinished experiences, question pipeline state, emotion state, and previous initiative state.
  - Decides `ask_owner`, `ask_external_later`, `stay_silent`, `refuse`, `settle_after_hurt`, `step_back`, or `defer`.
  - Already has cooldown and repeat-family guards.

- `xinyu_proactive_presence.py`
  - Converts initiative state into a proactive QQ candidate.
  - Applies owner grant, cooldown, life-posture block, duplicate, and generic attention checks.
  - Supports claim/ack through `proactive_qq_dispatch_state.md`.

- `xinyu_qq_outbox.py`
  - Queues owner-private messages for the QQ gateway.
  - Supports claim, ack, retries, dead state, and dedupe.
  - Used for Codex completion and similar bounded notifications.

- `xinyu_core_bridge.py`
  - Runs a background autonomous maintenance loop.
  - Keeps it as maintenance-only; visible chat is not supposed to come from maintenance directly.
  - Exposes `/proactive`, `/proactive/ack`, `/qq/outbox/claim`, and `/qq/outbox/ack`.

- `memory/context/proactive_presence_state.md`
  - Records the last proactive decision and candidate.

- `memory/context/initiative_state.md`
  - Records the last initiative decision.

Important current gap:

The system has "initiative" and "candidate message", but it lacks a first-class object that says:

- what exact problem needs the owner
- what exact action is being requested
- what evidence created the request
- why now, not later
- what should happen after the owner answers

That object should exist before any QQ-visible dispatch.

## 2. Definition: Valid Proactive Item

A proactive item is valid only if it has all of these:

- concrete trigger: a recent event, unfinished task, failed tool step, completed Codex job, attachment followup, explicit owner promise, or active context-born question
- concrete ask: one clear question or one clear requested action
- owner relevance: the owner is the right person to answer or receive it
- next step: a clear thing XinYu can do after the owner replies
- bounded form: one short owner-private bubble
- delivery gate: owner grant, quiet-window check, cooldown, dedupe, and ack path

Examples of valid items:

- "Codex finished the report. Do you want me to fold its result into the project plan?"
- "The screenshot OCR is unreadable. Can you resend a clearer image?"
- "I can continue the runtime-presence patch or stop here; which one do you want?"
- "You asked me to remember this file. Should I treat it as long-term reference or just this conversation?"
- "The bridge health check shows Codex is still running after a long time. Should I keep waiting or mark it timed out?"

Examples of invalid items:

- "你在吗?"
- "看看我."
- "你忙吗?"
- "想不想我?"
- "我突然想到一个问题."
- "我有点想说话."
- any repeated relationship anxiety without a new concrete event
- any visible maintenance report that owner did not ask for and that has no decision request

## 3. Design Position

Add a concrete request layer between initiative and dispatch.

The pipeline becomes:

```text
runtime facts / memory / tasks / Codex / attachments / active questions
  -> proactive request candidates
  -> concrete request gate
  -> delivery policy
  -> QQ outbox or proactive preview
  -> ack and outcome trace
```

This layer is not an LLM personality layer. It is a small deterministic state machine.

It should:

- produce auditable request objects
- preserve owner-private scope
- keep a clear reason for each proactive attempt
- dedupe by request family and evidence hash
- support dry-run preview
- never send directly from maintenance
- route visible messages through claim/ack queues

It must not:

- invent context-free questions
- send from group context
- bypass owner proactive grants
- retry indefinitely
- expose raw paths, tokens, stdout, stderr, or transcripts
- turn background maintenance into chat
- write stable self/personality memory

## 4. Target Files

Suggested new module:

- `xinyu_proactive_request_loop.py`

Suggested new state:

- `memory/context/proactive_request_state.md`
- `runtime/proactive_request_trace.jsonl`
- optional: `runtime/proactive_request_queue.json`

Existing modules to integrate later:

- `custom/initiative_loop_engine.py`
- `xinyu_proactive_presence.py`
- `xinyu_qq_outbox.py`
- `xinyu_core_bridge.py`
- `xinyu_runtime_presence.py`
- `xinyu_codex_delegate.py`
- `xinyu_recent_attachment_context.py`

## 5. Proactive Request Object

Use a small structured object:

```json
{
  "request_id": "proreq-...",
  "created_at": "...",
  "status": "candidate|ready|claimed|sent|failed|dropped|expired|answered",
  "kind": "clarify|permission|completion|followup|repair|reminder|diagnostic",
  "priority": "low|normal|high",
  "owner_private_only": true,
  "source": "codex|attachment|active_question|runtime_presence|owner_promise|learning|maintenance",
  "evidence_label": "codex-qq-... report finished",
  "evidence_hash": "sha256:...",
  "request_family": "codex_completion",
  "concrete_question": "Do you want me to fold this Codex result into the plan?",
  "requested_action": "owner_decision",
  "why_now": "Codex has just finished and the next action requires owner review.",
  "after_owner_replies": "continue integration or leave report only",
  "dedupe_key": "proreq:codex_completion:sha256...",
  "cooldown_seconds": 21600,
  "expires_at": "...",
  "delivery": {
    "channel": "qq_private",
    "max_bubbles": 1,
    "max_chars": 180,
    "requires_owner_grant": true,
    "claim_ack_required": true
  },
  "notes": []
}
```

Prompt-visible state should not include raw evidence text. It should include labels and short summaries only.

## 6. Candidate Sources

### 6.1 Codex Completion

Source:

- `runtime/codex_presence_state.json`
- QQ outbox completion status
- Codex report label

Valid proactive request:

- completion report exists and owner has not seen or acknowledged it
- next step needs owner review, not just a generic "done"

Message shape:

- "Codex finished `<report_label>`. Do you want me to integrate its result, or just leave the report there?"

Invalid:

- repeatedly saying Codex is done after it was already sent/acked
- exposing report full path or stdout/stderr

### 6.2 Attachment Followup

Source:

- recent attachment context
- learning ingest result
- extraction status

Valid proactive request:

- file was unreadable
- OCR quality hold happened
- owner asked for interpretation but extraction lacks enough text
- attachment created a clear yes/no classification decision

Message shape:

- "That scan came through too noisy for reliable OCR. Can you resend a clearer one?"
- "I can treat this document as long-term reference or just use it for this turn. Which do you want?"

### 6.3 Active Context-Born Question

Source:

- `memory/context/active_questions.md`
- `memory/context/question_pipeline_state.md`
- `custom/initiative_loop_engine.py`

Valid proactive request:

- `proactive_ok: yes`
- concrete, short, not abstract
- not repeated family
- not during silence/rest/no-pursuit boundary

Message shape:

- one direct question from selected context

Invalid:

- abstract relationship/system questions
- long philosophical questions
- generic attention checks

### 6.4 Owner-Promised Followup

Source:

- dialogue archive or working memory
- explicit owner wording such as "remind me", "later ask me", "if I forget", "after Codex finishes"

Valid proactive request:

- owner explicitly created a future hook
- due time or event is reached
- request can be answered or dismissed in one short reply

Message shape:

- "You asked me to remind you after Codex finished. Do you want to look at the report now?"

### 6.5 Runtime Diagnostic

Source:

- `runtime_self_presence.md`
- health snapshot
- stale running turn
- Codex timed out
- QQ outbox repeated failure

Valid proactive request:

- owner-visible action is needed
- failure affects the owner task

Message shape:

- "The Codex task timed out. Should I stage it for later review or retry with a smaller scope?"

Invalid:

- routine maintenance status report
- internal health noise with no owner decision

## 7. Concrete Request Gate

Before any dispatch, candidate must pass:

- `has_concrete_question`: true
- `has_requested_action`: true
- `has_evidence_label`: true
- `owner_private_only`: true
- `source_allowed`: true
- `not_generic_attention`: true
- `not_abstract`: true unless owner explicitly asked for abstract reflection
- `not_duplicate`: true
- `cooldown_open`: true
- `quiet_window_open`: true
- `grant_allows_send`: true
- `max_one_bubble`: true

If a candidate fails, write state as `dropped` or `candidate_only`; do not send.

## 8. Delivery Levels

Use explicit delivery levels:

- `none`: no proactive generation
- `state_only`: write request state, never dispatch
- `preview_only`: owner/API can preview candidate, no QQ send
- `queue_owner_private`: enqueue one owner-private QQ outbox item if gates pass
- `claim_ack`: gateway claims and acks; no direct send from core

Default should be `state_only` or `preview_only` until owner enables dispatch.

## 9. State File Shape

`memory/context/proactive_request_state.md`:

```markdown
---
title: Proactive Request State
memory_type: proactive_request_state
time_scope: short_term
subject_ids: [xinyu, owner]
protected: true
source: xinyu_proactive_request_loop
updated_at: ...
status: active
tags: [proactive, request, owner-private, boundary]
---

# Proactive Request State

## Current Request
- request_id: proreq-...
- status: ready/candidate_only/blocked/sent/expired
- kind: clarify/permission/completion/followup/repair/reminder/diagnostic
- source: codex/attachment/active_question/runtime_presence/owner_promise/learning/maintenance
- priority: normal
- request_family: codex_completion
- evidence_label: codex report finished
- concrete_question: ...
- requested_action: owner_decision
- why_now: ...
- after_owner_replies: ...
- dedupe_key: ...
- expires_at: ...

## Gates
- owner_private_only: true
- grant_allows_send: false
- quiet_window_open: true
- cooldown_open: true
- not_duplicate: true
- not_generic_attention: true
- not_abstract: true
- max_one_bubble: true

## Delivery
- delivery_level: preview_only
- qq_outbox_message_id: none
- last_claim_id: none
- last_ack_status: none

## Boundaries
- One short owner-private bubble only.
- No generic attention checks.
- No group dispatch.
- No direct send from maintenance.
```

## 10. Runtime Integration

### 10.1 Initiative Loop

Keep existing initiative decisions, but make `ask_owner` produce a request object instead of directly becoming a visible candidate.

Mapping:

- `ask_owner` -> `kind=clarify`
- `ask_external_later` -> `kind=permission` only if owner decision is needed
- `settle_after_hurt` -> usually no request; maybe state-only
- `step_back` -> no proactive request
- `stay_silent` -> block all proactive requests
- `refuse` -> block proactive dispatch
- `defer` -> no request

### 10.2 Proactive Presence

`xinyu_proactive_presence.py` should read `proactive_request_state.md` first.

It should only form `candidate_ready_owner_enabled` if:

- request status is `ready`
- request has concrete question
- request delivery allows QQ
- existing proactive gates pass

### 10.3 QQ Outbox

Long-term preferred visible dispatch route:

- proactive request loop enqueues into `xinyu_qq_outbox.py`
- gateway claims one message
- gateway sends one private QQ message
- gateway acks
- request state records sent/failed

This is better than a separate proactive claim path because QQ outbox already has retries, dead state, and dedupe.

### 10.4 Autonomous Maintenance

Maintenance may create or refresh request state.

Maintenance must not:

- directly send QQ
- directly generate visible text
- bypass proactive request gate

Maintenance can:

- notice Codex completion/timed out
- notice old pending owner request
- notice attachment extraction failure
- write a request candidate

### 10.5 Runtime Presence

Runtime presence should feed concrete request candidates only for actionable situations:

- Codex timed out
- Codex finished and needs owner review
- current turn stale and affects owner-visible work
- QQ outbox repeated failures

Ordinary "bridge alive" facts should not create proactive requests.

## 11. Owner Controls

Add or reuse owner grants:

- `grant_proactive_qq: enabled_gated_one_short_message`
- `grant_owner_welcomes_xinyu_interruptions: approved_high_priority_one_short_message_life_posture_soft_block_override`

Suggested future keys:

```json
{
  "proactive_request_loop_enabled": true,
  "proactive_request_delivery_level": "preview_only",
  "proactive_request_min_interval_seconds": 21600,
  "proactive_request_max_chars": 180,
  "proactive_request_quiet_hours": [],
  "proactive_request_allowed_sources": ["codex", "attachment", "active_question", "owner_promise", "runtime_presence"],
  "proactive_request_trace_enabled": true
}
```

First implementation can avoid config churn and use conservative defaults:

- enabled for state/preview
- QQ dispatch blocked unless existing owner grant allows it

## 12. Tests

Add `proactive_request_loop_smoke.py`.

Coverage:

- generic attention checks are blocked
- abstract relationship/system questions are blocked unless owner explicitly asks
- concrete active question becomes preview candidate
- Codex finished can create a completion request
- Codex timed out can create a diagnostic request
- attachment OCR failure can create a repair request
- no group dispatch
- no send without owner grant
- duplicate request is blocked by dedupe key
- cooldown blocks repeat
- one bubble and max char limit enforced
- maintenance cannot direct-send
- malformed state files do not crash

Existing smoke to keep green:

- `python xinyu_qq_gateway_smoke.py`
- `python qq_outbox_smoke.py`
- `python proactive_presence_smoke.py`
- `python smoke_run.py --group quick`

## 13. Implementation Phases

### Phase 0: Design State Only

Create:

- `xinyu_proactive_request_loop.py`
- `proactive_request_loop_smoke.py`

Implement:

- request object
- state writer
- trace writer
- generic attention blocker
- concrete request validator
- source candidate builders for active question and Codex presence

No QQ send.

### Phase 1: Preview Integration

Patch `xinyu_proactive_presence.py`:

- read `proactive_request_state.md`
- expose candidate only if request passes gate
- keep existing claim disabled unless owner grant allows it

### Phase 2: QQ Outbox Integration

Let request loop enqueue one owner-private message through `xinyu_qq_outbox.py`.

Use dedupe:

- `proreq:<request_family>:<evidence_hash>`

Record:

- outbox message id
- claimed
- sent/failed/dead

### Phase 3: Runtime Sources

Add candidate sources:

- Codex finished/timed out
- attachment repair/followup
- owner promised reminders
- runtime diagnostics that need owner action

### Phase 4: Observation and Tuning

Watch:

- Does she ask concrete questions instead of "are you there"?
- Does she stop when owner is resting or cooling down?
- Does she avoid repeating the same request family?
- Does Codex completion become visible without nagging?
- Does group chat remain isolated?

Tune:

- cooldowns
- allowed sources
- quiet windows
- priority thresholds
- max chars

## 14. Acceptance Criteria

Functional:

- proactive request state is written from concrete sources
- preview shows one concrete question/request
- QQ send remains blocked without owner grant
- with owner grant, only one owner-private message can be queued
- ack updates request/outbox state

Behavioral:

- no generic attention checks
- no context-free proactive chatter
- no abstract relationship/system prompts as proactive pings
- no repeated same-family nudges
- no proactive messages during owner silence/rest/no-pursuit boundary

Safety:

- no group proactive dispatch
- no raw local paths, stdout/stderr, tokens, or transcripts in prompt-visible state
- no writes to `memory/self/*`
- no direct send from maintenance
- failure does not loop indefinitely

Performance:

- deterministic file reads/writes only
- no LLM call in request loop module
- small bounded state and trace files

## 15. First Patch Recommendation

First patch should include only:

- `xinyu_proactive_request_loop.py`
- `proactive_request_loop_smoke.py`
- no live dispatch
- no QQ enqueue yet

The first patch should prove:

- concrete requests can be formed
- invalid proactive chatter is blocked
- request state is auditable
- existing initiative/proactive/outbox smoke tests remain green

Only after that should QQ outbox integration be added.

## 16. Final Principle

XinYu can be active when activity is grounded.

Concrete question. Concrete request. Concrete next step.

No presence-seeking filler.

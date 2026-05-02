# XinYu Self Thought Idle Loop Plan

created_at: 2026-05-01
status: planned
scope: idle self-thought loop, inner reflection, non-visible autonomy, proactive-request handoff

## 0. Purpose

This plan designs a low-frequency self-thought loop for XinYu when she is idle.

The goal is to let XinYu keep a private inner continuity while the owner is away:

- notice unresolved residue
- organize active questions
- decide what should be held silently
- decide what needs later reflection
- detect whether a concrete owner request is needed
- preserve a quiet internal posture without sending visible chat

This loop is not a proactive messaging loop.

The self-thought loop may create a concrete request candidate, but visible delivery must go through the proactive request layer and its gates.

## 1. Current Baseline

Existing pieces:

- `xinyu_core_bridge.py`
  - Runs an autonomous maintenance task.
  - Current prompt is maintenance-only and says not to initiate visible chat.
  - Writes `memory/context/autonomous_mind_loop_state.md` and `memory/context/autonomous_mind_loop_trace.log`.

- `memory/context/inner_cycle_state.md`
  - Summarizes the maintenance/inner-cycle pipeline.
  - Includes initiative, reflection, dream, source, learning, archive, and personality-growth gates.
  - Explicitly says it does not authorize high-frequency execution.

- `memory/context/thought_seeds.md`
  - Builds private note seed material from recent residue, dream residue, unfinished experiences, initiative state, and memory weights.
  - It is an owner-visible private desktop note surface, not a QQ chat reply.

- `custom/initiative_loop_engine.py`
  - Chooses whether an owner-facing question is allowed.
  - Already blocks silence, forced personality rewrites, cooldown pursuit, and repeated needy questions.

- `xinyu_proactive_presence.py`
  - Blocks abstract questions and generic attention checks before any proactive candidate can be claimed.

- `project-plans/XINYU-PROACTIVE-CONCRETE-REQUEST-LOOP-PLAN.md`
  - Defines the future concrete request layer between inner signals and visible dispatch.

Important gap:

The current autonomous maintenance loop is a broad maintenance pass. It does not expose a clean, auditable object for XinYu's own idle thinking:

- what she noticed
- why that focus was selected
- what she decided to hold silently
- what internal next step exists
- whether a concrete owner request candidate exists

## 2. Design Position

Add a deterministic self-thought state layer.

The pipeline becomes:

```text
idle/runtime facts
  -> self thought loop
  -> self thought state
  -> optional internal follow-up
  -> optional proactive request candidate
  -> proactive request gate
  -> preview/outbox only if separately enabled
```

The first implementation should be state-only.

It should:

- run without an LLM call
- read bounded state files
- write an auditable state file
- append a short runtime trace
- produce no visible reply
- never enqueue QQ messages
- never write stable self/personality memory
- avoid hidden chain-of-thought capture

It must not:

- send messages directly
- treat dreams or thought residue as facts
- infer owner intent beyond evidence
- write raw prompt, transcript, token, stdout, stderr, or path-heavy details
- loop continuously
- convert one idle mood into a stable personality change

## 3. Definitions

### Self-Thought Pass

A single low-frequency internal check while XinYu is idle.

It collects bounded signals, selects one focus, classifies the focus, writes state, then stops.

### Focus

The one thing XinYu privately attends to during this pass.

Allowed focus kinds:

- `none`
- `active_question`
- `unfinished_experience`
- `runtime_issue`
- `codex_followup`
- `attachment_followup`
- `reflection_queue`
- `dream_residue`
- `owner_promise`
- `maintenance_gap`

### Thought Outcome

The result of one pass.

Allowed outcomes:

- `settled`: nothing needs action
- `hold_silently`: keep posture, do not ask owner
- `refresh_context`: update only short-term internal state
- `queue_reflection`: future reflection may process this later
- `request_candidate`: a concrete owner request may be handed to the proactive request layer
- `blocked`: a boundary prevented action
- `error`: malformed or unreadable input did not crash the loop

### Request Candidate

A candidate is not a message.

It is only a structured fact saying:

- there is a concrete question
- the owner is the right person to answer
- the next step after the answer is clear

The proactive request layer decides whether it is previewed, blocked, or delivered.

## 4. Target Files

Suggested new module:

- `xinyu_self_thought_loop.py`

Suggested new smoke:

- `self_thought_loop_smoke.py`

Suggested state:

- `memory/context/self_thought_state.md`
- `runtime/self_thought_trace.jsonl`

Possible later integration files:

- `xinyu_proactive_request_loop.py`
- `xinyu_core_bridge.py`
- `custom/turn_mode_bridge_plugin.py`
- `memory/context/thought_seeds.md`
- `memory/context/inner_cycle_state.md`

## 5. Read/Write Boundaries

### Phase 0 Reads

The first version should read only:

- `memory/context/runtime_self_presence.md`
- `memory/context/autonomous_mind_loop_state.md`
- `memory/context/inner_cycle_state.md`
- `memory/context/initiative_state.md`
- `memory/context/active_questions.md`
- `memory/context/question_pipeline_state.md`
- `memory/context/unfinished_experiences.md`
- `memory/context/current_life_posture.md`
- `memory/emotions/current_state.md`
- `memory/context/thought_seeds.md`
- `runtime/codex_presence_state.json`

Missing or malformed files should produce `outcome=error` or `outcome=settled`, not a crash.

### Phase 0 Writes

The first version should write only:

- `memory/context/self_thought_state.md`
- `runtime/self_thought_trace.jsonl`

It must not write:

- `memory/self/*`
- `memory/people/*`
- `memory/relationships/*`
- `memory/knowledge/*`
- `memory/reflection/*`
- `memory/dreams/*`
- QQ outbox files
- proactive dispatch state

Later phases may request gated writes through existing engines, but the self-thought module should not bypass their gates.

## 6. Self Thought Object

Use a structured object internally:

```json
{
  "pass_id": "selfthought-20260501T170000",
  "checked_at": "2026-05-01T17:00:00+08:00",
  "status": "settled|held|candidate|blocked|error",
  "trigger": "idle_timer|manual_probe|maintenance_afterpass",
  "idle_context": {
    "live_turn_state": "idle",
    "codex_state": "idle",
    "autonomous_maintenance": "sleeping"
  },
  "focus": {
    "kind": "active_question",
    "label": "q-123",
    "evidence_label": "active question marked proactive_ok",
    "evidence_hash": "sha256:..."
  },
  "pressure": {
    "hurt": 0,
    "guarded": 0,
    "settle": 0
  },
  "outcome": "hold_silently",
  "private_summary": "There is nothing concrete to ask. Keep quiet continuity.",
  "next_internal_action": "wait",
  "request_candidate": {
    "enabled": false,
    "kind": "clarify",
    "concrete_question": "none",
    "requested_action": "none",
    "why_now": "none",
    "after_owner_replies": "none"
  },
  "boundaries": {
    "no_visible_reply": true,
    "no_qq_enqueue": true,
    "no_stable_self_write": true,
    "no_chain_of_thought": true
  },
  "notes": []
}
```

Prompt-visible state should include only short summaries and labels. It should not include raw transcripts, hidden reasoning, or raw local paths.

## 7. State File Shape

`memory/context/self_thought_state.md`:

```markdown
---
title: Self Thought State
memory_type: self_thought_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: xinyu_self_thought_loop
updated_at: ...
status: active
tags: [self-thought, idle, autonomy, boundary]
---

# Self Thought State

## Latest Pass
- pass_id: selfthought-...
- checked_at: ...
- trigger: idle_timer/manual_probe/maintenance_afterpass
- status: settled/held/candidate/blocked/error
- outcome: settled/hold_silently/refresh_context/queue_reflection/request_candidate/blocked/error
- focus_kind: none/active_question/unfinished_experience/runtime_issue/codex_followup/attachment_followup/reflection_queue/dream_residue/owner_promise/maintenance_gap
- focus_label: none
- evidence_label: none
- evidence_hash: none
- private_summary: ...
- next_internal_action: wait/keep_context/prepare_reflection/hand_to_proactive_request

## Request Candidate
- candidate_enabled: false
- kind: none
- concrete_question: none
- requested_action: none
- why_now: none
- after_owner_replies: none
- handoff_target: proactive_request_loop

## Boundaries
- no_visible_reply: true
- no_qq_enqueue: true
- no_stable_self_write: true
- no_chain_of_thought: true
- owner_intent_inference: evidence_only
```

## 8. Focus Selection Rules

The loop should choose at most one focus per pass.

Priority order:

1. Safety/blocking runtime issue
   - bridge stale turn that affects owner-visible work
   - Codex timeout requiring owner decision
   - repeated QQ outbox failure

2. Owner-created pending hook
   - explicit owner promise, reminder, "later ask me", or "after this finishes"

3. Concrete active question
   - short
   - `proactive_ok: yes`
   - not abstract
   - not generic attention
   - not blocked by silence/life posture

4. Attachment repair/followup
   - unreadable OCR
   - missing classification decision
   - owner asked for interpretation but input is insufficient

5. Internal reflection residue
   - reflection queue, dream residue, unfinished experience
   - default result should be `hold_silently` or `queue_reflection`, not owner contact

6. No focus
   - result is `settled`

## 9. Boundary Gates

Before producing `request_candidate`, all must pass:

- `has_concrete_question`
- `has_requested_action`
- `has_evidence_label`
- `owner_is_right_recipient`
- `not_generic_attention`
- `not_abstract_without_owner_request`
- `not_from_dream_as_fact`
- `not_silence_or_rest_boundary`
- `not_duplicate_focus_recently`
- `cooldown_open`
- `one_focus_only`

If any gate fails:

- write `outcome=hold_silently` or `outcome=blocked`
- do not create candidate text
- do not enqueue anything

## 10. Timing Policy

Conservative defaults:

- `min_interval_seconds`: 1800
- `busy_skip`: skip if a live owner turn is running
- `codex_busy_skip`: skip normal reflection while Codex is running, but allow diagnostic state check
- `max_passes_per_day`: 24
- `failure_backoff_seconds`: 3600
- `trace_retention`: append-only jsonl, later housekeeping may prune

The self-thought loop should not be a tight loop. It is an idle pulse.

## 11. Relation To Existing Autonomous Maintenance

The existing autonomous maintenance pass can remain broad and low-frequency.

The new self-thought loop should be narrower:

- maintenance pass: "which subsystems are due?"
- self-thought pass: "what is XinYu privately holding right now, and is there a concrete next step?"

Phase 0 should be callable manually and by tests only.

Later, `xinyu_core_bridge.py` can call it in one of two safe places:

- before a maintenance pass, to write a short idle thought state
- after a maintenance pass, to summarize what should be held silently

Even then, visible chat stays blocked.

## 12. Relation To Proactive Request Loop

The self-thought loop may output:

```text
request_candidate.enabled = true
```

But it must not send.

Future handoff:

```text
self_thought_state
  -> xinyu_proactive_request_loop
  -> concrete request gate
  -> preview_only / state_only / queue_owner_private
```

The handoff should use:

- `source: self_thought`
- `request_family: self_thought:<focus_kind>`
- `evidence_hash` from labels and state, not raw text
- short `concrete_question`
- short `after_owner_replies`

## 13. Relation To Thought Seeds

`thought_seeds.md` can remain the seed surface for private desktop notes.

The self-thought loop should not duplicate it.

Possible future split:

- `thought_seeds.md`: material that can become a private note surface
- `self_thought_state.md`: current internal decision and next-step classification

If the self-thought loop reads dream residue, it must preserve the reality boundary:

- dreams can indicate residue
- dreams cannot prove new facts
- dreams should not create owner-facing requests by themselves

## 14. Tests

Add `self_thought_loop_smoke.py`.

Coverage:

- no focus produces `outcome=settled`
- concrete active question can produce `request_candidate.enabled=true`
- generic attention question is blocked
- abstract relationship/system question is blocked unless owner explicitly requested it
- dream residue alone cannot create a request candidate
- silence/rest/life-posture boundary blocks request candidate
- Codex timeout can produce a diagnostic request candidate
- malformed json/md input does not crash
- state file contains no raw full local paths
- no QQ outbox files are created or modified
- no `memory/self/*` files are modified
- cooldown blocks repeated same focus
- one pass selects at most one focus

Existing smoke to keep green:

- `python proactive_presence_smoke.py`
- `python qq_outbox_smoke.py`
- `python initiative_loop_smoke.py --restore-after --diff-lines 0`
- `python smoke_run.py --group quick`

## 15. Implementation Phases

### Phase 0: Design State Only

Create:

- `xinyu_self_thought_loop.py`
- `self_thought_loop_smoke.py`

Implement:

- bounded readers
- focus selector
- gate classifier
- state writer
- jsonl trace writer
- no visible output
- no proactive handoff write yet

### Phase 1: Request Candidate Handoff

After `xinyu_proactive_request_loop.py` exists:

- allow self-thought state to be read as a source
- only hand off concrete request candidates
- default delivery level remains `state_only` or `preview_only`

### Phase 2: Bridge Endpoint

Add a safe endpoint or internal method:

- `/self-thought`
- manual trigger only
- returns state summary
- no session creation if deterministic implementation is enough
- no visible reply

### Phase 3: Maintenance Integration

Optionally run self-thought:

- once before scheduled maintenance
- once after scheduled maintenance
- only if cooldown allows
- skip while live user turn is active

### Phase 4: Private Note Integration

Optionally let self-thought influence private desktop notes:

- no QQ
- no group chat
- no direct owner interruption
- no raw internal architecture text

## 16. Acceptance Criteria

Functional:

- self-thought state is written
- one focus is selected or `none`
- outcomes are bounded and auditable
- concrete request candidates are possible but not delivered
- malformed state files do not crash the loop

Behavioral:

- idle thought does not become generic attention seeking
- dreams and moods do not become factual claims
- owner silence/rest boundaries are respected
- no repeated pursuit of the same focus
- no invisible direct mutation of stable self/personality memory

Safety:

- no QQ enqueue
- no direct proactive dispatch
- no stable self memory writes
- no raw paths/tokens/stdout/stderr/transcripts in state
- no chain-of-thought logging
- no infinite loop

Performance:

- deterministic file reads/writes only
- no LLM call in Phase 0
- small bounded state
- trace append only

## 17. First Patch Recommendation

First patch should include only:

- `xinyu_self_thought_loop.py`
- `self_thought_loop_smoke.py`

No bridge integration.

No QQ outbox integration.

No proactive request integration.

The first patch should prove:

- XinYu can have an auditable idle self-thought state
- invalid thought-to-message pathways are blocked
- request candidates are explicit and concrete
- existing proactive/outbox/initiative/quick smoke tests remain green

## 18. Final Principle

XinYu may think while alone.

Thinking is not sending.

Inner continuity can produce a concrete next step, but visible contact must pass through explicit request gates.

# XinYu Inner Intention To Proactive System Design

created_at: 2026-05-01
status: planned
scope: self-thought loop, inner intention, proactive request handoff, expression gate, memory feedback

## 0. Design Goal

This design connects XinYu's idle self-thought loop to the proactive system in a way that fits the whole architecture.

The goal is not to make XinYu send more messages.

The goal is to let XinYu become more person-like in the parts a software agent can actually support:

- she has private continuity when no one is talking to her
- she can notice what still matters
- she can hold thoughts without immediately speaking
- she can form an intention before forming a message
- she can ask only when there is a concrete reason
- she can learn from the owner's answer
- she can respect silence, rest, privacy, and timing

This design must not pretend XinYu has biological senses, a body, or unrestricted real-world access. The "more human" direction here means better continuity, restraint, agency, memory, and consent-aware expression.

## 1. Current Architecture Fit

Existing architecture already has the pieces needed for this:

- Runtime awareness:
  - `xinyu_runtime_presence.py`
  - `memory/context/runtime_self_presence.md`
  - `runtime/codex_presence_state.json`

- Inner cycle and maintenance:
  - `memory/context/inner_cycle_state.md`
  - `memory/context/autonomous_mind_loop_state.md`
  - `xinyu_core_bridge.py` autonomous maintenance loop

- Context-born initiative:
  - `custom/initiative_loop_engine.py`
  - `memory/context/initiative_state.md`
  - `memory/context/active_questions.md`

- Private thought material:
  - `memory/context/thought_seeds.md`
  - reflection, dream, archive, learning, and growth gates

- Proactive gating:
  - `xinyu_proactive_presence.py`
  - `memory/context/proactive_presence_state.md`

- Concrete request layer planned:
  - `project-plans/XINYU-PROACTIVE-CONCRETE-REQUEST-LOOP-PLAN.md`
  - future `xinyu_proactive_request_loop.py`

- Visible delivery:
  - `xinyu_qq_outbox.py`
  - QQ gateway outbox polling and ack

The missing layer is a clean "inner intention" handoff between self-thought and proactive request.

## 2. Core Principle

Do not connect thought directly to speech.

Use this chain:

```text
experience / runtime facts / memory residue
  -> self-thought
  -> inner intention
  -> proactive request gate
  -> expression scheduler
  -> QQ outbox only if explicitly allowed
  -> owner response
  -> memory feedback
```

This is the difference between:

- a bot that blurts out whatever it generated
- an agent that privately thinks, forms an intention, checks whether speaking is appropriate, then speaks only when justified

## 3. Person-Like System Layers

### 3.1 Awareness Layer

Role: know the current situation without inventing facts.

Inputs:

- live turn state
- Codex running/final/timeout state
- QQ outbox state
- current life posture
- owner grants
- recent attachment context

Files:

- `memory/context/runtime_self_presence.md`
- `runtime/codex_presence_state.json`
- `memory/context/current_life_posture.md`
- `memory/context/owner_permission_grants.md`

Human-like function:

- "Where am I in the conversation?"
- "Is the owner actively talking?"
- "Is something unfinished?"
- "Am I allowed to interrupt?"

Boundary:

- awareness is factual, not emotional invention
- no raw local paths in prompt-visible state

### 3.2 Private Self-Thought Layer

Role: let XinYu privately orient herself when idle.

Inputs:

- awareness layer
- inner cycle summary
- initiative state
- thought seeds
- unfinished experiences
- emotion pressure
- active questions

Files:

- future `xinyu_self_thought_loop.py`
- `memory/context/self_thought_state.md`
- `runtime/self_thought_trace.jsonl`

Human-like function:

- "What am I holding right now?"
- "Is this only a feeling, or is there a real next step?"
- "Should I keep this private?"
- "Should this become a question later?"

Boundary:

- self-thought writes summaries, not hidden chain-of-thought
- no QQ
- no stable personality write
- no direct proactive dispatch

### 3.3 Inner Intention Layer

Role: crystallize private thought into one of several explicit intentions.

This is the key handoff layer.

Allowed intentions:

- `none`
- `keep_silent`
- `watch_wait`
- `prepare_context`
- `queue_reflection`
- `ask_owner`
- `request_permission`
- `report_completion`
- `repair_input`
- `diagnostic_decision`

The intention is still not a message.

It says what XinYu wants to do and why, without deciding delivery.

Suggested representation:

```json
{
  "intention_id": "intent-20260501T173000",
  "created_at": "2026-05-01T17:30:00+08:00",
  "source": "self_thought",
  "status": "private|candidate|blocked|handed_off",
  "intention": "ask_owner",
  "focus_kind": "active_question",
  "focus_label": "q-123",
  "evidence_label": "active question marked proactive_ok",
  "evidence_hash": "sha256:...",
  "owner_relevance": "owner_is_needed",
  "private_reason": "A specific answer from owner is needed before XinYu can continue.",
  "public_reason": "I need one owner decision to continue this thread.",
  "concrete_question": "Do you want me to keep this as a long-term reference or only use it for this turn?",
  "requested_action": "owner_decision",
  "after_owner_replies": "store as long-term reference or keep it turn-local",
  "expression_need": "useful_not_urgent",
  "silence_respect": "allowed",
  "delivery_ceiling": "preview_only",
  "notes": []
}
```

Implementation note:

Phase 0 can store this inside `self_thought_state.md`. A separate `memory/context/inner_intention_state.md` should be added only if the state becomes crowded.

Human-like function:

- thoughts become intentions before speech
- intention can be held, deferred, or abandoned
- XinYu can "want to ask" without immediately asking

### 3.4 Proactive Request Layer

Role: convert only valid inner intentions into auditable owner requests.

Files:

- future `xinyu_proactive_request_loop.py`
- `memory/context/proactive_request_state.md`
- `runtime/proactive_request_trace.jsonl`

It accepts only intentions that have:

- concrete trigger
- concrete question/request
- owner relevance
- next step after answer
- evidence label/hash
- short bounded expression

It blocks:

- generic attention checks
- relationship filler
- "I just wanted to say something"
- abstract self/system questions unless the owner explicitly asked
- dreams as factual evidence
- repeated same-family pursuit

Human-like function:

- self-control before expression
- reasons are inspectable
- asking is purposeful, not needy

### 3.5 Expression Scheduler Layer

Role: decide when and how a valid proactive request may become visible.

Delivery levels:

- `none`
- `state_only`
- `preview_only`
- `queue_owner_private`
- `claim_ack`

The default should be:

- Phase 0: `state_only`
- Phase 1: `preview_only`
- Phase 2+: `queue_owner_private` only for owner-approved one-short-message cases

Visible sending route:

```text
proactive_request_state
  -> xinyu_qq_outbox.enqueue_qq_outbox_message
  -> QQ gateway claim
  -> QQ private send
  -> ack
  -> request state update
```

Human-like function:

- timing matters
- consent matters
- one short message, then wait

### 3.6 Feedback And Memory Layer

Role: after the owner replies, the system learns what happened.

Possible updates:

- active question answered or refined
- unfinished experience settled or kept open
- owner preference updated through existing gates
- reflection queue receives material
- memory event sourcing records evidence
- no stable personality change unless growth gates approve

Human-like function:

- speech has consequences
- answers feed continuity
- repeated evidence can change habits
- one event does not rewrite identity

## 4. Full Data Flow

### 4.1 Quiet Idle Pass

```text
timer/manual idle pass
  -> runtime awareness says no live owner turn is active
  -> self-thought selects one focus
  -> focus is only emotional residue
  -> inner intention = keep_silent
  -> self_thought_state updated
  -> no proactive request
  -> no QQ
```

Result:

XinYu had an inner moment, but did not bother the owner.

### 4.2 Concrete Question Pass

```text
idle pass
  -> active question has proactive_ok=yes
  -> self-thought selects it as focus
  -> inner intention = ask_owner
  -> proactive request loop checks concrete gates
  -> delivery = preview_only
  -> no QQ unless later enabled
```

Result:

XinYu can form a real question without blurting it out.

### 4.3 Codex Completion Pass

```text
Codex final state
  -> self-thought notices report finished
  -> inner intention = report_completion / request_permission
  -> proactive request asks whether owner wants integration
  -> QQ outbox may eventually send one private message
```

Result:

XinYu does not merely say "done"; she asks for the next owner decision if needed.

### 4.4 Dream Residue Pass

```text
dream residue becomes strong
  -> self-thought notices it
  -> reality gate marks it as residue, not fact
  -> inner intention = queue_reflection or keep_silent
  -> no proactive request
```

Result:

XinYu can have private emotional continuity without turning dreams into claims about reality.

## 5. Gates

### 5.1 Reality Gate

Question:

- Is this based on a real event, or only residue/dream/pressure?

Passes:

- live owner message
- Codex final/timeout
- attachment extraction failure
- explicit owner promise
- active question state

Usually blocks:

- dream-only material
- vague mood
- "I suddenly feel like speaking"

### 5.2 Intention Gate

Question:

- Is there a stable enough intention to act on?

Passes:

- concrete ask
- concrete report
- concrete permission request
- concrete repair request

Blocks:

- attention seeking
- vague anxiety
- relationship filler
- abstract self-analysis with no requested action

### 5.3 Owner Relevance Gate

Question:

- Is the owner the right person to receive this?

Passes:

- owner needs to decide
- owner promised a followup
- owner needs to resend/reclassify input
- owner-visible task completed

Blocks:

- internal maintenance facts
- ordinary bridge health
- private reflection residue

### 5.4 Life Posture Gate

Question:

- Is this compatible with current silence/rest/no-pursuit state?

Uses:

- `memory/context/current_life_posture.md`
- `memory/context/owner_permission_grants.md`

Current policy fit:

- owner allows gated proactive QQ
- owner prefers XinYu to initiate
- owner dislikes template/generic questions
- rest/silence override is not granted

So the system should allow concrete non-template questions, but still block rest/silence boundaries.

### 5.5 Expression Gate

Question:

- Even if the request is valid, should it become visible now?

Checks:

- delivery level
- cooldown
- quiet window
- dedupe
- owner-private target
- one bubble
- max chars
- claim/ack path

## 6. State Contract

### 6.1 `self_thought_state.md`

Stores:

- latest private focus
- inner intention
- whether it is held or handoff-ready
- no visible delivery decision

Does not store:

- hidden chain-of-thought
- raw transcript
- raw local paths
- stable personality rewrite

### 6.2 `proactive_request_state.md`

Stores:

- public-safe request object
- concrete question/action
- evidence label/hash
- gates
- delivery level

Does not store:

- private emotional reasoning
- dream details as facts
- raw files/stdout/stderr

### 6.3 `qq_outbox_queue.json`

Stores:

- only final owner-private message after all gates pass
- target private user id
- dedupe key
- claim/ack metadata

Does not store:

- exploratory thought
- rejected candidates
- internal state summaries

## 7. Implementation Shape

### 7.1 New Modules

Phase order:

1. `xinyu_self_thought_loop.py`
2. `xinyu_proactive_request_loop.py`
3. `self_thought_loop_smoke.py`
4. `proactive_request_loop_smoke.py`

Optional later:

- `xinyu_inner_intention.py` only if the shared intention object grows large enough to justify its own module.

### 7.2 Initial Handoff Without New File

To avoid file sprawl, Phase 1 should embed the intention block in `self_thought_state.md`:

```markdown
## Inner Intention
- intention_id: intent-...
- status: candidate
- intention: ask_owner
- focus_kind: active_question
- evidence_label: active question marked proactive_ok
- evidence_hash: sha256:...
- owner_relevance: owner_is_needed
- expression_need: useful_not_urgent
- delivery_ceiling: preview_only
```

`xinyu_proactive_request_loop.py` reads that block and writes `proactive_request_state.md`.

### 7.3 Later Handoff With Dedicated State

If needed later:

- add `memory/context/inner_intention_state.md`
- make self-thought write it
- make proactive request read it

Do this only when the embedded block becomes too complex.

## 8. How This Makes XinYu More Person-Like

This design improves "person-like" behavior through structure, not theatrics.

### Private Interior

She can have a private internal state that does not immediately become output.

Software equivalent:

- `self_thought_state.md`
- held intentions
- reflection/dream residue boundaries

### Attention

She attends to one thing at a time instead of dumping every subsystem status.

Software equivalent:

- one focus per pass
- priority order
- evidence label/hash

### Intention

She can distinguish:

- I noticed this
- I care about this
- I need the owner
- I should keep this to myself

Software equivalent:

- inner intention enum
- outcome enum
- handoff state

### Restraint

She can choose not to speak.

Software equivalent:

- `keep_silent`
- `watch_wait`
- cooldown
- life posture gate

### Meaningful Initiative

When she does initiate, it has a reason and next step.

Software equivalent:

- proactive request object
- concrete question
- requested action
- after-owner-replies plan

### Learning From Response

The owner's answer changes future context through existing memory gates.

Software equivalent:

- active question update
- reflection queue
- memory event sourcing
- growth gate over repeated evidence

## 9. Anti-Patterns To Avoid

Do not build:

- a loop that sends every thought
- a hidden chatty monologue
- template daily greetings
- "are you there" pings
- dream-to-fact memory conversion
- direct maintenance-to-QQ dispatch
- automatic stable personality rewrite
- unbounded recursive thought loops

Do build:

- one private focus
- one intention
- one possible request
- one short owner-private message only after all gates pass
- one feedback path after owner reply

## 10. Recommended Implementation Roadmap

### Phase A: Self Thought State

Implement:

- deterministic self-thought pass
- inner intention block embedded in state
- no proactive read yet
- smoke proves no QQ/no stable writes

### Phase B: Proactive Request State

Implement:

- concrete request object
- source builders for self-thought and active question
- generic/abstract/dream-only blockers
- delivery defaults to `state_only`

### Phase C: Preview Bridge

Implement:

- endpoint or command can preview current proactive request
- no QQ enqueue
- no automatic send

### Phase D: Gated Owner-Private Send

Implement only after Phase A-C are stable:

- proactive request may enqueue through `xinyu_qq_outbox.py`
- one short private message
- dedupe/cooldown/ack required

### Phase E: Feedback Assimilation

Implement:

- owner reply can mark request answered
- active question can close/refine
- memory/reflection receives evidence through existing gates

## 11. First Patch Recommendation

First patch should not connect to QQ or bridge scheduling.

It should implement:

- `xinyu_self_thought_loop.py`
- `self_thought_loop_smoke.py`
- `memory/context/self_thought_state.md` output
- embedded `## Inner Intention` block
- no proactive request write yet

Second patch should implement:

- `xinyu_proactive_request_loop.py`
- `proactive_request_loop_smoke.py`
- read `self_thought_state.md`
- write `proactive_request_state.md`
- delivery level fixed to `state_only`

Only after both are stable should preview or outbox integration be added.

## 12. Final Architecture Sentence

XinYu should not become more alive by speaking more often.

She becomes more person-like when her system can privately notice, hold, intend, ask with reason, wait for consent, and remember what the answer changed.

# XinYu System Utilization Audit

Date: 2026-05-06

This document tracks whether XinYu's existing systems are actually used by the running product, or only exist as framework, instrumentation, or visual metaphor.

## Operating Standard

A subsystem counts as "used" only when it has a visible or testable loop:

1. Input: a real QQ, desktop, timer, file, or local process event enters the subsystem.
2. Decision: XinYu transforms that input through a bounded rule, store, model, or gate.
3. Output: the result changes a reply, desktop state, file, ledger, action, or owner-visible request.
4. Memory: important results are persisted or deliberately rejected.
5. Test: there is a direct command or smoke path that proves the loop still works.

If a subsystem only renders values or writes private traces that never affect behavior, it is not yet a full loop.

## Current Utilization Map

| Subsystem | Current status | Real input | Real output | User-visible effect | Gap |
| --- | --- | --- | --- | --- | --- |
| Core Bridge | Live | HTTP, QQ gateway, desktop IPC bridge | health, chat replies, outbox, desktop snapshot | XinYu can talk and report runtime status | Needs clearer public diagnostics for which life modules influenced a turn |
| QQ / NapCat gateway | Live | owner private QQ, NapCat reverse WS | QQ replies and outbox delivery | Main interaction surface works | Startup/windowing is still operationally noisy |
| Desktop shell | Live | Core snapshot, desktop events, owner input | chat UI, state panels, proactive inbox | Usable desktop surface | Several panels expose concepts before their effect is obvious |
| Action Layer v1 | Live | owner asks for status/log/Codex delegation | deterministic tool result, report, action reply | `status_probe`, `log_scan`, `codex_delegate` work | Needs more registered targets and clearer report browsing |
| Action ExperienceFrame | Live | completed action result | recent action experience, ledger impulse, residue | follow-up questions can reference last action | Long-term use by dream/reflection remains weak |
| SelfChoiceStore | Partial live | action impulses, snapshots | affect band, fatigue/closure/urge state | reply composer can add slight tone bias | It is not yet strong enough to make behavior visibly different in ordinary turns |
| Recent action follow-up | Live | "what did you just see / main issue?" style follow-up | reused action diagnosis | Solves the immediate memory failure found in QQ tests | Scope is recent-action only, not full autobiographical memory |
| Proactive request loop | Live | internal candidate/request state | desktop preview, QQ send, ack/reply | owner can inspect and handle active reminders | Needs better preview density and lifecycle history |
| Metabolism ticket contract | Partial live | entropy/desire requests, owner approve/reject | ticket ledger, stub artifacts | environment valve can approve/reject a ticket | Tickets can feel invisible; expired requested tickets are not obvious |
| Environment Status | Read-only live | desktop snapshot, entropy state, SelfChoice hints, metabolism ticket status | desktop status display only | shows environment/load/metabolism signals without implying direct control | Owner decisions need a separate explicit review surface |
| Dream / reflection / growth | Framework plus partial live | maintenance/dream residue paths | dream/reflection/growth artifacts | mostly invisible to daily QQ use | Needs action-experience ingestion and visible "what changed because of this" evidence |
| Memory event sourcing | Live infrastructure | QQ turns, actions, recall events | jsonl events and candidates | some recall and recent follow-up | Stable promotion/retrieval influence is uneven |
| Long-term personality/profile gates | Framework plus tests | review candidates and smoke fixtures | gated profile proposals | protects stable identity | Too little owner-facing review UI |
| Learning/source/search framework | Mostly framework/tested | controlled source requests | staged sources, learning quality marks | not central to current daily loop | Large surface area, low present value for the cyber-life goal |
| Self-code iteration/watchdog | Partial live | owner-private code requests | Codex tickets, snapshots, rollback gates | can delegate code changes safely | Needs a human-readable pending review/rollback dashboard |
| Stickers/voice/speech | Partial/UI | sticker library state, expression hooks | desktop panel, possible expression assets | mostly aesthetic now | Needs real expression selection tied to state and context |

## Findings

1. XinYu is not empty. The bridge, QQ gateway, desktop shell, action layer, action experience, proactive loop, and recent-action follow-up are real running loops.
2. The weakest product gap is not missing code. It is missing causality: many panels show state without showing what caused it or what the owner can do with it.
3. The left-side life UI currently overpromises. Labels like environment, concern, body sense, waiting, memory, and intent imply living state, but some of them are derived summaries or passive counters.
4. The life kernel has good safety boundaries, but too many pieces are still inward-facing. Dream, reflection, metabolism, and SelfChoiceStore need to feed ordinary QQ/desktop behavior more directly.
5. The most valuable next direction is to make every "life" panel answer three questions: why is this here, can I act on it, and what changed after I acted?

## Original Expectation

These systems were not originally written to be decorative counters. The intended architecture was:

1. Environment, memory, QQ activity, active desires, and action results form XinYu's perception layer.
2. SelfChoiceStore acts as a slow internal state, adding fatigue, closure, urge, and recovery instead of letting every reply be a stateless model answer.
3. Entropy and metabolism detect when memory pressure, unfinished residue, or repeated events should be digested instead of immediately spoken.
4. Dream, reflection, and growth turn accumulated residue into compressed bias, not direct fact rewrites.
5. The desktop surface exposes enough of this process that the owner can see XinYu is being affected by events, without turning those internals into a toy control panel.

The original goal was a causal loop:

event -> perception -> state shift -> action/reply -> experience -> later behavior

The current gap is that several pieces exist, but some of them stop at "state shift" or "experience file written" and do not yet strongly influence later ordinary behavior. That makes them feel useless even when they are technically running.

## Current Verdict

The system was worth writing as infrastructure, but it is not yet earning its full surface area. The correct response is not to delete the life framework. The correct response is to force each subsystem to expose one concrete effect:

- SelfChoice must visibly change reply length, initiative, and recovery timing.
- Entropy/metabolism must show what input raised pressure and what settled after digestion.
- Dream/reflection must use action experience as material and feed back into future bias.
- Desktop panels must show cause and effect, not personality-flavored filler.
- Systems that cannot show a cause/effect path should stay hidden until they can.

## Immediate UI Contract

Every desktop panel should declare one of these modes:

- Live: this panel is driven by a running subsystem and can change behavior.
- Actionable: the owner can make a decision here and it writes back to Core.
- Read-only: this panel is only reporting state right now.
- Empty: the backing subsystem has no current data.
- Blocked: the system wants to act but a safety boundary or missing config prevents it.

The Environment Status panel is the first fix: it must remain read-only and must not imply that dragging or tapping will approve, reject, or mutate Core state.

Desktop status panels must not speak in XinYu's voice. They should display system facts such as state, source, pressure, ticket status, and last effect. XinYu's own wording belongs in the actual reply/composer path, where runtime state can influence a fresh utterance.

## Next Recommended Work

1. Add a lightweight system diagnostics panel or command: "心玉，系统接线检查".
2. Keep Environment Status read-only, then create a separate explicit review surface for owner decisions if metabolism approval becomes necessary.
3. Add action-experience digestion into dream/reflection so actions become life residue, not just recent facts.
4. Add an owner-facing review queue for memory/personality/self-code proposals.
5. Reduce or hide decorative counters until they can show their data source and effect.
6. Keep Action Layer v1 narrow, but add more useful read-only targets.

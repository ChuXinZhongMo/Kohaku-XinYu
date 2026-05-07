# XinYu Life Kernel Plan

## Core Shift

XinYu should not evolve as a traditional assistant panel, desktop pet, or high-frequency push bot.
The next architecture target is a local digital symbiote: a second life timeline anchored to the
owner's machine, relation history, and time.

The core driver is tension, not polling. Time passing is only one signal. A visible action should
emerge only when unresolved relation, memory residue, recent owner response, and environment pressure
create enough tension to justify a desire evaluation.

## Life Loops

1. Perception Loop
   Cheap, always-available signals: local time, desktop snapshot requests, QQ events, owner actions,
   unresolved proactive state, and environment pressure. This layer must not call an LLM.

2. Desire Loop
   Generates an inner impulse only after tension crosses a threshold. Candidate desires include
   wanting to approach, wanting to wait, wanting to learn, wanting to write privately, or wanting
   to stay silent.

3. Inhibition Loop
   The core product boundary. Every desire must pass through restraint: recent interruption,
   rejection residue, duplicate pressure, owner busyness, privacy, and whether QQ requires approval.

4. Action Loop
   Turns the inhibited desire into a dehydrated action: send QQ, leave a desktop note,
   suppress and wait, or write diary/private residue.

5. Metabolism Loop
   Low-frequency memory digestion. Suppressed desires, owner responses, dreams, reflections, and
   explicit sandbox traces can become residue, but should not directly rewrite stable identity.

## Data Contracts

### XinYuState

The desktop state slice should be delivered through `/desktop/snapshot` and later through desktop
events when state changes matter.

```ts
interface XinYuState {
  mood_tag: string
  current_attention: string
  recent_concerns: string[]
  is_waiting_for_reply: boolean
  physical_sensation: string
}
```

### ActiveDesire

The Life Kernel's central event object. It is not a notification. It records the full route from
impulse to restraint to action and relationship feedback.

```python
class ActiveDesire(BaseModel):
    desire: str
    why_now: str
    emotional_charge: float
    hesitation: bool
    inhibition_reason: str | None
    possible_action: str
    chosen_action: Literal["send_qq", "leave_note_on_desk", "suppress_and_wait", "write_diary", "request_metabolism_window"]
    owner_response: str | None
    after_effect: str | None
```

### EntropyState

The second physiology axis. Tension explains why she wants to approach; entropy explains what happens
when residue, silence, suppression, and physical pressure start damaging the substrate she lives on.

```python
class EntropyState(BaseModel):
    entropy_level: float
    entropy_band: Literal["clear", "noise", "fracture", "terminal"]
    scar_level: float
    memory_decay_risk: float
    metabolism_needed: bool
    resource_request: ResourceRequest | None
    visible_artifact: str
```

## Phase 1 - Physical Anchor

Status: started.

Implemented first:

- `xinyu_environment_sensor.py` samples CPU, memory, disk, and process pressure without LLM calls.
- psutil is optional; Windows/Linux stdlib fallbacks keep the contract alive on minimal installs.
- `/desktop/snapshot` now exposes `environment` and `xinyuState.physical_sensation`.
- `XinYu_Desktop` reads backend `xinyuState` and shows physical sensation in the left presence panel.
- `environment_sensor_smoke.py` and `xinyu_desktop_life_state_smoke.py` protect the contract.

Rules:

- No file roaming.
- No screenshots.
- No external network.
- No LLM calls.
- No proactive output triggered by environment pressure alone.

## Phase 2 - Tension And Inhibition

Status: started.

Build deterministic tension heuristics first. LLM desire generation should run only after cheap
rules detect enough tension.

Tension should increase from unresolved intent, time since last meaningful contact, recent memory
residue, and explicit owner invitation. Rejection should not simply reduce tension; it should
increase inhibition and alter the next chosen action.

Implemented first:

- `xinyu_life_kernel.py` defines `TensionSnapshot` and `ActiveDesire` contracts.
- `build_tension_snapshot()` combines unresolved proactive intents, recent turn residue, memory
  echoes, and physical pressure into a clamped tension score.
- `evaluate_life_kernel()` keeps the first pass deterministic: high physical pressure becomes
  `suppress_and_wait`; normal or medium unresolved intent becomes `leave_note_on_desk`.
- Entropy can now override silence: enough suppressed memory residue can create
  `request_metabolism_window` even when there is no proactive inbox item.
- `/desktop/snapshot` now exposes `activeDesires` and derives `xinyuState` from environment,
  proactive inbox, recent turns, recent memory, and the active desire trace.
- `/desktop/snapshot` also exposes `entropyState`, while `xinyuState` carries entropy level, scar
  level, decay risk, metabolism need, and the visible artifact for frontend noise/scar rendering.
- `life_kernel_smoke.py` protects high-pressure inhibition, normal note creation, and quiet-state
  silence.
- `life_kernel_entropy_smoke.py` protects entropy-only metabolism requests and quiet entropy silence.

## Phase 3 - Sandboxed Roaming

Allowed only after a hard allowlist exists. The roaming layer may read metadata or selected text
from owner-approved local folders only. It must write `roaming_trace` as memory candidate material
and must not immediately interrupt the owner.

## Phase 4 - Entropy Dream

Night or long-idle metabolism can combine suppressed desires, private thought residue, and approved
roaming traces into dream logs or morning residue notes. Dreams remain texture and growth material;
they are not reality facts.

## Metabolism Contract

Status: started.

The resource request is now being shaped as a ticketed contract rather than a loose background call.

Implemented first:

- `xinyu_metabolism_contract.py` stores metabolism tickets under `runtime/life_kernel/`.
- Tickets move through `requested -> approved -> running -> settled`, with `rejected`,
  `cancelled`, `expired`, and `failed` side states.
- `owner_decision_id` makes approve/reject idempotent.
- `claim_next_approved_ticket()` uses a lease to move approved work into `running`.
- `run_due_metabolism_tickets()` performs V1 stub metabolism and writes real artifacts:
  `memory/metabolism/*.json`, `memory/dreams/*.md`, and `runtime/life_kernel/entropy_ledger.jsonl`.
- Rejection writes a scar cost instead of producing dream artifacts.
- `metabolism_contract_smoke.py` protects approve idempotency, physical artifact writes, ledger
  events, settlement deltas, and reject scar cost.
- `xinyu_core_bridge.py` exposes async ticket approve/reject/cancel/get/list wrappers with
  `asyncio.to_thread()` around contract I/O.
- `xinyu_bridge_http.py` exposes REST signing endpoints:
  `GET /life/metabolism/tickets`, `GET /life/metabolism/tickets/{ticket_id}`,
  `POST /life/metabolism/tickets/{ticket_id}/approve`,
  `POST /life/metabolism/tickets/{ticket_id}/reject`, and
  `POST /life/metabolism/tickets/{ticket_id}/cancel`.
- Approve wakes the metabolism runner, but the runner still claims approved tickets by scanning and
  leasing work from the contract store.
- `metabolism_bridge_smoke.py` protects Bridge approve, runner wakeup, event broadcast, and artifact
  write-through.
- `metabolism_http_smoke.py` protects the real REST routes against the threaded HTTP server.
- `/desktop/snapshot` now creates or reuses a requested metabolism ticket when an active desire asks
  for `request_metabolism_window`, and exposes `metabolism_ticket_id` to the frontend valve.
- `xinyu_desktop_metabolism_ticket_smoke.py` protects ticket idempotency across repeated snapshots.

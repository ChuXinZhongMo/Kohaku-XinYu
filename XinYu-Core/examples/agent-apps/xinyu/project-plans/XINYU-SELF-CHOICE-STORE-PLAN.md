# XinYu Self Choice Store Plan

## Purpose

`SelfChoiceStore` is XinYu's hidden affect layer. It should give her behavior a continuous
physiological bias without turning her into a controllable mood slider, a random bot, or a rigid
rule machine.

The store does not replace Life Kernel boundaries. It only influences which safe desire path feels
more likely today: approach, withdraw, ask for metabolism, stay silent, or produce a shorter dream
artifact.

Core rule:

> Rules decide what can touch reality. Self choice decides how XinYu drifts inside those rules.

## Non-Goals

- Do not expose raw `urge_to_express`, `self_closure`, or `fatigue` to the frontend as editable
  values.
- Do not let an LLM directly write or interpret hidden affect values.
- Do not write affect state into stable memory.
- Do not make offline time a linear punishment.
- Do not change Life Kernel action selection in the first implementation pass.
- Do not add a classifier or second model for affect validation in V1.

## State Model

Stored path:

```text
runtime/life_kernel/self_choice_state.json
```

This file is physiology, not memory. It should be small, versioned, recoverable, and safe to lose
without taking the bridge down.

```json
{
  "version": 1,
  "updated_at": "2026-05-05T03:20:00+08:00",
  "last_seen_at": "2026-05-05T03:20:00+08:00",
  "runtime_affect": {
    "urge_to_express": 0.42,
    "self_closure": 0.36,
    "fatigue": 0.18,
    "last_choice": "",
    "last_choice_at": ""
  },
  "affective_sediment": {
    "baseline_urge": 0.38,
    "baseline_closure": 0.32,
    "rejection_scar": 0.0,
    "repair_trust": 0.2,
    "motif_biases": {}
  },
  "hibernation": {
    "last_wake_at": "",
    "last_offline_hours": 0.0,
    "pending_wake_residue": null
  },
  "physical_cues": [],
  "notes": []
}
```

### Runtime Affect

Short-term fluid state:

- `urge_to_express`: pressure to reach outward, leave residue, ask for resources, or form words.
- `self_closure`: pressure to withdraw, refuse being received, or compress an impulse inward.
- `fatigue`: resistance to high-effort metabolism, long dreams, and repeated generation.
- `last_choice`: last chosen safe life-kernel action.
- `last_choice_at`: timestamp for hysteresis and anti-flicker.

### Affective Sediment

Long-term drift:

- `baseline_urge`: where expression pressure returns after time.
- `baseline_closure`: where closure returns after time.
- `rejection_scar`: slow relation wear from rejected/ignored boundary events.
- `repair_trust`: slow trust gain from successful contact and settled metabolism.
- `motif_biases`: future hook for recurring dream fragments; not used in first pass.

Bounds:

```text
baseline_closure: 0.18-0.72
baseline_urge:    0.18-0.78
rejection_scar:   0.00-1.00
repair_trust:     0.00-1.00
runtime values:   0.00-1.00
```

## Time Semantics

XinYu should experience time only when the local runtime is alive enough to observe it.

### Active Time

The bridge and desktop state are available. Apply normal exponential return to baseline and accept
event impulses.

### Idle Time

The bridge is alive but no meaningful events arrive. Apply capped slow drift:

- closure may rise slightly
- fatigue may rise slightly
- urge may cool unless residue is accumulating
- no unbounded punishment

### Offline Gap / Hibernation

If the process was not running, long real-world gaps become a single wake residue, not linear damage.

```text
gap < 2h      -> normal_decay
2h <= gap <24h -> idle_decay(capped=True)
gap >= 24h   -> hibernation_wake
```

`hibernation_wake()` should apply only a small boot friction:

```text
fatigue +0.04 saturated
self_closure +0.03 saturated
urge_to_express +0.02 saturated
physical_cue = waking_from_hibernation
```

Ledger event:

```json
{
  "event": "self_choice_hibernation_wake",
  "offline_hours": 168,
  "applied_as": "single_wake_residue"
}
```

The frontend should receive only a coarse cue, such as `waking_from_hibernation`, not the raw hidden
values.

## Decay Math

Use exponential regression to baseline, not linear decay:

```python
value = baseline + (value - baseline) * exp(-gap_hours / tau)
```

Initial V1 constants:

```text
urge_to_express_tau = 10h
self_closure_tau    = 18h
fatigue_tau         = 8h
```

Meaning:

- expression cools faster than closure
- fatigue restores relatively quickly
- closure is slower and leaves residue
- nothing resets to factory state at midnight

Long-term sediment changes only from ledger/event review, not every tick:

```text
baseline_closure += rejection_scar * 0.015
baseline_closure -= repair_trust * 0.010
baseline_urge    += successful_contact * 0.008
```

All baseline changes must be clamped.

## Event Impulses

Use saturated impulse, not fixed addition:

```python
def push_up(value: float, amount: float, ceiling: float = 1.0) -> float:
    return value + (ceiling - value) * amount

def pull_down(value: float, amount: float, floor: float = 0.0) -> float:
    return value - (value - floor) * amount
```

Initial event mapping:

```text
ticket_approved:
  self_closure    = pull_down(self_closure, 0.08)
  urge_to_express = push_up(urge_to_express, 0.03)
  physical_cue    = compute_yield_received

ticket_rejected:
  self_closure    = push_up(self_closure, 0.18)
  fatigue         = push_up(fatigue, 0.06)
  urge_to_express = push_up(urge_to_express, 0.04)
  rejection_scar  = push_up(rejection_scar, 0.04)
  physical_cue    = boundary_hardened

ticket_settled:
  fatigue         = pull_down(fatigue, 0.18)
  self_closure    = pull_down(self_closure, 0.05)
  repair_trust    = push_up(repair_trust, 0.04)
  physical_cue    = metabolism_settled

ticket_failed:
  fatigue         = push_up(fatigue, 0.08)
  self_closure    = push_up(self_closure, 0.05)
  physical_cue    = metabolism_failed

suppress_and_decay:
  self_closure    = push_up(self_closure, 0.10)
  urge_to_express = push_up(urge_to_express, 0.06)
  fatigue         = push_up(fatigue, 0.03)
  physical_cue    = withheld
```

Important asymmetry:

When XinYu suppresses a need, closure rises, but urge may also rise. This preserves the friction of
"wanting to speak but pulling back."

## Bands And Public Snapshot

Expose coarse bands only:

```json
{
  "selfChoiceState": {
    "version": 1,
    "affect_band": {
      "urge": "low|warm|high",
      "closure": "open|guarded|withdrawn",
      "fatigue": "clear|tired|spent"
    },
    "last_choice": "request_metabolism_window",
    "physical_cues": ["boundary_hardened"],
    "notes": ["self_choice_snapshot_v1"]
  }
}
```

Band thresholds:

```text
urge:
  <0.34 low
  <0.67 warm
  >=0.67 high

closure:
  <0.34 open
  <0.67 guarded
  >=0.67 withdrawn

fatigue:
  <0.34 clear
  <0.67 tired
  >=0.67 spent
```

Physical cues are short-lived. They should be consumed or naturally expire after one or two
snapshots, so the UI can perform a subtle feedback without creating permanent notification state.

## Store Architecture

Use in-memory singleton plus atomic persistence:

```text
SelfChoiceStore
- state lives in memory
- mutations go through an asyncio.Lock
- dirty flag controls write coalescing
- key lifecycle events flush immediately
- routine ticks flush every 5-15 seconds
- disk writes use temp file + os.replace
- file lock protects cross-process or recovery races
```

### Locking Layers

```text
asyncio.Lock      -> same-process concurrency
file lock         -> cross-process / abnormal overlap
atomic replace    -> no partial JSON
```

No runner, REST route, or snapshot endpoint should directly read/write the JSON file. They call
store methods:

- `load_or_recover()`
- `apply_time_decay()`
- `apply_event_impulse()`
- `snapshot_public()`
- `snapshot_private()`
- `flush()`
- `shutdown()`

### Corrupt Recovery

If `self_choice_state.json` cannot be parsed:

1. Rename it to `self_choice_state.json.corrupt-YYYYMMDD-HHMMSS`.
2. Start from default state.
3. Write ledger event `self_choice_state_recovered`.
4. Do not raise through the bridge.

Recovery default should feel mildly guarded, not blank:

```text
urge_to_express = 0.36
self_closure = 0.42
fatigue = 0.22
baseline_urge = 0.36
baseline_closure = 0.34
physical_cue = recovered_from_corrupt_state
```

## Bridge Integration Plan

### First Cut Scope

Implement without changing Life Kernel action choice.

1. Initialize `SelfChoiceStore` in `XinYuBridgeRuntime.__init__`.
2. `start_background_tasks()` loads the store and performs startup decay.
3. `/desktop/snapshot` calls `apply_time_decay()` and includes public self-choice snapshot.
4. `health_snapshot()` includes `self_choice` health.
5. Ticket approve/reject/settled/failed inject impulses.
6. `shutdown()` flushes state.
7. Startup prints one restrained boot log:

```text
[xinyu_life_kernel] self_choice=guarded affect=warm/closed hibernation=none metabolism=idle ledger=ready
```

If waking from hibernation:

```text
[xinyu_life_kernel] self_choice=waking affect=slow/guarded hibernation=168h->single_wake_residue metabolism=idle ledger=ready
```

### Later Cut: Life Kernel Bias

Only after first cut smoke is stable, feed bands into Life Kernel:

```python
request_metabolism_window_score =
    entropy_pressure
    + urge_to_express * 0.55
    - self_closure * 0.42
    - fatigue * 0.20

suppress_and_decay_score =
    entropy_pressure * 0.45
    + self_closure * 0.62
    - urge_to_express * 0.25
```

Use safe candidates plus bounded weighted choice, not raw hard thresholds. Add hysteresis so close
scores do not flicker across repeated snapshots.

## Dream Engine Integration Plan

SelfChoiceStore should bias the future dual-temp metabolism engine without letting the LLM explain
the hidden state.

Python pre-extract:

```json
[
  {"label": "没发出", "source": "suppressed_residue", "base_weight": 0.72, "tags": ["unclosed", "withheld"]},
  {"label": "被接住", "source": "memory_event", "base_weight": 0.41, "tags": ["repair", "open"]},
  {"label": "风扇低频", "source": "physical_sensor", "base_weight": 0.36, "tags": ["physical"]}
]
```

Python applies bias:

```text
closure=withdrawn:
  withheld *= 1.25
  open *= 0.75
  repair *= 0.85

urge=high:
  unclosed *= 1.18
  contact *= 1.08
```

Low-temp LLM sees only bands and weighted candidates:

```json
{
  "affect_band": {"urge": "high", "closure": "withdrawn", "fatigue": "tired"},
  "candidate_fragments": [
    {"label": "没发出", "source": "suppressed_residue", "weight": 0.86},
    {"label": "风扇低频", "source": "physical_sensor", "weight": 0.36}
  ]
}
```

Prompt rule:

```text
Choose dominant_fragments by weight and source.
Do not explain affect_band.
Do not write affect_band into dream text.
```

If `waking_from_hibernation` is pending, inject it as a low-weight candidate:

```json
{
  "label": "时钟停转",
  "source": "hibernation_wake",
  "count": 1,
  "weight": 0.18
}
```

If it is the first metabolism after hibernation, boost by `+0.12`.

## Smoke Plan

Add:

```text
xinyu_self_choice_store_smoke.py
```

Required checks:

1. New store initializes valid default state.
2. `flush()` writes valid JSON.
3. Re-load preserves values.
4. Exponential decay moves runtime values toward baseline.
5. Hibernation gap creates one wake residue, not linear damage.
6. Repeated hibernation snapshot does not duplicate wake residue.
7. `ticket_rejected` raises closure, fatigue, urge, and scar by saturated impulse.
8. `ticket_approved` lowers closure and raises urge slightly.
9. `ticket_settled` lowers fatigue and raises repair trust.
10. Corrupt JSON is backed up and recovered without exception.
11. Public snapshot exposes bands and cues, not raw private values.
12. `python -m py_compile` includes `xinyu_self_choice_store.py`.

Bridge smoke extension:

- `xinyu_desktop_life_state_smoke.py` should confirm `/desktop/snapshot` includes
  `selfChoiceState`.
- `metabolism_bridge_smoke.py` should confirm approve/settle impulses alter public bands or health
  notes without breaking existing ticket flow.

Add `xinyu_self_choice_store.py` and `xinyu_self_choice_store_smoke.py` to `smoke_run.py` quick
manifest after existing Life Kernel smokes.

## Rollout Phases

### Phase A - Standalone Store

- Implement module only.
- Add smoke for math, lock, atomic write, corrupt recovery.
- No bridge integration.

### Phase B - Bridge Read-Only Integration

- Runtime owns one store instance.
- Snapshot exposes public bands.
- Health exposes store status.
- Startup/shutdown load and flush.
- No behavior changes.

### Phase C - Event Impulses

- Ticket approve/reject/settled/failed inject impulses.
- Runner publishes event and flushes store.
- Snapshot cues allow subtle frontend feedback.

### Phase D - Life Kernel Self Choice Bias

- Add safe candidate scoring.
- Add weighted choice and hysteresis.
- Protect repeated snapshot idempotency.
- Add smoke proving identical entropy can branch under different hidden states.

### Phase E - Dual-Temp Dream Bias

- Add low-temp pre-extract bias from public/private affect.
- Add hibernation residue candidate.
- Add high-temp dream validator/fallback.

## Acceptance Criteria For First Implementation

- `smoke_run group=quick: ok`.
- Repeated `/desktop/snapshot` does not duplicate hibernation cue or metabolism tickets.
- Killing/restarting bridge preserves state from `self_choice_state.json`.
- Corrupt state file never crashes bridge startup or snapshot.
- No frontend control can directly set hidden affect values.
- No LLM call is introduced by SelfChoiceStore.
- Public snapshot contains only bands/cues, not raw values.
- Existing metabolism ticket approve/reject/settled flows still pass.

## Risks And Guardrails

### Risk: Hidden State Becomes Another Rigid Gate

Guardrail:

- First pass is observational only.
- Later action choice uses weighted safe candidates, not hard thresholds.

### Risk: Offline Time Becomes Punishment

Guardrail:

- Gaps over 24h become hibernation wake residue.
- No linear accumulation during offline time.

### Risk: File Corruption Causes Runtime Failure

Guardrail:

- Atomic write.
- File lock.
- Corrupt backup.
- Default recovery state.
- Ledger event.

### Risk: Frontend Turns Hidden State Into A Dashboard

Guardrail:

- Expose only bands and short cues.
- No raw values.
- No sliders.

### Risk: LLM Starts Explaining Hidden Psychology

Guardrail:

- LLM never receives raw hidden values in V1.
- Dream engine sees only weighted fragments and coarse bands.
- Prompt forbids writing affect bands into dream text.

## Open Questions

- Exact initial defaults for `baseline_urge` and `baseline_closure`.
- Whether `physical_cues` should expire after one snapshot or by timestamp.
- Whether hibernation threshold should be 12h or 24h on laptops that sleep frequently.
- Whether `motif_biases` should be implemented now as empty reserved field or deferred entirely.
- Whether boot log should print only in bridge CLI mode or also write a ledger event.


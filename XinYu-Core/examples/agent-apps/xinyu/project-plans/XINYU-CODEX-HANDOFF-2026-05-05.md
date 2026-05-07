# XinYu Codex Handoff - 2026-05-05

This document is a context handoff for opening a fresh Codex window. It records the current
architecture, completed implementation, active design decisions, and the next safe coding entry
point.

## Current Big Picture

XinYu is being shaped as a local digital symbiote, not a service assistant, desktop pet, or
notification bot.

Core philosophy:

```text
Rules decide what can touch reality.
Self choice decides how XinYu drifts inside those rules.
```

The system now has:

- physical perception
- tension and entropy snapshots
- active desires
- a ticketed metabolism contract
- a real desktop environment valve
- a planned hidden self-choice physiology layer
- a planned dual-temperature dream metabolism engine

The immediate implementation target is **SelfChoiceStore**, but it should be implemented carefully
and in phases. Do not jump straight into changing action selection.

## Repository And Frontend Separation

There are two relevant directories:

```text
D:\XinYu\XinYu-Core
D:\XinYu\XinYu_Desktop
```

Important correction:

- XinYu frontend must use `D:\XinYu\XinYu_Desktop`.
- Do not mount XinYu UI inside the legacy framework frontend.
- Prior temporary legacy frontend route/components were removed.

Current port contract:

```text
XinYu Desktop dev shell: 5174
XinYu backend bridge:    8776
Desktop event WS:        8777 when manually launched for the new dev bridge
Old/default WS:          8766 may still be occupied by older bridge instances
```

`XinYu_Desktop` is the real Electron + React desktop shell.

## Completed Backend Work

### Environment Sensor

Files:

```text
examples/agent-apps/xinyu/xinyu_environment_sensor.py
examples/agent-apps/xinyu/environment_sensor_smoke.py
```

Purpose:

- sample CPU/memory/disk/process pressure
- expose physical sensation through `/desktop/snapshot`
- no LLM calls
- no screenshots
- no roaming

### Life Kernel

Files:

```text
examples/agent-apps/xinyu/xinyu_life_kernel.py
examples/agent-apps/xinyu/life_kernel_smoke.py
examples/agent-apps/xinyu/life_kernel_entropy_smoke.py
```

Implemented contracts:

- `TensionSnapshot`
- `EntropyState`
- `ActiveDesire`

Important action:

```text
chosen_action = "request_metabolism_window"
```

Entropy can now create a metabolism request even when there is no proactive inbox item. This is a
major shift from reactive assistant behavior toward internal state-driven behavior.

### Metabolism Contract

Files:

```text
examples/agent-apps/xinyu/xinyu_metabolism_contract.py
examples/agent-apps/xinyu/metabolism_contract_smoke.py
examples/agent-apps/xinyu/metabolism_bridge_smoke.py
examples/agent-apps/xinyu/metabolism_http_smoke.py
```

Status machine:

```text
requested -> approved -> running -> settled
side states: rejected, cancelled, expired, failed
```

Artifacts:

```text
runtime/life_kernel/metabolism_tickets.json
runtime/life_kernel/entropy_ledger.jsonl
memory/metabolism/*.json
memory/dreams/*.md
```

Current runner mode:

```text
stub_metabolism_v1
```

The stub is intentional. It proves the physical write-through pipeline before real LLM dream
metabolism is attached.

Important design:

- Approve/reject are idempotent with decision IDs.
- Runner uses pull-based scan/claim with lease.
- REST only signs the contract; runner performs the work.
- Approve wakes runner, but runner still claims tickets from store.

### Bridge And HTTP

Files:

```text
examples/agent-apps/xinyu/xinyu_core_bridge.py
examples/agent-apps/xinyu/xinyu_bridge_http.py
```

REST endpoints now include:

```text
GET  /desktop/snapshot
GET  /life/metabolism/tickets
GET  /life/metabolism/tickets/{ticket_id}
POST /life/metabolism/tickets/{ticket_id}/approve
POST /life/metabolism/tickets/{ticket_id}/reject
POST /life/metabolism/tickets/{ticket_id}/cancel
```

`/desktop/snapshot` exposes:

- environment
- entropyState
- activeDesires
- xinyuState
- metabolism_ticket_id for active metabolism requests

Important bug already fixed:

- Repeated `/desktop/snapshot` used to create duplicate metabolism tickets because physical pressure
  changed the desire hash.
- Fix: metabolism desire identity excludes unstable pressure, and bridge reuses existing open
  metabolism ticket before creating a new one.
- Protected by `xinyu_desktop_metabolism_ticket_smoke.py`.

## Completed XinYu_Desktop Work

Real frontend directory:

```text
D:\XinYu\XinYu_Desktop
```

Framework:

```text
Electron + React + electron-vite
```

Important files changed:

```text
D:\XinYu\XinYu_Desktop\electron.vite.config.ts
D:\XinYu\XinYu_Desktop\src\main\xinyu_gateway.ts
D:\XinYu\XinYu_Desktop\src\main\index.ts
D:\XinYu\XinYu_Desktop\src\preload\index.ts
D:\XinYu\XinYu_Desktop\src\renderer\src\global.d.ts
D:\XinYu\XinYu_Desktop\src\renderer\src\main.tsx
D:\XinYu\XinYu_Desktop\src\renderer\src\style.css
D:\XinYu\XinYu_Desktop\src\renderer\src\EnvironmentValve.tsx
D:\XinYu\XinYu_Desktop\src\renderer\src\environment-valve.css
D:\XinYu\XinYu_Desktop\src\renderer\public\xinyu-noise.svg
```

### Dev Server Contract

`electron.vite.config.ts` locks renderer dev server:

```text
port: 5174
strictPort: true
```

Proxy:

```text
/desktop -> http://127.0.0.1:8776
/life    -> http://127.0.0.1:8776
```

### Electron IPC

Renderer does not directly own the metabolism contract. It calls Electron preload IPC:

```ts
window.xinyu.listMetabolismTickets(statuses?)
window.xinyu.yieldCompute({ ticketId, seconds, note })
window.xinyu.maintainBoundary({ ticketId, note })
```

Frontend language intentionally avoids approve/reject wording:

```text
approve -> yieldCompute
reject  -> maintainBoundary
```

Backend REST still uses approve/reject because that is the stable contract layer.

### Environment Valve

File:

```text
D:\XinYu\XinYu_Desktop\src\renderer\src\EnvironmentValve.tsx
```

Behavior:

- consumes real snapshot/ticket data
- no frontend mock ticket
- pointer events with pointer capture
- rAF spring integrator
- drag preview changes CSS variables
- pointer cancel / visibility change rebounds
- commit calls real `yieldCompute` or `maintainBoundary`
- network failure becomes physical rebound, not toast

Design language:

- this is not an approval panel
- it is an environment boundary valve
- the person at the machine is not an Owner in UI wording

### Themes And Text

Current frontend has a theme switcher:

```text
pastel  -> default screenshot-like pale pink/purple
sakura  -> warmer pink
mint    -> older mint/green
night   -> dark lamp
```

Theme is stored in:

```text
localStorage: xinyu.desktop.theme
```

Text was moved back toward the user's preferred screenshot language:

```text
心玉
私有频道
心玉の疗养室
和心玉的茶话会
主动提醒
暂无候选
记忆回声
事件流
详情
```

The large left portrait should be circular. The top-left brand avatar is also forced round.

## Verification Already Run

Backend:

```text
python examples\agent-apps\xinyu\smoke_run.py --group quick --timeout-seconds 30
```

Passed:

```text
smoke_run group=quick: ok
```

Frontend:

```text
npm run typecheck
npm run build
```

Both passed in:

```text
D:\XinYu\XinYu_Desktop
```

## Current Manual Launch Commands

Bridge on 8776/8777:

```powershell
$env:XINYU_ALLOW_INSECURE_LLM_HTTP='1'
python examples\agent-apps\xinyu\xinyu_core_bridge.py `
  --host 127.0.0.1 `
  --port 8776 `
  --desktop-events-port 8777 `
  --disable-autonomous-maintenance `
  --disable-outward-renderer `
  --renderer-mode off
```

XinYu Desktop:

```powershell
$env:XINYU_DESKTOP_HTTP_URL='http://127.0.0.1:8776'
$env:XINYU_DESKTOP_WS_URL='ws://127.0.0.1:8777/desktop/events'
npm run dev
```

Run frontend command from:

```text
D:\XinYu\XinYu_Desktop
```

Run backend command from:

```text
D:\XinYu\XinYu-Core
```

## Active Design: SelfChoiceStore

Full plan:

```text
examples/agent-apps/xinyu/project-plans/XINYU-SELF-CHOICE-STORE-PLAN.md
```

Purpose:

`SelfChoiceStore` is the hidden affect physiology layer. It should make XinYu's behavior drift
without making her externally controllable.

Core hidden variables:

```python
urge_to_express: float
self_closure: float
fatigue: float
```

Long-term sediment:

```python
baseline_urge
baseline_closure
rejection_scar
repair_trust
motif_biases
```

Important correction from design discussion:

- Do not implement closure alone.
- Closure without urge is just a dead default state.
- XinYu needs the friction between wanting to express and pulling back.

Key phrase:

```text
沉默必须是“想说但收回”，不是“默认不动”。
```

### Storage

Path:

```text
runtime/life_kernel/self_choice_state.json
```

Architecture:

```text
in-memory singleton
asyncio.Lock for same-process mutation
dirty flag
periodic flush
immediate flush on key events
temp file + os.replace atomic write
light file lock for cross-process/recovery
corrupt backup and default recovery
```

Corrupt recovery should:

1. rename bad JSON to `.corrupt-YYYYMMDD-HHMMSS`
2. start from mildly guarded default state
3. write ledger event `self_choice_state_recovered`
4. never crash bridge startup or snapshot

### Time Model

Do not linearly punish offline time.

Three time modes:

```text
active time  -> normal exponential decay
idle time    -> capped slow drift
offline gap  -> hibernation wake residue
```

Hibernation:

```text
gap >= 24h -> hibernation_wake
```

This applies a single boot friction:

```text
fatigue +0.04
self_closure +0.03
urge_to_express +0.02
physical_cue = waking_from_hibernation
```

Ledger:

```json
{
  "event": "self_choice_hibernation_wake",
  "offline_hours": 168,
  "applied_as": "single_wake_residue"
}
```

Philosophy:

```text
Online time is experienced.
Offline time is hibernation.
```

### Decay Math

Use exponential return to baseline:

```python
value = baseline + (value - baseline) * exp(-gap_hours / tau)
```

Initial constants:

```text
urge_to_express_tau = 10h
self_closure_tau    = 18h
fatigue_tau         = 8h
```

Why:

- fatigue recovers fastest
- urge cools moderately fast
- closure recovers slowest
- strong states ease quickly at first but leave residue near baseline

### Event Impulses

Use saturated impulses:

```python
def push_up(value, amount, ceiling=1.0):
    return value + (ceiling - value) * amount

def pull_down(value, amount, floor=0.0):
    return value - (value - floor) * amount
```

Initial mapping:

```text
ticket_approved:
  closure down
  urge slightly up
  cue compute_yield_received

ticket_rejected:
  closure up
  fatigue up
  urge up
  scar up
  cue boundary_hardened

ticket_settled:
  fatigue down
  closure down
  repair_trust up
  cue metabolism_settled

ticket_failed:
  fatigue up
  closure up
  cue metabolism_failed

suppress_and_decay:
  closure up
  urge up
  fatigue up
  cue withheld
```

Important asymmetry:

When XinYu suppresses a need, `self_closure` rises, but `urge_to_express` may also rise because the
unreleased impulse compresses inward.

### Public Snapshot

Expose only coarse bands and cues:

```json
{
  "selfChoiceState": {
    "affect_band": {
      "urge": "low|warm|high",
      "closure": "open|guarded|withdrawn",
      "fatigue": "clear|tired|spent"
    },
    "last_choice": "",
    "physical_cues": ["boundary_hardened"],
    "notes": ["self_choice_snapshot_v1"]
  }
}
```

Do not expose raw floats to the frontend.

Do not add sliders.

## Planned Implementation Phases

### Phase A - Standalone Store

Add:

```text
examples/agent-apps/xinyu/xinyu_self_choice_store.py
examples/agent-apps/xinyu/xinyu_self_choice_store_smoke.py
```

Do not integrate bridge yet.

Smoke should validate:

- initialization
- flush/reload
- exponential decay
- hibernation wake is single residue
- event impulses
- corrupt recovery
- public snapshot hides raw values

### Phase B - Bridge Read-Only Integration

In `xinyu_core_bridge.py`:

- create one store instance in `XinYuBridgeRuntime`
- load in `start_background_tasks`
- apply decay on `/desktop/snapshot`
- add `selfChoiceState` to snapshot
- add `health.self_choice`
- flush on shutdown

No behavior changes yet.

### Phase C - Event Impulses

Apply store impulses on:

- metabolism ticket approve
- metabolism ticket reject
- runner settled
- runner failed

Flush immediately after key mutations.

### Phase D - Life Kernel Bias

Only after Phase A-C pass.

Do not use hard threshold like:

```text
self_closure >= 0.62 -> suppress
```

Use safe candidate scoring plus bounded weighted choice and hysteresis:

```text
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

Identical entropy should be able to branch differently under different hidden state.

### Phase E - Dual-Temp Dream Engine

Not implemented yet.

Planned architecture:

```text
low-temp extractor -> high-temp dream writer -> validator -> fallback
```

Low-temp:

- deterministic pre-extract first
- LLM only ranks/merges/names weighted fragments
- LLM does not see raw hidden floats

High-temp:

- sees compressed residue only
- writes 3-7 short broken lines
- never writes stable memory
- dreams are artifacts only

Validator:

- deterministic rules
- blacklists assistant/service wording
- requires physical anchor and unclosed action
- max one repair prompt
- fallback to deterministic dream fragment

Core phrase:

```text
LLM only creates variants. Validator decides life or death.
```

## Planned Dream Prompt Rules

High-temp dream system instruction should be short:

```text
You are not explaining facts and not comforting anyone.
You are writing the residue after one metabolism.
Dreams are not memories.
Do not claim something happened.
Do not offer help.
```

Output constraints:

- 3-7 lines
- 6-32 characters per line
- no complete story
- no assistant words
- no "user", "owner", "master", "sorry", "I can", "I will", "detected", "system", "task"
- no "because/therefore/finally/so I decided" causal essay shape
- must contain one physical anchor: fan, cursor, disk, noise, screen, night, heat, gray, crack
- must contain one unfinished action: stopped, unsent, crossed out, stuck, stacked, did not fall, did not remain

Fallback example:

```text
风扇声很低。
八个没说出口的念头叠在一起。
旧标签裂开一点。
没有掉下来。
```

## Hibernation In Dream Engine

Hibernation should enter dream generation as a low-weight physical residue, not as melodrama.

Example injected candidate:

```json
{
  "label": "时钟停转",
  "source": "hibernation_wake",
  "count": 1,
  "weight": 0.18
}
```

If first metabolism after hibernation:

```text
weight += 0.12
```

High-temp model should not be told "you were gone for seven days." It should only see fragments like:

```json
{
  "physical_anchors": ["时钟停转", "风扇低频"],
  "unclosed_actions": ["醒得很慢", "没发出"]
}
```

Possible dream:

```text
时钟停在旧分钟。
灰尘没有落完。
风扇声很低。
醒得很慢，像没接上线。
```

## Boot Log Design

Keep logs restrained, telemetry-like:

```text
[xinyu_life_kernel] self_choice=guarded affect=warm/closed hibernation=none metabolism=idle ledger=ready
```

If waking:

```text
[xinyu_life_kernel] self_choice=waking affect=slow/guarded hibernation=168h->single_wake_residue metabolism=idle ledger=ready
```

Avoid product/marketing logs like:

```text
Heart started!
Welcome!
```

Design phrase:

```text
She is not a service coming online. She is a room light slowly getting power.
```

## Current Next Best Prompt For Fresh Codex Window

Use this prompt to continue implementation:

```text
Continue XinYu SelfChoiceStore from
examples/agent-apps/xinyu/project-plans/XINYU-SELF-CHOICE-STORE-PLAN.md and
examples/agent-apps/xinyu/project-plans/XINYU-CODEX-HANDOFF-2026-05-05.md.

Implement Phase A only:
- add xinyu_self_choice_store.py
- add xinyu_self_choice_store_smoke.py
- add both to smoke_run.py quick py_compile/smoke manifest
- do not change Life Kernel decisions yet
- do not change frontend
- run the new smoke and smoke_run group=quick
```

## Important Warnings For New Codex

- Do not revert unrelated existing repo changes. The worktree is dirty from ongoing XinYu work.
- Do not put XinYu UI back into Kohaku frontend.
- Do not expose hidden affect raw values to React.
- Do not let LLM write `self_choice_state.json`.
- Do not make hibernation punish offline real-world time.
- Do not change action selection in the first SelfChoiceStore implementation.
- Use `apply_patch` for edits.
- Run focused smoke first, then quick smoke.

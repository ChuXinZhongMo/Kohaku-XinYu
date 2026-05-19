# Xinyu Structure Notes v0.1

This file explains the current file-layer grouping so future edits stay coherent.

## 0. Subtractive Target Boundary

The active app should converge toward these responsibility buckets:

```text
core/      XinYu turn chain, living memory recall, persona, emotion modulation, policy
adapters/  QQ, Desktop, HTTP bridge, Codex, CLI, external transport
stores/    dialogue archive, state IO, memory/library manifests, persistence helpers
services/  LLM, embeddings, OCR, search, diagnostics, replay support
ops/       start/stop scripts, status checks, health, migrations, smoke runner
lab/       experiments and shadow systems that do not control the live path
archive/   historical code/docs not imported by live code
```

The current flat root layout is tolerated while the system is being reduced. New code should state which bucket it belongs to before it is added. Large live files should become thinner by moving transport details to `adapters`, persistence to `stores`, and experiments to `lab`.

Current owner surfaces:

- Living memory recall: `xinyu_living_memory_recall.py`
- Recall implementation compatibility/provider: `xinyu_context_retrieval.py`
- Contextual runtime packs: `xinyu_contextual_recall.py` and
  `xinyu_contextual_self_loop.py` are context providers, not recall owners.
- Context observability/replay: `xinyu_contextual_self_observatory.py` is ops
  observability; `xinyu_contextual_self_replay.py` is lab/offline replay.
- Conversation experience hints: `xinyu_conversation_experience_matcher.py` and
  `xinyu_conversation_experience_sidecar.py` are advisory providers; the
  current turn and canonical recall owner outrank them.
- Persona runtime state: `xinyu_persona_runtime.py`
- Memory reduction contract: `MEMORY-REDUCTION-RULES.md`
- QQ transport adapter: `xinyu_qq_gateway.py` plus `xinyu_qq_*.py`
- Core HTTP/Desktop adapter: `xinyu_core_bridge.py` plus `xinyu_bridge_*.py`;
  route-sized bridge behavior should live in focused `xinyu_bridge_*_routes.py`
  modules, not inline in the core runtime class.

Subtractive rule: if a module does not feed `input -> current state -> living memory recall -> persona/emotion modulation -> reply/action -> memory update`, it belongs in `adapters`, `stores`, `services`, `ops`, `lab`, or `archive`, not in the core turn path.

Memory reduction rule: if a change makes XinYu remember by storing more raw
text, it needs stronger justification than a change that stores a smaller
source-indexed summary, adds a write gate, or improves decay.

## 1. Identity Layer

Files:

- `memory/self/core.md`
- `memory/self/narrative.md`
- `memory/self/boundaries.md`

Purpose:

- hold slow self continuity

## 2. Emotion / Relationship Layer

Files:

- `memory/emotions/*`
- `memory/relationships/*`
- `memory/people/*`

Purpose:

- hold present feeling and social meaning

## 3. Time / Rhythm / Maintenance Layer

Files:

- `memory/context/time_anchor.md`
- `memory/context/continuity_index.md`
- `memory/context/inner_sync_state.md`
- `memory/context/runtime_rhythm.md`
- `memory/context/maintenance_plan.md`
- `memory/context/maintenance_targets.md`

Purpose:

- hold reality-time anchoring and maintenance cadence

## 4. Question / Exploration Layer

Files:

- `memory/context/active_questions.md`
- `memory/context/question_states.md`
- `memory/context/exploration_queue.md`
- `memory/knowledge/*`

Purpose:

- hold curiosity, clarification, and controlled outward learning

## 5. Reflection / Dream / Archive Layer

Files:

- `memory/reflection/*`
- `memory/dreams/*`
- `memory/archive/*`

Purpose:

- hold slow reinterpretation, residue, and memory lightening

## 6. Operations Layer

Files:

- `INNER-MEMORY-ORDER.md`
- `RUNBOOK.md`
- `IMPLEMENTATION-NEXT.md`
- `TEST-SCENARIOS.md`
- `EXPLORATION-SCENARIOS.md`
- `WRITER-ROUTING.md`
- `MEMORY-LINKS.md`
- `FAILURE-MODES.md`
- `PROMPT-TUNING.md`
- `ops/manual/`
- `ops/launch/`
- `ops/diagnostics/`
- `ops/probes/`
- `ops/validation/`

Purpose:

- support validation, debugging, and iteration

`ops/manual/` contains operator-only `manual_*.py` entry points. They are
kept out of the app root because they are not part of the live turn path.

`ops/launch/` contains operator startup helpers. Root launchers should stay
thin compatibility wrappers when older scripts rely on their paths.

`ops/diagnostics/` contains operator-only checks and inspection scripts. They
may read runtime state but should not be imported by live code.

`ops/probes/` contains longer no-restore or lived-session validation harnesses.
They are not part of normal startup.

`ops/validation/` contains operator-run validation harnesses that may call a
local service or write runtime reports, but do not belong to the live turn path.

Root smoke/manual/diagnostic wrappers that were moved out of the app root are
not active modules. They now live under `tests/smoke/`, `ops/manual/`,
`ops/diagnostics/`, `ops/probes/`, or `ops/archive/custom-manifests/`.

## 6.5 Stores Layer

Files:

- `stores/`
- `state_service.py` compatibility wrapper

Purpose:

- hold persistence helpers and app-local state IO primitives

`stores/state_service.py` owns atomic text/JSON writes, JSON reads, and JSONL
append helpers. The app-root `state_service.py` stays as a compatibility
wrapper for older imports while new persistence helpers should live under
`stores/`.

## 6.6 Services Layer

Files:

- `services/`
- `xinyu_daily_digest.py` compatibility wrapper

Purpose:

- hold runtime service helpers that support the turn path without owning
  transport adapters, bridge routing, or stable persona policy

`services/daily_digest.py` owns watched-source daily digest maintenance. The
app-root `xinyu_daily_digest.py` stays as a compatibility wrapper for older
imports.

## 7. Growth Principle

New files should usually extend one of the layers above.

If a new file does not clearly belong to one layer, it probably needs more thought before being added.

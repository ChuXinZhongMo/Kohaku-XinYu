# XinYu Cognitive Architecture (v0.2)

**Date:** 2026-06-30  
**Status:** Draft - Integrating current runtime with Cognitive Kernel  
**Goal:** Move from reactive/event-driven system to Experience → Self Model → Prediction Error → Belief/World Model Reorganization

## 1. Overall Philosophy

XinYu is an **experience-driven cognitive system**, not a prompted persona.

- LLM is **only the final expressor**.
- **Self** is the persistent owning subject.
- All beliefs, memories, goals, and predictions are **owned by Self**.
- Personality / Identity emerges from long-term ownership of high-importance Experiences.
- Core update signal: **Prediction Error** (not raw event reward).

This aligns with:
- Predictive Processing / Active Inference
- Modern agent work (Generative Agents, Reflexion, MemGPT)
- Ownership as the mechanism for "self"

## 2. Layered Architecture

```
External Input (QQ / Desktop / File / Internal)
          │
          ▼
┌─────────────────────────────┐
│ 1. Perception & Intake      │  (xinyu_qq_gateway + bridge intake)
│    - Normalize events       │
│    - Enrich context         │
└──────────────┬──────────────┘
               │ raw event dict
               ▼
┌─────────────────────────────┐
│ 2. Experience Processor     │  (experience/processor.py)
│    - Rule + light LLM       │
│    - importance_score       │
│    - belief_update_proposals│
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│ 3. Cognitive Kernel (Core)  │  <-- New focus
│    ├── Self (ownership)     │
│    ├── Self Model           │  (stable: Identity, Values, Boundaries)
│    ├── Goals / Motivation   │
│    ├── Prediction Engine    │
│    └── State Dynamics       │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│ 4. Memory System            │  (memory/ + event sourcing)
│    - Event Sourcing (raw/structured/claims)
│    - Attention Buffer       │
│    - Episodic / Semantic    │
│    - Working Memory         │
│    - All items owned by Self│
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│ 5. Decision & Policy Layer  │  (bridge_* + custom plugins)
│    - Utility Evaluation     │
│    - Policy Selection       │
│    - Sidecar execution      │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│ 6. Narrative Builder        │
│    - Identity + Current     │
│    - Inner monologue        │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│ 7. LLM (Expressor only)     │  (Codex runtime, prompts)
│    - Style from LoRA (rare) │
│    - Content from above     │
└──────────────┬──────────────┘
               │
               ▼
Output (Reply / Action / Proactive / Note)
```

## 3. Key Components Status (2026-06-30)

### Existing Strong Parts
- **Runtime Bridge**: xinyu_core_bridge.py + dozens of xinyu_bridge_*.py (chat, codex, autonomous, desktop)
- **Gateway**: xinyu_qq_gateway.py (transport + normalization)
- **Event Sourcing**: memory/events/ (raw, structured, claims, summaries) + memory_consistency_gate
- **Custom Plugin System**: custom/*_bridge_plugin.py + *_engine.py
- **Experience Layer**: experience/ (just added, importance + proposals)
- **Action Experience**: xinyu_bridge_action_experience.py etc.
- **Memory Layers**: Well documented (runtime trace → candidates → long-term, with gates)
- **Autonomy**: Many autonomous_* modules, proactive, reflection, dreams

### New / In Progress (Cognitive Kernel)
- **kernel/** (K-001): Minimal Self + Ownership
  - self_id
  - claim/verify/get_owned
  - to_dict / persistence (json)

### Missing / Weak (per analysis)
- Self Model (stable identity/values/boundaries) ← Priority
- Explicit Goals/Motivation
- Prediction + Prediction Error (biggest gap)
- Attention selection
- State dynamics between variables
- Clean separation: Identity vs Belief vs Current Narrative

## 4. Self Model Details (Core of Kernel)

Self Model is the **stable, slowly evolving** part of Self.

**Representation**:
- Collection of `CoreStatement` owned by Self.
- Types: identity, core_value, boundary, long_term_orientation
- Each has: content, confidence, source_event_id, last_confirmed_at

**Evolution Rules** (strict):
- Only proposed from high-importance ExperienceResult
- Gated by importance_score + confidence + stability check
- Changes logged as events (traceable)
- Never directly mutated by runtime or LLM

**Ownership**:
- Every CoreStatement is an OwnedObject of this Self.
- Future Beliefs, Goals, Memories must reference owning Self.

## 5. Data Flow for Self Update (Experience → Self)

1. Event arrives (chat, action result, observation)
2. ExperienceProcessor.process(event) → importance + proposals
3. If importance high → filter self-related proposals (boundary, self_observation...)
4. Self.propose_self_update(proposals, importance, event_id)
5. Gate in kernel: accept/reject/replace
6. If accepted: claim_ownership + record in core_statements + write to event log
7. Future: Prediction Error can trigger re-evaluation of existing statements

## 6. Integration Points (Current → Kernel)

- experience/processor.py → kernel via adapter
- xinyu_memory_event_sourcing.py → record Self Model changes as special claims or sidecar events
- custom/ plugins can query kernel_self.get_self_model() for high-level guidance (rarely)
- All memory items should eventually carry `owner_self_id`

## 7. Non-Goals (What we deliberately do NOT do)

- No hand-written persona rules
- No direct LLM control of Self Model
- No emotion as part of Self Model (emotions are dynamic Cognitive State)
- No tight coupling to bridge/runtime (Kernel is independent layer)
- LoRA only for linguistic style, not content/personality

## 8. Roadmap

**K-001** (done): Minimal Self + Ownership
**K-002** (advanced): Self Model (CoreStatement + propose/apply from Experience)
  - CoreStatement model + get/propose/commit flow implemented
  - Adapter in experience/kernel_adapter.py
  - Traceable change event helper (writes to self_model_events.jsonl when possible)
  - Stricter stability gate (modeled after memory consistency gate)
  - Safe bridge query: get_kernel_self_model() exported via compat
  - Guarded integration in xinyu_memory_event_sourcing.py
  - Demo and tests updated
**K-003** (in progress): Prediction Engine + Prediction Error as primary update signal
  - Full Prediction / PredictionError models + engine implemented
  - Self now owns PredictionEngine
  - generate_prediction + record_outcome + error_to_self_proposal
  - prediction_adapter.py for cycle
  - Demo extended to show K-002 + K-003 loop
  - Error magnitude drives Self Model reorganization proposals
**K-004** (advanced): Goals/Motivation owned by Self
  - Goal and GoalManager with priority, status, proposal from experience/error
  - Self owns GoalManager, propose_goal, get_active_goals
  - Goals influence prediction generation (K-003 integration)
  - Traceable via source_event_id and ownership
  - Demo and tests updated
**K-005** (advanced): Attention Buffer + Working Memory selection
  - AttentionBuffer + AttentionItem implemented
  - update_from_self_model, goals, prediction_error
  - Integrated into Self (update_attention, get_working_memory, attention_to_context)
  - Boosts relevant items from core statements + goals + high-error predictions
  - Feeds into Prediction (K-003)
  - Adapter and demo updated
  - Full loop K-002 to K-005 demonstrated
  - 15 kernel tests passing
**K-006** (advanced): Belief Engine owned by Self
  - Belief and BeliefEngine implemented
  - propose_belief + commit with gate (confidence, contradiction check)
  - Owned by Self (claim_ownership + source_self_id)
  - Integrated with Prediction (beliefs_to_context), Goals, Attention
  - belief_adapter.py for Experience/PredictionError → Belief
  - Demo and tests updated
  - 16 kernel tests passing (new test added)
**K-007 (主线, advanced)**: World Model with generative predictions
  - WorldModel + WorldFact implemented as core of K-007
  - Owned by Self (via claim_ownership)
  - add_fact, generate_prediction (horizon), update_from_error, add_generative_rule
  - **更完整 generative simulation (信念/目标驱动规则学习)**:
    - learn_rule_from_belief_and_goal + simulate_with_beliefs_goals (structured output with deltas)
    - generate_hypothetical + derive_new_expectation
    - sync_with_self_state (from current Beliefs/Goals)
    - reorganize (integrates multiple errors + new beliefs/goals)
  - **更深 turn pipeline hook**: WM update now explicitly after real Experience processing in xinyu_memory_event_sourcing.py (post-experience reorganization)
  - **Owner review gate**: high-impact changes (via owner_review_gate_for_world_model) return 'review_only' / 'needs_owner_review'; pending facts held until apply_reviewed
  - Full integration chain: Experience → ... → World Model
  - Demo + tests cover sync/reorg/learn/sim + review + pending apply
  - 18 kernel tests passing
  - See bridge_integration.py and adapters for usage

**K-008 (advanced)**: Self Reorganization Loop
  - `ReorganizationLoop` + `ReorgProposal` in `kernel/reorganization.py`
  - Consumes Prediction Errors + Belief updates + WM changes + Experience proposals
  - Propagates structural impact: Attention boosts, Goal priority shifts, memory candidates, belief reinforcement, Self Model proposals
  - Owner review gate: high-impact proposals held as `review_only` until `apply_reviewed_reorg`
  - `reorg_events.jsonl` via `kernel/reorg_event_recorder.py`
  - Turn pipeline hook in `xinyu_memory_event_sourcing.py` (post-experience, after K-007)
  - `experience/reorganization_adapter.py` + integration in `prediction_adapter.py`
  - 20 kernel tests passing

**K-009 (advanced)**: Complete Experience → Prediction Error → Belief → World Model → Self Reorganization loop
  - `kernel/cognitive_cycle.py`: `run_full_cognitive_cycle` orchestrates all stages
  - Slow vs fast reorg: `classify_reorg_mode` + slow-signal escalation (3 slow → fast)
  - Slow mode defers structural actions (goal/memory/self_model) to pending; fast applies all
  - Persistent runtime Self: `memory/kernel/xinyu_runtime_self.json` (v2 full state)
  - `cognitive_cycle_events.jsonl` trace + turn pipeline uses unified cycle hook
  - 26 kernel tests passing

**K-010 (advanced)**: Deep Bridge Integration + Owner Governance
  - `kernel/bridge_access.py`: `query_kernel_state`, `run_kernel_turn_update`, `apply_kernel_owner_reviews`
  - `kernel/bridge_governance.py`: unified review inbox + `apply_kernel_owner_review` across WM/Reorg/Belief
  - `xinyu_bridge_kernel_turn.py`: pre-turn context inject + post-turn cognitive cycle in finish sidecars
  - `xinyu_bridge_pre_model_routes.py`: pre-turn hook on every chat turn
  - `xinyu_status.py`: `kernel_pending_review_count`, `kernel_writes_blocked`, etc.
  - Codex context uses full persistent runtime Self (not MiniSelf stub)
  - 32 kernel + bridge tests passing

**K-011 (Higher Goal 1, advanced)**: Kernel self-story from WM + Reorg history
  - `kernel/narrative_builder.py`: reads reorg/cycle jsonl + kernel state → `memory/kernel/self_story.md`
  - Auto-updates on structural impact or every 5 cycles
  - Exposed via `query_kernel_state.self_story_summary`

**K-012 (Higher Goal 3 prep, advanced)**: Owner co-evolution grants
  - `kernel/owner_grants.py`: `memory/kernel/owner_grants.json` explicit scope grants
  - Granted scopes downgrade `review_only` → `candidate` in review inbox
  - `grant_kernel_owner_scope(root, scope)` via bridge_access

**K-013 (Higher Goal 4, advanced)**: Reorg meta-learning
  - `kernel/meta_learning.py`: tracks fast/slow impact rates in `memory/kernel/reorg_meta_state.json`
  - Recommendations: `balanced`, `consider_lower_slow_escalation_threshold`, etc.
  - Exposed in `query_kernel_state.reorg_meta` and pre-turn metadata

**Later / Higher**:
- Long-term identity continuity narrative merge with stage13
- Dynamic threshold adjustment from meta-learning (currently observability only)

**Core Principle Reminder**:
After K-007, the focus shifts from "building the layers" to "making Experience actually change the system" in a controlled, owned, traceable way.

## 9. Current Project Structure (Relevant)

- `xinyu_core_bridge.py` + `xinyu_bridge_*.py` : Runtime orchestration
- `xinyu_qq_gateway.py` : Perception
- `experience/` : Early Experience layer
- `memory/` + `memory/events/` : Event sourcing + state files
- `custom/` : Extensible plugins/sidecars
- `kernel/` : Cognitive foundation (new)
- `tests/kernel/` : Kernel tests

## 10. References

- ChatGPT feedback on 认知内核架构设计_v0.1 (2026-06)
- Existing XinYu ARCHITECTURE.md (runtime focus)
- MEMORY-LAYERS.md, STATE-OF-XINYU.md
- kernel/README.md
- NEURO-INSPIRED-ENGINEERING-RULES.md

This document will be updated as layers are implemented.
```

This creates the architecture doc first.
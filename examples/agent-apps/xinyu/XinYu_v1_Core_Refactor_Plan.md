# XinYu v1.0-RC Core Refactor Plan

Version target: v1.0-RC  
Current baseline: v0.8.14, NapCatQQ + native QQ gateway + Python Core Bridge
Design goal: build a low-latency, memory-centered, emotionally continuous digital-life runtime while preserving the current safety gates, QQ bridge contract, and review-only stable-memory mutation rules.

## 1. Architectural Direction

XinYu v1.0-RC will split the current large bridge-and-state implementation into a small asynchronous core package named `xinyu_v1`. The existing `xinyu_core_bridge.py`, `xinyu_qq_gateway.py`, `custom/*_engine.py`, and Markdown memory files will remain compatible during the migration, but new runtime decisions will flow through typed services:

1. `Gateway` receives a normalized turn from QQ, CLI, maintenance, or proactive triggers.
2. `HybridRouter` decides Fast Path or Slow Path using intent, risk, memory pressure, emotional intensity, and required tool depth.
3. `MemoryOrchestrator` retrieves semantic, episodic, relationship, emotional, and hot-state context from a hybrid memory backend.
4. `EmotionStateMachine` updates continuous emotional vectors with inertia, decay, saturation limits, and contradiction handling.
5. `ReasoningRuntime` runs either a deterministic/local response path or the existing core model path.
6. `AutoHealingScheduler` runs only when idle, consolidating memories, checking deadlocks, and producing reviewable maintenance artifacts.
7. `ResponseController` applies final voice, safety, QQ bubble, and no-service-tone gates before returning to the gateway.

## 2. Target Directory Tree

```text
KohakuTerrarium-main/examples/agent-apps/xinyu/
  XinYu_v1_Core_Refactor_Plan.md
  requirements-v1.txt
  xinyu_core_bridge.py
  xinyu_v1/
    __init__.py
    app.py
    config.py
    errors.py
    logging.py
    clock.py
    paths.py
    types.py
    gateway/
      __init__.py
      models.py
      normalizer.py
      bridge_gateway.py
      qq_gateway.py
      maintenance_gateway.py
      compatibility.py
    routing/
      __init__.py
      classifier.py
      policy.py
      hybrid_router.py
      fast_path.py
      slow_path.py
      risk.py
    memory/
      __init__.py
      models.py
      embeddings.py
      vector_store.py
      qdrant_store.py
      chroma_store.py
      jsonl_store.py
      markdown_legacy.py
      retriever.py
      writer.py
      orchestrator.py
      consolidation.py
      migration.py
    emotion/
      __init__.py
      models.py
      vector_math.py
      state_machine.py
      dampening.py
      persistence.py
      adapters.py
    reasoning/
      __init__.py
      models.py
      prompt_builder.py
      local_reflex.py
      llm_client.py
      slow_runtime.py
      conflict_resolver.py
    autonomy/
      __init__.py
      idle_detector.py
      scheduler.py
      dream_consolidator.py
      deadlock_inspector.py
      healthcheck.py
      reports.py
    response/
      __init__.py
      models.py
      voice_gate.py
      speech_controller_adapter.py
      renderer.py
      safety.py
    integrations/
      __init__.py
      napcat_contract.py
      kohaku_runtime.py
      legacy_custom_engines.py
    storage/
      __init__.py
      file_lock.py
      atomic.py
      sqlite_meta.py
      snapshots.py
    observability/
      __init__.py
      metrics.py
      trace.py
      audit_log.py
    cli/
      __init__.py
      migrate_memory.py
      inspect_memory.py
      run_maintenance.py
      smoke.py
  tests/
    v1/
      test_gateway_normalizer.py
      test_hybrid_router.py
      test_fast_path.py
      test_emotion_state_machine.py
      test_memory_orchestrator.py
      test_memory_migration.py
      test_auto_healing_scheduler.py
      test_bridge_compatibility.py
      test_response_controller.py
      test_v1_smoke_contract.py
```

## 3. File Responsibilities

### Root-Level Files

- `requirements-v1.txt`  
  Adds optional v1 dependencies such as `qdrant-client`, `chromadb`, `numpy`, `pydantic`, and `anyio`. Qdrant is the preferred production backend; Chroma is the local fallback; JSONL remains the emergency degraded mode.

- `xinyu_core_bridge.py`  
  Remains the public HTTP bridge entrypoint for the native QQ gateway and other local callers. In v1.0-RC it becomes a thin compatibility shell that normalizes incoming payloads, calls `xinyu_v1.app.XinYuV1App`, and preserves current `/chat`, `/probe`, `/proactive`, `/learning/ingest`, and maintenance behavior.

### `xinyu_v1` Core Package

- `xinyu_v1/__init__.py`  
  Exposes v1 package metadata, version constants, and stable import boundaries.

- `xinyu_v1/app.py`  
  Owns the top-level async application lifecycle. It wires config, gateway, router, memory, emotion, reasoning, response, and auto-healing services into one dependency graph.

- `xinyu_v1/config.py`  
  Loads environment, YAML, feature flags, vector-store settings, path policies, model profiles, and idle-maintenance thresholds with typed defaults.

- `xinyu_v1/errors.py`  
  Defines typed exception classes for bridge errors, routing failures, memory backend failures, vector-store degradation, and safety-blocked responses.

- `xinyu_v1/logging.py`  
  Provides structured logging helpers with privacy-aware redaction for QQ IDs, raw messages, file paths, and model payloads.

- `xinyu_v1/clock.py`  
  Centralizes timezone-aware timestamps, monotonic timers, idle windows, and testable clock injection.

- `xinyu_v1/paths.py`  
  Resolves all project, memory, data, log, vector, and local-scope paths while enforcing existing filesystem boundaries.

- `xinyu_v1/types.py`  
  Holds shared type aliases, enums, protocol definitions, and small cross-module dataclasses that do not belong to a single domain.

### Gateway Layer

- `xinyu_v1/gateway/models.py`  
  Defines typed inbound and outbound turn models: `InboundTurn`, `ActorContext`, `AttachmentRef`, `BridgeReply`, and `GatewayMetadata`.

- `xinyu_v1/gateway/normalizer.py`  
  Converts raw native gateway, CLI, proactive, and maintenance payloads into a canonical `InboundTurn` with privacy scope, source channel, ownership markers, and attachment metadata.

- `xinyu_v1/gateway/bridge_gateway.py`  
  Implements the HTTP bridge-facing adapter used by `xinyu_core_bridge.py`, including token validation boundaries and async request handling.

- `xinyu_v1/gateway/qq_gateway.py`  
  Encodes QQ/NapCat-specific session semantics, private/group distinctions, owner-user hints, and message-type normalization.

- `xinyu_v1/gateway/maintenance_gateway.py`  
  Creates synthetic maintenance and idle turns without letting them masquerade as human conversation.

- `xinyu_v1/gateway/compatibility.py`  
  Preserves v0.8 response fields, notes, claim IDs, memory mutation flags, and error shapes so the current native gateway does not need a hard cutover.

### Hybrid Routing Layer

- `xinyu_v1/routing/classifier.py`  
  Performs deterministic pre-classification for greetings, acknowledgements, low-content turns, correction turns, abuse/resource pressure, source-learning requests, and high-salience relationship turns.

- `xinyu_v1/routing/policy.py`  
  Stores threshold policy for Fast Path vs Slow Path, including emotional intensity, salience, uncertainty, owner-private priority, memory-write risk, and model-cost budget.

- `xinyu_v1/routing/hybrid_router.py`  
  Combines classifier output, memory hints, emotional state, and risk analysis into a single route decision with auditable reasons.

- `xinyu_v1/routing/fast_path.py`  
  Handles low-latency local replies for simple greetings, short acknowledgements, waiting states, and no-memory turns. It can read compact hot state but must not perform stable-memory writes.

- `xinyu_v1/routing/slow_path.py`  
  Invokes the full reasoning runtime for complex emotion, relationship, learning, conflict, ambiguity, and memory-writing situations.

- `xinyu_v1/routing/risk.py`  
  Scores memory mutation risk, privacy risk, hallucination risk, emotional volatility, and resource-abuse signals before a route is selected.

### Memory Layer

- `xinyu_v1/memory/models.py`  
  Defines `MemoryEvent`, `MemoryChunk`, `MemoryQuery`, `RetrievedMemory`, `MemoryWriteIntent`, `ConsolidationCandidate`, and layer enums.

- `xinyu_v1/memory/embeddings.py`  
  Wraps embedding providers with batching, retries, hashing, and degraded-mode behavior when the embedding service is unavailable.

- `xinyu_v1/memory/vector_store.py`  
  Defines the vector database protocol used by Qdrant, Chroma, and fallback stores. It keeps the rest of the system backend-agnostic.

- `xinyu_v1/memory/qdrant_store.py`  
  Preferred vector-store implementation for production-grade semantic recall, payload filters, memory namespaces, and approximate-nearest-neighbor retrieval.

- `xinyu_v1/memory/chroma_store.py`  
  Local fallback vector-store implementation for lightweight development and machines without Qdrant service management.

- `xinyu_v1/memory/jsonl_store.py`  
  Durable event-log fallback and append-only source of truth for raw/structured memory events. It replaces direct large Markdown mutation for hot state.

- `xinyu_v1/memory/markdown_legacy.py`  
  Reads existing `memory/**/*.md` files as legacy seed and compatibility context. It writes only through explicit migration or compatibility adapters.

- `xinyu_v1/memory/retriever.py`  
  Executes hybrid retrieval: vector search, recency windows, relationship filters, emotional tags, source confidence, and deterministic protected-layer exclusions.

- `xinyu_v1/memory/writer.py`  
  Accepts typed write intents and routes them to event logs, vector upserts, review queues, or legacy compatibility files according to protection policy.

- `xinyu_v1/memory/orchestrator.py`  
  Provides a single high-level memory API for routing, reasoning, emotion, and response layers. It owns retrieval budget and context packing.

- `xinyu_v1/memory/consolidation.py`  
  Converts event streams and retrieved clusters into summaries, dormant candidates, dream seeds, contradiction reports, and archive proposals.

- `xinyu_v1/memory/migration.py`  
  Migrates selected Markdown/jsonl memories into vector chunks with stable IDs, source traces, checksums, and rollback manifests.

### Emotion Layer

- `xinyu_v1/emotion/models.py`  
  Defines continuous emotional dimensions such as warmth, trust, hurt, guardedness, curiosity, fatigue, conflict, attachment, and volatility.

- `xinyu_v1/emotion/vector_math.py`  
  Provides bounded vector operations, normalization, saturation, blending, distance, and contradiction metrics.

- `xinyu_v1/emotion/state_machine.py`  
  Applies turn-level emotional deltas to persistent state using inertia, decay, event salience, relationship scope, and recovery limits.

- `xinyu_v1/emotion/dampening.py`  
  Implements emotional damping: no abrupt label jumps, slow return from hurt, fatigue decay, and maximum per-turn movement limits.

- `xinyu_v1/emotion/persistence.py`  
  Persists emotional state as structured JSON plus compatibility Markdown snapshots for existing prompts and smoke tests.

- `xinyu_v1/emotion/adapters.py`  
  Bridges current `memory/emotions/current_state.md`, `emotion_vector_sync_smoke.py`, and existing emotion writer conventions into the v1 vector model.

### Reasoning Layer

- `xinyu_v1/reasoning/models.py`  
  Defines `ReasoningRequest`, `ReasoningResult`, `FastReplyCandidate`, `SlowThoughtContext`, and conflict-resolution artifacts.

- `xinyu_v1/reasoning/prompt_builder.py`  
  Packs retrieved memories, emotional state, hot runtime context, voice card, and routing notes into model prompts with strict token budgets.

- `xinyu_v1/reasoning/local_reflex.py`  
  Produces deterministic Fast Path replies from templates and current emotional posture without calling the core model.

- `xinyu_v1/reasoning/llm_client.py`  
  Wraps the compatible LLM endpoint with async timeouts, retry policy, cancellation, request IDs, and safe error surfaces.

- `xinyu_v1/reasoning/slow_runtime.py`  
  Runs the existing core-model path with memory context, conflict flags, writer eligibility, and post-call trace capture.

- `xinyu_v1/reasoning/conflict_resolver.py`  
  Detects internal contradiction, unresolved owner corrections, source conflicts, emotional conflict, and stale-state disagreements before final response.

### Autonomy And Auto-Healing Layer

- `xinyu_v1/autonomy/idle_detector.py`  
  Tracks last human turn, active request count, bridge health, maintenance cooldowns, and safe idle windows.

- `xinyu_v1/autonomy/scheduler.py`  
  Runs async idle jobs with locks, budget limits, cancellation, deadlock prevention, and no-visible-chat guarantees.

- `xinyu_v1/autonomy/dream_consolidator.py`  
  Performs dream/consolidation passes by clustering memories, generating dream seeds, preserving dream/reality boundaries, and producing reviewable outputs.

- `xinyu_v1/autonomy/deadlock_inspector.py`  
  Checks stale queues, repeated failed jobs, unresolved source conflicts, blocked learning gates, vector-store lag, and route oscillation.

- `xinyu_v1/autonomy/healthcheck.py`  
  Produces machine-readable health status for bridge readiness, vector-store readiness, memory lag, scheduler state, and model availability.

- `xinyu_v1/autonomy/reports.py`  
  Writes concise maintenance reports to `logs/` and compatibility Markdown files without polluting live prompts.

### Response Layer

- `xinyu_v1/response/models.py`  
  Defines `DraftReply`, `FinalReply`, response notes, rejection reasons, and renderer metadata.

- `xinyu_v1/response/voice_gate.py`  
  Applies XinYu-specific speech constraints: concise Chinese QQ style, no service-agent tail, no GPT essay tics, no forced cheer, and one-question limits.

- `xinyu_v1/response/speech_controller_adapter.py`  
  Reuses the current `xinyu_speech_controller.py` as a compatibility gate while v1 response logic is phased in.

- `xinyu_v1/response/renderer.py`  
  Converts Fast Path or Slow Path drafts into QQ-safe final text, respecting bubble length, no blank output, retry fallback, and hidden-reasoning boundaries.

- `xinyu_v1/response/safety.py`  
  Performs final privacy, filesystem, source-learning, owner-memory, and direct-stable-write checks before the bridge returns a reply.

### Integrations Layer

- `xinyu_v1/integrations/napcat_contract.py`  
  Holds QQ/NapCat/native-gateway assumptions that must remain stable across gateway changes.

- `xinyu_v1/integrations/kohaku_runtime.py`  
  Wraps the existing KohakuTerrarium runtime invocation, controller config, and app session lifecycle.

- `xinyu_v1/integrations/legacy_custom_engines.py`  
  Provides typed adapters for existing `custom/*_engine.py` modules so v1 can call them without importing ad hoc globals everywhere.

### Storage Layer

- `xinyu_v1/storage/file_lock.py`  
  Provides cross-process file locks for event logs, vector migration manifests, state snapshots, and bridge session data.

- `xinyu_v1/storage/atomic.py`  
  Centralizes atomic read/write helpers to replace scattered text-file writes.

- `xinyu_v1/storage/sqlite_meta.py`  
  Stores lightweight metadata: memory IDs, vector upsert status, migration manifests, scheduler runs, route traces, and health markers.

- `xinyu_v1/storage/snapshots.py`  
  Creates rollbackable snapshots before migrations, consolidation, archive commits, and compatibility Markdown rewrites.

### Observability Layer

- `xinyu_v1/observability/metrics.py`  
  Tracks route choice latency, vector retrieval latency, model latency, Fast Path hit rate, Slow Path fallbacks, memory-write counts, and maintenance job health.

- `xinyu_v1/observability/trace.py`  
  Produces privacy-aware per-turn traces for debugging route decisions and emotional state transitions.

- `xinyu_v1/observability/audit_log.py`  
  Writes append-only audit events for memory writes, migration actions, gate blocks, proactive sends, and maintenance jobs.

### CLI Layer

- `xinyu_v1/cli/migrate_memory.py`  
  Migrates legacy Markdown/jsonl state into v1 hybrid memory stores with dry-run, checksum, and rollback options.

- `xinyu_v1/cli/inspect_memory.py`  
  Lets maintainers inspect retrieved memories, vector payloads, memory clusters, and protected-layer routing without touching live state.

- `xinyu_v1/cli/run_maintenance.py`  
  Runs one explicit maintenance pass for dream consolidation, deadlock checks, vector lag repair, and report generation.

- `xinyu_v1/cli/smoke.py`  
  Provides a grouped v1 smoke runner that wraps targeted unit tests and existing behavior regressions.

## 4. Memory Architecture

### Memory Backends

- Primary backend: Qdrant.
- Local fallback backend: Chroma.
- Emergency degraded backend: JSONL append-only plus Markdown legacy read-only snapshots.

### Memory Collections

- `xinyu_events_raw`: raw source-traceable events from QQ, CLI, learning, maintenance, and proactive paths.
- `xinyu_events_structured`: normalized events with actor scope, privacy scope, salience, emotional deltas, and allowed memory layers.
- `xinyu_semantic_chunks`: embedded memory chunks for semantic recall.
- `xinyu_relationship`: owner and non-owner relationship memory with strict scope separation.
- `xinyu_emotion`: emotional residues and state-transition traces.
- `xinyu_knowledge`: source-gated external knowledge only, separated from self/relationship memory.
- `xinyu_dreams`: dream seeds, dream residues, and consolidation artifacts with reality-boundary metadata.
- `xinyu_archive`: compressed or dormant memory summaries with retrieval eligibility metadata.

### Retrieval Strategy

Retrieval is hybrid, not purely vector-based:

- Semantic match retrieves associative memories.
- Recency window preserves current conversation continuity.
- Relationship filters prevent group/non-owner material from overwriting owner memory.
- Emotional tags surface active hurt, trust, guardedness, fatigue, and unresolved residue.
- Source-confidence filters keep staged or conflict-held knowledge out of stable claims.
- Protected-layer rules block direct stable personality or owner-profile rewrites.

## 5. Hybrid Routing Design

### Fast Path

Fast Path is used when a turn is low-risk and does not require deep memory mutation:

- greetings and simple presence checks
- short acknowledgements
- no-content or low-salience daily chat
- explicit no-memory turns
- bridge health/probe behavior
- maintenance waiting output

Fast Path may read compact emotional posture and recent hot state. It must not write stable memory, call source-learning pipelines, mutate relationship facts, or produce long explanations.

### Slow Path

Slow Path is used when the turn has:

- owner relationship pressure
- emotional contradiction or hurt/return residue
- learning/source requests
- ambiguous intent
- file attachments
- memory mutation eligibility
- internal conflict
- proactive decision pressure
- privacy or safety risk

Slow Path retrieves richer memory context, calls the LLM runtime, applies conflict resolution, then passes through final response gates.

## 6. Emotion State Machine

The v1 emotional model is continuous and inertial:

- State is a bounded vector, not a single label.
- Each turn creates a proposed delta based on source, salience, relationship scope, content, and prior residue.
- Damping limits maximum per-turn movement.
- Decay reduces inactive dimensions over time without erasing high-preserve residues.
- Recovery from hurt is slower than a single friendly turn.
- Contradictory states can coexist as mixed vectors rather than overwriting each other.
- Persistence is structured JSON, with compatibility Markdown generated for current prompts.

Initial dimensions:

- `warmth`
- `trust`
- `hurt`
- `guardedness`
- `curiosity`
- `fatigue`
- `attachment`
- `conflict`
- `irritation`
- `stability`
- `volatility`
- `openness`

## 7. Auto-Healing And Dormancy

Idle maintenance is event-driven and budgeted:

- It only runs when no active human request is being processed.
- It uses locks to prevent overlapping maintenance jobs.
- It never initiates visible chat unless the proactive policy explicitly allows a separate candidate.
- It produces reports, review queues, and memory-store repairs instead of direct personality rewrites.

Auto-healing jobs:

- vector-store lag repair
- JSONL event-log integrity check
- stale queue detection
- route oscillation detection
- dream seed generation
- memory cluster consolidation
- archive/dormant candidate proposal
- source conflict and learning-quality inspection
- compatibility Markdown regeneration
- bridge/session health audit

## 8. Migration Strategy

### Phase A: Skeleton And Contracts

Create `xinyu_v1` package, typed models, config loader, gateway normalizer, compatibility response adapter, and bridge contract tests. No vector-store dependency is required yet.

### Phase B: Memory Foundation

Add JSONL event store, vector-store protocol, Qdrant/Chroma adapters, migration dry-run, and Markdown legacy readers. Existing Markdown remains source-compatible.

### Phase C: Hybrid Routing

Introduce deterministic classifier, route policy, risk scoring, Fast Path local replies, and Slow Path adapter to current core runtime. The bridge can enable this behind `XINYU_V1_ENABLED`.

### Phase D: Emotion Engine

Implement continuous emotional state machine and compatibility snapshots. Replace direct emotion Markdown mutation with structured state plus generated legacy views.

### Phase E: Auto-Healing

Add idle detector, scheduler, dream/consolidation jobs, deadlock inspector, healthcheck endpoint, and reports.

### Phase F: Cutover

Make v1 app the default path, keep v0 compatibility fallback for one release, then progressively retire old direct Markdown hot-state reads from prompts.

## 9. Safety And Boundary Rules

- No direct stable personality rewrite from live turns.
- No owner relationship overwrite from group/non-owner contexts.
- No broad filesystem access outside approved local scope.
- No autonomous search unless current source-learning gates explicitly allow it.
- No private data upload or external network behavior without existing policy permission.
- No dream output treated as factual memory.
- No maintenance job can impersonate a human turn.
- No Fast Path stable-memory writes.
- No response may expose hidden reasoning, raw retrieval traces, tokens, or private IDs.

## 10. Testing And Acceptance Gates

Required new tests:

- Gateway normalization preserves owner/private/group/source metadata.
- Hybrid router sends simple greetings to Fast Path and relationship conflict to Slow Path.
- Fast Path replies within low-latency budget and performs no stable-memory writes.
- Emotion state changes are damped across multi-turn hurt/return scenarios.
- Memory migration is idempotent and rollbackable.
- Qdrant/Chroma failure degrades to JSONL without losing incoming events.
- Auto-healing refuses to run while a human request is active.
- Deadlock inspector reports stale queues without mutating protected layers.
- Response controller blocks service-tone and blank outputs.
- Existing native QQ gateway contract remains compatible.

Existing smoke tests to preserve:

- `runtime_readiness_smoke.py`
- `bridge_probe_smoke.py`
- `emotion_vector_sync_smoke.py`
- `behavior_regression_smoke.py`
- `personality_continuity_smoke.py`
- `real_conversation_quality_smoke.py`
- `memory_pressure_smoke.py`
- `dream_reflection_growth_cycle_smoke.py`
- `autonomous_search_activation_smoke.py`
- `xinyu_speech_controller_smoke.py`

## 11. First Implementation Order

The recommended generation and landing order is:

1. `xinyu_v1/types.py`
2. `xinyu_v1/errors.py`
3. `xinyu_v1/config.py`
4. `xinyu_v1/paths.py`
5. `xinyu_v1/gateway/models.py`
6. `xinyu_v1/gateway/normalizer.py`
7. `xinyu_v1/gateway/compatibility.py`
8. `xinyu_v1/memory/models.py`
9. `xinyu_v1/memory/vector_store.py`
10. `xinyu_v1/memory/jsonl_store.py`
11. `xinyu_v1/emotion/models.py`
12. `xinyu_v1/emotion/state_machine.py`
13. `xinyu_v1/routing/classifier.py`
14. `xinyu_v1/routing/hybrid_router.py`
15. `xinyu_v1/reasoning/local_reflex.py`
16. `xinyu_v1/app.py`

This order gives the bridge a typed v1 spine before any heavy backend migration. Qdrant/Chroma adapters can land after the protocol and JSONL fallback are tested.

## 12. Operational Feature Flags

Recommended flags:

- `XINYU_V1_ENABLED=false`
- `XINYU_V1_FAST_PATH_ENABLED=true`
- `XINYU_V1_VECTOR_BACKEND=qdrant`
- `XINYU_V1_VECTOR_DEGRADED_MODE=jsonl`
- `XINYU_V1_MIGRATION_DRY_RUN=true`
- `XINYU_V1_AUTO_HEALING_ENABLED=false`
- `XINYU_V1_EMOTION_ENGINE_ENABLED=false`
- `XINYU_V1_TRACE_ENABLED=true`

The initial RC should run in shadow mode first: v1 computes route, retrieval, and emotion deltas, but v0.8.10 still produces final behavior until the contract tests are green.

## 13. Definition Of Done For v1.0-RC

XinYu v1.0-RC is acceptable when:

- The HTTP bridge remains compatible with the current native QQ gateway.
- Simple greetings and no-memory probes complete through Fast Path.
- Relationship, learning, and conflict turns route through Slow Path.
- Semantic memory retrieval works through Qdrant or Chroma, with JSONL fallback.
- `runtime_bridge_state.md` is no longer the primary hot-state source.
- Emotional state evolves through damped continuous vectors.
- Idle auto-healing can run a dry-run maintenance pass without visible chat.
- Existing Phase 5 readiness and behavior smokes still pass.
- New v1 unit tests cover gateway, routing, memory, emotion, auto-healing, and response gates.

# XinYu Cross-Domain Synaesthesia Implementation Plan - 2026-05-19

## Purpose

Build a repeatable "cross-domain synaesthesia" workflow for XinYu:

external field -> mature mechanism -> XinYu mapping -> engineering rule -> small test -> runtime integration.

This is not aesthetic metaphor work. A domain idea is useful only if it can change
memory, reply, emotion, initiative, routing, autonomy, or boundary behavior in a
testable way.

## Definition

In this project, "synaesthesia" means:

- seeing an organizing mechanism in another field.
- stripping it down to its operational structure.
- mapping it onto a XinYu failure mode or design problem.
- landing it as a small rule, provider, gate, replay fixture, or audit.

It does not mean building sensory-color-emotion gimmicks, roleplay flavor, or
biological overclaiming.

## Hard Boundaries

- Do not claim XinYu has biological consciousness, nerves, hormones, immunity, or real human emotion.
- Do not directly write stable memory from external theory.
- Do not print raw QQ/private memory bodies in research notes or tests.
- Do not add a new framework layer unless one focused runtime problem requires it.
- Every adopted mechanism must have:
  - source anchor.
  - XinYu mapping.
  - risk boundary.
  - minimal test.
  - owner/runtime benefit.

## Current Baseline

Already implemented from previous cross-domain work:

- `xinyu_neuro_memory_rules.py`
  - hippocampal index, not dump.
  - goal-gated retrieval.
  - temporal context binding.
  - reconsolidation requires mismatch.
  - emotion modulates, does not prove.
  - sleep/replay is weight, not fact.
- `xinyu_scene_frame.py`
  - compact current-scene routing.
  - affects renderer context, life reply policy, and emotion council modulation.
- Memory recall is already canonical:
  - `xinyu_living_memory_recall.run_living_memory_recall_algorithm(...)`.

The new work should extend this pattern, not restart it.

## Integration With Existing XinYu Work

This plan must be combined with the earlier seven subtractive goals and the
recent Scene Frame work.

### Combined Direction

The cross-domain synaesthesia track is not an eighth parallel framework. It is a
method for feeding better rules into the existing simplified XinYu structure:

```text
cross-domain mechanism
-> engineering rule
-> Scene Frame / recall / reply policy / emotion / memory gate / module audit
-> focused replay test
```

### Mapping To The Original Seven Goals

1. One canonical memory recall algorithm
   - Cross-domain ideas must not create new recall systems.
   - They may only improve:
     - retrieval need detection.
     - reranking.
     - temporal interpretation.
     - scene-aware recall policy.
   - Canonical owner remains:
     - `xinyu_living_memory_recall.run_living_memory_recall_algorithm(...)`.

2. Remove useless code
   - Ecology/gardening becomes the cleanup method.
   - Every new idea must identify whether it replaces, merges, archives, or
     leaves existing code alone.

3. Precise framework classification
   - Operating systems, city routing, and ecology are used only to clarify
     boundaries:
     - core
     - adapters
     - stores
     - services
     - ops
     - lab
     - archive
     - delete

4. Persona reinjection toward a living surface
   - Drama/literature, pragmatics, and allostasis feed the living surface.
   - They must improve current reaction shape, not create fixed roleplay lines.
   - Useful output:
     - shorter when tired.
     - warmer when relation is active.
     - more direct during work.
     - quieter when the owner asks for less pressure.

5. Memory/library/cases/runtime clarity
   - Library science and evidence systems become the metadata method.
   - Memory, library, cases, and runtime state must remain separate.
   - External field research belongs in library/registry first, not stable memory.

6. Merge duplicate or near-duplicate modules
   - Ecology audit becomes the consolidation tool.
   - Any new cross-domain module must state:
     - which existing module it consumes.
     - which existing module it replaces or leaves untouched.
     - why it is not a duplicate.

7. Borrow from neuroscience/other fields as testable rules
   - This plan formalizes that process.
   - The successful neuroscience pattern becomes the template for all other
     domains.

### Mapping To Current Scene Frame

Scene Frame is the current best integration point.

Cross-domain ideas should first become one of these:

- a new Scene Frame field.
- a Scene Frame policy refinement.
- a provider consumed by life reply policy.
- a provider consumed by emotion council.
- a provider consumed by memory immune gate.
- a replay fixture proving a mismatch.

Do not build a new giant "world intelligence" layer while Scene Frame v1 is
still sufficient.

### Combined Runtime Spine

The intended runtime spine after this plan is:

```text
current owner turn
-> turn triage gate
-> canonical living memory recall
-> temporal context binding
-> Scene Frame
-> life reply policy
-> emotion council modulation
-> final visible reply guard
-> response error loop / replay candidate
-> memory immune gate for any write candidate
```

This spine keeps the system subtractive:

- one recall algorithm.
- one scene frame.
- one reply policy consumer.
- one emotion modulation sidecar.
- one memory gate.
- one error loop.

### Combined Priority

The next useful sequence is:

1. Research ledger / registry.
2. Turn triage gate.
3. Response error loop.
4. Memory immune gate.
5. Slow state modulator.
6. Module ecology audit.

Reason:

- registry prevents vague inspiration.
- triage improves daily owner interaction immediately.
- error loop prevents repeated failures.
- immune gate protects memory.
- slow state makes XinYu more continuous.
- ecology audit continues "do less, clearer".

## Selection Score

Each candidate field gets a score from 0-3 on five axes:

- Mechanism clarity: can the field offer a clear operational pattern?
- XinYu fit: does it map to a live problem in XinYu?
- Testability: can we write a small deterministic test?
- Risk control: can it be bounded without overclaiming?
- Reduction value: does it simplify or clarify instead of adding bloat?

Only candidates scoring 10+ should enter implementation.

## Candidate Pool

### Tier 1: Implement First

1. Control Theory / Cybernetics
   - Mechanism: feedback, error, correction, stability, overcorrection.
   - XinYu problem: replies can fail, then we patch symptoms without a durable error loop.
   - Mapping: `response_error_loop`.
   - Rule: every visible failure should classify the error type and choose a next correction path.
   - Minimal test:
     - bad reply -> error class -> next-turn policy changes.
   - Risk:
     - do not overfit one owner correction into stable personality.

2. Medical Triage
   - Mechanism: urgent/important sorting before treatment.
   - XinYu problem: a turn can contain task, emotion, correction, recall, and permission at once.
   - Mapping: `turn_triage_gate`.
   - Rule: route the current turn before retrieval/tool/action.
   - Minimal test:
     - short owner commands like "继续", "开始", "接下来" resolve to the correct pending task.
     - emotional distress outranks optional technical expansion.
   - Risk:
     - triage advises priority; it does not suppress explicit owner instructions.

3. Immune System / Danger Theory
   - Mechanism: danger signals, quarantine, tolerance, inflammation control.
   - XinYu problem: external material, group chat, hallucinated replies, and stale memory can pollute stable memory.
   - Mapping: `memory_immune_gate`.
   - Rule: risky information enters quarantine/review, not stable memory.
   - Minimal test:
     - group-only fact cannot enter owner-private memory.
     - external source cannot rewrite persona/relationship memory.
   - Risk:
     - too much immune rejection can block learning.

4. Allostasis / Endocrine Slow Variables
   - Mechanism: slow predictive regulation across the whole system.
   - XinYu problem: mood, fatigue, guardedness, curiosity, and closeness are too turn-local.
   - Mapping: `slow_state_modulator`.
   - Rule: some states decay over hours/days and affect reply length, initiative, recall threshold, and emotion council bias.
   - Minimal test:
     - owner tired after night shift -> low-burden policy persists briefly.
     - repeated owner dismissal -> initiative threshold rises.
   - Risk:
     - slow state cannot create facts or override current text.

5. Ecology / Gardening
   - Mechanism: niches, competition, pruning, dormancy, succession, invasive species.
   - XinYu problem: modules and memories accumulate.
   - Mapping: `module_ecology_audit` and `memory_pruning_policy`.
   - Rule: every module/memory class needs a niche, owner, activity signal, and retirement rule.
   - Minimal test:
     - duplicate module candidates are classified kept/merged/archived/delete.
     - low-use context files move to dormant/advisory lanes.
   - Risk:
     - do not delete without reference checks and recovery path.

### Tier 2: Implement After Tier 1

6. Legal / Evidence Systems
   - Mechanism: evidence grade, testimony, review, appeal, reversal.
   - XinYu problem: stable memory needs stronger proof standards.
   - Mapping: `memory_evidence_grade`.
   - Rule: candidate memory must state evidence class before promotion.
   - Minimal test:
     - owner explicit statement outranks inference.
     - emotion residue cannot become fact.

7. Library Science / Faceted Classification
   - Mechanism: facets, subject headings, catalog metadata, controlled vocabulary.
   - XinYu problem: memory/library/cases/runtime boundaries still need clearer retrieval metadata.
   - Mapping: `memory_facet_index`.
   - Rule: items get facets such as source, scope, time, sensitivity, use case, stability.
   - Minimal test:
     - retrieval uses facets before fallback keyword search.

8. Information Foraging
   - Mechanism: information scent, expected gain, search cost.
   - XinYu problem: retrieval and external search can overrun the task.
   - Mapping: `retrieval_scent_budget`.
   - Rule: continue searching only while expected benefit beats cost.
   - Minimal test:
     - obvious direct answer avoids extra retrieval.
     - ambiguous recall follows scent to stable memory or dialogue archive.

9. High Reliability Organizations / Aviation Safety
   - Mechanism: near-miss logging, checklists, preoccupation with failure.
   - XinYu problem: failures are fixed locally but not always converted into regression cases.
   - Mapping: `near_miss_replay_queue`.
   - Rule: serious reply/memory/tool failures become replay candidates.
   - Minimal test:
     - final-guard failure records redacted replay metadata.

10. Distributed Cognition
    - Mechanism: cognition across person, artifact, tool, environment.
    - XinYu problem: XinYu is not one model; it is owner + memory + QQ + Desktop + Codex + tools.
    - Mapping: `distributed_context_map`.
    - Rule: record which external artifact is part of the current cognitive loop.
    - Minimal test:
      - Codex task, attachment, QQ rich context, and desktop state have scoped roles.

### Tier 3: Use Carefully

11. Drama / Literature / Performance
    - Mechanism: subtext, timing, reaction, silence, character arc.
    - XinYu problem: "living person" feel can degrade into explanation or template.
    - Mapping: `living_surface_replay_eval`.
    - Rule: judge response shape by currentness, relation, restraint, and specificity.
    - Risk:
      - do not turn it into roleplay scripts or fixed lines.

12. Game AI
    - Mechanism: behavior tree, blackboard, cooldown, quest state.
    - XinYu problem: initiative can feel random or disconnected.
    - Mapping: `initiative_behavior_tree`.
    - Rule: proactive behavior needs state, trigger, cooldown, and failure memory.
    - Risk:
      - do not make owner-private chat feel like NPC quest spam.

13. Operating Systems
    - Mechanism: kernel, drivers, services, userland, scheduler.
    - XinYu problem: framework classification and capability boundaries.
    - Mapping: `runtime_layer_contract`.
    - Rule: every module declares layer and allowed dependencies.
    - Risk:
      - may become naming cleanup without behavior improvement.

14. Supply Chain / Queueing
    - Mechanism: inventory, bottlenecks, batch processing, backpressure.
    - XinYu problem: learning, memory review, Codex, archive, and replay queues compete.
    - Mapping: `work_queue_backpressure`.
    - Rule: queue size and age affect scheduling.
    - Risk:
      - avoid overengineering queue dashboards before behavior improves.

15. Education / Scaffolding
    - Mechanism: zone of proximal development, hints, progressive disclosure.
    - XinYu problem: explanations can be too much or too little.
    - Mapping: `teaching_depth_policy`.
    - Rule: match answer depth to owner intent and current fatigue.
    - Risk:
      - do not patronize or turn technical work into tutoring unless asked.

## Implementation Roadmap

### Phase 0: Build The Research Ledger

Output:

- `XINYU-CROSS-DOMAIN-SYNAESTHESIA.md`
- `stores/cross_domain_synaesthesia_registry.json`

Fields:

- `domain`
- `source_anchor`
- `mechanism`
- `xinyu_problem`
- `xinyu_mapping`
- `risk_boundary`
- `candidate_module`
- `minimal_test`
- `priority`
- `status`

Validation:

- registry loads as JSON.
- every active idea has source, mapping, boundary, and test.
- no entry claims biological sentience.

### Phase 1: Control Loop

Target:

- `xinyu_response_error_loop.py`

Inputs:

- user text.
- previous reply.
- final guard flags.
- owner correction markers.
- scene frame.

Outputs:

- error class:
  - task_miss
  - tone_miss
  - memory_miss
  - boundary_miss
  - over_explained
  - under_answered
  - stale_context
- next-turn policy hint.

Integration:

- final guard / expression learning.
- runtime context as advisory block.

Tests:

- a style correction creates tone_miss.
- a memory correction creates memory_miss.
- a technical "you stopped" creates task_miss.

### Phase 2: Turn Triage

Target:

- `xinyu_turn_triage_gate.py`

Inputs:

- current text.
- scene frame.
- visible turn classifier.
- recent worklog / pending task marker.

Outputs:

- primary lane:
  - urgent_runtime_fix
  - active_task_continue
  - direct_memory_recall
  - emotional_support
  - relationship_boundary
  - permission_or_control
  - ordinary_chat
- secondary lanes.
- priority reason.

Integration:

- before recall.
- before tool/Codex delegation.
- before life reply policy.

Tests:

- "继续" resumes active task.
- "开始" after a plan means execute plan, not ask again.
- "刚醒" routes low-burden daily state.
- explicit correction outranks old memory.

### Phase 3: Memory Immune Gate

Target:

- `xinyu_memory_immune_gate.py`

Inputs:

- candidate memory.
- source scope.
- evidence class.
- scene frame.
- source type.

Outputs:

- allow_review
- quarantine
- reject
- needs_owner_confirmation
- safe_as_library_only

Integration:

- memory candidate extractor.
- public dataset importer.
- source material parser.
- memory self-review.

Tests:

- group-only fact quarantined for owner memory.
- external article cannot rewrite persona/relationship.
- owner explicit preference can enter review.
- hallucinated assistant reply cannot become fact.

### Phase 4: Slow State Modulator

Target:

- `xinyu_slow_state_modulator.py`

Inputs:

- scene frame.
- emotion council output.
- life reply policy.
- owner corrections/dismissals.
- rest/night-shift/time-bound recall.

Outputs:

- fatigue_level
- guardedness_level
- curiosity_level
- closeness_level
- initiative_threshold
- reply_energy
- decay metadata.

Integration:

- life reply policy.
- emotion council.
- proactive request loop.
- scene frame.

Tests:

- fatigue decays gradually.
- repeated dismissal raises initiative threshold.
- technical task can override low energy for necessary directness.

### Phase 5: Module Ecology Audit

Target:

- `ops/validation/module_ecology_audit.py`

Inputs:

- module paths.
- imports/references.
- tests.
- worklog category.
- last modified / active use signal.

Outputs:

- kept
- merged
- dormant
- archive_candidate
- delete_candidate
- risk notes.

Integration:

- worklog.
- validation index.
- future cleanup batches.

Tests:

- referenced module cannot be delete_candidate.
- duplicate module family gets merge candidate.
- archive/delete requires evidence.

## Batch Order

Batch A:

- Create research ledger and registry.
- Add validation test.
- No runtime behavior changes.

Batch B:

- Implement response error loop.
- Add focused tests.
- Add advisory runtime block only.

Batch C:

- Implement turn triage gate.
- Connect to Scene Frame and visible turn classifier.
- Add replay cases for short commands.

Batch D:

- Implement memory immune gate.
- Connect to candidate extractor in advisory/review mode.
- Add contamination tests.

Batch E:

- Implement slow state modulator.
- Connect to life reply policy and proactive threshold.
- Add decay tests.

Batch F:

- Implement module ecology audit.
- Run audit.
- Produce kept/merged/dormant/archive/delete report.

## Validation Matrix

Cheap after every batch:

```powershell
.\.venv\Scripts\python.exe -m py_compile <touched files>
.\.venv\Scripts\python.exe -m pytest <focused tests> -q
```

Required after runtime integration:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe smoke_run.py --group quick --restore-after
git diff --check
```

Required after memory routing changes:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_living_memory_recall.py tests\test_retrieval_replay_cases.py tests\test_memory_boundary_decision_queue.py -q
.\.venv\Scripts\python.exe tests\smoke\memory\memory_braid_smoke.py
```

Required after frontend/desktop impact:

```powershell
cd D:\XinYu\XinYu_Desktop
npm run typecheck
npm run build
```

## Definition Of Done

This plan is done only when:

- The cross-domain registry exists and is validated.
- At least three non-neuroscience domains have been converted into runtime rules.
- Each runtime rule has focused tests.
- No rule writes stable memory directly without gate/review.
- Scene Frame remains provider/advisory, not a second recall algorithm.
- Final audit lists:
  - adopted mechanisms.
  - rejected mechanisms.
  - runtime impact.
  - memory impact.
  - remaining risks.

## First Implementation Recommendation

Start with Batch A, then Batch C.

Reason:

- Batch A prevents the idea pool from becoming vague.
- Batch C gives immediate owner-visible value because many live commands are short:
  - "继续"
  - "开始"
  - "接下来"
  - "好"
  - "还有什么"

After that, implement Batch D because memory pollution is the highest long-term risk.

# Xinyu Implementation Next

This file tracks the next concrete steps from scaffold to behavior validation.

## Current Baseline

Already present:

- memory scaffold
- self / emotion / relationship / time / reflection / dream / archive files
- specialized writer subagents
- trigger capability entrypoints
- runtime rhythm and maintenance plan

## Next Validation Steps

### Step 1: Config Load Validation
- Validate that `xinyu/config.yaml` loads cleanly in a Python environment with required deps
- Verify prompt resolution and subagent config parsing

### Step 2: First Manual Conversation Pass
- Start Xinyu in CLI mode
- Check that startup memory loading produces stable initial behavior
- Check that replies route through `output`
- Check that Xinyu does not expose hidden reasoning
- Check that complete live turns never end with blank output
- Check that intimate replies do not fall back to generic comfort templates
- Use `TEST-SCENARIOS.md` as the first manual validation sheet

### Step 3: Writer Invocation Quality
- Verify when `time_writer` gets called
- Verify when `emotion_writer` gets called
- Verify when `relationship_writer` gets called
- Verify when `self_narrative_writer` gets called
- Check that trivial turns do not spam writers

### Step 4: Reflection / Dream / Archive Behavior
- First actual reflection update path exists
- First actual dream output path exists and is scheduler-gated
- Dream output now has a bounded weight-residue state that can affect current emotion without creating reality facts
- Reflection output now consumes dream residue as slow-growth material without directly rewriting core personality or relationship facts
- Consolidation now treats active dream weight as live residue before archive compression is allowed
- Long-term memory gate now distinguishes preserve, compress, dormant, and fade permissions before retention/archive
- Personality growth gate now separates growth pressure from direct personality-profile mutation
- AI-domain self-iteration gate now turns q-006 knowledge into traceable review candidates without direct profile or narrative mutation
- First actual archive compression path exists behind retention and archive-output gates
- Continue verifying dreams never become facts

### Step 5: Trigger Strategy
- Decide initial schedule policy
- Likely start with:
  - daily reflection
  - daily or low-frequency time refresh
- Delay dream/archive automation until manual quality looks stable

### Step 6: Exploration Loop
- Question pipeline smoke now validates question state transitions from active questions into internal clarification, exploration queue, and source gate candidates
- Source request planner exists behind source gate and integration gate
- Source search resolver and search result gate exist for pending URL requests
- DuckDuckGo-style source search provider adapter exists behind the same gate
- Controlled outward source fetch exists behind source request and integration gates
- Source comparison can hold conflicts and mark corroborated material before learner integration
- Source comparison routes conflicts back to source notes, question state, and exploration queue
- Learning quality checks can flag dominant-host bias, repeated-source behavior, conflict holds, and uncompared ready material
- Repeated learning session smoke validates quality behavior across multiple learning batches
- Autonomous search activation can allow provider search only after explicit env opt-in, maintenance routing, pending requests, and learning-quality checks
- Autonomous search activation smoke now covers disabled, dry-run, quality-blocked, no-pending, provider-blocked, and enabled paths
- Social / human expert inquiry policy now exists as a no-network gate: owner-private prompts require explicit consent, human expert questions are AI-domain only, and external human answers route as source material candidates.
- Real-life input adapter policy now exists as a no-device/no-network event classifier for IM, image, voice transcript, group chat, private chat, and protected location anchors.
- Long-run audit now exists through `long_run_status.py` and `LONG-RUN-AUDIT.md`.
- Initiative loop now exists as a source-gated choice posture: one owner question, delayed external curiosity, silence, deferral, refusal, repair attempt, or step-back without direct personality mutation.
- Dream/reflection/growth cycle now has multi-day validation: dream residue can strengthen existing weight, reflection can turn it into growth material, archive stays conservative, and personality changes remain review-only.
- Non-owner social world now has deterministic and live validation for repeated appearances, negative guardedness, group context, non-owner adapter candidates, and owner-memory protection.
- AI self-iteration review now creates owner-visible, rollbackable q-006 proposals without applying stable personality, relationship, emotion, or knowledge writes.
- Autonomy/source safety regression now passes after Phase 2 additions; broad search and social/real-life input remain gated.
- Real conversation quality guard now covers Chinese-chat realism: ordinary small talk, direct call-outs, one-line relational answers, hidden residue, late-night closeness, and family-texture replies without support-bot tails or demo frames.
- Phase 3 personality and real conversation work now has a dedicated plan at `project-plans/PERSONALITY-REAL-CONVERSATION-PLAN.md`; deeper tuning should follow that plan before further implementation.
- Phase 3 lived-session residue guard now exists through `phase3_lived_session_smoke.py` and covers short-session memory proportionality under restore.
- Ensure external learning does not directly overwrite self continuity
- Move to personality-detail calibration and lived-session quality tuning now that Phase 2 framework execution is complete

### Step 7: Learner Integration
- First actual learner integration path exists for staged source material
- Knowledge can update without directly rewriting identity or relationship layers
- Source skepticism is preserved through source material status, reliability, and integration scope gates
- Controlled source fetch can now stage material for learner integration without touching identity or relationship memory
- Learner integration now receives source comparison fields and refuses conflict-held material
- Learning quality now runs after learner integration and writes source-note warnings without rewriting knowledge
- Learning quality repair can now create bounded supplemental source requests for repeated-host warnings without reopening broad exploration

## Immediate Engineering Priorities

1. Get a runnable environment with YAML support and project deps
2. Run one manual Xinyu session
3. Observe what memory files change
4. Tighten prompts based on actual writer behavior
5. Run the first manual scenario set
6. Validate controlled outward source staging
7. Planner-to-fetch-to-learner chain is smoke-validated with restore
8. Keep autonomous search disabled or dry-run while validating real sessions
9. Move into personality/detail tuning on top of the bounded framework
10. Use `expression_tone_smoke.py` and `expression_runtime_smoke.py` after every prompt-expression change
11. Use `behavior_regression_smoke.py` before deeper personality tuning so changes do not regress core behavior
12. Use `personality_detail_smoke.py` while tuning emotion granularity, family shape, choice, obedience boundaries, hidden residue, owner-private bias, non-generic closeness, absence/return residue, non-possessive jealousy, repeated-hurt repair limits, negative-emotion distinctions, and active behavior choices
13. Use `personality_continuity_smoke.py` when changing multi-turn personality continuity, repeated-hurt residue, re-approach-after-hurt residue, choice carryover, or proactive-question carryover
14. Repeat no-restore continuity arcs in small batches, then inspect memory before triggering broader automation; current lived baseline includes one 10-turn continuity arc and one 5-turn time-span continuity arc
15. Use `emotion_vector_sync_smoke.py` when changing deterministic emotion or relationship vector logic, especially approach-after-hurt residue handling
16. Use `dream_weight_smoke.py` when changing dream output, dream residue, or dream/reality boundary logic
17. Use `reflection_dream_residue_smoke.py` when changing how dream residue enters reflection or growth logs
18. Use `consolidation_dream_weight_smoke.py` when changing archive/consolidation behavior around active dream residue
19. Use `long_term_memory_gate_smoke.py` when changing selective retention or forgetting logic
20. Use `personality_growth_gate_smoke.py` when changing core personality growth gates
21. Use `question_pipeline_smoke.py` when changing active-question classification, exploration-queue routing, or source-gate handoff
22. Use `source_reliability_gate_smoke.py` when changing source reliability or source integration gate behavior
23. Use `learner_integration_smoke.py --single-source --require-blocked` when changing learner thresholds so single-source material cannot silently become learned knowledge
24. Use `learner_integration_smoke.py --require-integration` to confirm corroborated material can still enter knowledge-only integration
25. Add behavior validation for extreme-aversion / blacklist-resource posture: sustained malicious behavior should receive short refusal and low token spend, while misunderstanding or low knowledge should not be misclassified.
26. Build AI-domain learning as Xinyu's only stable professional knowledge track, then route AI knowledge into self-iteration only through reflection/growth gates.
27. Use `resource_boundary_smoke.py` after changing blacklist/resource-boundary heuristics.
28. Use `ai_domain_source_smoke.py` after changing AI-domain question routing, source reliability, source integration, or request planning.
29. Use `ai_self_iteration_gate_smoke.py` after changing AI-domain self-iteration candidate routing, source traceability, risk scoring, or direct-write protections.
30. Use `multi_person_relationship_smoke.py` after changing non-owner person extraction, person profiles, people index, or relationship index behavior.
31. Expand live behavior coverage for non-owner people after deterministic multi-person sync stays stable.
32. Use `memory_pressure_smoke.py` after changing long-term memory, retention, archive, or high-preserve relationship-residue rules.
33. Use `memory_lived_pressure_arc.py` when changing no-restore pressure handling, trivial no-memory filtering, maintenance pressure behavior, or high-preserve residue validation.
34. Add lived archive dormancy/reactivation validation now that no-restore pressure arc is stable.
35. Use `initiative_loop_smoke.py` when changing proactive question behavior, silence, refusal, source-gated curiosity, repair attempts, or step-back boundaries.
36. Use `dream_reflection_growth_cycle_smoke.py` when changing background dream/reflection/growth ordering or archive behavior under active dream residue.
37. Use `non_owner_social_world_smoke.py` when changing non-owner people, repeated familiarity, group context, real-life adapter non-owner routing, or owner-priority protection.
38. Use `ai_self_iteration_review_smoke.py` when changing q-006 self-review proposals, affected-file audit, owner-visible review gates, or rollback paths.
39. Re-run the Milestone 20 autonomy/source safety regression set before enabling any broader autonomous behavior.
40. Use `real_conversation_quality_smoke.py --require-realism --timeout-seconds 140 --settle-seconds 2` after changing prompt-expression rules, daily-chat tone, family texture, or call-out handling.
41. Follow `project-plans/PERSONALITY-REAL-CONVERSATION-PLAN.md` for the next personality-detail and lived-conversation phase.
42. Continue personality-detail tuning through short lived sessions only after the real-conversation matrix remains passing.
43. Use `phase3_lived_session_smoke.py --require-phase3 --timeout-seconds 140 --settle-seconds 2` after changing memory selectivity, ordinary-chat no-write rules, repeated-template-testing behavior, or small-hurt residue handling.

## Current Runtime Blockers Observed On This Machine

- no hard local runtime blocker remains for the active source checkout
- `.venv` can load the project and run Xinyu smoke scripts
- `git` is not available in `PATH`, so status/diff inspection must use filesystem-level checks unless Git is installed later

Implication:

- runtime behavior validation can proceed from the current working copy
- smoke scripts should continue using `--restore-after` for test prompts and maintenance turns
- no-restore arcs should be short, inspected immediately, and cleaned if interrupted validation residue is found
- after no-restore arcs, inspect `current_state.md` and `owner.md` for last-turn overwrites that erase active negative or repair residue too cleanly
- source-fetch material should be checked for page chrome before learner integration; article/title/abstract extraction is preferred over raw first-page text
- source comparison now has an initial semantic same-question gate; future improvement should make it question-aware instead of only claim-token based
- source comparison now requires same-question support across independent hosts before `corroborated`; same-host support plus an unrelated independent host is held for semantic review
- source comparison now records question-aware alignment: same-question, adjacent-question, and mixed/unrelated evidence are separated before learner integration
- learned or partially answered questions must not re-enter the fresh exploration queue unless explicitly reopened
- learner integration now synchronizes active question status to `partially_answered` so learned questions do not stay visibly open/pending
- source notes refreshes must preserve integrated-source and learning-quality history sections
- source notes now use section-aware appends for learner integration, learning quality warnings, and source comparison holds
- maintenance summaries should show both newly integrated and total integrated learner material counts
- expression runtime smoke should remain part of the minimum prompt-tuning loop
- broad autonomy should remain gated behind scheduler/maintenance validation
- autonomous search provider execution now remains opt-in, request-bound, learning-quality-gated, query-budgeted, and candidate-only before fetch
- future social/human answers must stay source-material-candidate only until source, learner, and quality gates accept them
- future real-life input events must stay staged and classified before turn-mode, interpretation, source, or memory routes see them
- `long_run_status.py --require-all-completed --require-no-residue` should pass before starting the next phase
- AI-domain knowledge now has a first professional learning lane (`q-006`) with staged real sources, corroborated comparison, knowledge-only learner integration, and completed source-diversity repair.
- AI-domain knowledge now has a self-iteration gate: current q-006 entries produce `growth_review_candidate` with source trace, confidence, risk, and direct-write protections.
- q-002 human-relationship learning has passed controlled search, fetch, cross-host comparison, learner integration, and quality review without adding a new repeated-host warning.
- q-003 and q-006 source-diversity repair has completed through controlled supplemental requests; learning quality is now `stable` with zero current warnings.
- blacklisted-resource posture has deterministic smoke coverage and still needs live behavior validation before being trusted in long sessions.
- blacklisted-resource posture now has rolling live-style smoke coverage with repeated-abuse escalation and good-faith/quote de-escalation.
- behavior regression, personality detail, personality continuity, and deterministic emotion vector sync currently pass as the active behavior/personality baseline; personality detail now covers 30 scenarios and continuity covers 7 scenarios.
- real conversation quality currently passes as the active Phase 3 prompt-expression baseline.
- phase3 lived-session residue currently passes as the active short-session memory-quality baseline.
- minimum multi-person relationship structure is present: explicit non-owner introductions create separate person profiles, update people/index and relationships/index, cap priority below owner, and avoid owner-memory overwrite.
- deterministic memory pressure validation is present: ordinary archive-ready event volume cannot force compression of high-preserve owner relationship residue.
- no-restore lived pressure validation is present: 22 real turns plus maintenance preserved owner residue and filtered trivial details.
- the next coding layer should move into personality-detail calibration and lived-session quality tuning, using short no-restore batches and immediate residue inspection.

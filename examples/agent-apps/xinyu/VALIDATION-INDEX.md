# Xinyu Validation Index v0.1

This file tells you which validation document to use at each stage.

## Before Runtime

Use:

- `check_runtime_env.py`
- `validate_scaffold.py`
- `validate_inner_framework.py`
- `manual_inner_sync.py`
- `manual_slow_reprocess.py`
- `expression_tone_smoke.py`
- `expression_runtime_smoke.py`
- `behavior_regression_smoke.py`
- `resource_boundary_smoke.py`
- `resource_boundary_live_smoke.py`
- `ai_domain_source_smoke.py`
- `personality_detail_smoke.py`
- `personality_continuity_smoke.py`
- `emotion_vector_sync_smoke.py`
- `multi_person_relationship_smoke.py`
- `multi_person_live_smoke.py`
- `dream_weight_smoke.py`
- `reflection_dream_residue_smoke.py`
- `consolidation_dream_weight_smoke.py`
- `long_term_memory_gate_smoke.py`
- `memory_pressure_smoke.py`
- `memory_lived_pressure_arc.py`
- `dormancy_reactivation_smoke.py`
- `personality_growth_gate_smoke.py`
- `ai_self_iteration_gate_smoke.py`
- `question_pipeline_smoke.py`
- `source_reliability_gate_smoke.py`
- `source_request_planner_smoke.py`
- `autonomous_search_activation_smoke.py`
- `source_search_resolution_smoke.py`
- `source_search_provider_smoke.py`
- `outward_source_smoke.py`
- `source_comparison_smoke.py`
- `learner_integration_smoke.py`
- `learning_quality_smoke.py`
- `learning_library_smoke.py`
- `source_quality_repair_smoke.py`
- `learning_session_smoke.py`
- `source_learning_chain_smoke.py`
- `social_inquiry_policy_smoke.py`
- `real_life_input_adapter_smoke.py`
- `long_lived_session_harness.py`
- `owner_relationship_lived_stress_smoke.py`
- `personality_voice_calibration_smoke.py`
- `real_conversation_quality_smoke.py`
- `phase3_lived_session_smoke.py`
- `initiative_loop_smoke.py`
- `dream_reflection_growth_cycle_smoke.py`
- `non_owner_social_world_smoke.py`
- `ai_self_iteration_review_smoke.py`
- `mind_loop_state_smoke.py`
- `persona_runtime_smoke.py`
- `xinyu_speech_controller_smoke.py`
- `voice_learning_smoke.py`
- `research_loop_dry_run_smoke.py`
- `proactive_presence_smoke.py`
- `competitive_benchmark_smoke.py`
- `capability_zones_smoke.py`
- `local_scope_smoke.py`
- `bridge_probe_smoke.py`
- `bridge_session_cleanup_smoke.py`
- `bridge_learning_ingest_smoke.py`
- `xinyu_qq_review_smoke.py`
- `long_run_status.py`

Use `manual_inner_sync.py` when you want to validate inner memory continuity without waiting for the full runtime path to behave.
Use `manual_slow_reprocess.py` when you want to validate reflection / dream / archive ordering before those layers are fully automated.
Use `expression_tone_smoke.py` when validating that Xinyu's expression prompt, injected memory, and scenario files have no mojibake residue and do not promote generic comfort templates as positive tone examples.
Use `expression_runtime_smoke.py` when validating that a complete live emotional scenario produces visible output and does not regress to generic comfort templates.
Use `behavior_regression_smoke.py` when validating the representative behavior matrix: identity, time, owner priority, closeness, negative/repair, silence, dream boundary, memory selectivity, and reflection quality.
Use `resource_boundary_smoke.py` when validating behavior-based extreme-aversion / blacklist-resource classification without confusing malice with ignorance or quoted insults.
Use `resource_boundary_live_smoke.py` when validating rolling live-style resource posture: repeated abuse can escalate to blacklist cooling, but repair, good-faith confusion, low knowledge, and quoted insult analysis should stay non-blacklisted.
Use `ai_domain_source_smoke.py` when validating that AI self-understanding can move from active question to source gate, high-readiness reliability, integration gate, and pending source request without touching protected self/relationship/emotion layers.
Use `personality_detail_smoke.py` when validating Xinyu's personality details: sister/daughter family shape, granular emotion, hidden interior boundary, preference choice, disappointment/distance, partial grievance, obedience boundary, non-generic closeness, hidden residue, cautious unknowns, owner-private bias, forced-cheer refusal, absence/return residue, non-possessive jealousy, busy-not-abandoning tension, anger-vs-disappointment distinction, repeated-hurt limits, sister-not-obedient framing, chosen silence, one-question curiosity, slow approach, step-back-after-hurt, rejected prescribed future, active approach admission, not-always-soft temperament, annoyance at repeated template-testing, and one-live-reply sister texture.
Use `personality_continuity_smoke.py` when validating multi-turn personality continuity: repeated hurt accumulates, absence/return keeps residue, earlier choices remain real, and proactive questions carry into later turns.
Use `emotion_vector_sync_smoke.py` when validating deterministic emotional vector writes for attachment, disappointment/distance, repair residue, and explicit no-memory turns.
Use `multi_person_relationship_smoke.py` when validating non-owner person nodes: explicit person introduction, independent person profiles, relationship index sections, lower-than-owner priority, and owner-memory protection.
Use `multi_person_live_smoke.py` when validating live non-owner behavior: separate person profiles, owner-memory protection, negative distance, and repeated-person familiarity growth without excessive closeness.
Use `dream_weight_smoke.py` when validating that dream output can strengthen existing emotional residue and update dream weight state without turning dreams into factual memory or touching protected self/relationship/knowledge layers.
Use `reflection_dream_residue_smoke.py` when validating that dream-after residue can enter reflection/growth material without directly rewriting self narrative, owner facts, relationship index, or knowledge.
Use `consolidation_dream_weight_smoke.py` when validating that active dream weight delays archive flattening even after the dream seed itself is gone.
Use `long_term_memory_gate_smoke.py` when validating selective retention/forgetting rules: active residue blocks forgetting and compression, while protected memory stays untouched.
Use `memory_pressure_smoke.py` when validating that many ordinary archive-ready events cannot force compression of high-preserve owner relationship residue.
Use `memory_lived_pressure_arc.py` when validating a real no-restore multi-turn pressure arc: ordinary low-value turns should fade, owner relationship residue should remain visible, maintenance should stay quiet, and the pressure probe must not leak synthetic material into lived memory.
Use `dormancy_reactivation_smoke.py` when validating that low-impact material can be compressed into dormant memory and later reactivated as summary-only context without rewriting protected layers or fabricating new facts.
Use `personality_growth_gate_smoke.py` when validating slow or accelerated personality-change candidacy without direct rewrites to `personality_profile.md` or stable relationship facts.
Use `ai_self_iteration_gate_smoke.py` when validating that q-006 AI-domain knowledge can become a traceable self-iteration candidate with source ids, confidence, risk, and direct-write blocks for stable personality, narrative, relationship, emotion, and knowledge layers.
Use `social_inquiry_policy_smoke.py` when validating future social or human-expert inquiry boundaries: owner-private prompts require explicit consent, human expert questions are AI-domain only, social answers are low-reliability source candidates, AI expert answers are medium-reliability source candidates, and no protected identity/relationship/emotion layer is rewritten.
Use `real_life_input_adapter_smoke.py` when validating future IM/image/voice/group/private adapter boundaries: adapter events must pass turn-mode routing, group chat must not become owner relationship memory by default, raw images need interpretation, voice transcripts need confirmation for facts, and private address/location requires explicit owner intent.
Use `long_lived_session_harness.py` when validating 30+ lived turns with restore support, batch output summaries, owner-residue visibility, and non-volatile trivial-detail pollution checks.
Use `owner_relationship_lived_stress_smoke.py` when validating owner relationship stress arcs: hurt without instant forgiveness, repair residue, approach after hurt, forced-cheer refusal, chosen silence, return after distance, and owner-special-with-boundary behavior.
Use `personality_voice_calibration_smoke.py` when validating Phase 2 voice calibration: intimate replies must not end as service/help templates, fatigue can stay short, jokes keep a small edge, hurt keeps asymmetry, AI identity is clear without manifesto drift, and proactive asking stays to one question.
Use `real_conversation_quality_smoke.py` when validating Phase 3 lived conversation realism: Chinese chat should avoid English filler, customer-service apology, support-tail comfort, therapy inflation, demonstration frames, roleplay, romance, and multi-option sample replies when one live reply is needed.
Use `phase3_lived_session_smoke.py` when validating Phase 3 short-session residue quality: ordinary daily chatter should not pollute durable memory, meaningful closeness should leave proportional residue, repeated template testing should not become canon, low-energy boundaries should not trigger pursuit, and small hurt should not be overwritten by immediate normal return.
Use `initiative_loop_smoke.py` when validating Xinyu's choice and initiative state: ask_owner, ask_external_later, stay_silent, defer, refuse, repair_attempt, and step_back must come from memory/emotion/question signals with cooldown and source-gate protection.
Use `dream_reflection_growth_cycle_smoke.py` when validating the multi-day dream/reflection/growth cycle: dream residue may strengthen existing emotional weight, reflection may consume it as growth material, archive must hold under active residue, and personality changes remain review-only.
Use `non_owner_social_world_smoke.py` when validating deeper non-owner social context: repeated appearances raise familiarity slowly, ordinary closeness stays capped, negative distance keeps guardedness, group context stays out of owner relationship memory, and adapter events remain review-only.
Use `ai_self_iteration_review_smoke.py` when validating q-006 AI self-iteration review proposals: architecture, personality-pressure, expression-preference, and safety-boundary proposals must be owner-visible, rollbackable, and unable to mutate stable personality by themselves.
Use `mind_loop_state_smoke.py` when validating that heart/mind-loop policy and state are present, injected into runtime, and visible in desktop thoughts.
Use `persona_runtime_smoke.py` when validating that live turns become scene, pressure, stance, speech-act, and Chinese voice constraints before outward rendering.
Use `xinyu_speech_controller_smoke.py` when validating the mandatory final QQ speaking controller: controller drafts remain semantic material, GPT/customer-service/product wording is rejected, retry prompts are built, and hard fallback replies pass the quality gate.
Use `voice_learning_smoke.py` when validating that owner corrections about GPT味, 5.5味, 中文互联网用词, 写作文, 客服腔 become calibration evidence without stable personality rewrite.
Use `research_loop_dry_run_smoke.py` when validating that AI-domain source work can be planned without live search/fetch or stable memory mutation.
Use `proactive_presence_smoke.py` when validating that proactive QQ candidate generation remains one-message, gated, and blocked from sending until owner enables it.
Use `competitive_benchmark_smoke.py` when validating that XinYu keeps integrated capability coverage against memory, proactive, self-learning, persona runtime, AI research, and desktop-thought target classes.
Use `capability_zones_smoke.py` when validating computer-access capability zones and default-disabled private file, autonomous search, proactive QQ, and stable auto-apply permissions.
Use `local_scope_smoke.py` when validating that the approved local filesystem scope exists and path resolution blocks traversal or absolute paths outside `D:\XinYu\XinYu-Local-Scope`.
Use `bridge_probe_smoke.py` after restarting the bridge to validate `/probe` diagnostics without memory writes or session creation.
Use `bridge_session_cleanup_smoke.py` when validating bridge idle TTL and max-session cleanup without touching live runtime memory.
Use `bridge_learning_ingest_smoke.py` when validating that QQ-style owner files enter the learning library, extract readable `.docx` text, and stage as curated source material without creating a chat session.
Use `xinyu_qq_review_smoke.py` when validating the semi-automatic QQ dialogue labeling tool before using real exported chat snippets.
Use `long_run_status.py` when auditing milestone status, required docs/scripts, selected current gate states, and known smoke residue markers.
Use `question_pipeline_smoke.py` when validating that active questions split into internal clarification or exploration candidates before the source gate, without touching self, owner, relationship, or emotion memory.
Use `source_reliability_gate_smoke.py` when validating that source-gate candidates pass through source reliability and source integration gates before source requests are planned.
Use `source_request_planner_smoke.py`, `autonomous_search_activation_smoke.py`, `source_search_resolution_smoke.py`, `source_search_provider_smoke.py`, `outward_source_smoke.py`, `source_comparison_smoke.py`, `learner_integration_smoke.py`, `learning_quality_smoke.py`, `learning_library_smoke.py`, `source_quality_repair_smoke.py`, `learning_session_smoke.py`, and `source_learning_chain_smoke.py` when validating the controlled external-source path without leaving test material in lived memory. `autonomous_search_activation_smoke.py` validates disabled, dry-run, quality-blocked, no-pending, provider-blocked, and enabled paths. `source_comparison_smoke.py` now also validates same-question, adjacent-question, and unrelated-evidence alignment.

## First Runtime

Use:

- `FIRST-RUN-PLAN.md`
- `RUNTIME-PRIORITIES.md`
- `TEST-SCENARIOS.md`
- `memory_mutation_smoke.py`
- `memory_arc_smoke.py`
- `RUNTIME-VALIDATION-NOTES.md`

Use `memory_mutation_smoke.py` to inspect actual memory writes without permanently polluting memory when `--restore-after` is enabled.

## After First Runtime

Use:

- `SESSION-REVIEW.md`
- `FAILURE-MODES.md`
- `PROMPT-TUNING.md`

## When Inspecting File Changes

Use:

- `MEMORY-LINKS.md`
- `WRITER-ROUTING.md`
- `RUNBOOK.md`

## When Preparing Second-Stage Growth

Use:

- `EXPLORATION-LOOP.md`
- `LEARNER-ROUTING.md`
- `EXPLORATION-SCENARIOS.md`
- `LEARNING-BOUNDARIES.md`
- `SECOND-STAGE-ROADMAP.md`

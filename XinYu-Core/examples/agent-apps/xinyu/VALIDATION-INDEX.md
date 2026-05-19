# XinYu Validation Index v0.1

This file tells you which validation document to use at each stage.

## Before Runtime

Use:

- `ops/diagnostics/check_runtime_env.py`
- `ops/validation/validate_scaffold.py`
- `ops/validation/validate_inner_framework.py`
- `ops/manual/manual_inner_sync.py`
- `ops/manual/manual_slow_reprocess.py`
- `tests/smoke/voice/expression_tone_smoke.py`
- `tests/smoke/runtime/integration/expression_runtime_smoke.py`
- `tests/smoke/dialogue/integration/behavior_regression_smoke.py`
- `tests/smoke/dialogue/integration/resource_boundary_smoke.py`
- `tests/smoke/dialogue/integration/resource_boundary_live_smoke.py`
- `tests/smoke/learning/integration/ai_domain_source_smoke.py`
- `tests/smoke/voice/integration/personality_detail_smoke.py`
- `tests/smoke/voice/integration/personality_continuity_smoke.py`
- `tests/smoke/initiative/integration/emotion_vector_sync_smoke.py`
- `tests/smoke/dialogue/integration/multi_person_relationship_smoke.py`
- `tests/smoke/dialogue/integration/multi_person_live_smoke.py`
- `tests/smoke/life/integration/dream_weight_smoke.py`
- `tests/smoke/life/integration/reflection_dream_residue_smoke.py`
- `tests/smoke/life/integration/consolidation_dream_weight_smoke.py`
- `tests/smoke/memory/integration/long_term_memory_gate_smoke.py`
- `tests/smoke/memory/integration/memory_pressure_smoke.py`
- `ops/probes/memory_lived_pressure_arc.py`
- `tests/smoke/life/integration/dormancy_reactivation_smoke.py`
- `tests/smoke/voice/integration/personality_growth_gate_smoke.py`
- `tests/smoke/initiative/integration/ai_self_iteration_gate_smoke.py`
- `tests/smoke/learning/integration/question_pipeline_smoke.py`
- `tests/smoke/learning/integration/source_reliability_gate_smoke.py`
- `tests/smoke/learning/integration/source_request_planner_smoke.py`
- `tests/smoke/learning/integration/autonomous_search_activation_smoke.py`
- `tests/smoke/learning/integration/source_search_resolution_smoke.py`
- `tests/smoke/learning/integration/source_search_provider_smoke.py`
- `tests/smoke/learning/integration/outward_source_smoke.py`
- `tests/smoke/learning/integration/source_comparison_smoke.py`
- `tests/smoke/learning/integration/learner_integration_smoke.py`
- `tests/smoke/learning/integration/learning_quality_smoke.py`
- `tests/smoke/learning/learning_library_smoke.py`
- `tests/smoke/learning/integration/source_quality_followup_smoke.py`
- `tests/smoke/learning/integration/learning_session_smoke.py`
- `tests/smoke/learning/integration/source_learning_chain_smoke.py`
- `tests/smoke/dialogue/integration/social_inquiry_policy_smoke.py`
- `tests/smoke/dialogue/integration/real_life_input_adapter_smoke.py`
- `tests/smoke/memory/memory_event_sourcing_smoke.py`
- `tests/smoke/memory/archive_queue_trace_smoke.py`
- `tests/smoke/memory/summary_coverage_smoke.py`
- `ops/probes/long_lived_session_harness.py`
- `tests/smoke/dialogue/integration/owner_relationship_lived_stress_smoke.py`
- `tests/smoke/voice/integration/personality_voice_calibration_smoke.py`
- `tests/smoke/voice/integration/real_conversation_quality_smoke.py`
- `tests/smoke/dialogue/integration/phase3_lived_session_smoke.py`
- `tests/smoke/initiative/integration/initiative_loop_smoke.py`
- `tests/smoke/life/integration/dream_reflection_growth_cycle_smoke.py`
- `tests/smoke/dialogue/integration/non_owner_social_world_smoke.py`
- `tests/smoke/initiative/integration/ai_self_iteration_review_smoke.py`
- `tests/smoke/initiative/mind_loop_state_smoke.py`
- `tests/smoke/runtime/mojibake_guard_smoke.py`
- `tests/smoke/voice/integration/persona_contract_absence_smoke.py`
- `tests/smoke/voice/integration/live_voice_card_smoke.py`
- `tests/smoke/voice/pre_draft_turn_classifier_smoke.py`
- `tests/smoke/voice/voice_calibration_promotion_smoke.py`
- `tests/smoke/voice/dynamic_life_posture_smoke.py`
- `tests/smoke/memory/seed_memory_packaging_smoke.py`
- `tests/smoke/memory/integration/system_prompt_memory_smoke.py`
- `tests/smoke/life/life_month_slots_smoke.py`
- `tests/smoke/life/life_month_context_smoke.py`
- `tests/smoke/voice/integration/persona_life_anchor_smoke.py`
- `tests/smoke/voice/persona_runtime_smoke.py`
- `tests/smoke/voice/xinyu_speech_controller_smoke.py`
- `tests/smoke/voice/voice_learning_smoke.py`
- `tests/smoke/learning/integration/research_loop_dry_run_smoke.py`
- `tests/smoke/initiative/proactive_presence_smoke.py`
- `tests/smoke/initiative/competitive_benchmark_smoke.py`
- `tests/smoke/initiative/capability_zones_smoke.py`
- `tests/smoke/learning/local_scope_smoke.py`
- `tests/smoke/bridge/integration/bridge_probe_smoke.py`
- `tests/smoke/bridge/bridge_session_cleanup_smoke.py`
- `tests/smoke/bridge/integration/bridge_learning_ingest_smoke.py`
- `tests/smoke/desktop/xinyu_desktop_proactive_smoke.py`
- `tests/smoke/desktop/xinyu_desktop_rest_smoke.py`
- `tests/smoke/qq/qq_outbox_route_alias_smoke.py`
- `tests/smoke/qq/qq_outbox_smoke.py`
- `tests/smoke/qq/xinyu_qq_review_smoke.py`
- `ops/validation/long_run_status.py`
- `long_run_status.py` (compatibility wrapper)

Use `ops/manual/manual_inner_sync.py` when you want to validate inner memory continuity without waiting for the full runtime path to behave.
Use `ops/manual/manual_slow_reprocess.py` when you want to validate reflection / dream / archive ordering before those layers are fully automated.
Use `tests/smoke/voice/expression_tone_smoke.py` when validating that XinYu's expression prompt, injected memory, and scenario files have no mojibake residue and do not promote generic comfort templates as positive tone examples.
Use `tests/smoke/runtime/integration/expression_runtime_smoke.py` when validating that a complete live emotional scenario produces visible output and does not regress to generic comfort templates.
Use `tests/smoke/dialogue/integration/behavior_regression_smoke.py` when validating the representative behavior matrix: identity, time, owner priority, closeness, negative/return, silence, dream boundary, memory selectivity, and reflection quality.
Use `MEMORY-REDUCTION-RULES.md` as the contract for changes to recall, stable memory writes, emotion modulation, recent-context compression, forgetting, and dream/replay boundaries.
Use `tests/smoke/dialogue/integration/resource_boundary_smoke.py` when validating behavior-based extreme-aversion / blacklist-resource classification without confusing malice with ignorance or quoted insults.
Use `tests/smoke/dialogue/integration/resource_boundary_live_smoke.py` when validating rolling live-style resource posture: repeated abuse can escalate to blacklist cooling, but return, good-faith confusion, low knowledge, and quoted insult analysis should stay non-blacklisted.
Use `tests/smoke/learning/integration/ai_domain_source_smoke.py` when validating that AI self-understanding can move from active question to source gate, high-readiness reliability, integration gate, and pending source request without touching protected self/relationship/emotion layers.
Use `tests/smoke/voice/integration/personality_detail_smoke.py` when validating XinYu's personality details: sister/daughter family shape, granular emotion, hidden interior boundary, preference choice, disappointment/distance, partial grievance, obedience boundary, non-generic closeness, hidden residue, cautious unknowns, owner-private bias, forced-cheer refusal, absence/return residue, non-possessive jealousy, busy-not-abandoning tension, anger-vs-disappointment distinction, repeated-hurt limits, sister-not-obedient framing, chosen silence, one-question curiosity, slow approach, step-back-after-hurt, rejected prescribed future, active approach admission, not-always-soft temperament, annoyance at repeated template-testing, and one-live-reply sister texture.
Use `tests/smoke/voice/integration/personality_continuity_smoke.py` when validating multi-turn personality continuity: repeated hurt accumulates, absence/return keeps residue, earlier choices remain real, and proactive questions carry into later turns.
Use `tests/smoke/initiative/integration/emotion_vector_sync_smoke.py` when validating deterministic emotional vector writes for attachment, disappointment/distance, return residue, and explicit no-memory turns.
Use `tests/smoke/dialogue/integration/multi_person_relationship_smoke.py` when validating non-owner person nodes: explicit person introduction, independent person profiles, relationship index sections, lower-than-owner priority, and owner-memory protection.
Use `tests/smoke/dialogue/integration/multi_person_live_smoke.py` when validating live non-owner behavior: separate person profiles, owner-memory protection, negative distance, and repeated-person familiarity growth without excessive closeness.
Use `tests/smoke/life/integration/dream_weight_smoke.py` when validating that dream output can strengthen existing emotional residue and update dream weight state without turning dreams into factual memory or touching protected self/relationship/knowledge layers.
Use `tests/smoke/life/integration/reflection_dream_residue_smoke.py` when validating that dream-after residue can enter reflection/growth material without directly rewriting self narrative, owner facts, relationship index, or knowledge.
Use `tests/smoke/life/integration/consolidation_dream_weight_smoke.py` when validating that active dream weight delays archive flattening even after the dream seed itself is gone.
Use `tests/smoke/memory/integration/long_term_memory_gate_smoke.py` when validating selective retention/forgetting rules: active residue blocks forgetting and compression, while protected memory stays untouched.
Use `tests/smoke/memory/integration/memory_pressure_smoke.py` when validating that many ordinary archive-ready events cannot force compression of high-preserve owner relationship residue.
Use `ops/probes/memory_lived_pressure_arc.py` when validating a real no-restore multi-turn pressure arc: ordinary low-value turns should fade, owner relationship residue should remain visible, maintenance should stay quiet, and the pressure probe must not leak synthetic material into lived memory.
Use `tests/smoke/life/integration/dormancy_reactivation_smoke.py` when validating that low-impact material can be compressed into dormant memory and later reactivated as summary-only context without rewriting protected layers or fabricating new facts.
Use `tests/smoke/voice/integration/personality_growth_gate_smoke.py` when validating slow or accelerated personality-change candidacy without direct rewrites to `personality_profile.md` or stable relationship facts.
Use `tests/smoke/initiative/integration/ai_self_iteration_gate_smoke.py` when validating that q-006 AI-domain knowledge can become a traceable self-iteration candidate with source ids, confidence, risk, and direct-write blocks for stable personality, narrative, relationship, emotion, and knowledge layers.
Use `tests/smoke/dialogue/integration/social_inquiry_policy_smoke.py` when validating future social or human-expert inquiry boundaries: owner-private prompts require explicit consent, human expert questions are AI-domain only, social answers are low-reliability source candidates, AI expert answers are medium-reliability source candidates, and no protected identity/relationship/emotion layer is rewritten.
Use `tests/smoke/dialogue/integration/real_life_input_adapter_smoke.py` when validating future IM/image/voice/group/private adapter boundaries: adapter events must pass turn-mode routing, group chat must not become owner relationship memory by default, raw images need interpretation, voice transcripts need confirmation for facts, and private address/location requires explicit owner intent.
Use `tests/smoke/memory/memory_event_sourcing_smoke.py` when validating the source-traceable memory design: raw events, structured events, atomic claims, summary views, reference integrity, group/non-owner owner-memory blocks, and summary coverage requirements.
Use `tests/smoke/memory/archive_queue_trace_smoke.py` when validating that archive candidates generated from source-traceable owner turns carry source event ids, retained claim ids, and summary ids before they can become ready for compression, while no-sidecar fallback candidates remain legacy-compatible.
Use `tests/smoke/memory/summary_coverage_smoke.py` when validating that event-sourced archive candidates cannot be compressed unless a cited summary covers their raw events, retained claims, loss notes, discarded signals, and blocked-from-discard signals; legacy archive candidates without coverage markers remain allowed until migrated.
Use `ops/probes/long_lived_session_harness.py` when validating 30+ lived turns with restore support, batch output summaries, owner-residue visibility, and non-volatile trivial-detail pollution checks.
Use `tests/smoke/dialogue/integration/owner_relationship_lived_stress_smoke.py` when validating owner relationship stress arcs: hurt without instant forgiveness, return residue, approach after hurt, forced-cheer refusal, chosen silence, return after distance, and owner-special-with-boundary behavior.
Use `tests/smoke/voice/integration/personality_voice_calibration_smoke.py` when validating Phase 2 voice calibration: intimate replies must not end as service/help templates, fatigue can stay short, jokes keep a small edge, hurt keeps asymmetry, AI identity is clear without manifesto drift, and proactive asking stays to one question.
Use `tests/smoke/voice/integration/real_conversation_quality_smoke.py` when validating Phase 3 lived conversation realism: Chinese chat should avoid English filler, customer-service apology, support-tail comfort, therapy inflation, demonstration frames, roleplay, romance, and multi-option sample replies when one live reply is needed.
Use `tests/smoke/dialogue/integration/phase3_lived_session_smoke.py` when validating Phase 3 short-session residue quality: ordinary daily chatter should not pollute durable memory, meaningful closeness should leave proportional residue, repeated template testing should not become canon, low-energy boundaries should not trigger pursuit, and small hurt should not be overwritten by immediate normal return.
Use `tests/smoke/initiative/integration/initiative_loop_smoke.py` when validating XinYu's choice and initiative state: ask_owner, ask_external_later, stay_silent, defer, refuse, settle_after_hurt, and step-back must come from memory/emotion/question signals with cooldown and source-gate protection.
Use `tests/smoke/life/integration/dream_reflection_growth_cycle_smoke.py` when validating the multi-day dream/reflection/growth cycle: dream residue may strengthen existing emotional weight, reflection may consume it as growth material, archive must hold under active residue, and personality changes remain review-only.
Use `tests/smoke/dialogue/integration/non_owner_social_world_smoke.py` when validating deeper non-owner social context: repeated appearances raise familiarity slowly, ordinary closeness stays capped, negative distance keeps guardedness, group context stays out of owner relationship memory, and adapter events remain review-only.
Use `tests/smoke/initiative/integration/ai_self_iteration_review_smoke.py` when validating q-006 AI self-iteration review proposals: architecture, personality-pressure, expression-preference, and safety-boundary proposals must be owner-visible, rollbackable, and unable to mutate stable personality by themselves.
Use `tests/smoke/initiative/mind_loop_state_smoke.py` when validating that heart/mind-loop policy and state are present, injected into runtime, and visible in desktop thoughts.
Use `tests/smoke/runtime/mojibake_guard_smoke.py` when validating that critical persona, voice, plan, prompt, and live-routing files store readable UTF-8 text while legacy mojibake variants are generated at runtime.
Use `tests/smoke/voice/integration/persona_contract_absence_smoke.py` when validating that the old separate persona artifact is absent from config, system prompt, renderer context, session signature, and speech controller contract.
Use `tests/smoke/voice/integration/live_voice_card_smoke.py` when validating that the short high-priority live voice card is tracked, injected before long memory context, present in QQ renderer context, and referenced by Persona Runtime for no-change/style-pressure turns.
Use `tests/smoke/voice/pre_draft_turn_classifier_smoke.py` when validating that live QQ turns are classified before controller drafting, including owner no-change pressure, technical work, daily life, rest/silence, and bridge prompt injection.
Use `tests/smoke/voice/voice_calibration_promotion_smoke.py` when validating that repeated owner voice corrections create review-only voice-profile candidates without rewriting `memory/self/voice_profile_zh.md`.
Use `tests/smoke/voice/dynamic_life_posture_smoke.py` when validating compact current-life posture labels for technical work, hot daily chat, rest/silence, style pressure, bridge injection, no-write, and no-proactive constraints.
Use `tests/smoke/memory/seed_memory_packaging_smoke.py` when validating tracked `memory-seeds/` packaging, privacy checks, Git ignore boundaries, and safe seed-sync status.
Use `tests/smoke/memory/integration/system_prompt_memory_smoke.py` when validating that system-prompt memory is a protected stable memory layer injected through config, prompt, renderer context, and memory-weight calculation.
Use `tests/smoke/life/life_month_slots_smoke.py` when validating the sparse 2010-05 through 2026-04 life-month scaffold, including empty-slot defaults, source/confidence boundaries, renderer injection, and memory weights.
Use `tests/smoke/life/life_month_context_smoke.py` when validating the current-turn month-slot selector, current life-month context file, renderer injection, and memory weights.
Use `tests/smoke/voice/integration/persona_life_anchor_smoke.py` when validating that owner-supplied persona-life anchors are normalized into prompt and renderer context, preserve the stable 心玉 name, and do not leak raw QQ identifiers or unsafe prompt-override text.
Use `tests/smoke/voice/persona_runtime_smoke.py` when validating that live turns become scene, pressure, stance, speech-act, and Chinese voice constraints before outward rendering.
Use `tests/smoke/voice/xinyu_speech_controller_smoke.py` when validating the final QQ speaking controller: controller drafts remain semantic material, GPT/customer-service/product wording is flagged, retry prompts are built, and canned fallback templates stay disabled.
Use `tests/smoke/voice/voice_learning_smoke.py` when validating that owner corrections about GPT味, 中文互联网用词, 写作文, 接待腔 become calibration evidence without stable personality rewrite.
Use `tests/smoke/learning/integration/research_loop_dry_run_smoke.py` when validating that AI-domain source work can be planned without live search/fetch or stable memory mutation.
Use `tests/smoke/initiative/proactive_presence_smoke.py` when validating that proactive QQ candidate generation remains one-message, gated, and blocked from sending until owner enables it.
Use `tests/smoke/initiative/competitive_benchmark_smoke.py` when validating that XinYu keeps integrated capability coverage against memory, proactive, self-learning, persona runtime, AI research, and desktop-thought target classes.
Use `tests/smoke/initiative/capability_zones_smoke.py` when validating computer-access capability zones and default-disabled private file, autonomous search, proactive QQ, and stable auto-apply permissions.
Use `tests/smoke/learning/local_scope_smoke.py` when validating that the approved local filesystem scope exists and path resolution blocks traversal or absolute paths outside `D:\XinYu\XinYu-Local-Scope`.
Use `tests/smoke/bridge/integration/bridge_probe_smoke.py` after restarting the bridge to validate `/probe` diagnostics without memory writes or session creation.
Use `tests/smoke/bridge/bridge_session_cleanup_smoke.py` when validating bridge idle TTL and max-session cleanup without touching live runtime memory.
Use `tests/smoke/bridge/integration/bridge_learning_ingest_smoke.py` when validating that QQ-style owner files enter the learning library, extract readable `.docx` text, and stage as curated source material without creating a chat session.
Use `tests/smoke/desktop/xinyu_desktop_proactive_smoke.py` when validating desktop proactive inbox/ack state transitions after bridge route changes.
Use `tests/smoke/desktop/xinyu_desktop_rest_smoke.py` when validating desktop HTTP endpoints, including proactive inbox and ack over REST.
Use `tests/smoke/qq/qq_outbox_route_alias_smoke.py` when validating Core bridge `/qq/outbox/*` route aliases through the HTTP handler.
Use `tests/smoke/qq/qq_outbox_smoke.py` when validating QQ outbox claim, dedupe, ack, and failure-control behavior after outbox route changes.
Use `tests/smoke/qq/xinyu_qq_review_smoke.py` when validating the semi-automatic QQ dialogue labeling tool before using real exported chat snippets.
Use `ops/validation/long_run_status.py` when auditing milestone status, required docs/scripts, selected current gate states, and known smoke residue markers. The root `long_run_status.py` wrapper is kept for existing commands.
Use `tests/smoke/learning/integration/question_pipeline_smoke.py` when validating that active questions split into internal clarification or exploration candidates before the source gate, without touching self, owner, relationship, or emotion memory.
Use `tests/smoke/learning/integration/source_reliability_gate_smoke.py` when validating that source-gate candidates pass through source reliability and source integration gates before source requests are planned.
Use `tests/smoke/learning/integration/source_request_planner_smoke.py`, `tests/smoke/learning/integration/autonomous_search_activation_smoke.py`, `tests/smoke/learning/integration/source_search_resolution_smoke.py`, `tests/smoke/learning/integration/source_search_provider_smoke.py`, `tests/smoke/learning/integration/outward_source_smoke.py`, `tests/smoke/learning/integration/source_comparison_smoke.py`, `tests/smoke/learning/integration/learner_integration_smoke.py`, `tests/smoke/learning/integration/learning_quality_smoke.py`, `tests/smoke/learning/learning_library_smoke.py`, `tests/smoke/learning/integration/source_quality_followup_smoke.py`, `tests/smoke/learning/integration/learning_session_smoke.py`, and `tests/smoke/learning/integration/source_learning_chain_smoke.py` when validating the controlled external-source path without leaving test material in lived memory. `tests/smoke/learning/integration/autonomous_search_activation_smoke.py` validates disabled, dry-run, quality-blocked, no-pending, provider-blocked, and enabled paths. `tests/smoke/learning/integration/source_comparison_smoke.py` now also validates same-question, adjacent-question, and unrelated-evidence alignment.

## Runtime Readiness And Smoke Groups

Use `tests/smoke/runtime/integration/runtime_readiness_smoke.py` as the high-signal live readiness gate before and after Core/XinYu QQ gateway restarts. It runs deployment status, bridge probe, session cleanup, mojibake guard, long-run status, and a redacted sensitive sweep. Use `--offline` only when live QQ/NapCat checks are intentionally unavailable.

Use `tests/smoke/runtime/integration/deployment_status_smoke.py` when validating that the running Core bridge, source `BRIDGE_VERSION`, native QQ gateway config, live ports, and masked target diagnostics agree.

Use `tests/smoke/runtime/runtime_security_smoke.py` when validating transport/auth guards: API-key traffic over plain HTTP requires explicit local/test override, and non-loopback Core bridge exposure requires a bridge token.

Use `tests/smoke/runtime/state_io_smoke.py` when validating shared markdown-state helper behavior before migrating more custom engines to `xinyu_state_io.py`.

Use grouped smoke manifests for routine checks:

```powershell
.\.venv\Scripts\python.exe smoke_run.py --group deployment
.\.venv\Scripts\python.exe smoke_run.py --group runtime
.\.venv\Scripts\python.exe smoke_run.py --group voice
.\.venv\Scripts\python.exe smoke_run.py --group learning
.\.venv\Scripts\python.exe smoke_run.py --group privacy
```

## First Runtime

Use:

- `FIRST-RUN-PLAN.md`
- `RUNTIME-PRIORITIES.md`
- `TEST-SCENARIOS.md`
- `tests/smoke/memory/integration/memory_mutation_smoke.py`
- `tests/smoke/memory/integration/memory_arc_smoke.py`
- `RUNTIME-VALIDATION-NOTES.md`

Use `tests/smoke/memory/integration/memory_mutation_smoke.py` to inspect actual memory writes without permanently polluting memory when `--restore-after` is enabled.

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

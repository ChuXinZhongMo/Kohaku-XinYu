# XinYu Index v0.1

This is the top-level map of the XinYu runtime source tree.

## 1. Core Entry

- `README.md`
- `config.yaml`
- `MEMORY-REDUCTION-RULES.md`
- `PERSONA-LIVING-SURFACE-RULES.md`
- `NEURO-INSPIRED-ENGINEERING-RULES.md`

## 2. Runtime Behavior

- `services/`
- `prompts/system.md`
- `prompts/output.md`
- `prompts/emotion_writer.md`
- `prompts/relationship_writer.md`
- `prompts/self_narrative_writer.md`
- `prompts/time_writer.md`
- `prompts/reflection_writer.md`
- `prompts/dream_writer.md`
- `prompts/archive_writer.md`
- `prompts/learner_writer.md`
- `custom/time_context_plugin.py`
- `custom/memory_sync_plugin.py`
- `custom/inner_framework_manifest.py`
- `custom/automation_bridge_manifest.py`
- `custom/automation_bridge_plugin.py`
- `xinyu_core_bridge.py`
- `xinyu_bridge_http.py`
- `xinyu_bridge_runtime.py`
- `xinyu_bridge_learning.py`
- `xinyu_bridge_renderer.py`
- `xinyu_bridge_proactive.py`
- `xinyu_bridge_proactive_delivery_routes.py`
- `xinyu_bridge_desktop_proactive_routes.py`
- `xinyu_bridge_desktop_self_action_routes.py`
- `xinyu_bridge_external_plugin_routes.py`
- `xinyu_bridge_metabolism_routes.py`
- `xinyu_bridge_utility_routes.py`
- `xinyu_runtime_security.py`
- `xinyu_state_io.py`
- `xinyu_turn_residue.py`
- `xinyu_persona_contract.py`
- `xinyu_neuro_memory_rules.py`
- `xinyu_life_month_slots.py`
- `xinyu_memory_weights.py`
- `memory/self/system_prompt_memory.md`
- `memory/context/real_world_anchor_policy.md`
- `memory/context/life_month_slots.md`
- `memory/context/current_life_month_context.md`

## 3. Memory Structure

- `stores/`
- `memory/self/`
- `memory/emotions/`
- `memory/relationships/`
- `memory/people/`
- `memory/context/`
- `memory/reflection/`
- `memory/dreams/`
- `memory/archive/`
- `memory/knowledge/`

## 4. Validation and Operation

- `INNER-MEMORY-ORDER.md`
- `EXECUTION-ORDER.md` (hold: local modifications)
- `RUNBOOK.md`
- `RUNTIME-PRIORITIES.md`
- `VALIDATION-INDEX.md`
- `LONG-RUN-AUDIT.md`
- `TEST-SCENARIOS.md`
- `EXPLORATION-SCENARIOS.md`
- `SESSION-REVIEW.md`
- `ops/archive/custom-manifests/2026-05-17/`
- `ops/launch/run_local_xinyu.py`
- `run_local_xinyu.py` (compatibility wrapper)
- `ops/validation/validate_scaffold.py`
- `ops/validation/validate_inner_framework.py`
- `ops/validation/validate_memory_library_manifest.py`
- `ops/validation/long_run_status.py`
- `long_run_status.py` (compatibility wrapper)
- `tests/smoke/runtime/integration/runtime_readiness_smoke.py`
- `tests/smoke/runtime/integration/deployment_status_smoke.py`
- `tests/smoke/runtime/runtime_security_smoke.py`
- `tests/smoke/voice/integration/persona_contract_absence_smoke.py`
- `tests/smoke/voice/persona_stability_layers_smoke.py`
- `tests/smoke/memory/integration/system_prompt_memory_smoke.py`
- `tests/smoke/life/life_month_slots_smoke.py`
- `tests/smoke/life/life_month_context_smoke.py`
- `tests/smoke/runtime/state_io_smoke.py`
- `smoke_run.py`
- `ops/manual/manual_inner_sync.py`
- `ops/manual/goldmark_dehydrate.py`
- `ops/manual/manual_slow_reprocess.py`
- `ops/manual/manual_question_pipeline.py`
- `ops/manual/manual_inner_cycle.py`
- `ops/manual/manual_reflection_output.py`
- `ops/manual/manual_source_gate.py`
- `ops/manual/manual_automation_bridge.py`
- `ops/diagnostics/check_runtime_env.py`
- `ops/diagnostics/diagnose_runtime_injection.py`
- `ops/diagnostics/dialogue_curiosity_review.py`
- `ops/diagnostics/xinyu_live_module_diagnostics.py`
- `ops/probes/memory_lived_pressure_arc.py`
- `ops/probes/long_lived_session_harness.py`
- `ops/probes/xinyu_research_loop_dry_run.py`
- `ops/validation/live_chat_regression_baseline.py`
- `ops/validation/sync_memory_seeds.py`

## 5. Tuning and Diagnosis

- `WRITER-ROUTING.md`
- `MEMORY-LINKS.md`
- `FAILURE-MODES.md`
- `PROMPT-TUNING.md`
- `QUESTION-TO-VALIDATION.md`

## 6. Design and Roadmap

- `IMPLEMENTATION-NEXT.md`
- `CURRENT-REFACTOR-PLAN.md`
- `STRUCTURE-NOTES.md`
- `EXPLORATION-LOOP.md`
- `LEARNER-ROUTING.md`
- `LEARNING-BOUNDARIES.md`
- `social_inquiry_policy.md`
- `real_life_input_adapter_policy.md`
- `SECOND-STAGE-ROADMAP.md`
- `OPEN-QUESTIONS.md`
- `project-plans/README.md`
- `project-plans/XINYU-CROSS-DOMAIN-SYNAESTHESIA-PLAN-2026-05-19.md`
- `project-plans/XINYU-PROACTIVE-CONCRETE-REQUEST-LOOP-PLAN.md` (hold: local modifications)
- `project-plans/XINYU-SELF-THOUGHT-IDLE-LOOP-PLAN.md` (hold: local modifications)
- `project-plans/未完成事项-QQ接回后续接计划.md` (hold: encoding/boundary review)
- `project-plans/XINYU-CONTEXT-MEMORY-LAYER-PLAN.md`
- `project-plans/XINYU-RUNTIME-PRESENCE-SELF-MAP-PLAN.md`

Archived design notes absorbed into this index:

- Action layer v1: keep owner-triggered local actions narrow, alias-bound,
  validator-gated, and converted into action experience instead of direct
  long-term memory writes.
- Public data replay: keep public dialogue datasets as local calibration
  material only; raw datasets stay out of git, and committed replay artifacts
  should contain hashes/counts/abstract reviewed case cards, not raw user text.
- System direction: XinYu's tools serve the living runtime loop; tool execution
  is not the identity layer.
- System diagrams: current active chain remains QQ/NapCat gateway -> core
  bridge -> runtime sidecars -> memory/runtime stores -> guarded visible reply
  or outbox.
- Utilization audit: every active subsystem should prove input, bounded
  decision, output/effect, persistence or deliberate rejection, and a test path.
- Historical originals are under `ops/archive/ops-docs/2026-05-19/`.

## 7. Change History

- `CHANGELOG-XINYU.md`

## 8. Workspace Docs

- `D:\\XinYu\\README.md`
- `D:\\XinYu\\XinYu-Autonomy\\README.md`
- `D:\\XinYu\\XinYu_Desktop\\README.md`

from __future__ import annotations

import os
import hashlib
from pathlib import Path
from urllib.parse import urlparse


TRUTHY = {"1", "true", "yes", "on"}

BRIDGE_RUNTIME_SOURCE_RELS = (
    "xinyu_core_bridge.py",
    "xinyu_bridge_bootstrap.py",
    "xinyu_bridge_bootstrap_store.py",
    "xinyu_bridge_prompt_context_signature_store.py",
    "xinyu_serviceization_contracts.py",
    "xinyu_serviceization_readiness.py",
    "xinyu_bridge_local_report_services.py",
    "xinyu_bridge_chat_turn_contract.py",
    "xinyu_bridge_chat_turn_service.py",
    "xinyu_bridge_turn_pipeline.py",
    "xinyu_bridge_turn_pipeline_facade.py",
    "xinyu_bridge_turn_pipeline_facade_bindings.py",
    "xinyu_bridge_turn_pipeline_facade_entry.py",
    "xinyu_bridge_turn_pipeline_facade_decisions.py",
    "xinyu_bridge_turn_pipeline_facade_routes.py",
    "xinyu_bridge_turn_pipeline_facade_routes_pre_model.py",
    "xinyu_bridge_turn_pipeline_facade_routes_runtime_repair.py",
    "xinyu_bridge_turn_pipeline_facade_routes_tinykernel.py",
    "xinyu_bridge_turn_pipeline_entry.py",
    "xinyu_bridge_turn_pipeline_decisions.py",
    "xinyu_bridge_turn_pipeline_routes.py",
    "xinyu_bridge_turn_pipeline_routes_payload.py",
    "xinyu_bridge_turn_pipeline_routes_payload_pre_model.py",
    "xinyu_bridge_turn_pipeline_routes_payload_observation.py",
    "xinyu_bridge_turn_pipeline_routes_payload_timeout.py",
    "xinyu_bridge_turn_pipeline_routes_payload_tinykernel.py",
    "xinyu_bridge_turn_pipeline_routes_payload_hooks.py",
    "xinyu_bridge_turn_pipeline_routes_dispatch.py",
    "xinyu_bridge_turn_pipeline_routes_response.py",
    "xinyu_bridge_turn_pipeline_routes_pre_model_bindings.py",
    "xinyu_bridge_turn_pipeline_routes_runtime_bindings.py",
    "xinyu_bridge_turn_sidecars.py",
    "xinyu_bridge_turn_prompt_injection.py",
    "xinyu_bridge_turn_prompt_payload.py",
    "xinyu_bridge_turn_prompt_reports.py",
    "xinyu_bridge_turn_sidecar_context.py",
    "xinyu_bridge_turn_sidecar_owner.py",
    "xinyu_bridge_turn_sidecar_state.py",
    "xinyu_bridge_turn_sidecar_state_payloads.py",
    "xinyu_bridge_turn_sidecar_state_normalize.py",
    "xinyu_bridge_turn_sidecar_memory.py",
    "xinyu_bridge_turn_time_facts.py",
    "xinyu_bridge_turn_live_state.py",
    "xinyu_bridge_turn_live_state_payload.py",
    "xinyu_bridge_turn_transport_sidecars.py",
    "xinyu_bridge_turn_finish_sidecars.py",
    "xinyu_bridge_turn_finish_service.py",
    "xinyu_bridge_turn_finish_service_deps.py",
    "xinyu_bridge_turn_finish_result.py",
    "xinyu_bridge_turn_finish_post_reply_service.py",
    "xinyu_bridge_turn_finish_post_reply_quality.py",
    "xinyu_bridge_turn_finish_memory_service.py",
    "xinyu_bridge_turn_finish_delivery_service.py",
    "xinyu_bridge_turn_finish_delivery_bindings.py",
    "xinyu_bridge_turn_finish_memory_bindings.py",
    "xinyu_bridge_turn_finish_post_reply_bindings.py",
    "xinyu_bridge_turn_finish_post_reply_owner_voice_bindings.py",
    "xinyu_bridge_proactive_context.py",
    "xinyu_bridge_proactive_context_feedback.py",
    "xinyu_bridge_proactive_context_feedback_payload.py",
    "xinyu_bridge_proactive_context_feedback_summary.py",
    "xinyu_bridge_proactive_context_feedback_thread.py",
    "xinyu_bridge_proactive_context_state_store.py",
    "xinyu_bridge_proactive_context_tail.py",
    "xinyu_bridge_proactive_context_thread.py",
    "xinyu_bridge_proactive_delivery_contract.py",
    "xinyu_bridge_proactive_delivery_service.py",
    "xinyu_bridge_proactive_delivery_routes.py",
    "xinyu_bridge_proactive_delivery_routes_claim_result.py",
    "xinyu_bridge_proactive_delivery_ack.py",
    "xinyu_bridge_proactive_delivery_claim.py",
    "xinyu_bridge_proactive_delivery_outbound.py",
    "xinyu_bridge_proactive_delivery_response.py",
    "xinyu_bridge_proactive_delivery_route_backend.py",
    "xinyu_bridge_proactive_delivery_worker_service.py",
    "xinyu_bridge_proactive_delivery_state_store.py",
    "xinyu_bridge_proactive_delivery_support.py",
    "xinyu_bridge_health_snapshot.py",
    "xinyu_bridge_health_diagnostics_service.py",
    "xinyu_bridge_health_provider_registry.py",
    "xinyu_bridge_health_provider_registry_service.py",
    "xinyu_bridge_health_snapshot_service.py",
    "xinyu_bridge_desktop_snapshot.py",
    "xinyu_bridge_desktop_snapshot_labels.py",
    "xinyu_bridge_desktop_snapshot_memory.py",
    "xinyu_bridge_desktop_snapshot_metrics.py",
    "xinyu_bridge_desktop_snapshot_projection.py",
    "xinyu_bridge_desktop_snapshot_service.py",
    "xinyu_bridge_desktop_snapshot_context.py",
    "xinyu_bridge_desktop_snapshot_state.py",
    "xinyu_bridge_desktop_snapshot_state_payload.py",
    "xinyu_bridge_desktop_snapshot_state_projection.py",
    "xinyu_bridge_desktop_snapshot_state_projection_action.py",
    "xinyu_bridge_desktop_snapshot_state_projection_assembly.py",
    "xinyu_bridge_desktop_snapshot_state_projection_attention.py",
    "xinyu_bridge_desktop_snapshot_state_projection_concern.py",
    "xinyu_bridge_desktop_snapshot_state_projection_mood.py",
    "xinyu_bridge_desktop_snapshot_state_projection_physical.py",
    "xinyu_bridge_desktop_snapshot_deps.py",
    "xinyu_bridge_desktop_snapshot_active_deps.py",
    "xinyu_bridge_desktop_service_status_store.py",
    "xinyu_bridge_desktop_snapshot_projection_deps.py",
    "xinyu_bridge_desktop_snapshot_service_deps.py",
    "xinyu_bridge_desktop_snapshot_wrapper_deps.py",
    "xinyu_bridge_desktop_surface_contract.py",
    "xinyu_bridge_desktop_surface_service.py",
    "xinyu_bridge_desktop_surface_route_backend.py",
    "xinyu_bridge_desktop_surface_worker_service.py",
    "xinyu_bridge_desktop_surface_projection_backend.py",
    "xinyu_bridge_desktop_surface_state_store.py",
    "xinyu_bridge_desktop_surface_snapshot_state_backend.py",
    "xinyu_desktop_events.py",
    "xinyu_desktop_ws.py",
    "xinyu_bridge_desktop_events.py",
    "xinyu_bridge_desktop_event_routes.py",
    "xinyu_bridge_desktop_event_helpers.py",
    "xinyu_bridge_desktop_event_publish.py",
    "xinyu_bridge_desktop_event_tts.py",
    "xinyu_bridge_desktop_event_payloads.py",
    "xinyu_bridge_desktop_event_memory.py",
    "xinyu_bridge_desktop_event_route_bindings.py",
    "xinyu_bridge_desktop_self_action_approval_backend.py",
    "xinyu_bridge_desktop_self_action_routes.py",
    "xinyu_bridge_desktop_self_action_approval.py",
    "xinyu_bridge_desktop_self_action_approval_payload.py",
    "xinyu_bridge_desktop_self_action_approval_dispatch.py",
    "xinyu_bridge_desktop_self_action_approval_response.py",
    "xinyu_bridge_desktop_self_action_approval_routing.py",
    "xinyu_bridge_desktop_self_action_labels.py",
    "xinyu_bridge_desktop_self_action_snapshot.py",
    "xinyu_bridge_desktop_self_action_snapshot_payload.py",
    "xinyu_bridge_desktop_self_action_snapshot_labels.py",
    "xinyu_bridge_desktop_self_action_snapshot_projection.py",
    "xinyu_bridge_desktop_self_action_snapshot_sections.py",
    "xinyu_bridge_desktop_proactive_routes.py",
    "xinyu_bridge_desktop_proactive_facade.py",
    "xinyu_bridge_desktop_proactive_facade_ack.py",
    "xinyu_bridge_desktop_proactive_facade_delivery.py",
    "xinyu_bridge_desktop_proactive_facade_inbox.py",
    "xinyu_bridge_desktop_proactive_route_glue.py",
    "xinyu_bridge_desktop_proactive_ack.py",
    "xinyu_bridge_desktop_proactive_ack_bindings.py",
    "xinyu_bridge_desktop_proactive_bindings.py",
    "xinyu_bridge_desktop_proactive_deps_support.py",
    "xinyu_bridge_desktop_proactive_history_bindings.py",
    "xinyu_bridge_desktop_proactive_inbox.py",
    "xinyu_bridge_desktop_proactive_inbox_history.py",
    "xinyu_bridge_desktop_proactive_inbox_payload.py",
    "xinyu_bridge_desktop_proactive_inbox_state.py",
    "xinyu_bridge_desktop_proactive_inbox_bindings.py",
    "xinyu_bridge_desktop_proactive_payloads.py",
    "xinyu_bridge_desktop_proactive_projection.py",
    "xinyu_bridge_desktop_proactive_projection_payload.py",
    "xinyu_bridge_desktop_proactive_projection_labels.py",
    "xinyu_bridge_desktop_proactive_projection_status.py",
    "xinyu_bridge_desktop_proactive_projection_bindings.py",
    "xinyu_bridge_desktop_proactive_publish.py",
    "xinyu_bridge_desktop_proactive_publish_bindings.py",
    "xinyu_bridge_desktop_proactive_qq.py",
    "xinyu_bridge_desktop_proactive_qq_bindings.py",
    "xinyu_bridge_desktop_proactive_route_ack.py",
    "xinyu_bridge_desktop_proactive_state_store.py",
    "xinyu_bridge_desktop_proactive_state_update.py",
    "xinyu_bridge_desktop_proactive_state_update_bindings.py",
    "xinyu_bridge_private_ecosystem_routes.py",
    "xinyu_bridge_private_ecosystem_browser.py",
    "xinyu_bridge_private_ecosystem_grant_sanitizer.py",
    "xinyu_bridge_private_ecosystem_payload.py",
    "xinyu_bridge_private_ecosystem_response.py",
    "xinyu_bridge_private_ecosystem_service.py",
    "xinyu_bridge_private_desktop_routes.py",
    "xinyu_bridge_private_desktop_backend.py",
    "xinyu_bridge_private_desktop_frame.py",
    "xinyu_bridge_private_desktop_frame_store.py",
    "xinyu_bridge_private_desktop_payload.py",
    "xinyu_bridge_private_desktop_status.py",
    "xinyu_bridge_private_desktop_status_store.py",
    "xinyu_bridge_external_plugin_call.py",
    "xinyu_bridge_external_plugin_payload.py",
    "xinyu_bridge_external_plugin_dispatch.py",
    "xinyu_bridge_external_plugin_dispatch_payload.py",
    "xinyu_bridge_external_plugin_dispatch_status.py",
    "xinyu_bridge_external_plugin_dispatch_trace.py",
    "xinyu_bridge_external_plugin_response.py",
    "xinyu_bridge_external_plugin_response_common.py",
    "xinyu_bridge_external_plugin_response_blocked.py",
    "xinyu_bridge_external_plugin_response_execution.py",
    "xinyu_bridge_external_plugin_trace_store.py",
    "xinyu_bridge_external_action_contract.py",
    "xinyu_bridge_external_action_backend.py",
    "xinyu_bridge_external_action_worker_service.py",
    "xinyu_bridge_external_action_service.py",
    "xinyu_bridge_external_action_route_backend.py",
    "xinyu_bridge_external_plugin_routes.py",
    "xinyu_bridge_external_plugin_route_admin.py",
    "xinyu_bridge_external_plugin_route_deps.py",
    "xinyu_bridge_external_plugin_route_bindings.py",
    "xinyu_bridge_external_plugin_route_self_thought.py",
    "xinyu_bridge_metabolism_routes.py",
    "xinyu_bridge_life_metabolism_contract.py",
    "xinyu_bridge_life_metabolism_service.py",
    "xinyu_bridge_life_metabolism_route_backend.py",
    "xinyu_bridge_metabolism_payloads.py",
    "xinyu_bridge_metabolism_selection.py",
    "xinyu_bridge_metabolism_ticket_routes.py",
    "xinyu_bridge_metabolism_publish.py",
    "xinyu_bridge_metabolism_runner.py",
    "xinyu_living_memory_recall.py",
    "xinyu_context_retrieval.py",
    "xinyu_retrieval_envelope.py",
    "xinyu_retrieval_need_reranker.py",
    "xinyu_sparse_memory_router.py",
    "xinyu_conversation_experience_cases.py",
    "xinyu_conversation_experience_matcher.py",
    "xinyu_conversation_experience_sidecar.py",
    "xinyu_storage_paths.py",
    "xinyu_bridge_state_persistence_contract.py",
    "xinyu_bridge_state_persistence_service.py",
    "xinyu_bridge_action_routes.py",
    "xinyu_bridge_action_dispatch.py",
    "xinyu_bridge_action_dispatch_codex.py",
    "xinyu_bridge_action_dispatch_external.py",
    "xinyu_bridge_action_experience.py",
    "xinyu_bridge_action_finish.py",
    "xinyu_bridge_action_followups.py",
    "xinyu_bridge_action_followups_deps.py",
    "xinyu_bridge_action_followups_dispatch.py",
    "xinyu_bridge_action_followup_core.py",
    "xinyu_bridge_action_followup_response.py",
    "xinyu_bridge_action_followup_status.py",
    "xinyu_bridge_action_followup_results.py",
    "xinyu_bridge_action_layer_turn.py",
    "xinyu_bridge_action_route_runtime.py",
    "xinyu_bridge_action_route_runtime_followups.py",
    "xinyu_bridge_action_support.py",
    "xinyu_bridge_promise_followup.py",
    "xinyu_bridge_promise_followup_state_store.py",
    "xinyu_bridge_promise_candidate.py",
    "xinyu_bridge_promise_owner_identity_store.py",
    "xinyu_bridge_promise_markers.py",
    "xinyu_bridge_promise_review.py",
    "xinyu_bridge_promise_state.py",
    "xinyu_bridge_observation.py",
    "xinyu_bridge_observation_payload.py",
    "xinyu_bridge_observation_reports.py",
    "xinyu_bridge_observation_reports_store.py",
    "xinyu_bridge_v1_routes.py",
    "xinyu_bridge_v1_payloads.py",
    "xinyu_bridge_v1_provider.py",
    "xinyu_bridge_v1_shadow.py",
    "xinyu_bridge_v1_canary.py",
    "xinyu_bridge_v1_route_adapter.py",
    "xinyu_bridge_slow_live_notes.py",
    "xinyu_bridge_slow_live_notes_payload.py",
    "xinyu_bridge_slow_live_notes_normalization.py",
    "xinyu_bridge_slow_live_notes_format.py",
    "xinyu_bridge_slow_live_publish.py",
    "xinyu_bridge_slow_live_publish_service.py",
    "xinyu_bridge_slow_live_publish_payloads.py",
    "xinyu_bridge_slow_live_turn_publish_bindings.py",
    "xinyu_bridge_slow_live_result.py",
    "xinyu_bridge_slow_live_finish.py",
    "xinyu_bridge_slow_live_finish_service.py",
    "xinyu_bridge_slow_live_finish_bindings.py",
    "xinyu_bridge_slow_live_finish_payloads.py",
    "xinyu_bridge_slow_live_finish_payloads_payload.py",
    "xinyu_bridge_slow_live_finish_payloads_notes.py",
    "xinyu_bridge_slow_live_finish_payloads_status.py",
    "xinyu_bridge_slow_live_contexts.py",
    "xinyu_bridge_slow_live_context_bindings.py",
    "xinyu_bridge_slow_live_context_recall.py",
    "xinyu_bridge_slow_live_context_prompt.py",
    "xinyu_bridge_slow_live_context_sidecars.py",
    "xinyu_bridge_slow_live_reply_adjustments.py",
    "xinyu_bridge_slow_live_reply_adjustment_bindings.py",
    "xinyu_bridge_slow_live_model_injection.py",
    "xinyu_bridge_slow_live_model_bindings.py",
    "xinyu_bridge_slow_live_model_payload.py",
    "xinyu_bridge_slow_live_model_context.py",
    "xinyu_bridge_slow_live_model_retry.py",
    "xinyu_bridge_slow_live_reply_dedupe.py",
    "xinyu_bridge_slow_live_reply_pipeline.py",
    "xinyu_bridge_slow_live_reply_pipeline_payload.py",
    "xinyu_bridge_slow_live_reply_pipeline_steps.py",
    "xinyu_bridge_slow_live_reply_pipeline_result.py",
    "xinyu_bridge_slow_live_reply_pipeline_bindings.py",
    "xinyu_bridge_slow_live_reply_policy.py",
    "xinyu_bridge_slow_live_reply_rendering.py",
    "xinyu_bridge_slow_live_reply_rendering_bindings.py",
    "xinyu_bridge_slow_live_reply_repair_bindings.py",
    "xinyu_bridge_slow_live_reply_repairs.py",
    "xinyu_bridge_slow_live_reply_shape.py",
    "xinyu_bridge_slow_live_reply_shape_bindings.py",
    "xinyu_bridge_slow_live_reply_sticker.py",
    "xinyu_bridge_slow_live_reply_sticker_bindings.py",
    "xinyu_bridge_autonomous_maintenance.py",
    "xinyu_bridge_autonomous_maintenance_note_bindings.py",
    "xinyu_bridge_autonomous_maintenance_payload.py",
    "xinyu_bridge_autonomous_maintenance_scheduling.py",
    "xinyu_bridge_autonomous_maintenance_response.py",
    "xinyu_bridge_autonomous_loop.py",
    "xinyu_bridge_autonomous_state.py",
    "xinyu_bridge_autonomous_state_store.py",
    "xinyu_bridge_autonomous_intake_sidecars.py",
    "xinyu_bridge_autonomous_intake_sidecars_payloads.py",
    "xinyu_bridge_autonomous_intake_sidecars_rendering.py",
    "xinyu_bridge_autonomous_intake_sidecars_appenders.py",
    "xinyu_bridge_autonomous_action_sidecars.py",
    "xinyu_bridge_autonomous_shadow_sidecars.py",
    "xinyu_bridge_autonomous_shadow_appenders.py",
    "xinyu_bridge_autonomous_shadow_append_plan.py",
    "xinyu_bridge_autonomous_shadow_appenders_helpers.py",
    "xinyu_bridge_autonomous_shadow_payloads.py",
    "xinyu_bridge_autonomous_shadow_rendering.py",
    "xinyu_bridge_autonomous_thought_sidecars.py",
    "xinyu_bridge_autonomous_thought_appenders.py",
    "xinyu_bridge_autonomous_thought_flow.py",
    "xinyu_bridge_autonomous_thought_desktop.py",
    "xinyu_bridge_autonomous_thought_payloads.py",
    "xinyu_bridge_autonomous_note_responses.py",
    "xinyu_bridge_autonomous_trace_helpers.py",
    "xinyu_bridge_autonomous_note_facade.py",
    "xinyu_bridge_autonomous_note_dispatch.py",
    "xinyu_bridge_autonomous_note_appenders.py",
    "xinyu_bridge_autonomous_note_dispatch_map.py",
    "xinyu_bridge_autonomous_note_results.py",
    "xinyu_bridge_autonomous_proactive_ready_note.py",
    "xinyu_bridge_learning.py",
    "xinyu_bridge_learning_ingest_contract.py",
    "xinyu_bridge_learning_ingest_service.py",
    "xinyu_bridge_learning_ingest_route_backend.py",
    "xinyu_bridge_learning_codex_reports.py",
    "xinyu_bridge_learning_ingest_helpers.py",
    "xinyu_bridge_learning_ingest_scope_store.py",
    "xinyu_bridge_learning_ingest_request.py",
    "xinyu_bridge_learning_ingest_response.py",
    "xinyu_bridge_learning_runtime.py",
    "xinyu_bridge_learning_routes.py",
    "xinyu_bridge_learning_sidecars.py",
    "xinyu_bridge_learning_study_reports.py",
    "xinyu_bridge_renderer.py",
    "xinyu_bridge_renderer_service.py",
    "xinyu_bridge_renderer_context.py",
    "xinyu_bridge_renderer_debug.py",
    "xinyu_bridge_renderer_debug_store.py",
    "xinyu_bridge_renderer_payload.py",
    "xinyu_bridge_renderer_trace.py",
    "xinyu_bridge_reply_pipeline.py",
    "xinyu_bridge_reply_policy_runtime.py",
    "xinyu_bridge_codex_finalization.py",
    "xinyu_bridge_codex_finalization_glue.py",
    "xinyu_bridge_codex_finalization_reports.py",
    "xinyu_bridge_codex_finalization_response.py",
    "xinyu_bridge_codex_finalization_background.py",
    "xinyu_bridge_codex_finalization_followups.py",
    "xinyu_bridge_codex_finalization_foreground.py",
    "xinyu_bridge_codex_runtime_delegate_finalization_bindings.py",
    "xinyu_bridge_codex_runtime_delegate_runner_bindings.py",
    "xinyu_bridge_codex_runtime_delegate_result_bindings.py",
    "xinyu_bridge_codex_payloads.py",
    "xinyu_bridge_codex_model_payload.py",
    "xinyu_bridge_codex_dialogue_context.py",
    "xinyu_bridge_codex_wait.py",
    "xinyu_bridge_codex_wait_projection.py",
    "xinyu_bridge_codex_wait_payloads.py",
    "xinyu_bridge_codex_runtime_wait_chat_bindings.py",
    "xinyu_bridge_codex_presence.py",
    "xinyu_bridge_codex_runtime_presence_bindings.py",
    "xinyu_bridge_codex_presence_status.py",
    "xinyu_bridge_codex_presence_reply.py",
    "xinyu_bridge_codex_presence_trace.py",
    "xinyu_bridge_codex_execution.py",
    "xinyu_bridge_codex_execution_contract.py",
    "xinyu_bridge_codex_execution_backend.py",
    "xinyu_bridge_codex_execution_worker_client.py",
    "xinyu_bridge_codex_execution_worker_service.py",
    "xinyu_bridge_codex_execution_service.py",
    "xinyu_bridge_codex_runtime_execution_bindings.py",
    "xinyu_bridge_codex_execution_payload.py",
    "xinyu_bridge_codex_execution_response.py",
    "xinyu_bridge_codex_execution_timeout.py",
    "xinyu_bridge_codex_execution_status.py",
    "xinyu_bridge_semantic_fast_routes.py",
    "xinyu_bridge_semantic_fast_payloads.py",
    "xinyu_bridge_semantic_fast_text.py",
    "xinyu_bridge_semantic_fast_text_extract.py",
    "xinyu_bridge_semantic_fast_text_format.py",
    "xinyu_bridge_semantic_fast_decision.py",
    "xinyu_bridge_semantic_fast_pipeline.py",
    "xinyu_bridge_semantic_fast_pipeline_stage.py",
    "xinyu_bridge_semantic_fast_pipeline_payload.py",
    "xinyu_bridge_semantic_fast_pipeline_result.py",
    "xinyu_bridge_semantic_fast_handler.py",
    "xinyu_bridge_semantic_fast_rendering.py",
    "xinyu_bridge_semantic_fast_finish.py",
    "xinyu_bridge_semantic_fast_finish_core.py",
    "xinyu_bridge_semantic_fast_finish_core_guard.py",
    "xinyu_bridge_semantic_fast_finish_core_dedupe.py",
    "xinyu_bridge_semantic_fast_finish_core_publish_result.py",
    "xinyu_bridge_semantic_fast_tail.py",
    "xinyu_bridge_semantic_fast_notes.py",
    "xinyu_bridge_semantic_fast_publish.py",
    "xinyu_bridge_semantic_fast_response.py",
    "xinyu_bridge_utility_routes.py",
    "xinyu_bridge_utility_route_helpers.py",
    "xinyu_bridge_utility_common.py",
    "xinyu_bridge_utility_probe.py",
    "xinyu_bridge_utility_review.py",
    "xinyu_bridge_utility_package.py",
    "xinyu_bridge_utility_learning_proxy.py",
    "xinyu_bridge_utility_sticker.py",
    "xinyu_bridge_utility_message.py",
    "xinyu_bridge_utility_goldmark.py",
    "xinyu_bridge_voice_flags.py",
    "xinyu_bridge_voice_flags_store.py",
    "xinyu_bridge_http.py",
    "xinyu_bridge_http_io.py",
    "xinyu_bridge_http_handler.py",
    "xinyu_bridge_http_server.py",
    "xinyu_bridge_http_runtime_invoker.py",
    "xinyu_bridge_http_dispatch_life_ticket.py",
    "xinyu_bridge_state_text.py",
    "xinyu_bridge_state_text_fields.py",
    "xinyu_bridge_state_text_store.py",
    "xinyu_bridge_state_text_time.py",
    "xinyu_bridge_runtime_repair_status_route.py",
    "xinyu_bridge_runtime_repair_status_route_completion.py",
    "xinyu_bridge_runtime_repair_status_route_payload.py",
    "xinyu_bridge_runtime_repair_status_route_diagnostics.py",
    "xinyu_bridge_runtime_repair_status_route_visibility.py",
    "xinyu_bridge_runtime_repair_status_probe.py",
    "xinyu_bridge_runtime_repair_status_response.py",
    "xinyu_runtime_context.py",
    "xinyu_memory_braid.py",
    "xinyu_turn_route_trace.py",
    "xinyu_turn_route_trace_store.py",
    "xinyu_turn_coherence.py",
    "xinyu_initiative_spine.py",
    "xinyu_initiative_orchestrator.py",
    "xinyu_emotion_council.py",
    "xinyu_self_chosen_goal_ecology.py",
    "xinyu_goal_outcome_observer.py",
    "xinyu_self_action_gateway.py",
    "xinyu_self_action_patch_executor.py",
    "xinyu_speech_controller.py",
    "xinyu_creative_writing.py",
)


def env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in TRUTHY


def is_loopback_host(host: str) -> bool:
    normalized = (host or "").strip().lower()
    if normalized in {"", "localhost", "127.0.0.1", "::1"}:
        return True
    if normalized.startswith("127."):
        return True
    return False


def enforce_llm_http_guard() -> None:
    """Fail startup when any configured model endpoint would send a key over plain HTTP."""
    _enforce_plain_http_endpoint_guard(
        label="LLM",
        base_envs=("XINYU_BASE_URL",),
        key_envs=("XINYU_API_KEY",),
        allow_envs=("XINYU_ALLOW_INSECURE_LLM_HTTP",),
    )
    if env_truthy("XINYU_IMAGE_VISION_ENABLED"):
        _enforce_plain_http_endpoint_guard(
            label="vision",
            base_envs=("XINYU_IMAGE_VISION_BASE_URL", "XINYU_BASE_URL", "OPENAI_BASE_URL"),
            key_envs=("XINYU_IMAGE_VISION_API_KEY", "XINYU_API_KEY", "XINYU_OPENAI_API_KEY", "OPENAI_API_KEY"),
            allow_envs=("XINYU_ALLOW_INSECURE_IMAGE_VISION_HTTP", "XINYU_ALLOW_INSECURE_LLM_HTTP"),
        )
    if os.environ.get("XINYU_VOICE_STT_ENABLED", "").strip() != "0":
        _enforce_plain_http_endpoint_guard(
            label="voice STT",
            base_envs=("XINYU_VOICE_STT_BASE_URL", "OPENAI_BASE_URL", "XINYU_BASE_URL"),
            key_envs=("XINYU_VOICE_STT_API_KEY", "XINYU_OPENAI_API_KEY", "OPENAI_API_KEY", "XINYU_API_KEY"),
            allow_envs=("XINYU_ALLOW_INSECURE_VOICE_STT_HTTP", "XINYU_ALLOW_INSECURE_LLM_HTTP"),
        )
    _enforce_plain_http_endpoint_guard(
        label="voice MiMo hearing",
        base_envs=("XINYU_VOICE_MIMO_BASE_URL",),
        key_envs=("XINYU_VOICE_MIMO_API_KEY",),
        allow_envs=("XINYU_ALLOW_INSECURE_VOICE_MIMO_HTTP", "XINYU_ALLOW_INSECURE_LLM_HTTP"),
    )
    if env_truthy("XINYU_TTS_ENABLED"):
        _enforce_plain_http_endpoint_guard(
            label="TTS",
            base_envs=("XINYU_TTS_BASE_URL", "OPENAI_BASE_URL", "XINYU_BASE_URL"),
            key_envs=("XINYU_TTS_API_KEY", "XINYU_OPENAI_API_KEY", "OPENAI_API_KEY", "XINYU_API_KEY"),
            allow_envs=("XINYU_ALLOW_INSECURE_TTS_HTTP", "XINYU_ALLOW_INSECURE_LLM_HTTP"),
        )


def _first_env_value(names: tuple[str, ...]) -> tuple[str, str]:
    for name in names:
        value = os.environ.get(name, "").strip()
        if value:
            return name, value
    return "", ""


def _enforce_plain_http_endpoint_guard(
    *,
    label: str,
    base_envs: tuple[str, ...],
    key_envs: tuple[str, ...],
    allow_envs: tuple[str, ...],
) -> None:
    key_name, api_key = _first_env_value(key_envs)
    base_name, base_url = _first_env_value(base_envs)
    if not api_key or not base_url:
        return
    parsed = urlparse(base_url)
    if parsed.scheme.lower() != "http":
        return
    if any(env_truthy(name) for name in allow_envs):
        return
    allow_hint = allow_envs[0] if allow_envs else "XINYU_ALLOW_INSECURE_LLM_HTTP"
    raise RuntimeError(
        f"{label} endpoint {base_name} uses plain HTTP while {key_name} is configured. "
        f"Set {allow_hint}=1 only for an explicit local/test override, "
        f"or switch {base_name} to HTTPS."
    )


def enforce_bridge_token_guard(host: str, token: str) -> None:
    if is_loopback_host(host):
        return
    if token.strip():
        return
    raise RuntimeError(
        "Non-loopback XinYu core bridge host requires a non-empty "
        "XINYU_BRIDGE_TOKEN or --bridge-token."
    )


def bridge_source_version(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("BRIDGE_VERSION"):
            continue
        _name, _eq, value = stripped.partition("=")
        return value.strip().strip('"').strip("'")
    return "unknown"


def source_file_digest(path: Path, *, length: int = 16) -> str:
    try:
        data = path.read_bytes()
    except OSError:
        return "unknown"
    digest = hashlib.sha256(data).hexdigest()
    return digest[: max(8, length)]


def runtime_source_paths(root: Path) -> tuple[Path, ...]:
    return tuple(Path(root) / rel for rel in BRIDGE_RUNTIME_SOURCE_RELS)


def source_files_digest(paths: list[Path] | tuple[Path, ...], *, length: int = 16) -> str:
    digest = hashlib.sha256()
    try:
        sorted_paths = sorted((path.resolve() for path in paths), key=lambda item: str(item).lower())
        for path in sorted_paths:
            digest.update(path.name.encode("utf-8", errors="replace"))
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    except OSError:
        return "unknown"
    return digest.hexdigest()[: max(8, length)]

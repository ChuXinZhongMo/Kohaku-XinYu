from __future__ import annotations

import asyncio
from functools import partialmethod

import xinyu_bridge_private_desktop_routes
import xinyu_bridge_bootstrap
import xinyu_bridge_private_ecosystem_routes
import xinyu_bridge_intervention_routes
import xinyu_bridge_external_plugin_routes
import xinyu_bridge_desktop_proactive_routes
import xinyu_bridge_proactive_delivery_routes
import xinyu_bridge_utility_routes
import xinyu_bridge_metabolism_routes
import xinyu_bridge_desktop_snapshot
import xinyu_bridge_desktop_self_action_routes
import xinyu_bridge_desktop_recent_routes
import xinyu_bridge_health_snapshot
import xinyu_bridge_promise_followup
import xinyu_bridge_proactive_context
import xinyu_bridge_renderer
import xinyu_bridge_reply_pipeline
import xinyu_bridge_desktop_events
import xinyu_bridge_session
import xinyu_bridge_v1_routes
import xinyu_bridge_semantic_fast_routes
import xinyu_bridge_codex_markers
import xinyu_bridge_codex_runtime
import xinyu_bridge_learning_sidecars
import xinyu_bridge_runtime_lifecycle
import xinyu_bridge_self_action_qq
import xinyu_bridge_turn_sidecars
import xinyu_bridge_context
import xinyu_bridge_action_routes
import xinyu_bridge_autonomous_maintenance
import xinyu_qq_rich_context
import xinyu_proactive_context_adapter
import xinyu_self_action_voice
import xinyu_visible_persona_voice
import xinyu_codex_service
import xinyu_core_bridge as core_bridge
from xinyu_core_bridge import (
    CODEX_DELEGATE_CLOSE,
    CODEX_DELEGATE_OPEN,
    CODEX_DELEGATE_PATTERNS,
    DEBUG_LIVE_SYSTEM_PROMPT_REL,
    DEBUG_PROMPT_DUMP_ENV,
    DESKTOP_PROACTIVE_FINAL_STATUSES,
    DESKTOP_PROACTIVE_HISTORY_MAX,
    DESKTOP_PROACTIVE_HISTORY_REL,
    DESKTOP_PROACTIVE_INBOX_STATUSES,
    DESKTOP_RECENT_MEMORY_EVENTS_MAX,
    DESKTOP_RECENT_TURNS_MAX,
    PROMPT_CONTEXT_SIGNATURE_FILES,
    BridgeRequestError,
    XinYuBridgeRuntime,
)


def test_bootstrap_runtime_method_is_route_alias() -> None:
    assert XinYuBridgeRuntime._load_runtime is xinyu_bridge_bootstrap.runtime_load_runtime


def test_private_ecosystem_runtime_methods_are_route_aliases() -> None:
    assert (
        XinYuBridgeRuntime.desktop_private_ecosystem_snapshot
        is xinyu_bridge_private_ecosystem_routes.desktop_private_ecosystem_snapshot
    )
    assert (
        XinYuBridgeRuntime.desktop_private_ecosystem_pause
        is xinyu_bridge_private_ecosystem_routes.desktop_private_ecosystem_pause
    )
    assert (
        XinYuBridgeRuntime.desktop_private_ecosystem_grant
        is xinyu_bridge_private_ecosystem_routes.desktop_private_ecosystem_grant
    )
    assert (
        XinYuBridgeRuntime.desktop_private_ecosystem_tick
        is xinyu_bridge_private_ecosystem_routes.desktop_private_ecosystem_tick
    )
    assert (
        XinYuBridgeRuntime.desktop_private_browser_snapshot
        is xinyu_bridge_private_ecosystem_routes.desktop_private_browser_snapshot
    )
    assert (
        XinYuBridgeRuntime.desktop_private_browser_action
        is xinyu_bridge_private_ecosystem_routes.desktop_private_browser_action
    )
    assert (
        XinYuBridgeRuntime._append_private_ecosystem_note
        is xinyu_bridge_private_ecosystem_routes.append_private_ecosystem_note
    )


def test_public_desktop_runtime_methods_are_route_aliases() -> None:
    assert XinYuBridgeRuntime._ensure_self_choice_ready is xinyu_bridge_runtime_lifecycle.ensure_self_choice_ready
    assert XinYuBridgeRuntime.start_background_tasks is xinyu_bridge_runtime_lifecycle.start_background_tasks
    assert XinYuBridgeRuntime.shutdown is xinyu_bridge_runtime_lifecycle.shutdown
    assert XinYuBridgeRuntime.desktop_snapshot is xinyu_bridge_desktop_snapshot.desktop_snapshot
    assert XinYuBridgeRuntime._desktop_active_desires is xinyu_bridge_desktop_snapshot.desktop_active_desires
    assert XinYuBridgeRuntime.desktop_events_recent is xinyu_bridge_desktop_recent_routes.desktop_events_recent
    assert XinYuBridgeRuntime.desktop_chat_recent is xinyu_bridge_desktop_recent_routes.desktop_chat_recent
    assert XinYuBridgeRuntime.desktop_memory_recent is xinyu_bridge_desktop_recent_routes.desktop_memory_recent
    assert (
        XinYuBridgeRuntime.desktop_memory_growth_candidates
        is xinyu_bridge_desktop_recent_routes.desktop_memory_growth_candidates
    )
    assert (
        XinYuBridgeRuntime._desktop_remember_turn
        is xinyu_bridge_desktop_recent_routes.desktop_remember_turn
    )
    assert (
        XinYuBridgeRuntime._desktop_remember_memory_event
        is xinyu_bridge_desktop_recent_routes.desktop_remember_memory_event
    )
    assert DESKTOP_RECENT_TURNS_MAX == xinyu_bridge_desktop_recent_routes.DESKTOP_RECENT_TURNS_MAX
    assert (
        DESKTOP_RECENT_MEMORY_EVENTS_MAX
        == xinyu_bridge_desktop_recent_routes.DESKTOP_RECENT_MEMORY_EVENTS_MAX
    )
    assert (
        XinYuBridgeRuntime.desktop_self_action_approval
        is xinyu_bridge_desktop_self_action_routes.desktop_self_action_approval
    )
    assert (
        XinYuBridgeRuntime._desktop_attach_self_action_patch_executor
        is xinyu_bridge_desktop_self_action_routes.desktop_attach_self_action_patch_executor
    )
    assert (
        XinYuBridgeRuntime._desktop_self_action_pending_item
        is xinyu_bridge_desktop_self_action_routes.desktop_self_action_pending_item
    )
    assert (
        XinYuBridgeRuntime._desktop_self_action_approval_reply
        is xinyu_bridge_desktop_self_action_routes.desktop_self_action_approval_reply
    )
    assert (
        XinYuBridgeRuntime._self_action_intent_label
        is xinyu_bridge_desktop_self_action_routes.self_action_intent_label
    )
    assert (
        XinYuBridgeRuntime._self_action_reason_label
        is xinyu_bridge_desktop_self_action_routes.self_action_reason_label
    )
    assert (
        XinYuBridgeRuntime._self_action_scope_label
        is xinyu_bridge_desktop_self_action_routes.self_action_scope_label
    )
    assert (
        XinYuBridgeRuntime._self_action_boundary_label
        is xinyu_bridge_desktop_self_action_routes.self_action_boundary_label
    )
    assert (
        XinYuBridgeRuntime._self_action_approval_effect_label
        is xinyu_bridge_desktop_self_action_routes.self_action_approval_effect_label
    )
    assert (
        XinYuBridgeRuntime._self_action_goal_label
        is xinyu_bridge_desktop_self_action_routes.self_action_goal_label
    )
    assert (
        XinYuBridgeRuntime._self_action_ecology_context_label
        is xinyu_bridge_desktop_self_action_routes.self_action_ecology_context_label
    )
    assert (
        XinYuBridgeRuntime._self_action_patch_goal_label
        is xinyu_bridge_desktop_self_action_routes.self_action_patch_goal_label
    )
    assert (
        XinYuBridgeRuntime._self_action_action_label
        is xinyu_bridge_desktop_self_action_routes.self_action_action_label
    )
    assert (
        XinYuBridgeRuntime._desktop_initiative_metrics_summary
        is xinyu_bridge_desktop_snapshot.desktop_initiative_metrics_summary
    )
    assert XinYuBridgeRuntime._desktop_xinyu_state is xinyu_bridge_desktop_snapshot.desktop_xinyu_state
    assert XinYuBridgeRuntime._desktop_event_state is xinyu_bridge_desktop_snapshot.desktop_event_state
    assert XinYuBridgeRuntime._desktop_services is xinyu_bridge_desktop_snapshot.desktop_services
    assert XinYuBridgeRuntime._desktop_publish_event is xinyu_bridge_desktop_events.desktop_publish_event
    assert (
        XinYuBridgeRuntime._desktop_publish_event_threadsafe
        is xinyu_bridge_desktop_events.desktop_publish_event_threadsafe
    )
    assert (
        XinYuBridgeRuntime._desktop_publish_chat_started
        is xinyu_bridge_desktop_events.desktop_publish_chat_started
    )
    assert (
        XinYuBridgeRuntime._desktop_publish_chat_finished
        is xinyu_bridge_desktop_events.desktop_publish_chat_finished
    )
    assert (
        XinYuBridgeRuntime._desktop_publish_memory_recall
        is xinyu_bridge_desktop_events.desktop_publish_memory_recall
    )
    assert XinYuBridgeRuntime._maybe_enqueue_tts is xinyu_bridge_desktop_events.maybe_enqueue_tts
    assert XinYuBridgeRuntime._desktop_latest_memory_route is xinyu_bridge_desktop_snapshot.desktop_latest_memory_route
    assert XinYuBridgeRuntime._desktop_memory_route_payload is xinyu_bridge_desktop_snapshot.desktop_memory_route_payload
    assert XinYuBridgeRuntime._desktop_recall_item is xinyu_bridge_desktop_snapshot.desktop_recall_item
    assert XinYuBridgeRuntime._desktop_turn_base is xinyu_bridge_desktop_snapshot.desktop_turn_base
    assert XinYuBridgeRuntime._desktop_session_label is xinyu_bridge_desktop_snapshot.desktop_session_label
    assert XinYuBridgeRuntime._desktop_account_label is xinyu_bridge_desktop_snapshot.desktop_account_label
    assert XinYuBridgeRuntime._desktop_metric_int is xinyu_bridge_desktop_snapshot.desktop_metric_int


def test_private_desktop_runtime_methods_are_route_aliases() -> None:
    assert (
        XinYuBridgeRuntime.desktop_private_desktop_snapshot
        is xinyu_bridge_private_desktop_routes.desktop_private_desktop_snapshot
    )
    assert (
        XinYuBridgeRuntime.desktop_private_desktop_live_state
        is xinyu_bridge_private_desktop_routes.desktop_private_desktop_live_state
    )
    assert XinYuBridgeRuntime.desktop_private_desktop_frame is xinyu_bridge_private_desktop_routes.desktop_private_desktop_frame
    assert (
        XinYuBridgeRuntime.desktop_private_desktop_observe
        is xinyu_bridge_private_desktop_routes.desktop_private_desktop_observe
    )
    assert XinYuBridgeRuntime.desktop_private_desktop_start is xinyu_bridge_private_desktop_routes.desktop_private_desktop_start
    assert XinYuBridgeRuntime.desktop_private_desktop_stop is xinyu_bridge_private_desktop_routes.desktop_private_desktop_stop


def test_turn_intervention_runtime_methods_are_route_aliases() -> None:
    assert XinYuBridgeRuntime.turn_current is xinyu_bridge_intervention_routes.turn_current
    assert XinYuBridgeRuntime.turn_cancel is xinyu_bridge_intervention_routes.turn_cancel
    assert XinYuBridgeRuntime.turn_retry_lightweight is xinyu_bridge_intervention_routes.turn_retry_lightweight
    assert XinYuBridgeRuntime.turn_skip_sidecar is xinyu_bridge_intervention_routes.turn_skip_sidecar
    assert XinYuBridgeRuntime.turn_continue is xinyu_bridge_intervention_routes.turn_continue
    assert XinYuBridgeRuntime.turn_status_message is xinyu_bridge_intervention_routes.turn_status_message


def test_external_plugin_runtime_methods_are_route_aliases() -> None:
    assert XinYuBridgeRuntime.external_plugin_manifest is xinyu_bridge_external_plugin_routes.external_plugin_manifest
    assert XinYuBridgeRuntime.external_plugin_config is xinyu_bridge_external_plugin_routes.external_plugin_config
    assert XinYuBridgeRuntime.external_plugin_install is xinyu_bridge_external_plugin_routes.external_plugin_install
    assert XinYuBridgeRuntime.external_plugin_call is xinyu_bridge_external_plugin_routes.external_plugin_call
    assert (
        XinYuBridgeRuntime._maybe_run_self_thought_external_plugin
        is xinyu_bridge_external_plugin_routes.maybe_run_self_thought_external_plugin
    )


def test_proactive_delivery_runtime_methods_are_route_aliases() -> None:
    assert XinYuBridgeRuntime.proactive is xinyu_bridge_proactive_delivery_routes.proactive
    assert XinYuBridgeRuntime.proactive_ack is xinyu_bridge_proactive_delivery_routes.proactive_ack
    assert XinYuBridgeRuntime.desktop_proactive_ack is xinyu_bridge_desktop_proactive_routes.desktop_proactive_ack
    assert (
        XinYuBridgeRuntime._record_desktop_initiative_feedback
        is xinyu_bridge_desktop_proactive_routes.record_desktop_initiative_feedback
    )
    assert XinYuBridgeRuntime.qq_outbox_claim is xinyu_bridge_proactive_delivery_routes.qq_outbox_claim
    assert XinYuBridgeRuntime.qq_outbox_claim_fast is xinyu_bridge_proactive_delivery_routes.qq_outbox_claim_fast
    assert XinYuBridgeRuntime.qq_outbox_ack is xinyu_bridge_proactive_delivery_routes.qq_outbox_ack
    assert XinYuBridgeRuntime.qq_outbox_ack_fast is xinyu_bridge_proactive_delivery_routes.qq_outbox_ack_fast
    assert (
        XinYuBridgeRuntime._claim_proactive_for_qq_outbox
        is xinyu_bridge_proactive_delivery_routes.claim_proactive_for_qq_outbox
    )
    assert (
        XinYuBridgeRuntime._claim_proactive_for_qq_outbox_sync
        is xinyu_bridge_proactive_delivery_routes.claim_proactive_for_qq_outbox_sync
    )
    assert (
        XinYuBridgeRuntime._ready_proactive_outbox_candidate
        is xinyu_bridge_proactive_delivery_routes.ready_proactive_outbox_candidate
    )
    assert (
        XinYuBridgeRuntime._proactive_candidate_already_handled
        is xinyu_bridge_proactive_delivery_routes.proactive_candidate_already_handled
    )
    assert (
        XinYuBridgeRuntime._desktop_approve_proactive_qq
        is xinyu_bridge_desktop_proactive_routes.desktop_approve_proactive_qq
    )
    assert (
        XinYuBridgeRuntime._desktop_finish_proactive_ack
        is xinyu_bridge_desktop_proactive_routes.desktop_finish_proactive_ack
    )
    assert (
        XinYuBridgeRuntime._desktop_publish_proactive_candidate_ready_from_state
        is xinyu_bridge_desktop_proactive_routes.desktop_publish_proactive_candidate_ready_from_state
    )
    assert (
        XinYuBridgeRuntime._desktop_schedule_proactive_candidate_ready_from_state
        is xinyu_bridge_desktop_proactive_routes.desktop_schedule_proactive_candidate_ready_from_state
    )
    assert (
        XinYuBridgeRuntime._desktop_publish_initiative_candidate_threadsafe
        is xinyu_bridge_desktop_proactive_routes.desktop_publish_initiative_candidate_threadsafe
    )
    assert (
        XinYuBridgeRuntime._desktop_update_proactive_request_state
        is xinyu_bridge_desktop_proactive_routes.desktop_update_proactive_request_state
    )
    assert (
        XinYuBridgeRuntime._desktop_proactive_delivery_payload
        is xinyu_bridge_desktop_proactive_routes.desktop_proactive_delivery_payload
    )
    assert (
        XinYuBridgeRuntime._desktop_apply_proactive_delivery
        is xinyu_bridge_desktop_proactive_routes.desktop_apply_proactive_delivery
    )
    assert (
        XinYuBridgeRuntime._desktop_publish_proactive_delivery_item
        is xinyu_bridge_desktop_proactive_routes.desktop_publish_proactive_delivery_item
    )
    assert (
        XinYuBridgeRuntime._desktop_publish_proactive_delivery_from_state
        is xinyu_bridge_desktop_proactive_routes.desktop_publish_proactive_delivery_from_state
    )
    assert (
        XinYuBridgeRuntime._desktop_publish_proactive_delivery_from_state_threadsafe
        is xinyu_bridge_desktop_proactive_routes.desktop_publish_proactive_delivery_from_state_threadsafe
    )
    assert (
        XinYuBridgeRuntime._desktop_proactive_existing
        is xinyu_bridge_desktop_proactive_routes.desktop_proactive_existing
    )
    assert (
        XinYuBridgeRuntime._desktop_upsert_proactive_inbox
        is xinyu_bridge_desktop_proactive_routes.desktop_upsert_proactive_inbox
    )
    assert (
        XinYuBridgeRuntime._desktop_remove_proactive_inbox
        is xinyu_bridge_desktop_proactive_routes.desktop_remove_proactive_inbox
    )
    assert (
        XinYuBridgeRuntime._desktop_remove_proactive_state_items
        is xinyu_bridge_desktop_proactive_routes.desktop_remove_proactive_state_items
    )
    assert (
        XinYuBridgeRuntime._desktop_clear_proactive_inbox
        is xinyu_bridge_desktop_proactive_routes.desktop_clear_proactive_inbox
    )
    assert (
        XinYuBridgeRuntime._desktop_prune_proactive_inbox
        is xinyu_bridge_desktop_proactive_routes.desktop_prune_proactive_inbox
    )
    assert (
        XinYuBridgeRuntime._desktop_remember_proactive_history
        is xinyu_bridge_desktop_proactive_routes.desktop_remember_proactive_history
    )
    assert (
        XinYuBridgeRuntime._desktop_load_proactive_history
        is xinyu_bridge_desktop_proactive_routes.desktop_load_proactive_history
    )
    assert DESKTOP_PROACTIVE_FINAL_STATUSES is xinyu_bridge_desktop_proactive_routes.DESKTOP_PROACTIVE_FINAL_STATUSES
    assert DESKTOP_PROACTIVE_HISTORY_MAX == xinyu_bridge_desktop_proactive_routes.DESKTOP_PROACTIVE_HISTORY_MAX
    assert DESKTOP_PROACTIVE_HISTORY_REL == xinyu_bridge_desktop_proactive_routes.DESKTOP_PROACTIVE_HISTORY_REL
    assert DESKTOP_PROACTIVE_INBOX_STATUSES is xinyu_bridge_desktop_proactive_routes.DESKTOP_PROACTIVE_INBOX_STATUSES
    assert (
        XinYuBridgeRuntime._desktop_compact_proactive_history
        is xinyu_bridge_desktop_proactive_routes.desktop_compact_proactive_history
    )
    assert (
        XinYuBridgeRuntime._desktop_proactive_item_from_state
        is xinyu_bridge_desktop_proactive_routes.desktop_proactive_item_from_state
    )
    assert (
        XinYuBridgeRuntime._record_proactive_outbound_dialogue
        is xinyu_bridge_proactive_delivery_routes.record_proactive_outbound_dialogue
    )


def test_utility_runtime_methods_are_route_aliases() -> None:
    assert XinYuBridgeRuntime.probe is xinyu_bridge_utility_routes.runtime_probe
    assert XinYuBridgeRuntime.package_install is xinyu_bridge_utility_routes.package_install
    assert XinYuBridgeRuntime.learning_ingest is xinyu_bridge_utility_routes.learning_ingest
    assert XinYuBridgeRuntime.learning_study is xinyu_bridge_utility_routes.learning_study
    assert XinYuBridgeRuntime.learning_observe is xinyu_bridge_utility_routes.learning_observe
    assert XinYuBridgeRuntime.sticker_import is xinyu_bridge_utility_routes.sticker_import
    assert XinYuBridgeRuntime.review_inbox_command is xinyu_bridge_utility_routes.review_inbox_command
    assert XinYuBridgeRuntime.message_ack is xinyu_bridge_utility_routes.message_ack
    assert XinYuBridgeRuntime.message_drop is xinyu_bridge_utility_routes.message_drop
    assert XinYuBridgeRuntime.goldmark_mark_request is xinyu_bridge_utility_routes.goldmark_mark_request


def test_life_metabolism_ticket_runtime_methods_are_route_aliases() -> None:
    assert XinYuBridgeRuntime._desktop_open_metabolism_ticket is xinyu_bridge_metabolism_routes.desktop_open_metabolism_ticket
    assert XinYuBridgeRuntime._metabolism_input_window is xinyu_bridge_metabolism_routes.metabolism_input_window
    assert XinYuBridgeRuntime.life_metabolism_ticket_get is xinyu_bridge_metabolism_routes.life_metabolism_ticket_get
    assert XinYuBridgeRuntime.life_metabolism_ticket_list is xinyu_bridge_metabolism_routes.life_metabolism_ticket_list
    assert (
        XinYuBridgeRuntime.life_metabolism_ticket_approve
        is xinyu_bridge_metabolism_routes.life_metabolism_ticket_approve
    )
    assert XinYuBridgeRuntime.life_metabolism_ticket_reject is xinyu_bridge_metabolism_routes.life_metabolism_ticket_reject
    assert XinYuBridgeRuntime.life_metabolism_ticket_cancel is xinyu_bridge_metabolism_routes.life_metabolism_ticket_cancel
    assert (
        XinYuBridgeRuntime._apply_self_choice_metabolism_decision
        is xinyu_bridge_metabolism_routes.apply_self_choice_metabolism_decision
    )
    assert XinYuBridgeRuntime._publish_metabolism_decision is xinyu_bridge_metabolism_routes.publish_metabolism_decision
    assert (
        XinYuBridgeRuntime._publish_metabolism_runner_result
        is xinyu_bridge_metabolism_routes.publish_metabolism_runner_result
    )
    assert XinYuBridgeRuntime._metabolism_runner_loop is xinyu_bridge_metabolism_routes.metabolism_runner_loop
    assert XinYuBridgeRuntime._run_due_metabolism_once is xinyu_bridge_metabolism_routes.run_due_metabolism_once
    assert XinYuBridgeRuntime._wake_metabolism_runner is xinyu_bridge_metabolism_routes.wake_metabolism_runner


def test_desktop_proactive_inbox_runtime_method_is_route_alias() -> None:
    assert XinYuBridgeRuntime.desktop_proactive_inbox is xinyu_bridge_desktop_proactive_routes.desktop_proactive_inbox


def test_misc_runtime_helpers_are_owner_module_aliases() -> None:
    assert XinYuBridgeRuntime.health_snapshot is xinyu_bridge_health_snapshot.runtime_health_snapshot
    assert XinYuBridgeRuntime.health is xinyu_bridge_health_snapshot.runtime_health
    assert XinYuBridgeRuntime._cleanup_idle_sessions is xinyu_bridge_session.runtime_cleanup_idle_sessions
    assert XinYuBridgeRuntime._append_dialogue_tail is xinyu_bridge_session.runtime_append_dialogue_tail
    assert (
        XinYuBridgeRuntime._dialogue_tail_user_content
        is xinyu_bridge_session.runtime_dialogue_tail_user_content
    )
    assert (
        XinYuBridgeRuntime._append_sticker_delivery_tail
        is xinyu_bridge_session.runtime_append_sticker_delivery_tail
    )
    assert isinstance(XinYuBridgeRuntime.__dict__["_get_session"], partialmethod)
    assert XinYuBridgeRuntime.__dict__["_get_session"].func is xinyu_bridge_session.runtime_get_session
    assert XinYuBridgeRuntime._session_prompt_signature is xinyu_bridge_context.runtime_session_prompt_signature
    assert PROMPT_CONTEXT_SIGNATURE_FILES is xinyu_bridge_context.PROMPT_CONTEXT_SIGNATURE_FILES
    assert XinYuBridgeRuntime._metabolism_health is xinyu_bridge_health_snapshot.metabolism_health
    assert (
        XinYuBridgeRuntime._autonomous_maintenance_health
        is xinyu_bridge_health_snapshot.autonomous_maintenance_health
    )
    assert (
        XinYuBridgeRuntime._autonomous_maintenance_loop
        is xinyu_bridge_autonomous_maintenance.autonomous_maintenance_loop
    )
    assert (
        XinYuBridgeRuntime._run_autonomous_maintenance_once
        is xinyu_bridge_autonomous_maintenance.run_autonomous_maintenance_once
    )
    assert core_bridge.AUTONOMOUS_MAINTENANCE_PROMPT is xinyu_bridge_autonomous_maintenance.AUTONOMOUS_MAINTENANCE_PROMPT
    assert (
        XinYuBridgeRuntime._create_autonomous_maintenance_event
        is xinyu_bridge_autonomous_maintenance.create_autonomous_maintenance_event
    )
    assert (
        XinYuBridgeRuntime._record_autonomous_failure
        is xinyu_bridge_autonomous_maintenance.record_autonomous_failure
    )
    assert XinYuBridgeRuntime._ensure_autonomous_session is xinyu_bridge_autonomous_maintenance.ensure_autonomous_session
    assert XinYuBridgeRuntime._trace_autonomous is xinyu_bridge_autonomous_maintenance.trace_autonomous
    assert (
        XinYuBridgeRuntime._write_autonomous_state
        is xinyu_bridge_autonomous_maintenance.write_autonomous_state
    )
    assert (
        XinYuBridgeRuntime._run_autonomous_self_thought_sidecars
        is xinyu_bridge_autonomous_maintenance.run_autonomous_self_thought_sidecars
    )
    assert (
        XinYuBridgeRuntime._append_watched_source_note
        is xinyu_bridge_autonomous_maintenance.append_watched_source_note
    )
    assert (
        XinYuBridgeRuntime._append_github_learning_note
        is xinyu_bridge_autonomous_maintenance.append_github_learning_note
    )
    assert (
        XinYuBridgeRuntime._append_daily_digest_note
        is xinyu_bridge_autonomous_maintenance.append_daily_digest_note
    )
    assert (
        XinYuBridgeRuntime._append_creative_writing_note
        is xinyu_bridge_autonomous_maintenance.append_creative_writing_note
    )
    assert (
        XinYuBridgeRuntime._append_review_inbox_note
        is xinyu_bridge_autonomous_maintenance.append_review_inbox_note
    )
    assert (
        XinYuBridgeRuntime._append_goldmark_dehydrate_note
        is xinyu_bridge_autonomous_maintenance.append_goldmark_dehydrate_note
    )
    assert (
        XinYuBridgeRuntime._append_goal_ecology_note
        is xinyu_bridge_autonomous_maintenance.append_goal_ecology_note
    )
    assert (
        XinYuBridgeRuntime._append_self_action_gateway_note
        is xinyu_bridge_autonomous_maintenance.append_self_action_gateway_note
    )
    assert (
        XinYuBridgeRuntime._append_self_action_patch_executor_note
        is xinyu_bridge_autonomous_maintenance.append_self_action_patch_executor_note
    )
    assert (
        XinYuBridgeRuntime._append_self_thought_loop_note
        is xinyu_bridge_autonomous_maintenance.append_self_thought_loop_note
    )
    assert (
        XinYuBridgeRuntime._append_proactive_request_note
        is xinyu_bridge_autonomous_maintenance.append_proactive_request_note
    )
    assert (
        XinYuBridgeRuntime._append_self_exploration_note
        is xinyu_bridge_autonomous_maintenance.append_self_exploration_note
    )
    assert (
        XinYuBridgeRuntime._append_learning_closed_loop_self_thought_note
        is xinyu_bridge_autonomous_maintenance.append_learning_closed_loop_self_thought_note
    )
    assert (
        XinYuBridgeRuntime._append_self_thought_research_notes
        is xinyu_bridge_autonomous_maintenance.append_self_thought_research_notes
    )
    assert (
        XinYuBridgeRuntime._append_desktop_proactive_candidate_ready_note
        is xinyu_bridge_autonomous_maintenance.append_desktop_proactive_candidate_ready_note
    )
    assert (
        XinYuBridgeRuntime._append_autonomous_outcome_shadow_notes
        is xinyu_bridge_autonomous_maintenance.append_autonomous_outcome_shadow_notes
    )
    assert (
        XinYuBridgeRuntime._append_autonomous_outward_note
        is xinyu_bridge_autonomous_maintenance.append_autonomous_outward_note
    )
    assert (
        XinYuBridgeRuntime._append_goal_outcome_observer_note
        is xinyu_bridge_autonomous_maintenance.append_goal_outcome_observer_note
    )
    assert (
        XinYuBridgeRuntime._append_proactivity_shadow_note
        is xinyu_bridge_autonomous_maintenance.append_proactivity_shadow_note
    )
    assert (
        XinYuBridgeRuntime._append_emotion_council_note
        is xinyu_bridge_autonomous_maintenance.append_emotion_council_note
    )
    assert (
        XinYuBridgeRuntime._append_impulse_soup_note
        is xinyu_bridge_autonomous_maintenance.append_impulse_soup_note
    )
    assert (
        XinYuBridgeRuntime._append_initiative_spine_note
        is xinyu_bridge_autonomous_maintenance.append_initiative_spine_note
    )
    assert core_bridge.PROMISE_FOLLOWUP_USER_MARKERS is xinyu_bridge_promise_followup.PROMISE_FOLLOWUP_USER_MARKERS
    assert core_bridge.PROMISE_FOLLOWUP_REPLY_MARKERS is xinyu_bridge_promise_followup.PROMISE_FOLLOWUP_REPLY_MARKERS
    assert core_bridge.PROMISE_FOLLOWUP_DONE_MARKERS is xinyu_bridge_promise_followup.PROMISE_FOLLOWUP_DONE_MARKERS
    assert XinYuBridgeRuntime._promised_followup_candidate is xinyu_bridge_promise_followup.candidate
    assert isinstance(XinYuBridgeRuntime.__dict__["_schedule_promised_followup_if_needed"], partialmethod)
    assert (
        XinYuBridgeRuntime.__dict__["_schedule_promised_followup_if_needed"].func
        is xinyu_bridge_promise_followup.schedule_if_needed
    )
    assert XinYuBridgeRuntime._owner_private_user_id is xinyu_bridge_promise_followup.owner_private_user_id
    assert XinYuBridgeRuntime._owner_private_payload is xinyu_bridge_proactive_context.owner_private_payload
    assert (
        XinYuBridgeRuntime._append_assistant_to_dialogue_tail
        is xinyu_bridge_proactive_context.append_assistant_to_dialogue_tail
    )
    assert (
        XinYuBridgeRuntime._sync_recent_proactive_to_dialogue_tail
        is xinyu_bridge_proactive_context.sync_recent_proactive_to_dialogue_tail
    )
    assert XinYuBridgeRuntime._mark_proactive_owner_reply is xinyu_bridge_proactive_context.mark_proactive_owner_reply
    assert XinYuBridgeRuntime._proactive_thread_context is xinyu_bridge_proactive_context.proactive_thread_context
    assert (
        XinYuBridgeRuntime._refresh_initiative_spine_after_proactive_feedback
        is xinyu_bridge_proactive_context.refresh_initiative_spine_after_proactive_feedback
    )
    assert XinYuBridgeRuntime._qq_rich_message_sidecar is xinyu_qq_rich_context.prompt_sidecar_from_payload
    assert (
        XinYuBridgeRuntime._desktop_recent_owner_private_turns
        is xinyu_proactive_context_adapter.runtime_owner_private_turns
    )
    assert XinYuBridgeRuntime._extract_self_code_approval_id is xinyu_bridge_codex_markers.extract_self_code_approval_id
    assert (
        XinYuBridgeRuntime._extract_model_codex_delegate
        is xinyu_bridge_codex_markers.extract_model_codex_delegate_default
    )
    assert CODEX_DELEGATE_OPEN == xinyu_bridge_codex_markers.CODEX_DELEGATE_OPEN
    assert CODEX_DELEGATE_CLOSE == xinyu_bridge_codex_markers.CODEX_DELEGATE_CLOSE
    assert CODEX_DELEGATE_PATTERNS is xinyu_bridge_codex_markers.CODEX_DELEGATE_PATTERNS
    assert (
        XinYuBridgeRuntime._trusted_public_search_task_allowed
        is xinyu_bridge_codex_runtime.trusted_public_search_task_allowed
    )
    assert (
        XinYuBridgeRuntime._extract_wait_to_think_task
        is xinyu_bridge_codex_runtime.extract_wait_to_think_task
    )
    assert (
        XinYuBridgeRuntime._wait_to_think_execution_plan
        is xinyu_bridge_codex_runtime.wait_to_think_execution_plan
    )
    assert (
        XinYuBridgeRuntime._transition_wait_to_think_reply
        is xinyu_bridge_codex_runtime.transition_wait_to_think_reply
    )
    assert (
        XinYuBridgeRuntime._prepare_self_code_watchdog_payload
        is xinyu_bridge_codex_runtime.prepare_self_code_watchdog_payload
    )
    assert XinYuBridgeRuntime._codex_learning_followup is xinyu_bridge_learning_sidecars.codex_learning_followup
    assert (
        core_bridge.OWNER_DIRECT_CODEX_DELEGATE_MARKERS
        is xinyu_bridge_codex_runtime.OWNER_DIRECT_CODEX_DELEGATE_MARKERS
    )
    assert (
        core_bridge.OWNER_DIRECT_CODEX_SUPPORT_MARKERS
        is xinyu_bridge_codex_runtime.OWNER_DIRECT_CODEX_SUPPORT_MARKERS
    )
    assert (
        core_bridge.OWNER_DIRECT_CODEX_NEGATIVE_MARKERS
        is xinyu_bridge_codex_runtime.OWNER_DIRECT_CODEX_NEGATIVE_MARKERS
    )
    assert (
        core_bridge.OWNER_SELF_CODE_EDIT_GRANT_MARKERS
        is xinyu_bridge_codex_runtime.OWNER_SELF_CODE_EDIT_GRANT_MARKERS
    )
    assert core_bridge.OWNER_SELF_CODE_START_MARKERS is xinyu_bridge_codex_runtime.OWNER_SELF_CODE_START_MARKERS
    assert (
        core_bridge.OWNER_SELF_CODE_NEGATIVE_MARKERS
        is xinyu_bridge_codex_runtime.OWNER_SELF_CODE_NEGATIVE_MARKERS
    )
    assert core_bridge.OWNER_SELF_CODE_GRANT_CUES is xinyu_bridge_codex_runtime.OWNER_SELF_CODE_GRANT_CUES
    assert XinYuBridgeRuntime._owner_direct_codex_task is xinyu_bridge_codex_runtime.owner_direct_codex_task
    assert XinYuBridgeRuntime._owner_self_code_grant_in_text is xinyu_bridge_codex_runtime.owner_self_code_grant_in_text
    assert XinYuBridgeRuntime._recent_owner_self_code_grant is xinyu_bridge_codex_runtime.recent_owner_self_code_grant
    assert (
        XinYuBridgeRuntime._owner_self_code_direct_grant_requested
        is xinyu_bridge_codex_runtime.owner_self_code_direct_grant_requested
    )
    assert (
        XinYuBridgeRuntime._owner_self_code_iteration_task
        is xinyu_bridge_codex_runtime.owner_self_code_iteration_task
    )
    assert XinYuBridgeRuntime._can_model_delegate_codex is xinyu_bridge_codex_runtime.can_model_delegate_codex
    assert XinYuBridgeRuntime._build_model_codex_payload is xinyu_bridge_codex_runtime.build_model_codex_payload
    assert (
        XinYuBridgeRuntime._build_self_code_iteration_codex_payload
        is xinyu_bridge_codex_runtime.build_self_code_iteration_codex_payload
    )
    assert (
        XinYuBridgeRuntime._augment_codex_payload_with_dialogue_context
        is xinyu_bridge_codex_runtime.augment_runtime_codex_payload_with_dialogue_context
    )
    assert XinYuBridgeRuntime.codex_execute is xinyu_bridge_codex_runtime.runtime_codex_execute
    assert (
        XinYuBridgeRuntime._schedule_codex_background_delegate
        is xinyu_bridge_codex_runtime.schedule_codex_background_delegate
    )
    assert (
        XinYuBridgeRuntime._start_codex_foreground_delegate
        is xinyu_bridge_codex_runtime.start_codex_foreground_delegate
    )
    assert (
        XinYuBridgeRuntime._prepare_codex_background_delegate_context
        is xinyu_bridge_codex_runtime.prepare_codex_background_delegate_context
    )
    assert (
        XinYuBridgeRuntime._record_codex_delegate_presence_state
        is xinyu_bridge_codex_runtime.record_codex_delegate_presence_state
    )
    assert (
        XinYuBridgeRuntime._record_codex_delegate_presence_result
        is xinyu_bridge_codex_runtime.record_codex_delegate_presence_result
    )
    assert (
        XinYuBridgeRuntime._run_codex_foreground_delegate
        is xinyu_bridge_codex_runtime.run_codex_foreground_delegate
    )
    assert (
        XinYuBridgeRuntime._run_codex_background_delegate
        is xinyu_bridge_codex_runtime.run_codex_background_delegate
    )
    assert (
        XinYuBridgeRuntime._finalize_codex_foreground_delegate_response
        is xinyu_bridge_codex_runtime.finalize_codex_foreground_delegate_response
    )
    assert (
        XinYuBridgeRuntime._stage_codex_report_material_after_delegate
        is xinyu_bridge_codex_runtime.stage_codex_report_material_after_delegate
    )
    assert (
        XinYuBridgeRuntime._handoff_codex_delegate_to_dream
        is xinyu_bridge_codex_runtime.handoff_codex_delegate_to_dream
    )
    assert (
        XinYuBridgeRuntime._settle_codex_delegate_action_experience
        is xinyu_bridge_codex_runtime.settle_codex_delegate_action_experience
    )
    assert (
        XinYuBridgeRuntime._notify_async_exploration_codex_result
        is xinyu_bridge_codex_runtime.notify_async_exploration_codex_result
    )
    assert (
        XinYuBridgeRuntime._append_codex_delegate_background_trace
        is xinyu_bridge_codex_runtime.append_codex_delegate_background_trace
    )
    assert (
        XinYuBridgeRuntime._codex_delegate_background
        is xinyu_bridge_codex_runtime.runtime_codex_delegate_background
    )
    assert XinYuBridgeRuntime._renderer_reason is xinyu_bridge_renderer.runtime_renderer_reason
    assert XinYuBridgeRuntime._build_renderer_messages is xinyu_bridge_renderer.runtime_build_renderer_messages
    assert XinYuBridgeRuntime._renderer_memory_context is xinyu_bridge_renderer.runtime_renderer_memory_context
    assert XinYuBridgeRuntime._read_text is xinyu_bridge_renderer.runtime_read_text
    assert XinYuBridgeRuntime._conversation_tail is xinyu_bridge_renderer.runtime_conversation_tail
    assert XinYuBridgeRuntime._strip_renderer_wrappers is xinyu_bridge_renderer.runtime_strip_renderer_wrappers
    assert XinYuBridgeRuntime._maybe_dump_live_system_prompt is xinyu_bridge_renderer.runtime_maybe_dump_live_system_prompt
    assert XinYuBridgeRuntime._render_outward_reply is xinyu_bridge_reply_pipeline.runtime_render_outward_reply
    assert XinYuBridgeRuntime._recover_empty_visible_reply is xinyu_bridge_reply_pipeline.recover_empty_visible_reply
    assert (
        XinYuBridgeRuntime._build_life_reply_policy
        is xinyu_bridge_reply_pipeline.build_life_reply_policy_for_runtime
    )
    assert isinstance(XinYuBridgeRuntime.__dict__["_speech_controller"], partialmethod)
    assert (
        XinYuBridgeRuntime.__dict__["_speech_controller"].func
        is xinyu_bridge_reply_pipeline.runtime_speech_controller
    )
    assert (
        XinYuBridgeRuntime._is_live_style_pressure
        is xinyu_bridge_reply_pipeline.runtime_is_live_style_pressure
    )
    assert (
        XinYuBridgeRuntime._is_owner_relationship_pressure
        is xinyu_bridge_reply_pipeline.runtime_is_owner_relationship_pressure
    )
    assert (
        XinYuBridgeRuntime._is_explicit_technical_request
        is xinyu_bridge_reply_pipeline.runtime_is_explicit_technical_request
    )
    assert XinYuBridgeRuntime._reply_quality_flags is xinyu_bridge_reply_pipeline.runtime_reply_quality_flags
    assert DEBUG_PROMPT_DUMP_ENV == xinyu_bridge_renderer.DEBUG_PROMPT_DUMP_ENV
    assert DEBUG_LIVE_SYSTEM_PROMPT_REL == xinyu_bridge_renderer.DEBUG_LIVE_SYSTEM_PROMPT_REL
    assert XinYuBridgeRuntime._self_action_approval_message is xinyu_self_action_voice.compose_self_action_approval_voice
    assert (
        XinYuBridgeRuntime._self_action_prepared_patch_message
        is xinyu_self_action_voice.compose_self_action_prepared_patch_voice
    )
    assert (
        XinYuBridgeRuntime._maybe_enqueue_self_action_approval_to_qq
        is xinyu_bridge_self_action_qq.maybe_enqueue_self_action_approval_to_qq
    )
    assert (
        XinYuBridgeRuntime._maybe_enqueue_self_action_prepared_patch_to_qq
        is xinyu_bridge_self_action_qq.maybe_enqueue_self_action_prepared_patch_to_qq
    )
    assert XinYuBridgeRuntime._settle_action_experience is xinyu_bridge_action_routes.settle_action_experience
    assert isinstance(XinYuBridgeRuntime.__dict__["_maybe_handle_action_layer_turn"], partialmethod)
    assert (
        XinYuBridgeRuntime.__dict__["_maybe_handle_action_layer_turn"].func
        is xinyu_bridge_action_routes.handle_action_layer_turn
    )
    assert (
        XinYuBridgeRuntime.__dict__["_maybe_handle_action_layer_turn"].keywords["bridge_request_error_type"]
        is BridgeRequestError
    )
    assert (
        XinYuBridgeRuntime._maybe_handle_recent_action_followup_turn
        is xinyu_bridge_action_routes.handle_recent_action_followup_turn
    )
    assert (
        XinYuBridgeRuntime._maybe_handle_action_digest_followup_turn
        is xinyu_bridge_action_routes.handle_action_digest_followup_turn
    )
    assert XinYuBridgeRuntime._promised_followup_message is xinyu_visible_persona_voice.compose_promise_followup_message
    assert XinYuBridgeRuntime._codex_status_reply is xinyu_codex_service.codex_status_reply
    assert XinYuBridgeRuntime._codex_delegate_running is xinyu_bridge_codex_runtime.codex_delegate_running_for_runtime
    assert XinYuBridgeRuntime._codex_busy_reply is xinyu_bridge_codex_runtime.codex_busy_reply_default
    assert XinYuBridgeRuntime._format_dialogue_tail is xinyu_bridge_codex_runtime.format_runtime_dialogue_tail
    assert XinYuBridgeRuntime._empty_visible_reply_fallback is xinyu_bridge_semantic_fast_routes.empty_visible_reply_fallback
    assert (
        XinYuBridgeRuntime._looks_like_time_fact_correction
        is xinyu_bridge_turn_sidecars.looks_like_time_fact_correction
    )
    assert isinstance(XinYuBridgeRuntime.__dict__["_inject_live_turn_context"], partialmethod)
    assert (
        XinYuBridgeRuntime.__dict__["_inject_live_turn_context"].func
        is xinyu_bridge_turn_sidecars.inject_live_turn_context
    )
    assert (
        XinYuBridgeRuntime.__dict__["_inject_live_turn_context"].keywords["codex_delegate_open"]
        == CODEX_DELEGATE_OPEN
    )
    assert (
        XinYuBridgeRuntime.__dict__["_inject_live_turn_context"].keywords["codex_delegate_close"]
        == CODEX_DELEGATE_CLOSE
    )
    assert (
        XinYuBridgeRuntime._owner_private_llm_failover_context
        is xinyu_bridge_semantic_fast_routes.owner_private_llm_failover_context
    )
    assert XinYuBridgeRuntime._codex_completion_summary is xinyu_bridge_codex_runtime.codex_completion_summary
    assert (
        XinYuBridgeRuntime._codex_completion_outbox_message
        is xinyu_bridge_codex_runtime.codex_completion_outbox_message
    )
    assert (
        XinYuBridgeRuntime._enqueue_codex_completion_if_needed
        is xinyu_bridge_codex_runtime.enqueue_codex_completion_if_needed
    )
    assert (
        XinYuBridgeRuntime._codex_generated_image_artifacts
        is xinyu_bridge_codex_runtime.codex_generated_image_artifacts
    )


def test_static_helper_aliases_do_not_bind_runtime_self() -> None:
    runtime = object.__new__(XinYuBridgeRuntime)

    assert runtime._desktop_metric_int("7") == 7
    assert runtime._extract_self_code_approval_id("Self-code approval id: approval-123") == "approval-123"
    assert (
        runtime._extract_model_codex_delegate("[[XINYU_CODEX_DELEGATE]] inspect [[/XINYU_CODEX_DELEGATE]]")
        == "inspect"
    )
    assert runtime._trusted_public_search_task_allowed("search public web sources for PyMuPDF docs") is True
    assert runtime._can_model_delegate_codex(
        {"message_type": "private_text", "metadata": {"is_owner_user": True}}
    ) is True
    assert runtime._self_action_approval_message({"goal_title": "test goal"})
    assert runtime._self_action_prepared_patch_message({"goal_title": "test goal"})
    assert runtime._promised_followup_message({"user_text": "test promise"})
    assert runtime._codex_status_reply("started", paths={}, auto_study=False, task_text="test task")


def test_desktop_event_adapter_aliases_bind_runtime_self() -> None:
    calls: list[tuple[str, dict[str, object], dict[str, object]]] = []

    class _EventBus:
        def publish_threadsafe(self, event_type: str, payload: dict[str, object], **kwargs):
            calls.append((event_type, payload, kwargs))

            class _Future:
                def add_done_callback(self, callback) -> None:
                    return None

            return _Future()

    runtime = object.__new__(XinYuBridgeRuntime)
    runtime.desktop_event_bus = _EventBus()

    runtime._desktop_publish_event_threadsafe("event.bound", {"ok": True}, privacy="owner_private")

    assert calls == [
        (
            "event.bound",
            {"ok": True},
            {"source": "xinyu_core_bridge", "privacy": "owner_private", "severity": None},
        )
    ]


def test_probe_route_alias_binds_runtime_bridge_version() -> None:
    runtime = object.__new__(XinYuBridgeRuntime)
    runtime.bridge_version = "bound-version"
    runtime._sessions = {}
    runtime._payload_text = lambda payload: str(payload.get("text") or "")  # type: ignore[method-assign]

    async def _cleanup_idle_sessions() -> dict[str, int]:
        return {"cleaned_sessions": 0}

    runtime._cleanup_idle_sessions = _cleanup_idle_sessions  # type: ignore[method-assign]

    result = asyncio.run(runtime.probe({"text": "hello"}))

    assert result["version"] == "bound-version"
    assert result["received_text_chars"] == 5
    assert result["session_created"] is False


def test_v1_runtime_helpers_are_route_aliases() -> None:
    assert core_bridge.V1_OWNER_SIMPLE_CANARY_ENV is xinyu_bridge_v1_routes.V1_OWNER_SIMPLE_CANARY_ENV
    assert core_bridge.V1_CANARY_GREETING_TEXTS is xinyu_bridge_v1_routes.V1_CANARY_GREETING_TEXTS
    assert core_bridge.V1_CANARY_ACK_TEXTS is xinyu_bridge_v1_routes.V1_CANARY_ACK_TEXTS
    assert XinYuBridgeRuntime._v1_health is xinyu_bridge_v1_routes.health
    assert XinYuBridgeRuntime._ensure_v1_app is xinyu_bridge_v1_routes.ensure_app
    assert XinYuBridgeRuntime._record_v1_shadow_readiness is xinyu_bridge_v1_routes.record_shadow_readiness
    assert XinYuBridgeRuntime._run_v1_shadow is xinyu_bridge_v1_routes.run_shadow
    assert XinYuBridgeRuntime._v1_canary_payload_allowed is xinyu_bridge_v1_routes.canary_payload_allowed
    assert XinYuBridgeRuntime._maybe_handle_v1_canary_turn is xinyu_bridge_v1_routes.handle_canary_turn


def test_semantic_fast_runtime_helpers_are_route_aliases() -> None:
    assert (
        XinYuBridgeRuntime._owner_private_semantic_fast_decision
        is xinyu_bridge_semantic_fast_routes.owner_private_semantic_fast_decision
    )
    assert (
        XinYuBridgeRuntime._maybe_handle_owner_private_semantic_fast_turn
        is xinyu_bridge_semantic_fast_routes.handle_owner_private_semantic_fast_turn
    )

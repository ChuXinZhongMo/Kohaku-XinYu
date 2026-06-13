from __future__ import annotations

from typing import Any

import xinyu_bridge_codex_runtime as codex_runtime


def install_runtime_codex_aliases(runtime_cls: type[Any]) -> type[Any]:
    runtime_cls._owner_direct_codex_task = codex_runtime.owner_direct_codex_task
    runtime_cls._owner_self_code_grant_in_text = codex_runtime.owner_self_code_grant_in_text
    runtime_cls._recent_owner_self_code_grant = codex_runtime.recent_owner_self_code_grant
    runtime_cls._owner_self_code_direct_grant_requested = codex_runtime.owner_self_code_direct_grant_requested
    runtime_cls._owner_self_code_iteration_task = codex_runtime.owner_self_code_iteration_task
    runtime_cls._codex_delegate_running = codex_runtime.codex_delegate_running_for_runtime
    runtime_cls._codex_busy_reply = staticmethod(codex_runtime.codex_busy_reply_default)
    runtime_cls._trusted_public_search_task_allowed = staticmethod(codex_runtime.trusted_public_search_task_allowed)
    runtime_cls.codex_execute = codex_runtime.runtime_codex_execute
    runtime_cls._extract_model_codex_delegate = staticmethod(codex_runtime.extract_model_codex_delegate_default)
    runtime_cls._extract_wait_to_think_task = staticmethod(codex_runtime.extract_wait_to_think_task)
    runtime_cls._wait_to_think_execution_plan = staticmethod(codex_runtime.wait_to_think_execution_plan)
    runtime_cls._extract_self_code_approval_id = staticmethod(codex_runtime.extract_self_code_approval_id)
    runtime_cls._prepare_self_code_watchdog_payload = codex_runtime.prepare_self_code_watchdog_payload
    runtime_cls._transition_wait_to_think_reply = codex_runtime.transition_wait_to_think_reply
    runtime_cls._can_model_delegate_codex = staticmethod(codex_runtime.can_model_delegate_codex)
    runtime_cls._build_model_codex_payload = staticmethod(codex_runtime.build_model_codex_payload)
    runtime_cls._build_self_code_iteration_codex_payload = codex_runtime.build_self_code_iteration_codex_payload
    runtime_cls._augment_codex_payload_with_dialogue_context = (
        codex_runtime.augment_runtime_codex_payload_with_dialogue_context
    )
    runtime_cls._codex_status_reply = staticmethod(codex_runtime.codex_status_reply)
    runtime_cls._codex_reply_variant = staticmethod(codex_runtime.codex_reply_variant)
    runtime_cls._codex_owner_task_text = staticmethod(codex_runtime.codex_owner_task_text)
    runtime_cls._codex_task_subject = staticmethod(codex_runtime.codex_task_subject)
    runtime_cls._codex_started_reply = staticmethod(codex_runtime.codex_started_reply)
    runtime_cls._schedule_codex_background_delegate = codex_runtime.schedule_codex_background_delegate
    runtime_cls._start_codex_foreground_delegate = codex_runtime.start_codex_foreground_delegate
    runtime_cls._prepare_codex_background_delegate_context = codex_runtime.prepare_codex_background_delegate_context
    runtime_cls._record_codex_delegate_presence_state = staticmethod(codex_runtime.record_codex_delegate_presence_state)
    runtime_cls._record_codex_delegate_presence_result = staticmethod(
        codex_runtime.record_codex_delegate_presence_result
    )
    runtime_cls._run_codex_foreground_delegate = codex_runtime.run_codex_foreground_delegate
    runtime_cls._run_codex_background_delegate = codex_runtime.run_codex_background_delegate
    runtime_cls._finalize_codex_foreground_delegate_response = codex_runtime.finalize_codex_foreground_delegate_response
    runtime_cls._stage_codex_report_material_after_delegate = codex_runtime.stage_codex_report_material_after_delegate
    runtime_cls._handoff_codex_delegate_to_dream = codex_runtime.handoff_codex_delegate_to_dream
    runtime_cls._settle_codex_delegate_action_experience = codex_runtime.settle_codex_delegate_action_experience
    runtime_cls._notify_async_exploration_codex_result = codex_runtime.notify_async_exploration_codex_result
    runtime_cls._append_codex_delegate_background_trace = staticmethod(
        codex_runtime.append_codex_delegate_background_trace
    )
    runtime_cls._codex_completion_summary = codex_runtime.codex_completion_summary
    runtime_cls._codex_completion_outbox_message = codex_runtime.codex_completion_outbox_message
    runtime_cls._enqueue_codex_completion_if_needed = codex_runtime.enqueue_codex_completion_if_needed
    runtime_cls._codex_generated_image_artifacts = codex_runtime.codex_generated_image_artifacts
    runtime_cls._looks_like_codex_image_generation_task = staticmethod(
        codex_runtime.looks_like_codex_image_generation_task
    )
    runtime_cls._codex_delegate_background = codex_runtime.runtime_codex_delegate_background
    runtime_cls._codex_learning_followup = codex_runtime.codex_learning_followup
    runtime_cls._format_dialogue_tail = codex_runtime.format_runtime_dialogue_tail
    return runtime_cls

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime
from http import HTTPStatus
from pathlib import Path
from typing import Any

from xinyu_async_exploration import (
    async_exploration_outbox_message as _async_exploration_outbox_message,
    create_async_exploration_closure,
    update_async_exploration_from_codex,
)
from xinyu_bridge_errors import BridgeRequestError
from xinyu_bridge_codex_markers import extract_model_codex_delegate_default, extract_self_code_approval_id
from xinyu_bridge_learning_sidecars import codex_learning_followup, should_run_learning_after_codex
from xinyu_bridge_codex_policy import (
    OWNER_DIRECT_CODEX_DELEGATE_MARKERS,
    OWNER_DIRECT_CODEX_NEGATIVE_MARKERS,
    OWNER_DIRECT_CODEX_SUPPORT_MARKERS,
    OWNER_SELF_CODE_EDIT_GRANT_MARKERS,
    OWNER_SELF_CODE_GRANT_CUES,
    OWNER_SELF_CODE_NEGATIVE_MARKERS,
    OWNER_SELF_CODE_START_MARKERS,
    owner_direct_codex_task,
    owner_self_code_direct_grant_requested,
    owner_self_code_grant_in_text,
    owner_self_code_iteration_task,
    recent_owner_self_code_grant,
)
from xinyu_bridge_codex_payloads import (
    augment_codex_payload_with_dialogue_context,
    augment_runtime_codex_payload_with_dialogue_context,
    build_model_codex_payload,
    build_self_code_iteration_codex_payload,
    can_model_delegate_codex,
    format_dialogue_tail,
    format_runtime_dialogue_tail,
)
from xinyu_bridge_codex_presence import (
    append_codex_delegate_background_trace,
    codex_busy_reply,
    codex_busy_reply_default,
    codex_delegate_background_error_trace_line,
    codex_delegate_background_success_trace_line,
    codex_delegate_running,
    codex_delegate_running_for_runtime,
    codex_foreground_result_status,
    codex_presence_status_from_result,
    record_codex_delegate_presence_result as _record_codex_delegate_presence_result,
    record_codex_delegate_presence_state as _record_codex_delegate_presence_state,
)
from xinyu_bridge_codex_wait import (
    WAIT_TO_THINK_PATTERNS,
    WAIT_TO_THINK_WRITE_RISK_MARKERS,
    build_wait_to_think_codex_payload,
    extract_wait_to_think_task,
    prepare_self_code_watchdog_payload as _prepare_self_code_watchdog_payload,
    wait_to_think_execution_plan,
)
from xinyu_bridge_codex_wait_transition import (
    transition_wait_to_think_reply as _runtime_transition_wait_to_think_reply,
)
from xinyu_bridge_codex_completion import (
    codex_completion_outbox_message as _runtime_codex_completion_outbox_message,
    codex_completion_summary as _runtime_codex_completion_summary,
    codex_generated_image_artifacts as _runtime_codex_generated_image_artifacts,
    enqueue_codex_completion_if_needed as _runtime_enqueue_codex_completion_if_needed,
)
from xinyu_bridge_codex_runtime_completion_bindings import (
    codex_completion_outbox_message_runtime,
    codex_completion_summary_runtime,
    codex_generated_image_artifacts_runtime,
    enqueue_codex_completion_if_needed_runtime,
)
from xinyu_bridge_codex_runtime_async_followup_bindings import (
    codex_async_exploration_result_outbox_payload_runtime,
    codex_delegate_action_outcome_runtime,
    notify_async_exploration_codex_result_runtime,
)
from xinyu_bridge_codex_runtime_delegate_finalization_bindings import (
    codex_foreground_result_response_runtime,
    codex_foreground_result_notes_runtime,
    finalize_codex_foreground_delegate_response_runtime,
    handoff_codex_delegate_to_dream_runtime,
    run_codex_background_delegate_runtime,
    run_codex_foreground_delegate_runtime,
    runtime_codex_delegate_background_runtime,
    settle_codex_delegate_action_experience_runtime,
    stage_codex_report_material_after_delegate_runtime,
)
from xinyu_bridge_codex_runtime_presence_bindings import (
    record_codex_delegate_presence_result_runtime,
    record_codex_delegate_presence_state_runtime,
)
from xinyu_bridge_codex_runtime_wait_chat_bindings import (
    apply_chat_codex_reply_delegates_runtime,
    transition_wait_to_think_reply_runtime,
)
from xinyu_bridge_codex_runtime_execution_bindings import (
    codex_background_scheduled_response_runtime,
    prepare_codex_background_delegate_context_runtime,
    prepare_codex_execute_payload_runtime,
    runtime_codex_execute_runtime,
    schedule_codex_background_delegate_runtime,
    start_codex_foreground_delegate_runtime,
)
from xinyu_bridge_codex_async_followups import (
    codex_async_exploration_result_outbox_payload as _runtime_codex_async_exploration_result_outbox_payload,
    codex_delegate_action_outcome as _runtime_codex_delegate_action_outcome,
    notify_async_exploration_codex_result as _runtime_notify_async_exploration_codex_result,
)
from xinyu_bridge_codex_chat_delegates import (
    ChatCodexReplyDelegateState,
    apply_chat_codex_reply_delegates as _runtime_apply_chat_codex_reply_delegates,
)
from xinyu_bridge_codex_execution import (
    codex_background_scheduled_response as _runtime_codex_background_scheduled_response,
    prepare_codex_background_delegate_context as _runtime_prepare_codex_background_delegate_context,
    prepare_codex_execute_payload as _runtime_prepare_codex_execute_payload,
    runtime_codex_execute as _runtime_codex_execute,
    schedule_codex_background_delegate as _runtime_schedule_codex_background_delegate,
    start_codex_foreground_delegate as _runtime_start_codex_foreground_delegate,
)
from xinyu_bridge_codex_runner import (
    run_codex_background_delegate as _runtime_run_codex_background_delegate,
    run_codex_foreground_delegate as _runtime_run_codex_foreground_delegate,
)
from xinyu_bridge_codex_finalization import (
    codex_foreground_result_notes as _runtime_codex_foreground_result_notes,
    codex_foreground_result_response as _runtime_codex_foreground_result_response,
    finalize_codex_foreground_delegate_response as _runtime_finalize_codex_foreground_delegate_response,
    handoff_codex_delegate_to_dream as _runtime_handoff_codex_delegate_to_dream,
    runtime_codex_delegate_background as _runtime_codex_delegate_background,
    settle_codex_delegate_action_experience as _runtime_settle_codex_delegate_action_experience,
    stage_codex_report_material_after_delegate as _runtime_stage_codex_report_material_after_delegate,
)
from xinyu_bridge_reply_text import normalize_bridge_reply
from xinyu_bridge_trusted_search import trusted_public_search_task_allowed as _trusted_public_search_task_allowed
from xinyu_bridge_values import safe_str
from xinyu_bridge_learning import stage_codex_report_material
from xinyu_bridge_memory_snapshot import memory_snapshot
from xinyu_codex_delegate import looks_like_codex_request, preview_codex_delegate_paths, run_codex_delegate
from xinyu_codex_dream_handoff import handoff_codex_to_dream
from xinyu_codex_service import codex_completion_outbox_message as _codex_completion_outbox_message
from xinyu_codex_service import codex_completion_summary as _codex_completion_summary
from xinyu_codex_service import codex_generated_image_artifacts as _codex_generated_image_artifacts
from xinyu_codex_service import codex_owner_task_text
from xinyu_codex_service import codex_reply_variant
from xinyu_codex_service import codex_started_reply
from xinyu_codex_service import codex_status_reply
from xinyu_codex_service import codex_task_subject
from xinyu_codex_service import enqueue_codex_completion_if_needed as _enqueue_codex_completion_if_needed
from xinyu_codex_service import looks_like_codex_image_generation_task
from xinyu_qq_outbox import enqueue_qq_outbox_message
from xinyu_runtime_presence import record_codex_presence
from xinyu_self_code_approval import mark_self_code_execution_scheduled
from xinyu_self_code_watchdog import create_self_code_snapshot
from xinyu_visible_persona_voice import compose_codex_chat_scheduled_reply, compose_watchdog_visible_message


CODEX_DEFAULT_TIMEOUT_SECONDS = 3600
CODEX_VISIBLE_WINDOW_TITLE = "Xinyu codex"
CODEX_AMBIGUOUS_REQUEST_MESSAGE = "这句还不像一个明确的 Codex 任务，我先不启动。你把要查或要做的主题说完整一点。"

def _deps() -> dict[str, Any]:
    return globals()

def trusted_public_search_task_allowed(task_text: str) -> bool:
    return _trusted_public_search_task_allowed(task_text)

def prepare_self_code_watchdog_payload(runtime: Any, payload: dict[str, Any], *, approval_id: str) -> dict[str, Any]:
    return _prepare_self_code_watchdog_payload(
        runtime,
        payload,
        approval_id=approval_id,
        snapshot_func=create_self_code_snapshot,
    )


def record_codex_delegate_presence_state(
    xinyu_dir: Path,
    payload: dict[str, Any],
    *,
    presence_paths: dict[str, Any],
    status: str,
    window_title: str = CODEX_VISIBLE_WINDOW_TITLE,
) -> None:
    record_codex_delegate_presence_state_runtime(locals(), _deps())


def record_codex_delegate_presence_result(
    xinyu_dir: Path,
    payload: dict[str, Any],
    *,
    result: Any,
    presence_paths: dict[str, Any],
    window_title: str = CODEX_VISIBLE_WINDOW_TITLE,
) -> None:
    record_codex_delegate_presence_result_runtime(locals(), _deps())


def codex_delegate_action_outcome(result: Any, *, summary: str) -> dict[str, Any]:
    return codex_delegate_action_outcome_runtime(result, summary=summary, deps=_deps())


def codex_async_exploration_result_outbox_payload(
    update: dict[str, Any],
    *,
    resume_id: str,
    owner_intervention: str = "",
    has_error: bool = False,
) -> dict[str, Any]:
    return codex_async_exploration_result_outbox_payload_runtime(locals(), _deps())


def notify_async_exploration_codex_result(
    runtime: Any,
    payload: dict[str, Any],
    *,
    async_resume_id: str,
    owner_intervention: str = "",
    result: Any | None = None,
    error: str = "",
) -> None:
    notify_async_exploration_codex_result_runtime(locals(), _deps())


async def transition_wait_to_think_reply(
    runtime: Any,
    payload: dict[str, Any],
    *,
    user_text: str,
    draft_reply: str,
    wait_task: str,
    session_key: str,
) -> tuple[str, dict[str, Any]]:
    return await transition_wait_to_think_reply_runtime(locals(), _deps())


async def apply_chat_codex_reply_delegates(
    runtime: Any,
    session: Any,
    payload: dict[str, Any],
    *,
    user_text: str,
    draft_reply: str,
    session_key: str,
    self_code_task: str,
    model_codex_task: str,
    wait_to_think_task: str,
) -> ChatCodexReplyDelegateState:
    return await apply_chat_codex_reply_delegates_runtime(locals(), _deps())


async def runtime_codex_delegate_background(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    auto_study: bool,
) -> None:
    await runtime_codex_delegate_background_runtime(locals(), _deps())


def codex_background_scheduled_response(
    paths: dict[str, Any],
    *,
    reply: str,
    auto_study: bool,
    cleanup: dict[str, Any],
    session_count: int,
) -> dict[str, Any]:
    return codex_background_scheduled_response_runtime(locals(), _deps())


async def schedule_codex_background_delegate(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    auto_study: bool,
) -> dict[str, Any]:
    return await schedule_codex_background_delegate_runtime(locals(), _deps())


async def start_codex_foreground_delegate(runtime: Any, payload: dict[str, Any]) -> dict[str, Any]:
    return await start_codex_foreground_delegate_runtime(locals(), _deps())


def prepare_codex_background_delegate_context(
    runtime: Any,
    payload: dict[str, Any],
    *,
    started_at: str | None = None,
) -> dict[str, Any]:
    return prepare_codex_background_delegate_context_runtime(locals(), _deps())


def prepare_codex_execute_payload(
    payload: dict[str, Any],
    *,
    text: str,
    should_auto_study: Callable[[str], bool],
    observed_at: datetime | None = None,
    timeout_seconds: int = CODEX_DEFAULT_TIMEOUT_SECONDS,
    window_title: str = CODEX_VISIBLE_WINDOW_TITLE,
) -> dict[str, bool]:
    return prepare_codex_execute_payload_runtime(locals(), _deps())


async def runtime_codex_execute(
    runtime: Any,
    payload: dict[str, Any] | None = None,
    *,
    should_auto_study: Callable[[str], bool] = should_run_learning_after_codex,
) -> dict[str, Any]:
    return await runtime_codex_execute_runtime(locals(), _deps())


def codex_foreground_result_response(
    result: Any,
    *,
    reply: str,
    memory_changed: bool,
    session_count: int,
    gate: dict[str, object],
    learner: dict[str, object],
    quality: dict[str, object],
    integrated: int,
    ready: int,
    blocked_unreadable: int,
    quality_grade: str,
    notes: list[str],
) -> dict[str, Any]:
    return codex_foreground_result_response_runtime(locals(), _deps())

async def run_codex_foreground_delegate(
    runtime: Any,
    payload: dict[str, Any],
    *,
    presence_paths: dict[str, Any],
) -> dict[str, Any]:
    return await run_codex_foreground_delegate_runtime(
        runtime,
        payload,
        presence_paths=presence_paths,
        deps=_deps(),
    )


async def run_codex_background_delegate(runtime: Any, payload: dict[str, Any]) -> Any:
    return await run_codex_background_delegate_runtime(
        runtime,
        payload,
        deps=_deps(),
    )


async def stage_codex_report_material_after_delegate(
    runtime: Any,
    *,
    result: Any,
    text: str,
    job_id: str,
    auto_study: bool,
    followup_task_name: str | None = None,
) -> dict[str, Any]:
    return await stage_codex_report_material_after_delegate_runtime(
        runtime,
        result=result,
        text=text,
        job_id=job_id,
        auto_study=auto_study,
        followup_task_name=followup_task_name,
        deps=_deps(),
    )


async def handoff_codex_delegate_to_dream(
    runtime: Any,
    *,
    result: Any,
    text: str,
    use_global_turn_lock: bool = False,
    contain_errors: bool = False,
) -> dict[str, Any]:
    return await handoff_codex_delegate_to_dream_runtime(
        runtime,
        result=result,
        text=text,
        use_global_turn_lock=use_global_turn_lock,
        contain_errors=contain_errors,
        deps=_deps(),
    )


async def settle_codex_delegate_action_experience(
    runtime: Any,
    payload: dict[str, Any],
    *,
    metadata: dict[str, Any],
    result: Any,
) -> list[str]:
    return await settle_codex_delegate_action_experience_runtime(
        runtime,
        payload,
        metadata=metadata,
        result=result,
        deps=_deps(),
    )


def codex_foreground_result_notes(
    result: Any,
    *,
    report_material_id: str,
    report_material_notes: list[str],
    handoff_notes: list[str],
    handoff_error_note: str,
    auto_study: bool,
    cleanup: dict[str, Any],
) -> list[str]:
    return codex_foreground_result_notes_runtime(
        result,
        report_material_id=report_material_id,
        report_material_notes=report_material_notes,
        handoff_notes=handoff_notes,
        handoff_error_note=handoff_error_note,
        auto_study=auto_study,
        cleanup=cleanup,
        deps=_deps(),
    )


async def finalize_codex_foreground_delegate_response(
    runtime: Any,
    payload: dict[str, Any],
    *,
    result: Any,
    text: str,
    auto_study: bool,
    cleanup: dict[str, Any],
    before_memory: Any,
    after_memory: Any,
    presence_paths: dict[str, Any],
) -> dict[str, Any]:
    return await finalize_codex_foreground_delegate_response_runtime(
        runtime,
        payload,
        result=result,
        text=text,
        auto_study=auto_study,
        cleanup=cleanup,
        before_memory=before_memory,
        after_memory=after_memory,
        presence_paths=presence_paths,
        deps=_deps(),
    )


def codex_completion_summary(runtime: Any, result: Any, *, limit: int = 220) -> str:
    return codex_completion_summary_runtime(
        runtime,
        result,
        limit=limit,
        deps=_deps(),
    )


def codex_completion_outbox_message(
    runtime: Any,
    result: Any,
    *,
    text: str,
    auto_study: bool,
    handoff_notes: list[str],
) -> str:
    return codex_completion_outbox_message_runtime(
        runtime,
        result,
        text=text,
        auto_study=auto_study,
        handoff_notes=handoff_notes,
        deps=_deps(),
    )


def enqueue_codex_completion_if_needed(
    runtime: Any,
    payload: dict[str, Any],
    *,
    result: Any | None,
    text: str,
    auto_study: bool,
    handoff_notes: list[str],
    error: str = "",
) -> None:
    enqueue_codex_completion_if_needed_runtime(
        runtime,
        payload,
        result=result,
        text=text,
        auto_study=auto_study,
        handoff_notes=handoff_notes,
        error=error,
        deps=_deps(),
    )


def codex_generated_image_artifacts(
    runtime: Any,
    result: Any | None,
    *,
    task_text: str,
    limit: int = 3,
) -> list[Path]:
    return codex_generated_image_artifacts_runtime(
        runtime,
        result,
        task_text=task_text,
        limit=limit,
        deps=_deps(),
    )


def install_runtime_codex_aliases(runtime_cls: type[Any]) -> type[Any]:
    from xinyu_bridge_runtime_codex_aliases import install_runtime_codex_aliases as install

    return install(runtime_cls)

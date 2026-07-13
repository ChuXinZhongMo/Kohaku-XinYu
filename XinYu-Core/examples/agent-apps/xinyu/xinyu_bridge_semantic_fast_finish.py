from __future__ import annotations

import time
from typing import Any

from xinyu_bridge_reply_text import normalize_bridge_reply
from xinyu_bridge_semantic_fast_finish_core import finish_owner_private_semantic_fast_turn_impl as _finish_impl
from xinyu_bridge_semantic_fast_finish_core import prepare_semantic_fast_visible_reply as _prepare_visible_reply_impl
from xinyu_bridge_semantic_fast_finish_core import publish_semantic_fast_finish_result as _publish_result_impl
from xinyu_bridge_semantic_fast_notes import append_post_reply_observation_notes as _append_notes_impl
from xinyu_bridge_semantic_fast_notes import build_semantic_fast_notes as _build_notes_impl
from xinyu_bridge_semantic_fast_notes import semantic_fast_memory_changed as _memory_changed_impl
from xinyu_bridge_semantic_fast_publish import publish_semantic_fast_success_turn
from xinyu_bridge_semantic_fast_response import build_semantic_fast_response
from xinyu_bridge_semantic_fast_tail import update_semantic_fast_session_tail
from xinyu_post_reply_self_observation import observe_post_reply_self_observation
from xinyu_turn_route_trace import record_turn_route_stage
from xinyu_visible_reply_guard import dedupe_visible_reply


async def finish_owner_private_semantic_fast_turn(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    session: Any | None,
    session_key: str,
    turn_id: str,
    turn_started_wall: str,
    turn_started_at: float,
    semantic_started_at: float,
    before_memory: dict[str, Any] | None,
    cleanup: dict[str, Any],
    event_sidecar: dict[str, Any],
    decision: dict[str, Any],
    rendered_reply: str,
    renderer_name: str,
    safe_str_func: Any,
    timestamp_func: Any,
) -> dict[str, Any] | None:
    finish_kwargs = dict(locals())
    finish_kwargs.pop("runtime")
    finish_kwargs.pop("payload")
    return await _finish_impl(
        runtime,
        payload,
        **finish_kwargs,
        clock_func=time.perf_counter,
        visible_reply_func=_prepare_semantic_fast_visible_reply,
        update_tail_func=_update_semantic_fast_session_tail,
        build_notes_func=_build_semantic_fast_notes,
        memory_changed_func=_semantic_fast_memory_changed,
        publish_result_func=_publish_semantic_fast_finish_result,
    )


def _prepare_semantic_fast_visible_reply(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    rendered_reply: str,
) -> tuple[str, Any, Any] | None:
    return _prepare_visible_reply_impl(
        runtime,
        payload,
        text=text,
        rendered_reply=rendered_reply,
        normalize_reply_func=normalize_bridge_reply,
        dedupe_visible_reply_func=dedupe_visible_reply,
    )


def _update_semantic_fast_session_tail(
    *args: Any,
    **kwargs: Any,
) -> None:
    return update_semantic_fast_session_tail(*args, **kwargs)


def _build_semantic_fast_notes(
    *args: Any,
    **kwargs: Any,
) -> list[str]:
    kwargs["append_post_reply_observation_notes_func"] = _append_post_reply_observation_notes
    return _build_notes_impl(*args, **kwargs)


def _append_post_reply_observation_notes(
    *args: Any,
    **kwargs: Any,
) -> None:
    kwargs["observe_post_reply_func"] = observe_post_reply_self_observation
    return _append_notes_impl(*args, **kwargs)


def _semantic_fast_memory_changed(runtime: Any, before_memory: dict[str, Any] | None, notes: list[str]) -> bool:
    return _memory_changed_impl(runtime, before_memory, notes)


async def _publish_semantic_fast_finish_result(
    *args: Any,
    **kwargs: Any,
) -> dict[str, Any]:
    kwargs["publish_success_func"] = publish_semantic_fast_success_turn
    kwargs["response_func"] = _semantic_fast_response
    kwargs["record_route_stage_func"] = record_turn_route_stage
    return await _publish_result_impl(*args, **kwargs)


def _semantic_fast_response(
    *args: Any,
    **kwargs: Any,
) -> dict[str, Any]:
    return build_semantic_fast_response(*args, **kwargs)

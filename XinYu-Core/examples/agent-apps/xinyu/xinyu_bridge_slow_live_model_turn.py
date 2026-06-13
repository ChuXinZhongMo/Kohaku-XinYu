from __future__ import annotations

from collections.abc import Callable
from typing import Any

from xinyu_bridge_slow_live_state import SlowLiveModelTurnState


TraceRouteStage = Callable[..., Any]


async def run_slow_live_model_turn_with_failure_publish(
    runtime: Any,
    payload: dict[str, Any],
    *,
    session: Any,
    text: str,
    session_key: str,
    turn_id: str,
    llm_failover_turn_id: str,
    turn_started_wall: str,
    turn_started_at: float,
    turn_event_timestamp: int,
    evaluated_at: str,
    curiosity_eval: dict[str, Any],
    trace_route_stage: TraceRouteStage,
    persona_observer_func: Callable[..., dict[str, Any]],
    visible_turn_classifier_func: Callable[..., Any],
    memory_recall_func: Callable[..., Any],
    model_contexts_func: Callable[..., Any],
    model_event_inject_func: Callable[..., Any],
    failure_publish_func: Callable[..., Any],
    safe_str_func: Callable[..., str],
    request_error_cls: type[Exception],
    gateway_timeout_status: Any,
) -> SlowLiveModelTurnState:
    persona_sidecar = persona_observer_func(runtime, payload, text=text)
    session.chunks.clear()
    event = runtime._create_user_input_event(
        text,
        source="qq_gateway",
        bridge_payload=payload,
        platform=safe_str_func(payload.get("platform"), "qq"),
        message_type=safe_str_func(payload.get("message_type")),
        session_id=session_key,
        user_id=safe_str_func(payload.get("user_id")),
        sender_name=safe_str_func(payload.get("sender_name")),
        received_at=turn_event_timestamp,
        llm_failover=runtime._owner_private_llm_failover_context(
            payload,
            text=text,
            session_key=session_key,
            turn_id=llm_failover_turn_id,
        ),
    )
    visible_turn = visible_turn_classifier_func(runtime.xinyu_dir, payload=payload, user_text=text)
    memory_recall = await memory_recall_func(
        runtime,
        payload,
        user_text=text,
        session=session,
        session_key=session_key,
        turn_id=turn_id,
        visible_turn=visible_turn,
        evaluated_at=evaluated_at,
        trace_route_stage=trace_route_stage,
    )
    recalled_context = memory_recall.recalled_context
    recalled_context_event = memory_recall.recalled_context_event
    recalled_context_notes = memory_recall.recalled_context_notes

    model_contexts = await model_contexts_func(
        runtime,
        payload,
        user_text=text,
        visible_turn=visible_turn,
        recalled_context=recalled_context,
        evaluated_at=evaluated_at,
    )
    try:
        await model_event_inject_func(
            runtime,
            payload=payload,
            session=session,
            event=event,
            text=text,
            turn_id=turn_id,
            visible_turn=visible_turn,
            persona_sidecar=persona_sidecar,
            curiosity_eval=curiosity_eval,
            recalled_context=recalled_context,
            runtime_presence_context=model_contexts.runtime_presence_context,
            life_reply_policy=model_contexts.life_reply_policy,
            emotion_council_context=model_contexts.emotion_council_context,
            trace_route_stage=trace_route_stage,
        )
    except TimeoutError as exc:
        await failure_publish_func(
            runtime,
            payload,
            session=session,
            text=text,
            session_key=session_key,
            turn_id=turn_id,
            turn_started_wall=turn_started_wall,
            turn_started_at=turn_started_at,
            status="timeout",
            notes=["turn_timeout"],
            recalled_context_event=recalled_context_event,
            recalled_context=recalled_context,
        )
        raise request_error_cls(
            gateway_timeout_status,
            f"XinYu turn timed out after {runtime.turn_timeout_seconds} seconds",
        ) from exc
    except Exception as exc:
        await failure_publish_func(
            runtime,
            payload,
            session=session,
            text=text,
            session_key=session_key,
            turn_id=turn_id,
            turn_started_wall=turn_started_wall,
            turn_started_at=turn_started_at,
            status="error",
            notes=[f"turn_error:{type(exc).__name__}"],
            recalled_context_event=recalled_context_event,
            recalled_context=recalled_context,
        )
        raise

    return SlowLiveModelTurnState(
        visible_turn=visible_turn,
        recalled_context=recalled_context,
        recalled_context_event=recalled_context_event,
        recalled_context_notes=recalled_context_notes,
        continuity_handoff=model_contexts.continuity_handoff,
        runtime_presence_context=model_contexts.runtime_presence_context,
        life_reply_policy=model_contexts.life_reply_policy,
        emotion_council_context=model_contexts.emotion_council_context,
        persona_sidecar=persona_sidecar,
    )

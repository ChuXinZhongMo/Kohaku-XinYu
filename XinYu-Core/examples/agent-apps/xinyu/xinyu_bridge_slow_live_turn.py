from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from xinyu_bridge_values import safe_str as _safe_str
from xinyu_continuity_handoff import build_continuity_handoff_prompt_block, refresh_continuity_handoff
from xinyu_life_reply_policy import build_life_reply_prompt_block
from xinyu_living_memory_recall import run_living_memory_recall_algorithm
from xinyu_emotion_council import build_emotion_council_prompt_block
from xinyu_early_visible_segment import observe_early_visible_segment_shadow
from xinyu_runtime_presence import build_runtime_presence_prompt_block
from xinyu_uncertainty_pause import build_uncertainty_pause_prompt_block


TraceRouteStage = Callable[..., Any]
MemoryRecallRunner = Callable[..., Any]
FinishSidecarsRunner = Callable[..., Any]
EMPTY_VISIBLE_RETRY_TIMEOUT_SECONDS = 45


@dataclass
class SlowLiveMemoryRecallResult:
    recalled_context: Any = None
    recalled_context_event: dict[str, Any] = field(default_factory=dict)
    recalled_context_notes: list[str] = field(default_factory=list)


@dataclass
class SlowLiveModelContexts:
    continuity_handoff: dict[str, Any]
    runtime_presence_context: str
    life_reply_policy: dict[str, Any]
    emotion_council_context: str


def _int_or_zero(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _session_output_notes(session: Any) -> list[str]:
    chunks = getattr(session, "chunks", None)
    if isinstance(chunks, list):
        chunk_count = len(chunks)
        visible_chars = sum(len(_safe_str(chunk)) for chunk in chunks)
    else:
        chunk_count = 0
        visible_chars = 0

    agent = getattr(session, "agent", None)
    controller = getattr(agent, "controller", None)
    raw_assistant = _safe_str(getattr(controller, "_last_assistant_content", ""))
    llm = getattr(agent, "llm", None)
    try:
        usage = getattr(llm, "last_usage", {}) if llm is not None else {}
    except Exception:
        usage = {}
    if not isinstance(usage, dict):
        usage = {}
    try:
        tool_calls = getattr(llm, "last_tool_calls", []) if llm is not None else []
    except Exception:
        tool_calls = []
    try:
        tool_call_count = len(tool_calls or [])
    except TypeError:
        tool_call_count = 0

    notes = [
        f"chunk_count:{chunk_count}",
        f"visible_chars:{visible_chars}",
        f"raw_assistant_chars:{len(raw_assistant)}",
        f"completion_tokens:{_int_or_zero(usage.get('completion_tokens'))}",
        f"tool_call_count:{tool_call_count}",
    ]
    if visible_chars <= 0:
        if raw_assistant:
            notes.append("empty_visible_parser_or_action_output")
        elif _int_or_zero(usage.get("completion_tokens")) <= 0:
            notes.append("empty_completion_no_visible_tokens")
        else:
            notes.append("empty_visible_model_or_provider_output")
    return notes


def _has_visible_chunks(session: Any) -> bool:
    chunks = getattr(session, "chunks", None)
    if not isinstance(chunks, list):
        return False
    return bool("".join(_safe_str(chunk) for chunk in chunks).strip())


def _owner_private_payload_matches(runtime: Any, payload: dict[str, Any]) -> bool:
    matcher = getattr(runtime, "_owner_private_payload_matches", None)
    if not callable(matcher):
        return False
    try:
        return bool(matcher(payload))
    except Exception:
        return False


def _create_empty_visible_retry_event(
    runtime: Any,
    *,
    payload: dict[str, Any],
    text: str,
    turn_id: str,
    session_key: str,
) -> Any:
    factory = getattr(runtime, "_create_user_input_event", None)
    if not callable(factory):
        return None
    retry_prompt = "\n".join(
        [
            "[internal visible-reply recovery]",
            "The previous model turn returned no visible text.",
            "Reply now to the immediately previous owner QQ private message.",
            "Produce a concise visible Chinese private-chat reply.",
            (
                "Do not call tools, do not output tool blocks, and do not mention this "
                "recovery, model output, logs, memory, or system mechanics."
            ),
            (
                "If the owner explicitly asked XinYu to wait or stay silent, return "
                "exactly [WAITING]. Otherwise do not stay silent."
            ),
        ]
    )
    return factory(
        retry_prompt,
        source="qq_gateway_empty_visible_retry",
        bridge_payload=payload,
        platform=_safe_str(payload.get("platform"), "qq"),
        message_type=_safe_str(payload.get("message_type")),
        session_id=session_key,
        user_id=_safe_str(payload.get("user_id")),
        received_at=_safe_str(payload.get("received_at") or payload.get("time") or ""),
        turn_id=turn_id,
        recovery_for="empty_visible_reply",
        original_text_len=len(_safe_str(text)),
    )


async def run_slow_live_memory_recall(
    runtime: Any,
    payload: dict[str, Any],
    *,
    user_text: str,
    session: Any,
    session_key: str,
    turn_id: str,
    visible_turn: Any,
    evaluated_at: str,
    trace_route_stage: TraceRouteStage,
    recall_runner: MemoryRecallRunner | None = None,
) -> SlowLiveMemoryRecallResult:
    recalled_context = None
    recalled_context_event: dict[str, Any] = {}
    recalled_context_notes: list[str] = []
    recall_runner = recall_runner or run_living_memory_recall_algorithm
    try:
        trace_route_stage("memory_recall_started", route="slow_live")
        recalled_algorithm = recall_runner(
            runtime.xinyu_dir,
            payload,
            user_text=user_text,
            dialogue_tail=session.dialogue_tail,
            visible_turn=visible_turn,
            evaluated_at=evaluated_at,
        )
        recalled_context = recalled_algorithm.result
        recalled_context_notes.extend(_safe_str(note) for note in recalled_algorithm.notes[:2])
        recalled_context_notes.extend(_safe_str(note) for note in recalled_context.notes[:3])
        recalled_context_event = await runtime._desktop_publish_memory_recall(
            payload,
            recalled_context,
            session_key=session_key,
            turn_id=turn_id,
        )
        trace_route_stage(
            "memory_recall_finished",
            route="slow_live",
            status="ok",
            notes=recalled_context_notes[:4],
        )
    except TimeoutError as exc:
        print(f"[xinyu_core_bridge] context retrieval timed out: {exc}", flush=True)
        timeout_note = f"context_retrieval_timeout:{type(exc).__name__}"
        recalled_context_notes.append(timeout_note)
        trace_route_stage(
            "memory_recall_timeout",
            route="slow_live",
            status="timeout",
            notes=[timeout_note],
        )
    except Exception as exc:
        print(f"[xinyu_core_bridge] context retrieval failed: {exc}", flush=True)
        error_note = f"context_retrieval_error:{type(exc).__name__}"
        recalled_context_notes.append(error_note)
        trace_route_stage(
            "memory_recall_error",
            route="slow_live",
            status="error",
            notes=[error_note],
        )
    return SlowLiveMemoryRecallResult(
        recalled_context=recalled_context,
        recalled_context_event=recalled_context_event,
        recalled_context_notes=recalled_context_notes,
    )


async def build_slow_live_model_contexts(
    runtime: Any,
    payload: dict[str, Any],
    *,
    user_text: str,
    visible_turn: Any,
    recalled_context: Any,
    evaluated_at: str,
) -> SlowLiveModelContexts:
    del payload
    continuity_handoff: dict[str, Any] = {"notes": []}
    try:
        continuity_handoff = refresh_continuity_handoff(
            runtime.xinyu_dir,
            user_text=user_text,
            observed_at=datetime.now().astimezone().isoformat(),
        )
    except Exception as exc:
        print(f"[xinyu_core_bridge] continuity handoff failed: {exc}", flush=True)
        continuity_handoff = {"notes": [f"continuity_handoff_error:{type(exc).__name__}"]}
    runtime_presence_context = build_runtime_presence_prompt_block(runtime.xinyu_dir, limit=2200)
    life_reply_policy = await runtime._build_life_reply_policy(
        user_text=user_text,
        visible_turn=visible_turn,
        canonical_recall_context=_safe_str(getattr(recalled_context, "prompt_block", "")),
        evaluated_at=evaluated_at,
    )
    emotion_council_context = ""
    if runtime.emotion_council_prompt_enabled:
        emotion_council_context = build_emotion_council_prompt_block(runtime.xinyu_dir)
    return SlowLiveModelContexts(
        continuity_handoff=continuity_handoff,
        runtime_presence_context=runtime_presence_context,
        life_reply_policy=life_reply_policy,
        emotion_council_context=emotion_council_context,
    )


async def inject_slow_live_model_event(
    runtime: Any,
    payload: dict[str, Any],
    *,
    session: Any,
    event: Any,
    text: str,
    turn_id: str,
    visible_turn: Any,
    persona_sidecar: dict[str, Any],
    curiosity_eval: dict[str, Any],
    recalled_context: Any,
    runtime_presence_context: str,
    life_reply_policy: dict[str, Any],
    emotion_council_context: str,
    trace_route_stage: TraceRouteStage,
) -> None:
    stop_early_shadow = asyncio.Event()
    loop = asyncio.get_running_loop()
    early_shadow_task: asyncio.Task[Any] | None = None
    session_chunks = getattr(session, "chunks", None)
    if isinstance(session_chunks, list):
        early_shadow_task = asyncio.create_task(
            observe_early_visible_segment_shadow(
                runtime.xinyu_dir,
                session_chunks,
                payload=payload,
                user_text=text,
                turn_id=turn_id,
                session_key=_safe_str(getattr(session, "key", "")),
                visible_turn=visible_turn,
                started_monotonic=loop.time(),
                stop_event=stop_early_shadow,
            ),
            name=f"xinyu-early-visible-segment-shadow-{turn_id or 'turn'}",
        )
    try:
        trace_route_stage("model_inject_started", route="slow_live")
        runtime._inject_live_turn_context(
            session.agent,
            payload=payload,
            text=text,
            dialogue_tail=session.dialogue_tail,
            turn_id=turn_id,
            persona_context=_safe_str(persona_sidecar.get("prompt_block")),
            curiosity_context=_safe_str(curiosity_eval.get("prompt_block")),
            visible_turn=visible_turn,
            recalled_context=_safe_str(getattr(recalled_context, "prompt_block", "")),
            runtime_presence_context=runtime_presence_context,
            continuity_context=build_continuity_handoff_prompt_block(runtime.xinyu_dir, user_text=text),
            uncertainty_pause_context=build_uncertainty_pause_prompt_block(runtime.xinyu_dir),
            life_reply_context=build_life_reply_prompt_block(life_reply_policy),
            emotion_council_context=emotion_council_context,
        )
        await asyncio.wait_for(
            session.agent.inject_event(event),
            timeout=runtime.turn_timeout_seconds,
        )
        output_notes = _session_output_notes(session)
        if (
            not _has_visible_chunks(session)
            and _owner_private_payload_matches(runtime, payload)
        ):
            trace_route_stage(
                "model_inject_empty_visible",
                route="slow_live",
                status="empty",
                notes=output_notes,
            )
            retry_event = _create_empty_visible_retry_event(
                runtime,
                payload=payload,
                text=text,
                turn_id=turn_id,
                session_key=_safe_str(getattr(session, "key", "")),
            )
            if retry_event is None:
                output_notes = output_notes + ["empty_visible_retry_unavailable"]
            else:
                retry_timeout = min(
                    EMPTY_VISIBLE_RETRY_TIMEOUT_SECONDS,
                    max(1, _int_or_zero(getattr(runtime, "turn_timeout_seconds", 1))),
                )
                trace_route_stage(
                    "model_inject_empty_visible_retry_started",
                    route="slow_live",
                    status="running",
                    notes=[f"timeout_seconds:{retry_timeout}"],
                )
                await asyncio.wait_for(
                    session.agent.inject_event(retry_event),
                    timeout=retry_timeout,
                )
                retry_notes = _session_output_notes(session)
                if _has_visible_chunks(session):
                    trace_route_stage(
                        "model_inject_empty_visible_retry_finished",
                        route="slow_live",
                        status="ok",
                        notes=retry_notes,
                    )
                    output_notes = retry_notes + ["empty_visible_retry_recovered"]
                else:
                    trace_route_stage(
                        "model_inject_empty_visible_retry_finished",
                        route="slow_live",
                        status="empty",
                        notes=retry_notes,
                    )
                    output_notes = retry_notes + ["empty_visible_retry_failed"]
        trace_route_stage(
            "model_inject_finished",
            route="slow_live",
            status="ok",
            notes=output_notes,
        )
    except TimeoutError:
        trace_route_stage(
            "model_inject_timeout",
            route="slow_live",
            status="timeout",
            notes=["turn_timeout"],
        )
        raise
    except Exception as exc:
        trace_route_stage(
            "model_inject_error",
            route="slow_live",
            status="error",
            notes=[f"turn_error:{type(exc).__name__}"],
        )
        raise
    finally:
        stop_early_shadow.set()
        if early_shadow_task is not None:
            with contextlib.suppress(Exception):
                await asyncio.wait_for(early_shadow_task, timeout=1)


async def run_slow_live_finish_sidecars_with_trace(
    runtime: Any,
    *,
    sidecars_runner: FinishSidecarsRunner,
    trace_route_stage: TraceRouteStage,
    **kwargs: Any,
) -> dict[str, Any]:
    try:
        trace_route_stage("finish_sidecars_started", route="slow_live")
        finish_sidecars = await sidecars_runner(runtime, **kwargs)
        trace_route_stage("finish_sidecars_finished", route="slow_live", status="ok")
        return finish_sidecars
    except TimeoutError:
        trace_route_stage(
            "finish_sidecars_timeout",
            route="slow_live",
            status="timeout",
            notes=["finish_sidecars_timeout"],
        )
        raise
    except Exception as exc:
        trace_route_stage(
            "finish_sidecars_error",
            route="slow_live",
            status="error",
            notes=[f"finish_sidecars_error:{type(exc).__name__}"],
        )
        raise

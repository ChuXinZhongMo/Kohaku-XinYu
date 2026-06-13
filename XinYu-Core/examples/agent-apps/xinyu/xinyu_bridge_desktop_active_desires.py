from __future__ import annotations

from typing import Any, Awaitable, Callable


async def desktop_active_desires(
    runtime: Any,
    *,
    environment: dict[str, Any],
    entropy_state: Any,
    proactive_items: list[Any],
    recent_turns: list[Any],
    recent_memory_events: list[Any],
    self_choice_state: dict[str, Any] | None,
    evaluate_life_kernel_func: Callable[..., Any],
    create_metabolism_ticket_func: Callable[..., dict[str, Any]],
    to_thread_func: Callable[..., Awaitable[Any]],
    safe_str_func: Callable[..., str],
) -> list[dict[str, Any]]:
    desire = evaluate_life_kernel_func(
        environment=environment,
        proactive_items=proactive_items,
        recent_turns=recent_turns,
        recent_memory_events=recent_memory_events,
        entropy_state=entropy_state,
        self_choice_state=self_choice_state,
    )
    if desire is None:
        return []
    desire_data = desire.model_dump(mode="json")
    await runtime.self_choice_store.record_life_choice(desire.chosen_action)
    if desire.chosen_action == "request_metabolism_window":
        ticket = await to_thread_func(runtime._desktop_open_metabolism_ticket)
        if not ticket:
            self_choice_dream_bias = await runtime.self_choice_store.dream_bias_snapshot()
            ticket_result = await to_thread_func(
                create_metabolism_ticket_func,
                runtime.xinyu_dir,
                entropy_state=entropy_state.model_dump(mode="json") if hasattr(entropy_state, "model_dump") else {},
                resource_request=desire_data.get("entropy", {}).get("resource_request")
                if isinstance(desire_data.get("entropy"), dict)
                else None,
                active_desire=desire_data,
                input_window=runtime._metabolism_input_window(
                    proactive_items=proactive_items,
                    recent_turns=recent_turns,
                    recent_memory_events=recent_memory_events,
                    self_choice_dream_bias=self_choice_dream_bias,
                ),
            )
            ticket = ticket_result.get("ticket") if isinstance(ticket_result.get("ticket"), dict) else {}
        desire_data["metabolism_ticket_id"] = safe_str_func(ticket.get("ticket_id"))
        desire_data["metabolism_ticket_status"] = safe_str_func(ticket.get("status"), "requested")
        desire_data["metabolism_ticket"] = ticket
    return [desire_data]

from __future__ import annotations

from typing import Any, Callable


def desktop_open_metabolism_ticket(
    runtime: Any,
    *,
    list_tickets_func: Callable[..., list[dict[str, Any]]],
    select_ticket_func: Callable[[list[dict[str, Any]]], dict[str, Any]],
    open_statuses: set[str],
) -> dict[str, Any]:
    tickets = list_tickets_func(runtime.xinyu_dir, statuses=open_statuses)
    return select_ticket_func(tickets)


async def life_metabolism_ticket_get(
    runtime: Any,
    payload: dict[str, Any],
    *,
    ticket_id_from_payload_func: Callable[..., str],
    get_ticket_func: Callable[..., dict[str, Any]],
    safe_str_func: Callable[..., str],
    to_thread_func: Callable[..., Any],
) -> dict[str, Any]:
    ticket_id = ticket_id_from_payload_func(payload, safe_str=safe_str_func)
    if not ticket_id:
        return {"accepted": False, "ticket": {}, "notes": ["missing_ticket_id"]}
    ticket = await to_thread_func(get_ticket_func, runtime.xinyu_dir, ticket_id)
    return {
        "accepted": bool(ticket),
        "ticket": ticket,
        "notes": ["ticket_found"] if ticket else ["ticket_not_found"],
    }


async def life_metabolism_ticket_list(
    runtime: Any,
    payload: dict[str, Any],
    *,
    statuses_from_payload_func: Callable[..., set[str] | None],
    list_tickets_func: Callable[..., list[dict[str, Any]]],
    safe_str_func: Callable[..., str],
    to_thread_func: Callable[..., Any],
) -> dict[str, Any]:
    statuses = statuses_from_payload_func(payload, safe_str=safe_str_func)
    tickets = await to_thread_func(list_tickets_func, runtime.xinyu_dir, statuses=statuses)
    return {"accepted": True, "tickets": tickets, "notes": ["tickets_listed"]}


async def life_metabolism_ticket_approve(
    runtime: Any,
    payload: dict[str, Any],
    *,
    ticket_id_from_payload_func: Callable[..., str],
    owner_decision_id_from_payload_func: Callable[..., str],
    approved_seconds_from_payload_func: Callable[..., int | None],
    note_from_payload_func: Callable[..., str],
    approve_ticket_func: Callable[..., dict[str, Any]],
    optional_int_func: Callable[..., int | None],
    safe_str_func: Callable[..., str],
    to_thread_func: Callable[..., Any],
    apply_decision_func: Callable[..., Any],
    publish_decision_func: Callable[..., Any],
) -> dict[str, Any]:
    result = await to_thread_func(
        approve_ticket_func,
        runtime.xinyu_dir,
        ticket_id_from_payload_func(payload, safe_str=safe_str_func),
        owner_decision_id=owner_decision_id_from_payload_func(payload, safe_str=safe_str_func),
        approved_seconds=approved_seconds_from_payload_func(payload, optional_int=optional_int_func),
        note=note_from_payload_func(payload, safe_str=safe_str_func),
    )
    await apply_decision_func(runtime, "ticket_approved", result)
    await publish_decision_func(runtime, "approved", result)
    if result.get("accepted"):
        runtime._wake_metabolism_runner()
    return result


async def life_metabolism_ticket_reject(
    runtime: Any,
    payload: dict[str, Any],
    *,
    ticket_id_from_payload_func: Callable[..., str],
    owner_decision_id_from_payload_func: Callable[..., str],
    note_from_payload_func: Callable[..., str],
    reject_ticket_func: Callable[..., dict[str, Any]],
    safe_str_func: Callable[..., str],
    to_thread_func: Callable[..., Any],
    apply_decision_func: Callable[..., Any],
    publish_decision_func: Callable[..., Any],
) -> dict[str, Any]:
    result = await to_thread_func(
        reject_ticket_func,
        runtime.xinyu_dir,
        ticket_id_from_payload_func(payload, safe_str=safe_str_func),
        owner_decision_id=owner_decision_id_from_payload_func(payload, safe_str=safe_str_func),
        note=note_from_payload_func(payload, safe_str=safe_str_func),
    )
    await apply_decision_func(runtime, "ticket_rejected", result)
    await publish_decision_func(runtime, "rejected", result)
    return result


async def life_metabolism_ticket_cancel(
    runtime: Any,
    payload: dict[str, Any],
    *,
    ticket_id_from_payload_func: Callable[..., str],
    cancel_reason_from_payload_func: Callable[..., str],
    cancel_ticket_func: Callable[..., dict[str, Any]],
    safe_str_func: Callable[..., str],
    to_thread_func: Callable[..., Any],
    publish_decision_func: Callable[..., Any],
) -> dict[str, Any]:
    result = await to_thread_func(
        cancel_ticket_func,
        runtime.xinyu_dir,
        ticket_id_from_payload_func(payload, safe_str=safe_str_func),
        reason=cancel_reason_from_payload_func(payload, safe_str=safe_str_func),
    )
    await publish_decision_func(runtime, "cancelled", result)
    return result

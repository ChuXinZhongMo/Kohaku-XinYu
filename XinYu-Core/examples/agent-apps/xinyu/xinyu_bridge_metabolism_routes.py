from __future__ import annotations

import asyncio
import os
from datetime import datetime
from typing import Any

from xinyu_bridge_desktop_projection import desktop_marker_count
from xinyu_bridge_life_metabolism_route_backend import maybe_execute_life_metabolism_backend
from xinyu_bridge_values import optional_int as _optional_int
from xinyu_bridge_values import safe_str as _safe_str
from xinyu_bridge_metabolism_payloads import (
    approved_seconds_from_payload,
    cancel_reason_from_payload,
    metabolism_input_window_payload,
    note_from_payload,
    owner_decision_id_from_payload,
    statuses_from_payload,
    ticket_id_from_payload,
)
from xinyu_bridge_metabolism_publish import (
    apply_self_choice_metabolism_decision as _apply_self_choice_metabolism_decision,
)
from xinyu_bridge_metabolism_publish import publish_metabolism_decision as _publish_metabolism_decision
from xinyu_bridge_metabolism_publish import publish_metabolism_runner_result as _publish_metabolism_runner_result
from xinyu_bridge_metabolism_runner import metabolism_runner_loop as _metabolism_runner_loop
from xinyu_bridge_metabolism_runner import run_due_metabolism_once as _run_due_metabolism_once
from xinyu_bridge_metabolism_runner import wake_metabolism_runner as _wake_metabolism_runner
from xinyu_bridge_metabolism_selection import OPEN_TICKET_STATUSES
from xinyu_bridge_metabolism_selection import select_desktop_metabolism_ticket as _select_desktop_metabolism_ticket
from xinyu_bridge_metabolism_ticket_routes import (
    desktop_open_metabolism_ticket as _desktop_open_metabolism_ticket,
)
from xinyu_bridge_metabolism_ticket_routes import (
    life_metabolism_ticket_approve as _life_metabolism_ticket_approve,
)
from xinyu_bridge_metabolism_ticket_routes import (
    life_metabolism_ticket_cancel as _life_metabolism_ticket_cancel,
)
from xinyu_bridge_metabolism_ticket_routes import (
    life_metabolism_ticket_get as _life_metabolism_ticket_get,
)
from xinyu_bridge_metabolism_ticket_routes import (
    life_metabolism_ticket_list as _life_metabolism_ticket_list,
)
from xinyu_bridge_metabolism_ticket_routes import (
    life_metabolism_ticket_reject as _life_metabolism_ticket_reject,
)
from xinyu_metabolism_contract import (
    approve_ticket as approve_metabolism_ticket,
    cancel_ticket as cancel_metabolism_ticket,
    get_ticket as get_metabolism_ticket,
    list_tickets as list_metabolism_tickets,
    reject_ticket as reject_metabolism_ticket,
    run_due_metabolism_tickets,
)


def _metabolism_now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def select_desktop_metabolism_ticket(tickets: list[dict[str, Any]]) -> dict[str, Any]:
    return _select_desktop_metabolism_ticket(tickets, safe_str=_safe_str)


def desktop_open_metabolism_ticket(runtime: Any) -> dict[str, Any]:
    return _desktop_open_metabolism_ticket(
        runtime,
        list_tickets_func=list_metabolism_tickets,
        select_ticket_func=select_desktop_metabolism_ticket,
        open_statuses=set(OPEN_TICKET_STATUSES),
    )


def metabolism_input_window(
    *,
    proactive_items: list[Any],
    recent_turns: list[Any],
    recent_memory_events: list[Any],
    self_choice_dream_bias: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return metabolism_input_window_payload(
        proactive_items=proactive_items,
        recent_turns=recent_turns,
        recent_memory_events=recent_memory_events,
        marker_count=desktop_marker_count,
        self_choice_dream_bias=self_choice_dream_bias,
    )


async def life_metabolism_ticket_get(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    backend_result = await maybe_execute_life_metabolism_backend(
        runtime,
        payload,
        route="/life/metabolism/tickets/{ticket_id}",
        http_method="GET",
        runtime_method="life_metabolism_ticket_get",
    )
    if backend_result is not None:
        return backend_result
    return await _life_metabolism_ticket_get(
        runtime,
        payload or {},
        ticket_id_from_payload_func=ticket_id_from_payload,
        get_ticket_func=get_metabolism_ticket,
        safe_str_func=_safe_str,
        to_thread_func=asyncio.to_thread,
    )


async def life_metabolism_ticket_list(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    backend_result = await maybe_execute_life_metabolism_backend(
        runtime,
        payload,
        route="/life/metabolism/tickets",
        http_method="GET",
        runtime_method="life_metabolism_ticket_list",
    )
    if backend_result is not None:
        return backend_result
    return await _life_metabolism_ticket_list(
        runtime,
        payload or {},
        statuses_from_payload_func=statuses_from_payload,
        list_tickets_func=list_metabolism_tickets,
        safe_str_func=_safe_str,
        to_thread_func=asyncio.to_thread,
    )


async def life_metabolism_ticket_approve(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    backend_result = await maybe_execute_life_metabolism_backend(
        runtime,
        payload,
        route="/life/metabolism/tickets/{ticket_id}/approve",
        http_method="POST",
        runtime_method="life_metabolism_ticket_approve",
    )
    if backend_result is not None:
        return backend_result
    return await _life_metabolism_ticket_approve(
        runtime,
        payload or {},
        ticket_id_from_payload_func=ticket_id_from_payload,
        owner_decision_id_from_payload_func=owner_decision_id_from_payload,
        approved_seconds_from_payload_func=approved_seconds_from_payload,
        note_from_payload_func=note_from_payload,
        approve_ticket_func=approve_metabolism_ticket,
        optional_int_func=_optional_int,
        safe_str_func=_safe_str,
        to_thread_func=asyncio.to_thread,
        apply_decision_func=apply_self_choice_metabolism_decision,
        publish_decision_func=publish_metabolism_decision,
    )


async def life_metabolism_ticket_reject(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    backend_result = await maybe_execute_life_metabolism_backend(
        runtime,
        payload,
        route="/life/metabolism/tickets/{ticket_id}/reject",
        http_method="POST",
        runtime_method="life_metabolism_ticket_reject",
    )
    if backend_result is not None:
        return backend_result
    return await _life_metabolism_ticket_reject(
        runtime,
        payload or {},
        ticket_id_from_payload_func=ticket_id_from_payload,
        owner_decision_id_from_payload_func=owner_decision_id_from_payload,
        note_from_payload_func=note_from_payload,
        reject_ticket_func=reject_metabolism_ticket,
        safe_str_func=_safe_str,
        to_thread_func=asyncio.to_thread,
        apply_decision_func=apply_self_choice_metabolism_decision,
        publish_decision_func=publish_metabolism_decision,
    )


async def life_metabolism_ticket_cancel(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    backend_result = await maybe_execute_life_metabolism_backend(
        runtime,
        payload,
        route="/life/metabolism/tickets/{ticket_id}/cancel",
        http_method="POST",
        runtime_method="life_metabolism_ticket_cancel",
    )
    if backend_result is not None:
        return backend_result
    return await _life_metabolism_ticket_cancel(
        runtime,
        payload or {},
        ticket_id_from_payload_func=ticket_id_from_payload,
        cancel_reason_from_payload_func=cancel_reason_from_payload,
        cancel_ticket_func=cancel_metabolism_ticket,
        safe_str_func=_safe_str,
        to_thread_func=asyncio.to_thread,
        publish_decision_func=publish_metabolism_decision,
    )


async def apply_self_choice_metabolism_decision(runtime: Any, event: str, result: dict[str, Any]) -> None:
    await _apply_self_choice_metabolism_decision(runtime, event, result)


async def publish_metabolism_decision(runtime: Any, decision: str, result: dict[str, Any]) -> None:
    await _publish_metabolism_decision(runtime, decision, result)


async def publish_metabolism_runner_result(runtime: Any, result: dict[str, Any], *, trigger: str) -> None:
    await _publish_metabolism_runner_result(runtime, result, trigger=trigger, safe_str=_safe_str)


async def run_due_metabolism_once(runtime: Any, *, trigger: str) -> dict[str, Any]:
    return await _run_due_metabolism_once(
        runtime,
        trigger=trigger,
        run_due_tickets=run_due_metabolism_tickets,
        runner_id=f"core_bridge:{os.getpid()}:{trigger}",
        now_iso=_metabolism_now_iso,
        to_thread=asyncio.to_thread,
    )


async def metabolism_runner_loop(runtime: Any) -> None:
    await _metabolism_runner_loop(runtime, event_factory=asyncio.Event, wait_for=asyncio.wait_for)


def wake_metabolism_runner(runtime: Any) -> None:
    _wake_metabolism_runner(runtime)

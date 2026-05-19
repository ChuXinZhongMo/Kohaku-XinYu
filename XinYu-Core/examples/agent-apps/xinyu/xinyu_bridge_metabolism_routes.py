from __future__ import annotations

import asyncio
from typing import Any

from xinyu_bridge_values import optional_int as _optional_int
from xinyu_bridge_values import safe_str as _safe_str
from xinyu_metabolism_contract import (
    approve_ticket as approve_metabolism_ticket,
    cancel_ticket as cancel_metabolism_ticket,
    get_ticket as get_metabolism_ticket,
    list_tickets as list_metabolism_tickets,
    reject_ticket as reject_metabolism_ticket,
)


async def life_metabolism_ticket_get(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    ticket_id = _safe_str(payload.get("ticket_id") or payload.get("id")).strip()
    if not ticket_id:
        return {"accepted": False, "ticket": {}, "notes": ["missing_ticket_id"]}
    ticket = await asyncio.to_thread(get_metabolism_ticket, runtime.xinyu_dir, ticket_id)
    return {
        "accepted": bool(ticket),
        "ticket": ticket,
        "notes": ["ticket_found"] if ticket else ["ticket_not_found"],
    }


async def life_metabolism_ticket_list(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    raw_status = _safe_str(payload.get("status") or payload.get("statuses")).strip()
    statuses = {part.strip() for part in raw_status.split(",") if part.strip()} if raw_status else None
    tickets = await asyncio.to_thread(list_metabolism_tickets, runtime.xinyu_dir, statuses=statuses)
    return {"accepted": True, "tickets": tickets, "notes": ["tickets_listed"]}


async def life_metabolism_ticket_approve(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    ticket_id = _safe_str(payload.get("ticket_id") or payload.get("id")).strip()
    result = await asyncio.to_thread(
        approve_metabolism_ticket,
        runtime.xinyu_dir,
        ticket_id,
        owner_decision_id=_safe_str(payload.get("owner_decision_id") or payload.get("decision_id")).strip(),
        approved_seconds=_optional_int(payload.get("approved_seconds")),
        note=_safe_str(payload.get("note")),
    )
    await apply_self_choice_metabolism_decision(runtime, "ticket_approved", result)
    await publish_metabolism_decision(runtime, "approved", result)
    if result.get("accepted"):
        runtime._wake_metabolism_runner()
    return result


async def life_metabolism_ticket_reject(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    ticket_id = _safe_str(payload.get("ticket_id") or payload.get("id")).strip()
    result = await asyncio.to_thread(
        reject_metabolism_ticket,
        runtime.xinyu_dir,
        ticket_id,
        owner_decision_id=_safe_str(payload.get("owner_decision_id") or payload.get("decision_id")).strip(),
        note=_safe_str(payload.get("note")),
    )
    await apply_self_choice_metabolism_decision(runtime, "ticket_rejected", result)
    await publish_metabolism_decision(runtime, "rejected", result)
    return result


async def life_metabolism_ticket_cancel(runtime: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    ticket_id = _safe_str(payload.get("ticket_id") or payload.get("id")).strip()
    result = await asyncio.to_thread(
        cancel_metabolism_ticket,
        runtime.xinyu_dir,
        ticket_id,
        reason=_safe_str(payload.get("reason"), "owner_cancelled"),
    )
    await publish_metabolism_decision(runtime, "cancelled", result)
    return result


async def apply_self_choice_metabolism_decision(runtime: Any, event: str, result: dict[str, Any]) -> None:
    if not result.get("accepted") or result.get("idempotent"):
        return
    result["selfChoiceState"] = await runtime.self_choice_store.apply_event_impulse(event)


async def publish_metabolism_decision(runtime: Any, decision: str, result: dict[str, Any]) -> None:
    ticket = result.get("ticket") if isinstance(result.get("ticket"), dict) else {}
    await runtime._desktop_publish_event(
        "metabolism_ticket_updated",
        {
            "decision": decision,
            "accepted": bool(result.get("accepted")),
            "ticket": ticket,
            "selfChoiceState": result.get("selfChoiceState") if isinstance(result.get("selfChoiceState"), dict) else {},
            "notes": result.get("notes", []),
        },
        severity="info" if result.get("accepted") else "warn",
    )

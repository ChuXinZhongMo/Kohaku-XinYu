from __future__ import annotations

import asyncio
from typing import Any, Callable

from xinyu_bridge_values import dedupe as _dedupe
from xinyu_bridge_values import safe_str as _safe_str


async def desktop_publish_proactive_candidate_ready_from_state(
    runtime: Any,
    *,
    notes: list[str] | tuple[str, ...] | None = None,
    safe_str: Callable[..., str] = _safe_str,
    dedupe: Callable[..., list[Any]] = _dedupe,
) -> dict[str, Any]:
    item = runtime._desktop_proactive_item_from_state(include_final=False)
    if not item:
        return {}
    existing = runtime._desktop_proactive_existing(item["candidateId"])
    runtime._desktop_upsert_proactive_inbox(item)
    if existing.get("readyEventId") and existing.get("candidatePreview") == item.get("candidatePreview"):
        return {"id": existing.get("readyEventId", "")}
    event_payload = {
        **item,
        "notes": dedupe(list(item.get("notes", [])) + list(notes or []))[:10],
    }
    event = await runtime._desktop_publish_event(
        "proactive.candidate.ready",
        event_payload,
        privacy="owner_private",
    )
    if event:
        item["readyEventId"] = safe_str(event.get("id"))
        runtime._desktop_upsert_proactive_inbox(item)
    return event


def desktop_schedule_proactive_candidate_ready_from_state(
    runtime: Any,
    *,
    notes: list[str] | tuple[str, ...] | None = None,
) -> bool:
    if runtime.desktop_event_bus is None:
        return False
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return False
    loop.create_task(
        runtime._desktop_publish_proactive_candidate_ready_from_state(notes=notes),
        name="xinyu-desktop-proactive-candidate-ready",
    )
    return True


def desktop_publish_initiative_candidate_threadsafe(
    runtime: Any,
    item: dict[str, Any],
    *,
    notes: list[str] | tuple[str, ...] | None = None,
    safe_str: Callable[..., str] = _safe_str,
    dedupe: Callable[..., list[Any]] = _dedupe,
) -> bool:
    if not item or not safe_str(item.get("candidateId")):
        return False
    safe_item = {
        **dict(item),
        "claimable": False,
        "deliveryLevel": safe_str(item.get("deliveryLevel"), "state_only") or "state_only",
        "requiresOwnerAck": True,
        "notes": dedupe(list(item.get("notes", [])) + list(notes or []))[:10],
    }
    existing = runtime._desktop_proactive_existing(safe_str(safe_item.get("candidateId")))
    runtime._desktop_upsert_proactive_inbox(safe_item)
    if (
        safe_str(existing.get("source")) == "initiative_orchestrator"
        and existing.get("candidatePreview") == safe_item.get("candidatePreview")
    ):
        return True
    if existing.get("readyEventId") and existing.get("candidatePreview") == safe_item.get("candidatePreview"):
        return True
    runtime._desktop_publish_event_threadsafe(
        "proactive.candidate.ready",
        dict(safe_item),
        privacy="owner_private",
    )
    return True


async def desktop_publish_proactive_delivery_item(
    runtime: Any,
    item: dict[str, Any],
    *,
    status_override: str = "",
    notes: list[str] | tuple[str, ...] | None = None,
    severity: str | None = None,
) -> dict[str, Any]:
    payload = runtime._desktop_proactive_delivery_payload(item, status_override=status_override, notes=notes)
    runtime._desktop_apply_proactive_delivery(payload)
    return await runtime._desktop_publish_event(
        "proactive.delivery.updated",
        payload,
        privacy="owner_private",
        severity=severity or ("error" if payload.get("status") == "failed" else None),
    )


async def desktop_publish_proactive_delivery_from_state(
    runtime: Any,
    *,
    status_override: str = "",
    notes: list[str] | tuple[str, ...] | None = None,
    severity: str | None = None,
) -> dict[str, Any]:
    item = runtime._desktop_proactive_item_from_state(include_final=True)
    if not item:
        return {}
    return await runtime._desktop_publish_proactive_delivery_item(
        item,
        status_override=status_override,
        notes=notes,
        severity=severity,
    )


def desktop_publish_proactive_delivery_from_state_threadsafe(
    runtime: Any,
    *,
    status_override: str = "",
    notes: list[str] | tuple[str, ...] | None = None,
    severity: str | None = None,
) -> None:
    item = runtime._desktop_proactive_item_from_state(include_final=True)
    if not item:
        return
    payload = runtime._desktop_proactive_delivery_payload(item, status_override=status_override, notes=notes)
    runtime._desktop_apply_proactive_delivery(payload)
    runtime._desktop_publish_event_threadsafe(
        "proactive.delivery.updated",
        payload,
        privacy="owner_private",
        severity=severity or ("error" if payload.get("status") == "failed" else None),
    )

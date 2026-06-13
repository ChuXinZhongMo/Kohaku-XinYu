from __future__ import annotations

from collections.abc import Callable
from typing import Any

from xinyu_bridge_values import safe_str as _safe_str


SafeStr = Callable[..., str]


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


async def publish_metabolism_runner_result(
    runtime: Any,
    result: dict[str, Any],
    *,
    trigger: str,
    safe_str: SafeStr = _safe_str,
) -> None:
    settled = result.get("settled") if isinstance(result.get("settled"), list) else []
    if not settled:
        return
    for item in settled:
        if not isinstance(item, dict):
            continue
        ticket = item.get("ticket") if isinstance(item.get("ticket"), dict) else {}
        status = safe_str(ticket.get("status"))
        self_choice_state: dict[str, Any] = {}
        if status == "settled" or item.get("settled"):
            self_choice_state = await runtime.self_choice_store.apply_event_impulse("ticket_settled")
            await runtime.self_choice_store.consume_hibernation_residue_for_metabolism()
        elif status == "failed":
            self_choice_state = await runtime.self_choice_store.apply_event_impulse("ticket_failed")
            await runtime.self_choice_store.consume_hibernation_residue_for_metabolism()
        await runtime._desktop_publish_event(
            "metabolism_ticket_updated",
            {
                "trigger": trigger,
                "ticket": ticket,
                "metabolism_path": safe_str(item.get("metabolism_path")),
                "dream_path": safe_str(item.get("dream_path")),
                "selfChoiceState": self_choice_state,
                "notes": item.get("notes", []),
            },
            severity="info",
        )

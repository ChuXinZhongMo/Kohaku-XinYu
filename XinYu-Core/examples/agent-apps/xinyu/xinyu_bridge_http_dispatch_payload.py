from __future__ import annotations

from typing import Any


def ensure_proactive_claim_default(payload: dict[str, Any]) -> None:
    payload.setdefault("claim", "false")


def attach_life_ticket_id(payload: dict[str, Any], ticket_id: str) -> None:
    payload["ticket_id"] = ticket_id

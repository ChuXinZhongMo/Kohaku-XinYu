from __future__ import annotations

from collections.abc import Callable
from typing import Any

from xinyu_bridge_semantic_fast_payloads import command_id


def build_semantic_fast_response(
    payload: dict[str, Any],
    *,
    reply: str,
    memory_changed: bool,
    turn_id: str,
    session_key: str,
    reply_hash: str,
    decision: dict[str, Any],
    intents: tuple[str, ...],
    elapsed_ms: int,
    renderer_name: str,
    notes: list[str],
    safe_str_func: Callable[..., str],
) -> dict[str, Any]:
    return {
        "accepted": True,
        "reply": reply,
        "memory_changed": memory_changed,
        "turn_id": turn_id,
        "command_id": command_id(payload),
        "session_id": session_key,
        "reply_hash": reply_hash,
        "archive_message_ids": [],
        "archive_assistant_message_id": "",
        "semantic_fast": {
            "scope": "owner_private_direct_fast" if renderer_name == "direct" else "owner_private_live_fast",
            "route": safe_str_func(decision.get("route"), "fast_path"),
            "intents": list(intents),
            "elapsed_ms": elapsed_ms,
            "renderer": renderer_name,
        },
        "notes": notes,
    }

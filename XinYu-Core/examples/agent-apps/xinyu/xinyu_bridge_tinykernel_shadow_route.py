from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import Any

from xinyu_bridge_time_utils import timestamp_or_now_iso
from xinyu_bridge_values import safe_str
from xinyu_tinykernel_shadow import record_tinykernel_shadow, shadow_enabled


async def run_tinykernel_shadow(
    runtime: Any,
    payload: dict[str, Any],
    *,
    text: str,
    turn_id: str,
    observed_at: str,
    shadow_enabled_func: Callable[[], bool] = shadow_enabled,
    record_shadow_func: Callable[..., dict[str, Any]] = record_tinykernel_shadow,
    to_thread_func: Callable[..., Any] = asyncio.to_thread,
    timestamp_func: Callable[..., str] = timestamp_or_now_iso,
    safe_str_func: Callable[..., str] = safe_str,
) -> dict[str, Any]:
    if not shadow_enabled_func():
        return {"notes": []}

    owner_private = getattr(runtime, "_owner_private_payload_matches", None)
    if callable(owner_private):
        try:
            if not owner_private(payload):
                return {"notes": []}
        except Exception as exc:
            return {"notes": [f"tinykernel_shadow_scope_error:{type(exc).__name__}"]}

    source = safe_str_func(payload.get("source") or payload.get("message_type") or "xinyu_bridge", "xinyu_bridge")
    try:
        return await to_thread_func(
            record_shadow_func,
            Path(runtime.xinyu_dir),
            turn_id=turn_id,
            source=source,
            user_text=text,
            context={
                "recent_turns": [],
                "persona_state": "",
                "owner_profile": "",
                "runtime_state": "",
                "memory_recall": [],
            },
            capabilities={
                "codex_available": True,
                "external_api_available": True,
                "local_tools_available": True,
            },
            observed_at=timestamp_func(observed_at),
        )
    except Exception as exc:
        return {"recorded": False, "ok": False, "notes": [f"tinykernel_shadow_error:{type(exc).__name__}"]}

from __future__ import annotations

import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_bridge_renderer_debug_store import write_live_system_prompt_dump


DEBUG_PROMPT_DUMP_ENV = "XINYU_DEBUG_PROMPT_DUMP"
DEBUG_LIVE_SYSTEM_PROMPT_REL = Path("runtime/debug/last_live_system_prompt.txt")


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def runtime_maybe_dump_live_system_prompt(
    runtime: Any,
    agent: Any,
    *,
    payload: dict[str, Any],
    session_key: str,
    turn_id: str,
    live_system_prompt: str,
) -> None:
    if os.environ.get(DEBUG_PROMPT_DUMP_ENV) != "1":
        return
    if not runtime._owner_private_payload_matches(payload):
        return

    base_system_prompt = ""
    getter = getattr(agent, "get_system_prompt", None)
    if callable(getter):
        try:
            base_system_prompt = _safe_str(getter())
        except Exception as exc:
            base_system_prompt = f"[debug_error:get_system_prompt:{type(exc).__name__}]"

    full_prompt = "\n\n".join(part for part in (base_system_prompt, live_system_prompt) if part)
    generated_at = datetime.now().astimezone().isoformat()
    prompt_hash = hashlib.sha256(full_prompt.encode("utf-8", errors="replace")).hexdigest()
    live_hash = hashlib.sha256(live_system_prompt.encode("utf-8", errors="replace")).hexdigest()
    content = "\n".join(
        [
            "# XinYu Debug Live System Prompt Dump",
            f"generated_at: {generated_at}",
            f"session_id: {session_key}",
            f"turn_id: {_safe_str(turn_id).strip() or 'unknown'}",
            f"full_prompt_sha256: sha256:{prompt_hash}",
            f"live_injection_sha256: sha256:{live_hash}",
            f"env_gate: {DEBUG_PROMPT_DUMP_ENV}=1",
            "scope: owner_private_live_turn_only",
            "storage_policy: overwrite_last_dump_only",
            "",
            "## Base System Prompt",
            base_system_prompt,
            "",
            "## Live System Injection",
            live_system_prompt,
            "",
        ]
    )

    try:
        write_live_system_prompt_dump(runtime.xinyu_dir, DEBUG_LIVE_SYSTEM_PROMPT_REL, content)
    except OSError as exc:
        print(f"[xinyu_core_bridge] debug prompt dump failed: {type(exc).__name__}: {exc}", flush=True)

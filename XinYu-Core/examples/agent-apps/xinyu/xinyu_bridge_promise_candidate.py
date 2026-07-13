from __future__ import annotations

import hashlib
import json
from typing import Any, Callable

from xinyu_bridge_promise_markers import (
    PROMISE_FOLLOWUP_DONE_MARKERS,
    PROMISE_FOLLOWUP_REPLY_MARKERS,
    PROMISE_FOLLOWUP_USER_MARKERS,
)
from xinyu_bridge_stores import (
    read_promise_owner_config_text,
    read_promise_owner_ids_env,
)


def owner_private_user_id(
    runtime: Any,
    *,
    as_str_set_func: Callable[[Any], set[str]],
) -> str:
    if runtime.v1_owner_user_ids:
        return sorted(runtime.v1_owner_user_ids)[0]

    env_owner_ids = as_str_set_func(read_promise_owner_ids_env())
    if env_owner_ids:
        return sorted(env_owner_ids)[0]

    config_path = runtime.xinyu_dir / "xinyu_qq_gateway.config.json"
    try:
        data = json.loads(read_promise_owner_config_text(config_path))
    except json.JSONDecodeError:
        return ""
    owner_ids = as_str_set_func(data.get("owner_user_ids") if isinstance(data, dict) else None)
    return sorted(owner_ids)[0] if owner_ids else ""


def candidate(
    runtime: Any,
    payload: dict[str, Any],
    *,
    user_text: str,
    reply: str,
    session_key: str,
    owner_private_user_id_func: Callable[[Any], str],
    owner_private_payload_matches_func: Callable[[dict[str, Any]], bool],
    compact_promise_text_func: Callable[[Any], str],
    safe_str_func: Callable[..., str],
    user_markers: tuple[str, ...] = PROMISE_FOLLOWUP_USER_MARKERS,
    reply_markers: tuple[str, ...] = PROMISE_FOLLOWUP_REPLY_MARKERS,
    done_markers: tuple[str, ...] = PROMISE_FOLLOWUP_DONE_MARKERS,
    model_codex_task: str = "",
) -> dict[str, str]:
    if model_codex_task or not owner_private_payload_matches_func(payload):
        return {}

    user_id = safe_str_func(payload.get("user_id")).strip() or owner_private_user_id_func(runtime)
    if not user_id:
        return {}

    compact_user = compact_promise_text_func(user_text)
    compact_reply = compact_promise_text_func(reply)
    if not any(marker in compact_user for marker in user_markers):
        return {}
    if not any(marker in compact_reply for marker in reply_markers):
        return {}
    if any(marker in compact_reply for marker in done_markers):
        return {}

    digest = hashlib.sha1(f"{session_key}\n{user_text}\n{reply}".encode("utf-8", errors="replace")).hexdigest()[:16]
    return {
        "user_id": user_id,
        "session_key": session_key,
        "user_text": safe_str_func(user_text).strip(),
        "reply": safe_str_func(reply).strip(),
        "dedupe_key": f"promise_followup:{digest}",
    }

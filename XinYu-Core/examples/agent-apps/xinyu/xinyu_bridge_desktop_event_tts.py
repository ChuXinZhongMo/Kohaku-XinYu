from __future__ import annotations

from collections.abc import Callable
from typing import Any

import xinyu_qq_voice_reply


SafeStrFunc = Callable[..., str]


def maybe_enqueue_tts(
    tts_output: Any,
    payload: dict[str, Any],
    *,
    reply: str,
    status: str,
    reply_hash: str,
    session_key: str,
    turn_id: str,
    safe_str_func: SafeStrFunc,
    owner_private_payload_matches_func: Callable[[dict[str, Any]], bool],
    visible_text_hash_func: Callable[[str], str],
) -> None:
    if safe_str_func(status).lower() not in {"ok", "finished"}:
        return
    if not owner_private_payload_matches_func(payload):
        return
    if tts_output is None or not tts_output.active():
        return
    clean_reply = safe_str_func(reply)
    if not clean_reply:
        return
    metadata = payload.get("metadata")
    metadata_map = metadata if isinstance(metadata, dict) else {}
    message_type = safe_str_func(payload.get("message_type"))
    if (
        message_type == "private"
        and xinyu_qq_voice_reply.voice_reply_enabled("private")
        and xinyu_qq_voice_reply.local_playback_enabled()
    ):
        return
    source = safe_str_func(metadata_map.get("source") or payload.get("source") or payload.get("adapter"))
    try:
        tts_output.enqueue(
            clean_reply,
            reply_hash=reply_hash or visible_text_hash_func(clean_reply),
            session_key=safe_str_func(session_key),
            turn_id=safe_str_func(turn_id),
            source=source,
            message_type=message_type,
        )
    except Exception as exc:
        print(f"[xinyu_core_bridge] tts enqueue warning: {exc}", flush=True)

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from xinyu_bridge_session_model import AgentSession
from xinyu_bridge_values import as_bool, safe_str
from xinyu_sticker_pack import sticker_mood_label


def append_dialogue_tail(
    runtime: Any,
    session: AgentSession,
    *,
    user_text: str,
    reply: str,
    save_dialogue_tail_func: Callable[..., Any],
    payload: dict[str, Any] | None = None,
) -> None:
    assistant_recorded_at = datetime.now().astimezone().isoformat()
    user_recorded_at = runtime._payload_event_time_iso(payload, fallback=assistant_recorded_at)
    user_content = runtime._dialogue_tail_user_content(user_text, payload=payload)
    if user_content.strip():
        session.dialogue_tail.append(
            {"role": "user", "content": user_content.strip(), "recorded_at": user_recorded_at}
        )
    if reply.strip():
        session.dialogue_tail.append(
            {"role": "assistant", "content": reply.strip(), "recorded_at": assistant_recorded_at}
        )
    if runtime.dialogue_session_tail_entries <= 0:
        session.dialogue_tail.clear()
    elif len(session.dialogue_tail) > runtime.dialogue_session_tail_entries:
        del session.dialogue_tail[:-runtime.dialogue_session_tail_entries]
    try:
        save_dialogue_tail_func(
            runtime.xinyu_dir,
            session.key,
            session.dialogue_tail,
            max_entries=runtime.dialogue_persisted_tail_entries,
        )
    except Exception:
        pass


def dialogue_tail_user_content(
    user_text: str,
    *,
    payload: dict[str, Any] | None = None,
) -> str:
    text = user_text.strip()
    payload = payload if isinstance(payload, dict) else {}
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict) or not as_bool(metadata.get("sticker_import_completed"), default=False):
        return text
    label = safe_str(metadata.get("sticker_mood_label") or metadata.get("sticker_mood")).strip()
    image_context = metadata.get("qq_image_context")
    image_context = image_context if isinstance(image_context, dict) else {}
    vision_summary = safe_str(image_context.get("vision_summary")).strip()
    meaning = safe_str(image_context.get("meaning")).strip()
    parts = [text or "我发了一张表情包。"]
    # Context note only: keep what helps understand the sticker (kind / meaning /
    # what it depicts) and drop the internal plumbing (confidence scores, on-disk
    # store path, raw mood enum) that would otherwise train a report-style voice.
    details = ["owner 刚发来一张 QQ 表情包"]
    if label:
        details.append(f"分类={label}")
    if meaning:
        details.append(f"语义={meaning}")
    if vision_summary:
        details.append(f"摘要={vision_summary[:500]}")
    parts.append("【收到的表情记录】" + "；".join(details))
    return "\n".join(parts)


def append_sticker_delivery_tail(
    runtime: Any,
    session: AgentSession,
    sticker_reply: Any,
    *,
    save_dialogue_tail_func: Callable[..., Any],
) -> bool:
    if not isinstance(sticker_reply, dict) or not as_bool(sticker_reply.get("queued"), default=False):
        return False
    mood = safe_str(sticker_reply.get("mood")).strip()
    mood_label = sticker_mood_label(mood) if mood else "表情"
    # Keep this an internal memory note, not a log line: the raw file name and the
    # internal send-mode enum (e.g. semantic_auto) only pollute the model's sense of
    # its own voice and bleed into report-style replies, so drop them here.
    detail = (
        f"我刚给 owner 回了一张{mood_label}表情。"
        "如果 owner 追问刚才那张表情，就顺着这个意思回应。"
    )
    session.dialogue_tail.append(
        {
            "role": "assistant",
            "content": f"【表情发送记录】{detail}",
            "recorded_at": datetime.now().astimezone().isoformat(),
        }
    )
    if runtime.dialogue_session_tail_entries <= 0:
        session.dialogue_tail.clear()
        return False
    if len(session.dialogue_tail) > runtime.dialogue_session_tail_entries:
        del session.dialogue_tail[:-runtime.dialogue_session_tail_entries]
    try:
        save_dialogue_tail_func(
            runtime.xinyu_dir,
            session.key,
            session.dialogue_tail,
            max_entries=runtime.dialogue_persisted_tail_entries,
        )
    except Exception:
        pass
    return True

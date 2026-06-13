from __future__ import annotations

import re
from typing import Any

from xinyu_visible_reply_guard import dedupe_visible_reply


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def normalize_reply(text: str) -> str:
    lines = [line.strip() for line in text.replace("\r\n", "\n").split("\n")]
    compact_lines: list[str] = []
    for line in lines:
        if line.strip():
            line = re.sub(r"^\s*(?:[-*\u2022>]+|\d+[.)])\s*", "", line).strip()
            line = re.sub(r"^\*{1,2}(.+?)\*{1,2}$", r"\1", line).strip()
            compact_lines.append(line)
    if not compact_lines:
        return ""
    reply = compact_lines[0]
    for line in compact_lines[1:]:
        if reply and reply[-1].isascii() and line and line[0].isascii():
            reply += " " + line
        else:
            reply += line
    return dedupe_visible_reply(reply).text


CRITICAL_FINAL_GUARD_FLAGS = frozenset(
    {
        "pseudo_tool_call_naturalized",
        "machine_introspection_naturalized",
        "visible_memory_mechanics_naturalized",
        "emotion_council_mechanics_blocked",
        "false_codex_unavailable_claim_blocked",
        "layered_voice_self_analysis_blocked",
        "self_state_mechanical_reply_blocked",
        "owner_address_label_blocked",
        "owner_address_query_blocked",
    }
)


def critical_final_guard_flags(flags: list[str] | tuple[str, ...]) -> list[str]:
    return [flag for flag in flags if flag in CRITICAL_FINAL_GUARD_FLAGS]


def replace_last_assistant_message(agent: Any, rendered_reply: str) -> None:
    controller = getattr(agent, "controller", None)
    conversation = getattr(controller, "conversation", None)
    if conversation is None or not hasattr(conversation, "get_last_assistant_message"):
        return
    try:
        message = conversation.get_last_assistant_message()
    except Exception:
        return
    if message is None:
        return
    try:
        message.content = rendered_reply
        message.tool_calls = None
    except Exception:
        pass


def normalize_renderer_mode(value: str) -> str:
    normalized = _safe_str(value, "off").strip().lower()
    if normalized in {"always", "quality", "pressure", "off"}:
        return normalized
    return "off"


def renderer_reason(
    speech_controller: Any,
    renderer_mode: str,
    *,
    payload: dict[str, Any],
    user_text: str,
    draft_reply: str,
) -> str:
    if renderer_mode == "off" or not draft_reply.strip():
        return ""
    if renderer_mode == "always":
        return "always"

    scene = speech_controller.classify(payload=payload, user_text=user_text)
    pressure = scene.style_pressure or (
        scene.relationship_pressure and scene.is_owner and not scene.technical_request
    )
    if pressure:
        return "pressure"
    if renderer_mode == "pressure":
        return ""

    quality_flags = speech_controller.reply_quality_flags(
        payload=payload,
        user_text=user_text,
        reply=draft_reply,
    )
    return "quality_flags" if quality_flags else ""


def build_renderer_messages(
    speech_controller: Any,
    renderer: Any,
    agent: Any,
    *,
    payload: dict[str, Any],
    user_text: str,
    draft_reply: str,
    canonical_recall_context: str = "",
    failed_reply: str = "",
    quality_flags: list[str] | None = None,
) -> list[dict[str, str]]:
    return speech_controller.build_messages(
        payload=payload,
        user_text=user_text,
        draft_reply=draft_reply,
        output_prompt=renderer.read_text("prompts/output.md", limit=16000),
        memory_context=renderer.renderer_memory_context(
            user_text=user_text,
            canonical_recall_context=canonical_recall_context,
        ),
        conversation_tail=renderer.conversation_tail(agent, max_messages=8),
        failed_reply=failed_reply,
        quality_flags=quality_flags,
    )


def strip_renderer_wrappers(speech_controller: Any, text: str) -> str:
    return speech_controller.strip_wrappers(text)

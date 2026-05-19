from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Any

from xinyu_runtime_context import build_renderer_memory_context, read_limited
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
            line = re.sub(r"^\s*(?:[-*•>]+|\d+[.)])\s*", "", line).strip()
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


class BridgeRenderer:
    def __init__(
        self,
        *,
        xinyu_dir: Path,
        speech_controller: Any,
        renderer_mode: str,
        render_timeout_seconds: int,
    ) -> None:
        self.xinyu_dir = xinyu_dir
        self.speech_controller = speech_controller
        self.renderer_mode = self.normalize_renderer_mode(renderer_mode)
        self.render_timeout_seconds = render_timeout_seconds

    async def render_outward_reply(
        self,
        agent: Any,
        *,
        payload: dict[str, Any],
        user_text: str,
        draft_reply: str,
        canonical_recall_context: str = "",
    ) -> str:
        llm = getattr(agent, "llm", None)
        if llm is None:
            return draft_reply

        messages = self.build_renderer_messages(
            agent,
            payload=payload,
            user_text=user_text,
            draft_reply=draft_reply,
            canonical_recall_context=canonical_recall_context,
        )
        try:
            response = await asyncio.wait_for(
                llm.chat_complete(messages, temperature=0.55, max_tokens=520),
                timeout=self.render_timeout_seconds,
            )
        except Exception as exc:
            print(f"[xinyu_core_bridge] outward renderer failed: {type(exc).__name__}: {exc}", flush=True)
            return draft_reply

        rendered = normalize_reply(getattr(response, "content", "") or "")
        rendered = self.strip_renderer_wrappers(rendered) or draft_reply

        quality_flags = self.speech_controller.reply_quality_flags(
            payload=payload,
            user_text=user_text,
            reply=rendered,
        )
        if quality_flags:
            retry_messages = self.build_renderer_messages(
                agent,
                payload=payload,
                user_text=user_text,
                draft_reply=draft_reply,
                canonical_recall_context=canonical_recall_context,
                failed_reply=rendered,
                quality_flags=quality_flags,
            )
            try:
                retry_response = await asyncio.wait_for(
                    llm.chat_complete(retry_messages, temperature=0.45, max_tokens=180),
                    timeout=self.render_timeout_seconds,
                )
            except Exception as exc:
                print(f"[xinyu_core_bridge] outward renderer retry failed: {type(exc).__name__}: {exc}", flush=True)
                return rendered

            retry_rendered = normalize_reply(getattr(retry_response, "content", "") or "")
            retry_rendered = self.strip_renderer_wrappers(retry_rendered)
            if retry_rendered:
                retry_flags = self.speech_controller.reply_quality_flags(
                    payload=payload,
                    user_text=user_text,
                    reply=retry_rendered,
                )
                if retry_flags:
                    return rendered
                print(
                    f"[xinyu_core_bridge] outward renderer retry applied: {', '.join(quality_flags)}",
                    flush=True,
                )
                return retry_rendered

        return rendered

    def renderer_reason(self, *, payload: dict[str, Any], user_text: str, draft_reply: str) -> str:
        if self.renderer_mode == "off" or not draft_reply.strip():
            return ""
        if self.renderer_mode == "always":
            return "always"

        scene = self.speech_controller.classify(payload=payload, user_text=user_text)
        pressure = scene.style_pressure or (
            scene.relationship_pressure and scene.is_owner and not scene.technical_request
        )
        if pressure:
            return "pressure"
        if self.renderer_mode == "pressure":
            return ""

        quality_flags = self.speech_controller.reply_quality_flags(
            payload=payload,
            user_text=user_text,
            reply=draft_reply,
        )
        return "quality_flags" if quality_flags else ""

    @staticmethod
    def normalize_renderer_mode(value: str) -> str:
        normalized = _safe_str(value, "off").strip().lower()
        if normalized in {"always", "quality", "pressure", "off"}:
            return normalized
        return "off"

    def build_renderer_messages(
        self,
        agent: Any,
        *,
        payload: dict[str, Any],
        user_text: str,
        draft_reply: str,
        canonical_recall_context: str = "",
        failed_reply: str = "",
        quality_flags: list[str] | None = None,
    ) -> list[dict[str, str]]:
        return self.speech_controller.build_messages(
            payload=payload,
            user_text=user_text,
            draft_reply=draft_reply,
            output_prompt=self.read_text("prompts/output.md", limit=16000),
            memory_context=self.renderer_memory_context(
                user_text=user_text,
                canonical_recall_context=canonical_recall_context,
            ),
            conversation_tail=self.conversation_tail(agent, max_messages=8),
            failed_reply=failed_reply,
            quality_flags=quality_flags,
        )

    def renderer_memory_context(self, *, user_text: str = "", canonical_recall_context: str = "") -> str:
        return build_renderer_memory_context(
            self.xinyu_dir,
            user_text=user_text,
            canonical_recall_context=canonical_recall_context,
        )

    def read_text(self, rel: str, *, limit: int) -> str:
        return read_limited(self.xinyu_dir, rel, limit=limit)

    def conversation_tail(self, agent: Any, *, max_messages: int) -> str:
        controller = getattr(agent, "controller", None)
        conversation = getattr(controller, "conversation", None)
        if conversation is None or not hasattr(conversation, "to_messages"):
            return ""
        try:
            messages = conversation.to_messages()
        except Exception:
            return ""

        lines: list[str] = []
        for message in messages[-max_messages:]:
            role = _safe_str(message.get("role"))
            if role == "system":
                continue
            content = message.get("content", "")
            if isinstance(content, list):
                content = " ".join(
                    _safe_str(part.get("text"))
                    for part in content
                    if isinstance(part, dict) and part.get("type") == "text"
                )
            content_text = _safe_str(content).strip()
            if content_text:
                lines.append(f"{role}: {content_text[:1000]}")
        return "\n".join(lines)

    def strip_renderer_wrappers(self, text: str) -> str:
        return self.speech_controller.strip_wrappers(text)

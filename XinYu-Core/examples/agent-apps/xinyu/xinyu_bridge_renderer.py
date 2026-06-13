from __future__ import annotations

from pathlib import Path
from typing import Any

import xinyu_bridge_renderer_context as renderer_context
import xinyu_bridge_renderer_payload as renderer_payload
from xinyu_bridge_renderer_context import build_renderer_memory_context, read_limited
from xinyu_bridge_renderer_debug import DEBUG_LIVE_SYSTEM_PROMPT_REL
from xinyu_bridge_renderer_debug import DEBUG_PROMPT_DUMP_ENV
from xinyu_bridge_renderer_debug import runtime_maybe_dump_live_system_prompt
from xinyu_bridge_renderer_payload import CRITICAL_FINAL_GUARD_FLAGS
from xinyu_bridge_renderer_payload import _safe_str
from xinyu_bridge_renderer_payload import critical_final_guard_flags
from xinyu_bridge_renderer_payload import normalize_reply
from xinyu_bridge_renderer_payload import replace_last_assistant_message
from xinyu_bridge_renderer_service import render_outward_reply_impl
from xinyu_bridge_renderer_trace import runtime_build_renderer_messages
from xinyu_bridge_renderer_trace import runtime_conversation_tail
from xinyu_bridge_renderer_trace import runtime_read_text
from xinyu_bridge_renderer_trace import runtime_renderer_memory_context
from xinyu_bridge_renderer_trace import runtime_renderer_reason
from xinyu_bridge_renderer_trace import runtime_strip_renderer_wrappers
from xinyu_visible_reply_guard import dedupe_visible_reply


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
        return await render_outward_reply_impl(
            self,
            agent,
            payload=payload,
            user_text=user_text,
            draft_reply=draft_reply,
            canonical_recall_context=canonical_recall_context,
        )

    def renderer_reason(self, *, payload: dict[str, Any], user_text: str, draft_reply: str) -> str:
        return renderer_payload.renderer_reason(
            self.speech_controller,
            self.renderer_mode,
            payload=payload,
            user_text=user_text,
            draft_reply=draft_reply,
        )

    @staticmethod
    def normalize_renderer_mode(value: str) -> str:
        return renderer_payload.normalize_renderer_mode(value)

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
        return renderer_payload.build_renderer_messages(
            self.speech_controller,
            self,
            agent,
            payload=payload,
            user_text=user_text,
            draft_reply=draft_reply,
            canonical_recall_context=canonical_recall_context,
            failed_reply=failed_reply,
            quality_flags=quality_flags,
        )

    def renderer_memory_context(self, *, user_text: str = "", canonical_recall_context: str = "") -> str:
        return renderer_context.renderer_memory_context(
            self.xinyu_dir,
            user_text=user_text,
            canonical_recall_context=canonical_recall_context,
            build_context=build_renderer_memory_context,
        )

    def read_text(self, rel: str, *, limit: int) -> str:
        return renderer_context.read_text(self.xinyu_dir, rel, limit=limit, read_limited_func=read_limited)

    def conversation_tail(self, agent: Any, *, max_messages: int) -> str:
        return renderer_context.conversation_tail(agent, max_messages=max_messages)

    def strip_renderer_wrappers(self, text: str) -> str:
        return renderer_payload.strip_renderer_wrappers(self.speech_controller, text)

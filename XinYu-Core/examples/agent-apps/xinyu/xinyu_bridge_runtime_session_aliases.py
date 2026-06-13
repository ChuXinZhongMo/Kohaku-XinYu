from __future__ import annotations

from functools import partialmethod
from typing import Any

import xinyu_bridge_codex_markers
import xinyu_bridge_context
import xinyu_bridge_turn_sidecars
import xinyu_qq_rich_context
from xinyu_bridge_null_input import NullInputModule
from xinyu_bridge_recent_sticker_reply import (
    current_sticker_question_reply,
    is_recent_sticker_question,
    recent_sticker_question_reply,
)
from xinyu_bridge_session import (
    runtime_append_dialogue_tail,
    runtime_append_sticker_delivery_tail,
    runtime_cleanup_idle_sessions,
    runtime_dialogue_tail_user_content,
    runtime_get_session,
)
from xinyu_dialogue_working_memory import load_dialogue_tail
from xinyu_recent_context_guard import ensure_recent_context_health


def install_session_turn_aliases(runtime_cls: type[Any]) -> None:
    runtime_cls._get_session = partialmethod(
        runtime_get_session,
        input_module_factory=NullInputModule,
        ensure_context_health=ensure_recent_context_health,
        dialogue_tail_loader=load_dialogue_tail,
    )
    runtime_cls._session_prompt_signature = xinyu_bridge_context.runtime_session_prompt_signature
    runtime_cls._cleanup_idle_sessions = runtime_cleanup_idle_sessions
    runtime_cls._looks_like_time_fact_correction = staticmethod(
        xinyu_bridge_turn_sidecars.looks_like_time_fact_correction
    )
    runtime_cls._inject_live_turn_context = partialmethod(
        xinyu_bridge_turn_sidecars.inject_live_turn_context,
        codex_delegate_open=xinyu_bridge_codex_markers.CODEX_DELEGATE_OPEN,
        codex_delegate_close=xinyu_bridge_codex_markers.CODEX_DELEGATE_CLOSE,
    )
    runtime_cls._qq_rich_message_sidecar = staticmethod(xinyu_qq_rich_context.prompt_sidecar_from_payload)
    runtime_cls._append_dialogue_tail = runtime_append_dialogue_tail
    runtime_cls._dialogue_tail_user_content = runtime_dialogue_tail_user_content
    runtime_cls._is_recent_sticker_question = staticmethod(is_recent_sticker_question)
    runtime_cls._current_sticker_question_reply = staticmethod(current_sticker_question_reply)
    runtime_cls._recent_sticker_question_reply = staticmethod(recent_sticker_question_reply)
    runtime_cls._append_sticker_delivery_tail = runtime_append_sticker_delivery_tail

from __future__ import annotations

from functools import partialmethod
from pathlib import Path
from typing import Any

import xinyu_bridge_renderer
import xinyu_bridge_reply_pipeline
from xinyu_bridge_renderer import BridgeRenderer, critical_final_guard_flags, replace_last_assistant_message


def install_reply_renderer_aliases(runtime_cls: type[Any], *, bridge_source_path: Path) -> None:
    runtime_cls._build_life_reply_policy = xinyu_bridge_reply_pipeline.build_life_reply_policy_for_runtime
    runtime_cls._maybe_dump_live_system_prompt = xinyu_bridge_renderer.runtime_maybe_dump_live_system_prompt
    runtime_cls._render_outward_reply = xinyu_bridge_reply_pipeline.runtime_render_outward_reply
    runtime_cls._renderer_reason = xinyu_bridge_renderer.runtime_renderer_reason
    runtime_cls._normalize_renderer_mode = staticmethod(BridgeRenderer.normalize_renderer_mode)
    runtime_cls._build_renderer_messages = xinyu_bridge_renderer.runtime_build_renderer_messages
    runtime_cls._speech_controller = partialmethod(
        xinyu_bridge_reply_pipeline.runtime_speech_controller,
        bridge_source_path=bridge_source_path,
    )
    runtime_cls._is_live_style_pressure = xinyu_bridge_reply_pipeline.runtime_is_live_style_pressure
    runtime_cls._is_owner_relationship_pressure = (
        xinyu_bridge_reply_pipeline.runtime_is_owner_relationship_pressure
    )
    runtime_cls._is_explicit_technical_request = xinyu_bridge_reply_pipeline.runtime_is_explicit_technical_request
    runtime_cls._reply_quality_flags = xinyu_bridge_reply_pipeline.runtime_reply_quality_flags
    runtime_cls._recover_empty_visible_reply = xinyu_bridge_reply_pipeline.recover_empty_visible_reply
    runtime_cls._critical_final_guard_flags = staticmethod(critical_final_guard_flags)
    runtime_cls._renderer_memory_context = xinyu_bridge_renderer.runtime_renderer_memory_context
    runtime_cls._read_text = xinyu_bridge_renderer.runtime_read_text
    runtime_cls._conversation_tail = xinyu_bridge_renderer.runtime_conversation_tail
    runtime_cls._replace_last_assistant_message = staticmethod(replace_last_assistant_message)
    runtime_cls._strip_renderer_wrappers = xinyu_bridge_renderer.runtime_strip_renderer_wrappers

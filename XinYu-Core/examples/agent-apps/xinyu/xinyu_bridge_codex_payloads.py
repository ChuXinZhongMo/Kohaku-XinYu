from __future__ import annotations

from xinyu_bridge_codex_dialogue_context import (
    augment_codex_payload_with_dialogue_context,
    augment_runtime_codex_payload_with_dialogue_context,
    format_dialogue_tail,
    format_runtime_dialogue_tail,
)
from xinyu_bridge_codex_model_payload import (
    CODEX_DEFAULT_TIMEOUT_SECONDS,
    CODEX_VISIBLE_WINDOW_TITLE,
    build_model_codex_payload,
    build_self_code_iteration_codex_payload,
    can_model_delegate_codex,
)

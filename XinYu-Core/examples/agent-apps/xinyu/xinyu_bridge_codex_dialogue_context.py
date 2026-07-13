from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from xinyu_bridge_values import as_bool, safe_str
from xinyu_dialogue_compression import SUMMARY_ROLE
from xinyu_dialogue_working_memory import compact_tail_for_prompt, load_dialogue_tail

# K-007+: optional kernel context (non-breaking)
try:
    from kernel.bridge_integration import augment_text_with_kernel_context, get_kernel_context
    from kernel import get_kernel_self_model
except Exception:
    def get_kernel_self_model(*a, **k): return {}
    def get_kernel_context(*a, **k): return {}
    def augment_text_with_kernel_context(text, *a, **k): return text


def format_dialogue_tail(
    dialogue_tail: list[dict[str, str]],
    *,
    max_entries: int,
) -> str:
    if not dialogue_tail:
        return "current session tail: none"
    lines = ["current session tail:"]
    for item in compact_tail_for_prompt(
        dialogue_tail,
        max_entries=max_entries,
        include_timestamps=True,
    ):
        role = safe_str(item.get("role")).strip()
        content = safe_str(item.get("content")).strip()
        if not role or not content:
            continue
        recorded_at = safe_str(item.get("recorded_at")).strip()
        time_suffix = f" ({recorded_at})" if recorded_at else ""
        if role == SUMMARY_ROLE:
            lines.append(f"- [earlier in session]{time_suffix}: {content}")
        else:
            lines.append(f"- {role}{time_suffix}: {content}")
    return "\n".join(lines) if len(lines) > 1 else "current session tail: none"


def format_runtime_dialogue_tail(runtime: Any, dialogue_tail: list[dict[str, str]]) -> str:
    return format_dialogue_tail(
        dialogue_tail,
        max_entries=runtime.dialogue_prompt_tail_entries,
    )


def augment_codex_payload_with_dialogue_context(
    xinyu_dir: Path,
    payload: dict[str, Any],
    text: str,
    *,
    dialogue_prompt_tail_entries: int,
    dialogue_tail_loader: Callable[..., list[dict[str, str]]] = load_dialogue_tail,
) -> str:
    if safe_str(payload.get("source")) != "qq_gateway_codex_execute_message":
        return text
    if not as_bool(payload.get("include_dialogue_context"), default=True):
        return text
    session_key = safe_str(payload.get("session_id")).strip()
    if not session_key:
        return text
    tail = dialogue_tail_loader(xinyu_dir, session_key, max_entries=8)
    if not tail:
        return text
    raw_task = safe_str(payload.get("raw_owner_task")).strip() or text
    tail_block = format_dialogue_tail(tail, max_entries=dialogue_prompt_tail_entries)
    augmented = "\n\n".join(
        [
            text,
            "Recent QQ context before this Codex request:",
            tail_block,
            "Use the recent context only to resolve references in the owner task.",
            f"Current owner Codex task: {raw_task}",
        ]
    )

    # K-010: augment with full persistent runtime Self when available
    try:
        from kernel.bridge_access import resolve_runtime_self

        kernel_self = resolve_runtime_self(xinyu_dir)
        if kernel_self.get_self_model().get("core_statements") or kernel_self.get_working_memory():
            augmented = augment_text_with_kernel_context(augmented, kernel_self)
            payload["kernel_context_included"] = True
    except Exception:
        pass

    payload["text"] = augmented
    payload["codex_context_included"] = True
    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        metadata["dialogue_context_included"] = True
    return augmented


def augment_runtime_codex_payload_with_dialogue_context(runtime: Any, payload: dict[str, Any], text: str) -> str:
    return augment_codex_payload_with_dialogue_context(
        runtime.xinyu_dir,
        payload,
        text,
        dialogue_prompt_tail_entries=runtime.dialogue_prompt_tail_entries,
    )

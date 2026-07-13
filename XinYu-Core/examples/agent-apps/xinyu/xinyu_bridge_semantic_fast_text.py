from __future__ import annotations

from typing import Any, Callable

from xinyu_bridge_semantic_fast_text_extract import SEMANTIC_FAST_ALLOWED_INTENTS
from xinyu_bridge_semantic_fast_text_extract import _CONFUSION_ONLY_MARKERS
from xinyu_bridge_semantic_fast_text_extract import _OWNER_STATE_QUESTION_MARKERS
from xinyu_bridge_semantic_fast_text_extract import _REPLY_QUALITY_COMPLAINT_MARKERS
from xinyu_bridge_semantic_fast_text_extract import _RUNTIME_STATUS_MARKERS
from xinyu_bridge_semantic_fast_text_extract import _STALE_PLAN_REPLY_MARKERS
from xinyu_bridge_semantic_fast_text_extract import _compact_text as _compact_text_base
from xinyu_bridge_semantic_fast_text_extract import _contains_any as _contains_any_base
from xinyu_bridge_semantic_fast_text_extract import (
    _looks_like_owner_state_question as _looks_like_owner_state_question_base,
)
from xinyu_bridge_semantic_fast_text_extract import _repair_intents_for_text as _repair_intents_for_text_base
from xinyu_bridge_semantic_fast_text_format import _direct_greeting_ack_reply as _direct_greeting_ack_reply_base
from xinyu_bridge_semantic_fast_text_format import _ordinary_private_repair_reply as _ordinary_private_repair_reply_base
from xinyu_bridge_semantic_fast_text_format import empty_visible_reply_fallback_impl as _empty_visible_reply_fallback_impl_base
from xinyu_bridge_semantic_fast_text_format import owner_private_direct_repair_reply_impl as _owner_private_direct_repair_reply_impl_base
from xinyu_bridge_semantic_fast_text_format import owner_private_empty_state_notice as _owner_private_empty_state_notice_base
from xinyu_bridge_semantic_fast_text_format import reply_looks_like_stale_plan_residue as _reply_looks_like_stale_plan_residue_base

# Public re-export for routes/tests that import from this facade module.
__all__ = (
    "SEMANTIC_FAST_ALLOWED_INTENTS",
)


def _compact_text(text: str) -> str:
    return _compact_text_base(text)


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return _contains_any_base(text, markers)


def _repair_intents_for_text(text: str) -> tuple[str, ...]:
    return _repair_intents_for_text_base(
        text,
        compact_text_func=_compact_text,
        contains_any_func=_contains_any,
        runtime_status_markers=_RUNTIME_STATUS_MARKERS,
        reply_quality_complaint_markers=_REPLY_QUALITY_COMPLAINT_MARKERS,
        confusion_only_markers=_CONFUSION_ONLY_MARKERS,
    )


def _looks_like_owner_state_question(text: str) -> bool:
    return _looks_like_owner_state_question_base(
        text,
        compact_text_func=_compact_text,
        owner_state_question_markers=_OWNER_STATE_QUESTION_MARKERS,
    )


def owner_private_empty_state_notice(text: str, *, seed: str = "") -> str:
    return _owner_private_empty_state_notice_base(
        text,
        seed=seed,
        compact_text_func=_compact_text,
        owner_state_question_func=_looks_like_owner_state_question,
    )


def empty_visible_reply_fallback_impl(
    runtime: Any,
    *,
    payload: dict[str, Any],
    user_text: str,
    delegate_note: str = "",
    empty_state_notice_func: Callable[..., str] = owner_private_empty_state_notice,
) -> str:
    return _empty_visible_reply_fallback_impl_base(
        runtime,
        payload=payload,
        user_text=user_text,
        delegate_note=delegate_note,
        empty_state_notice_func=empty_state_notice_func,
    )


def owner_private_direct_repair_reply_impl(
    runtime: Any,
    text: str,
    intents: tuple[str, ...] | None = None,
    *,
    repair_intents_func: Callable[[str], tuple[str, ...]] = _repair_intents_for_text,
    ordinary_repair_reply_func: Callable[[str], str] | None = None,
) -> str:
    ordinary_repair_reply_func = ordinary_repair_reply_func or _ordinary_private_repair_reply
    return _owner_private_direct_repair_reply_impl_base(
        runtime,
        text,
        intents,
        repair_intents_func=repair_intents_func,
        ordinary_repair_reply_func=ordinary_repair_reply_func,
        compact_text_func=_compact_text,
        contains_any_func=_contains_any,
    )


def _ordinary_private_repair_reply(text: str) -> str:
    return _ordinary_private_repair_reply_base(text, compact_text_func=_compact_text)


def reply_looks_like_stale_plan_residue(reply: str) -> bool:
    return _reply_looks_like_stale_plan_residue_base(
        reply,
        compact_text_func=_compact_text,
        stale_plan_reply_markers=_STALE_PLAN_REPLY_MARKERS,
    )


def _direct_greeting_ack_reply(text: str, intents: tuple[str, ...]) -> str:
    return _direct_greeting_ack_reply_base(text, intents, compact_text_func=_compact_text)

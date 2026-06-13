"""Provenance tags for the final visible reply (plan 11.9).

`final_text_source` must land from phase 2 onward so tests can tell "model
micro-regeneration succeeded" apart from "fell back to a canned constant". This
module is intentionally dependency-free so any layer (routes, pipeline, tests)
can import it.
"""

from __future__ import annotations

from typing import Final


class FinalTextSource:
    """Closed enumeration of where the owner-visible text came from."""

    MODEL_LIVE: Final = "model_live"
    MODEL_RENDERER: Final = "model_renderer"
    MODEL_MICRO: Final = "model_micro"
    MODEL_REGEN: Final = "model_regen"
    FUNCTIONAL_COMPOSER: Final = "functional_composer"
    CANNED_EMPTY_STATE: Final = "canned_empty_state"
    CANNED_BRIDGE_ALERT: Final = "canned_bridge_alert"
    STICKER: Final = "sticker"


ALL_FINAL_TEXT_SOURCES: Final[tuple[str, ...]] = (
    FinalTextSource.MODEL_LIVE,
    FinalTextSource.MODEL_RENDERER,
    FinalTextSource.MODEL_MICRO,
    FinalTextSource.MODEL_REGEN,
    FinalTextSource.FUNCTIONAL_COMPOSER,
    FinalTextSource.CANNED_EMPTY_STATE,
    FinalTextSource.CANNED_BRIDGE_ALERT,
    FinalTextSource.STICKER,
)

MODEL_BACKED_SOURCES: Final[frozenset[str]] = frozenset(
    {
        FinalTextSource.MODEL_LIVE,
        FinalTextSource.MODEL_RENDERER,
        FinalTextSource.MODEL_MICRO,
        FinalTextSource.MODEL_REGEN,
    }
)


def is_valid_final_text_source(value: str) -> bool:
    return value in ALL_FINAL_TEXT_SOURCES


def is_model_backed(value: str) -> bool:
    return value in MODEL_BACKED_SOURCES


# Historical canned constants that must never reappear as a model-backed reply.
# Used by regression tests (plan 11.10) and the post-processing non-canned check
# (plan 11.6) to detect a reply that silently regressed to a template.
HISTORICAL_CANNED_REPLIES: Final[tuple[str, ...]] = (
    "我在。",
    "嗯，我在。",
    "我在。刚才那句没接上。",
    "还在。刚才那一下没接上。",
    "可以拆。你要我拆哪段，我按一条一条发。",
    "哪句最明显？",
    "刚才那句接错了",
    "后台在处理当前这条私聊",
)


def equals_historical_canned(text: str) -> bool:
    """True when `text` is exactly one of the retired canned constants."""

    stripped = (text or "").strip()
    return any(stripped == canned for canned in HISTORICAL_CANNED_REPLIES)


# Map the semantic-fast renderer's provenance name to a final_text_source tag.
_SEMANTIC_FAST_RENDERER_SOURCE: Final[dict[str, str]] = {
    "outward_reply": FinalTextSource.MODEL_MICRO,
    "direct": FinalTextSource.CANNED_EMPTY_STATE,
    "canned_fallback": FinalTextSource.CANNED_EMPTY_STATE,
    "empty_state_notice": FinalTextSource.CANNED_EMPTY_STATE,
}


def final_text_source_for_renderer(renderer_name: str) -> str:
    """Provenance tag for a semantic-fast renderer name (plan 11.9)."""

    return _SEMANTIC_FAST_RENDERER_SOURCE.get(renderer_name, FinalTextSource.MODEL_MICRO)


def note_for_final_text_source(source: str) -> str:
    return f"final_text_source:{source}"

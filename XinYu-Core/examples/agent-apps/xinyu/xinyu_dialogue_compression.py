"""Dialogue-tail trajectory compression.

The prompt tail used to be raw turns mechanically truncated to a char budget
(`compact_tail_for_prompt`), which loses meaning mid-sentence and, on long
sessions, could even drop the freshest turns once the budget filled.

Compression instead keeps the freshest K turns verbatim and folds the older
turns into one compact "what happened" summary entry. By default this is a
zero-latency *extractive* fold (no model call) so the hot prompt-build path
stays fast. A richer LLM summary can be supplied through the `summarizer`
seam (see `compact_tail_for_prompt`), which a background pass can populate and
cache without blocking replies.

The summary row uses the dedicated `SUMMARY_ROLE` so the renderer can label it
distinctly; everything downstream that filters for user/assistant rows simply
ignores it.
"""

from __future__ import annotations

import os
import re
from typing import Any, Callable

SUMMARY_ROLE = "summary"

DEFAULT_KEEP_RECENT = 8
DEFAULT_TRIGGER = 6
DEFAULT_SUMMARY_CHARS = 600
DEFAULT_PER_TURN_CHARS = 90

# (older_rows, char_budget) -> summary text
Summarizer = Callable[[list[dict[str, str]], int], str]


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _env_int(name: str, default: int) -> int:
    try:
        return int(_safe_str(os.environ.get(name)).strip() or default)
    except (TypeError, ValueError):
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = _safe_str(os.environ.get(name)).strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on"}


def compression_enabled() -> bool:
    return _env_bool("XINYU_DIALOGUE_COMPRESSION_ENABLED", True)


def compression_keep_recent() -> int:
    return max(1, _env_int("XINYU_DIALOGUE_COMPRESSION_KEEP_RECENT", DEFAULT_KEEP_RECENT))


def compression_trigger() -> int:
    """Minimum number of *older* turns (beyond the kept-recent window) before it is
    worth folding them into a summary."""

    return max(2, _env_int("XINYU_DIALOGUE_COMPRESSION_TRIGGER", DEFAULT_TRIGGER))


def compression_summary_chars() -> int:
    return max(120, _env_int("XINYU_DIALOGUE_COMPRESSION_SUMMARY_CHARS", DEFAULT_SUMMARY_CHARS))


def compression_per_turn_chars() -> int:
    return max(24, _env_int("XINYU_DIALOGUE_COMPRESSION_PER_TURN_CHARS", DEFAULT_PER_TURN_CHARS))


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", _safe_str(text)).strip()


def _clip(text: str, limit: int) -> str:
    clean = _norm(text)
    if len(clean) <= limit:
        return clean
    return clean[: max(0, limit - 1)].rstrip() + "…"


def should_compress(usable_count: int, *, keep_recent: int | None = None, trigger: int | None = None) -> bool:
    keep = compression_keep_recent() if keep_recent is None else max(1, int(keep_recent))
    trig = compression_trigger() if trigger is None else max(2, int(trigger))
    return (usable_count - keep) >= trig


def build_extractive_summary(older: list[dict[str, str]], char_budget: int, *, per_turn_chars: int | None = None) -> str:
    """Deterministic, model-free fold of the older turns: one short role-prefixed
    clause per turn, kept newest-first so the budget favours the turns closest to
    the current moment, then re-ordered chronologically for reading."""

    per_turn = compression_per_turn_chars() if per_turn_chars is None else max(24, int(per_turn_chars))
    budget = max(120, int(char_budget))
    pieces: list[str] = []
    used = 0
    for row in reversed(older):
        role = _norm(row.get("role"))
        content = _norm(row.get("content"))
        if role not in {"user", "assistant"} or not content:
            continue
        piece = f"{role}: {_clip(content, per_turn)}"
        if pieces and used + len(piece) + 2 > budget:
            break
        pieces.append(piece)
        used += len(piece) + 2
    pieces.reverse()
    return " ; ".join(pieces)


def summary_row(text: str, *, recorded_at: str = "") -> dict[str, str]:
    row = {"role": SUMMARY_ROLE, "content": _norm(text)}
    if recorded_at:
        row["recorded_at"] = recorded_at
    return row


def compress_window(
    usable: list[dict[str, str]],
    *,
    keep_recent: int | None = None,
    trigger: int | None = None,
    summary_chars: int | None = None,
    summarizer: Summarizer | None = None,
) -> tuple[dict[str, str] | None, list[dict[str, str]]]:
    """Split a usable (user/assistant only) tail window into an optional summary row
    for the older turns plus the freshest turns kept verbatim.

    Returns (summary_row_or_None, recent_rows). When there are too few turns to be
    worth compressing, returns (None, usable) unchanged."""

    keep = compression_keep_recent() if keep_recent is None else max(1, int(keep_recent))
    if not should_compress(len(usable), keep_recent=keep, trigger=trigger):
        return None, usable
    older = usable[:-keep]
    recent = usable[-keep:]
    budget = compression_summary_chars() if summary_chars is None else max(120, int(summary_chars))
    text = ""
    if summarizer is not None:
        try:
            text = _norm(summarizer(older, budget))
        except Exception:
            text = ""
    if not text:
        text = build_extractive_summary(older, budget)
    if not text:
        return None, usable
    recorded_at = _safe_str(older[-1].get("recorded_at")).strip() if older else ""
    return summary_row(_clip(text, budget), recorded_at=recorded_at), recent

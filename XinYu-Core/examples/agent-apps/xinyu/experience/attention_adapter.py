"""Attention adapter for K-005.

Helps feed relevant items (from memory, experience, errors) into Self's AttentionBuffer.
"""

from __future__ import annotations

from typing import Any

from kernel.self import Self


def update_self_attention(
    kernel_self: Self,
    memory_items: list[dict[str, Any]] | None = None,
    prediction_error: dict[str, Any] | None = None,
    source_event_id: str | None = None,
) -> list[dict[str, Any]]:
    """Update attention buffer from available sources.

    Returns the current working memory after update.
    """
    # Add memory items if provided
    if memory_items:
        kernel_self.update_attention(items=memory_items)

    # Update from self model and goals (always)
    kernel_self.update_attention(from_self_model=True, from_goals=True)

    # Strong boost from recent prediction error
    if prediction_error:
        kernel_self.update_attention(from_last_error=prediction_error)

    return kernel_self.get_working_memory()

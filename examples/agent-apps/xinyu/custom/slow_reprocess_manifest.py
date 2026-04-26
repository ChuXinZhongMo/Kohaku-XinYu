"""Shared slow-reprocessing manifest for Xinyu.

This defines the queue order for reflection, dream, and archive preparation
without forcing those layers to mutate facts automatically.
"""

from __future__ import annotations

SLOW_REPROCESS_SOURCES: list[dict[str, object]] = [
    {
        "name": "reflection_queue",
        "path": "memory/reflection/reflection_queue.md",
        "priority": 1,
        "role": "reinterpret meaning after repeated or unresolved experience",
    },
    {
        "name": "dream_seeds",
        "path": "memory/dreams/dream_seeds.md",
        "priority": 2,
        "role": "hold emotionally weighted fragments that may reappear indirectly",
    },
    {
        "name": "archive_queue",
        "path": "memory/archive/archive_queue.md",
        "priority": 3,
        "role": "hold clusters that should remain preserved but not yet compressed away",
    },
]

SLOW_REPROCESS_TARGETS: list[str] = [
    "memory/reflection/reprocessing_state.md",
    "memory/reflection/growth_log.md",
    "memory/dreams/dream_log.md",
    "memory/archive/compressed.md",
    "memory/archive/dormant.md",
]

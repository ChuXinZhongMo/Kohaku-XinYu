from __future__ import annotations

import re
from typing import Any

from xinyu_bridge_values import safe_str


def trusted_public_search_task_allowed(
    task_text: str,
    *,
    public_search_markers: tuple[str, ...],
    local_block_markers: tuple[str, ...],
    local_path_pattern: Any,
    local_english_block_markers: tuple[str, ...],
) -> bool:
    raw_text = safe_str(task_text)
    compact = re.sub(r"\s+", "", raw_text).lower()
    if not compact:
        return False
    if local_path_pattern.search(raw_text):
        return False
    if any(marker.lower() in compact for marker in local_block_markers):
        return False
    if any(marker in compact for marker in local_english_block_markers):
        return False
    return any(marker.lower() in compact for marker in public_search_markers)

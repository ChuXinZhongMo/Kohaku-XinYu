from __future__ import annotations

import re
from typing import Any, Callable


TIME_FACT_CORRECTION_CUES = (
    "\u4e0d\u662f",
    "\u4e0d\u5bf9",
    "\u9519\u4e86",
    "\u7b97\u9519",
    "\u4f55\u610f\u5473",
    "\u4ec0\u4e48\u610f\u601d",
    "\u54ea\u6765\u7684",
    "\u600e\u4e48\u5c31",
    "\u600e\u4e48\u4f1a",
    "\u600e\u4e48\u662f",
    "\u4e0d\u5e94\u8be5",
)
TIME_FACT_CUES = (
    "\u4eca\u5929",
    "\u65e5\u671f",
    "\u65f6\u95f4",
    "\u661f\u671f",
    "\u5468\u51e0",
    "\u5047\u671f",
    "\u4e94\u4e00",
    "\u52b3\u52a8\u8282",
    "5.5",
    "5\u6708",
    "\u4e94\u6708",
    "\u6700\u540e\u4e00\u5929",
    "\u7ed3\u675f",
    "\u6536\u5c3e",
    "\u660e\u5929",
    "\u6628\u5929",
)


def has_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def looks_like_time_fact_correction(text: Any, *, safe_str_func: Callable[..., str]) -> bool:
    compact = re.sub(r"\s+", "", safe_str_func(text))
    if not compact:
        return False
    return has_any(compact, TIME_FACT_CORRECTION_CUES) and has_any(compact, TIME_FACT_CUES)

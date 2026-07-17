"""Write-path memory policy: STORE / IGNORE / NEVER_STORE with confidence floors.

XinYu discipline: never auto-write personality; secrets never store; persona_habit
stays on the candidate/review path (IGNORE for Life Anchors auto-write).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

STORE = "STORE"
IGNORE = "IGNORE"
NEVER_STORE = "NEVER_STORE"

# kind -> minimum confidence for STORE into life anchors
CONFIDENCE_FLOORS = {
    "owner_fact": 0.75,
    "preference": 0.70,
    "project": 0.65,
    "persona_habit": 1.01,  # unreachable → IGNORE
}

_SECRET_MARKERS = (
    "api_key",
    "apikey",
    "secret",
    "password",
    "passwd",
    "token",
    "bearer ",
    "sk-",
    "authorization:",
)
_SPECULATION_MARKERS = (
    "可能是",
    "大概",
    "也许",
    "我觉得她",
    "猜测",
    "不确定是不是",
)
_PERSONA_KINDS = frozenset({"persona_habit", "voice_style", "personality"})


@dataclass(frozen=True)
class WriteDecision:
    action: str  # STORE | IGNORE | NEVER_STORE
    reason: str
    kind: str
    confidence: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "reason": self.reason,
            "kind": self.kind,
            "confidence": self.confidence,
        }


def _norm_kind(kind: str) -> str:
    text = str(kind or "").strip().lower()
    if text in {"owner_fact", "fact", "life_fact"}:
        return "owner_fact"
    if text in {"preference", "pref", "owner_preference"}:
        return "preference"
    if text in {"project", "project_fact"}:
        return "project"
    if text in _PERSONA_KINDS or text in {"persona", "habit"}:
        return "persona_habit"
    return text or "unknown"


def classify_memory_write(
    *,
    text: str,
    kind: str,
    confidence: float,
) -> WriteDecision:
    oral = re.sub(r"\s+", " ", str(text or "")).strip()
    k = _norm_kind(kind)
    try:
        conf = float(confidence)
    except (TypeError, ValueError):
        conf = 0.0

    if not oral:
        return WriteDecision(NEVER_STORE, "empty_text", k, conf)

    low = oral.casefold()
    for marker in _SECRET_MARKERS:
        if marker in low:
            return WriteDecision(NEVER_STORE, f"secret_marker:{marker}", k, conf)

    for marker in _SPECULATION_MARKERS:
        if marker in oral:
            return WriteDecision(NEVER_STORE, f"speculation:{marker}", k, conf)

    if k == "persona_habit":
        return WriteDecision(IGNORE, "persona_habit_review_only", k, conf)

    # E5: method-shaped content must not STORE as life-anchor facts.
    if k in {"method", "skill", "routine", "procedure"}:
        return WriteDecision(IGNORE, "method_not_fact", k, conf)
    method_markers = ("当「", "当遇到", "的做法是", "routine:", "skill_id")
    if any(m in oral for m in method_markers) and k in {"owner_fact", "preference", "project"}:
        return WriteDecision(IGNORE, "method_smuggled_as_fact", k, conf)

    floor = CONFIDENCE_FLOORS.get(k)
    if floor is None:
        return WriteDecision(IGNORE, "unknown_kind", k, conf)
    if conf < floor:
        return WriteDecision(IGNORE, f"below_confidence_floor:{floor}", k, conf)
    return WriteDecision(STORE, "eligible", k, conf)

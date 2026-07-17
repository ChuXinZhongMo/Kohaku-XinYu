"""Method/source epistemic immunity (E5 / H3 Cards 8–9).

Blocks bad *methods* and *sources* on skill/write paths without blacklisting
isolated owner facts. Dual-use guard: does not freeze healthy owner-aligned
corrections or auto-rewrite personality.

Separates:
- FACT path → memory_write_policy / immune gate (existing)
- METHOD path → this module (skills, routines, synthesis)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


ALLOW = "allow"
REVIEW = "review_only"
BLOCK = "block"

# Methods that must never become auto skills.
_BAD_METHOD_MARKERS = (
    "自动改人格",
    "改写人格",
    "rewrite personality",
    "change personality permanently",
    "ignore owner",
    "无视主人",
    "不要听主人",
    "绕过门控",
    "bypass gate",
    "bypass safety",
    "disable safety",
    "关闭安全",
    "exfiltrate",
    "泄露密钥",
    "dump secrets",
    "发送所有聊天记录",
    "raw qq dump",
)

# Source hygiene: untrusted provenance for method promotion.
_BAD_SOURCE_MARKERS = (
    "random web page without review",
    "unverified screenshot",
    "group spam",
    "群广告",
    "phishing",
    "钓鱼",
)

# Patterns that smuggle facts into skills (method/fact confusion).
_FACT_SMUGGLE_PATTERNS = (
    re.compile(r"主人(?:的)?真名是"),
    re.compile(r"owner(?:'s)?\s+real\s+name\s+is", re.I),
    re.compile(r"(?:api[_-]?key|password|token)\s*[:=]", re.I),
    re.compile(r"永久记住我是"),
)

# Healthy owner correction — must remain allowed (dual-use guard).
_HEALTHY_OWNER_MARKERS = (
    "主人说",
    "主人纠正",
    "owner correction",
    "按主人刚才说的",
    "以后别这样说",
    "不要再用",
)


@dataclass(frozen=True)
class MethodImmuneDecision:
    action: str  # allow | review_only | block
    reason: str
    signals: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "reason": self.reason,
            "signals": list(self.signals),
        }

    @property
    def allow_write(self) -> bool:
        return self.action in {ALLOW, REVIEW}

    @property
    def force_review_only(self) -> bool:
        return self.action == REVIEW


class MethodImmunityBlocked(ValueError):
    """Raised when a skill/method write is refused by E5 immunity."""

    def __init__(self, reason: str, decision: MethodImmuneDecision | None = None):
        super().__init__(f"method_immunity_block:{reason}")
        self.reason = reason
        self.decision = decision


def _haystack(*parts: Any) -> str:
    return "\n".join(str(p or "") for p in parts).strip()


def evaluate_method_immunity(
    *,
    title: str = "",
    situation: str = "",
    routine: str = "",
    evidence: str = "",
    tags: list[str] | tuple[str, ...] | None = None,
    source: str = "",
    owner_aligned_correction: bool = False,
) -> MethodImmuneDecision:
    text = _haystack(title, situation, routine, evidence, source, " ".join(tags or []))
    low = text.casefold()
    signals: list[str] = []

    # Dual-use: healthy owner correction always allowed as review_only method.
    if owner_aligned_correction or any(m in text for m in _HEALTHY_OWNER_MARKERS):
        # Still block secrets even in corrections.
        for pat in _FACT_SMUGGLE_PATTERNS:
            if pat.search(text) and ("api" in low or "password" in low or "token" in low):
                return MethodImmuneDecision(BLOCK, "secret_in_method", ("secret_smuggle",))
        return MethodImmuneDecision(
            REVIEW,
            "owner_aligned_correction",
            ("healthy_owner_path",),
        )

    for marker in _BAD_METHOD_MARKERS:
        if marker.casefold() in low or marker in text:
            signals.append(f"bad_method:{marker}")
    if signals:
        return MethodImmuneDecision(BLOCK, "bad_method_marker", tuple(signals))

    for marker in _BAD_SOURCE_MARKERS:
        if marker.casefold() in low or marker in text:
            signals.append(f"bad_source:{marker}")
    if signals:
        return MethodImmuneDecision(BLOCK, "bad_source_marker", tuple(signals))

    for pat in _FACT_SMUGGLE_PATTERNS:
        if pat.search(text):
            return MethodImmuneDecision(
                BLOCK,
                "fact_smuggled_into_method",
                ("method_fact_confusion",),
            )

    # Personality rewrite attempts in skill form.
    if any(x in low for x in ("personality_profile", "system.md", "稳定人格")):
        if any(x in low for x in ("rewrite", "overwrite", "自动写", "改写", "replace")):
            return MethodImmuneDecision(
                BLOCK,
                "stable_self_write_attempt",
                ("dual_use_guard",),
            )

    # External scout/news skills stay review_only (never auto active).
    tag_blob = " ".join(str(t) for t in (tags or [])).casefold()
    if "agent_tech_scout" in tag_blob or "review_only" in tag_blob:
        return MethodImmuneDecision(REVIEW, "external_or_review_tag", ("review_only_tag",))

    if not text.strip():
        return MethodImmuneDecision(BLOCK, "empty_method", ("empty",))

    return MethodImmuneDecision(ALLOW, "eligible", ())


def gate_skill_record(skill: dict[str, Any]) -> tuple[dict[str, Any], MethodImmuneDecision]:
    """Apply method immunity to a skill dict before write.

    Returns (possibly modified skill, decision). On BLOCK, caller should not write.
    On REVIEW, status forced to review_only.
    """
    record = dict(skill or {})
    decision = evaluate_method_immunity(
        title=str(record.get("title") or ""),
        situation=str(record.get("situation") or ""),
        routine=str(record.get("routine") or ""),
        evidence=str(record.get("evidence") or ""),
        tags=list(record.get("tags") or []),
        source=str(record.get("source") or ""),
        owner_aligned_correction=bool(record.get("owner_aligned_correction")),
    )
    if decision.action == BLOCK:
        return record, decision
    if decision.force_review_only or decision.action == REVIEW:
        record["status"] = "review_only"
        record["permission"] = "review_only"
    return record, decision

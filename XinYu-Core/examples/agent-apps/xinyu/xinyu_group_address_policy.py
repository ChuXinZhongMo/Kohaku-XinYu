"""Decide how to address a group member, and guard the visible reply (plan §4.6 / §6.7).

Address candidate priority:
1. member self-preference / owner label (member.preferred_address)
2. the safe alias the current speaker just used for this member
3. a stable peer alias (repeated / multiple users)
4. group card, then nickname, only if nothing better and not account/junk
5. neutral ("你" / "那位")

Hard rules: never output a QQ number, never promote a one-shot joke/insult, never
copy a derogatory peer alias, never blindly use the raw sender_name.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from xinyu_group_alias_extractor import alias_polarity, is_promotable_alias, normalize_alias

NEUTRAL_DEFAULT = "你"

_QQ_NUMBER_RUN_RE = re.compile(r"\b\d{5,}\b")
_INTERNAL_NEEDLES = (
    "sha256:",
    "member_hash",
    "group_hash",
    "actor_hash",
    "alias evidence",
    "group_social",
    "群画像",
    "成员画像",
    "根据我的记忆",
    "根据群社会记忆",
    "我查到你",
)


@dataclass(frozen=True)
class AddressRecommendation:
    address: str
    source: str
    confidence: float
    reason: str


def _safe_candidate(text: Any, *, in_do_not_call: set[str]) -> str:
    alias = normalize_alias(text)
    if not alias or alias in in_do_not_call:
        return ""
    if not is_promotable_alias(alias) or alias_polarity(alias) == "negative":
        return ""
    return alias


def recommend_address(
    member_profile: dict[str, Any],
    *,
    speaker_alias_for_member: str = "",
    owner_label: str = "",
    neutral_default: str = NEUTRAL_DEFAULT,
) -> AddressRecommendation:
    profile = member_profile or {}
    do_not_call = {normalize_alias(x) for x in profile.get("do_not_call", []) if normalize_alias(x)}

    # 1. member self-preference / owner label (preferred_address already reflects
    #    strong self/owner evidence)
    preferred = _safe_candidate(profile.get("preferred_address"), in_do_not_call=do_not_call)
    if preferred:
        return AddressRecommendation(preferred, "self_or_owner", 0.95, "member_preferred_address")

    owner = _safe_candidate(owner_label, in_do_not_call=do_not_call)
    if owner:
        return AddressRecommendation(owner, "owner_label", 0.9, "owner_group_label")

    # 2. the safe alias the current speaker just used (e.g. B said "阿棠")
    speaker_alias = _safe_candidate(speaker_alias_for_member, in_do_not_call=do_not_call)
    if speaker_alias:
        return AddressRecommendation(speaker_alias, "current_speaker_alias", 0.7, "follow_speaker_alias")

    # 3. a stable peer alias: repeated evidence or multiple distinct users
    stable = _best_stable_peer_alias(profile.get("aliases", []), do_not_call)
    if stable:
        return AddressRecommendation(stable, "peer_alias", 0.6, "stable_peer_alias")

    # 4. group card, then nickname (latest safe display sample)
    card = _latest_safe_history(profile.get("card_history", []), do_not_call)
    if card:
        return AddressRecommendation(card, "group_card", 0.4, "group_card_fallback")
    nickname = _latest_safe_history(profile.get("nickname_history", []), do_not_call)
    if nickname:
        return AddressRecommendation(nickname, "nickname", 0.3, "nickname_fallback")

    # 5. neutral
    return AddressRecommendation(neutral_default, "neutral", 0.2, "no_safe_alias")


def _best_stable_peer_alias(aliases: Any, do_not_call: set[str]) -> str:
    best = ""
    best_score = -1.0
    for alias in aliases if isinstance(aliases, list) else []:
        if not isinstance(alias, dict) or alias.get("blocked_as_address"):
            continue
        name = _safe_candidate(alias.get("normalized") or alias.get("text"), in_do_not_call=do_not_call)
        if not name:
            continue
        repeated = int(alias.get("evidence_count", 0)) >= 2 or len(alias.get("used_by_hashes", [])) >= 2
        if not repeated:
            continue
        score = float(alias.get("confidence", 0))
        if score > best_score:
            best, best_score = name, score
    return best


def _latest_safe_history(history: Any, do_not_call: set[str]) -> str:
    for entry in reversed(history if isinstance(history, list) else []):
        if not isinstance(entry, dict):
            continue
        name = _safe_candidate(entry.get("display_sample"), in_do_not_call=do_not_call)
        if name:
            return name
    return ""


def visible_reply_violations(reply: str) -> list[str]:
    """Detect obvious leaks in a visible group reply (QQ number / hash / internal
    memory talk). The post-processing guard uses this; it does not rewrite."""

    text = "" if reply is None else str(reply)
    violations: list[str] = []
    if _QQ_NUMBER_RUN_RE.search(text):
        violations.append("qq_number_leak")
    lowered = text.lower()
    for needle in _INTERNAL_NEEDLES:
        if needle.lower() in lowered:
            violations.append(f"internal_leak:{needle}")
    return violations

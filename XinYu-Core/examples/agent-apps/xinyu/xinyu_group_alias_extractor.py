"""Alias evidence extraction + promotion for group members (plan §4.4 / §6.3).

Two layers:
- extraction: pull alias evidence out of a message (self-naming, self-correction,
  peer reference), classify its source and polarity.
- promotion: fold evidence into a member profile's alias list, recompute the
  preferred address, and maintain a do-not-call list — never letting a one-shot
  joke/insult, a QQ-number, or a pronoun become a stable address.
"""

from __future__ import annotations

import re
from typing import Any

_NAME = r"[一-龥A-Za-z0-9_]{1,12}"

# self naming / preference
_CALL_ME_RE = re.compile(rf"(?:以后|请|都|你们)?叫我({_NAME})")
_I_AM_NAME_RE = re.compile(rf"我叫({_NAME})")
# self correction: stop calling me Y
_DONT_CALL_ME_RE = re.compile(rf"(?:别|不要|不用|别再)叫我({_NAME})")
# peer reference: name immediately before a speech/topic verb. The name is lazy
# so it stops at the earliest verb instead of swallowing it (the verbs are CJK
# chars that also match the name class).
_PEER_RE = re.compile(r"([一-龥A-Za-z0-9_]{1,12}?)(?:刚才|刚刚|说的|说过|问的|提到|那个|呢)")

# things that must never become a stable address
_PRONOUNS = {
    "我", "你", "他", "她", "它", "我们", "你们", "他们", "大家", "各位",
    "这个", "那个", "这位", "那位", "哥们", "兄弟", "朋友", "谁", "某人",
}
_INSULTS = {"笨蛋", "傻子", "傻逼", "蠢货", "废物", "白痴", "煞笔", "沙雕", "智障", "垃圾"}
_QQ_NUMBER_RE = re.compile(r"^\d{4,}$")
_URLISH_RE = re.compile(r"https?://|www\.|\.com|\.cn", re.IGNORECASE)

# source -> base confidence ceiling
_SOURCE_BASE = {
    "self_correction": 0.95,
    "self_reference": 0.9,
    "owner_label": 0.85,
    "peer_reference": 0.45,
    "reply_context": 0.5,
    "at_mention": 0.4,
    "group_card": 0.35,
    "nickname": 0.25,
}
_STRONG_SOURCES = {"self_reference", "self_correction", "owner_label"}


def normalize_alias(text: Any) -> str:
    clean = re.sub(r"\s+", "", "" if text is None else str(text))
    return clean.strip("。.,，!！?？:：;；\"'`()（）[]【】")


def alias_polarity(text: str) -> str:
    return "negative" if normalize_alias(text) in _INSULTS else "neutral"


def is_promotable_alias(text: str) -> bool:
    alias = normalize_alias(text)
    if not (1 <= len(alias) <= 12):
        return False
    if alias in _PRONOUNS or alias in _INSULTS:
        return False
    if _QQ_NUMBER_RE.match(alias) or _URLISH_RE.search(alias):
        return False
    return True


def extract_alias_evidence(text: str) -> list[dict[str, Any]]:
    """Evidence with subject 'self' (the speaker) or 'other' (a named member)."""

    source_text = "" if text is None else str(text)
    evidence: list[dict[str, Any]] = []

    for match in _DONT_CALL_ME_RE.finditer(source_text):
        evidence.append(_make(match.group(1), "self_correction", "self", reject=True))
    for match in _CALL_ME_RE.finditer(source_text):
        evidence.append(_make(match.group(1), "self_reference", "self"))
    for match in _I_AM_NAME_RE.finditer(source_text):
        evidence.append(_make(match.group(1), "self_reference", "self"))
    for match in _PEER_RE.finditer(source_text):
        evidence.append(_make(match.group(1), "peer_reference", "other"))

    # de-dup by (normalized, source, subject, reject)
    seen: set[tuple] = set()
    unique: list[dict[str, Any]] = []
    for item in evidence:
        key = (item["normalized"], item["source"], item["subject"], item["reject"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _make(alias: str, source: str, subject: str, *, reject: bool = False) -> dict[str, Any]:
    normalized = normalize_alias(alias)
    return {
        "alias_text": alias,
        "normalized": normalized,
        "source": source,
        "subject": subject,
        "polarity": alias_polarity(normalized),
        "reject": reject,
        "promotable": is_promotable_alias(normalized),
    }


def update_member_alias(
    member: dict[str, Any],
    *,
    alias: str,
    source: str,
    observed_at: str,
    used_by_hash: str = "",
    polarity: str = "neutral",
) -> None:
    """Fold one alias observation into the member profile (mutates in place)."""

    normalized = normalize_alias(alias)
    if not normalized:
        return
    aliases = member.setdefault("aliases", [])
    entry = next((a for a in aliases if isinstance(a, dict) and a.get("normalized") == normalized), None)
    if entry is None:
        entry = {
            "text": normalized,
            "normalized": normalized,
            "sources": [],
            "used_by_hashes": [],
            "evidence_count": 0,
            "confidence": 0.0,
            "first_seen_at": observed_at,
            "blocked_as_address": False,
        }
        aliases.append(entry)
    if source not in entry["sources"]:
        entry["sources"].append(source)
    if used_by_hash and used_by_hash not in entry["used_by_hashes"]:
        entry["used_by_hashes"].append(used_by_hash)
    entry["evidence_count"] = int(entry.get("evidence_count", 0)) + 1
    entry["last_seen_at"] = observed_at
    if polarity == "negative" or not is_promotable_alias(normalized):
        entry["blocked_as_address"] = True
    entry["confidence"] = _confidence(entry)


def _confidence(entry: dict[str, Any]) -> float:
    sources = entry.get("sources", [])
    base = max((_SOURCE_BASE.get(s, 0.2) for s in sources), default=0.2)
    # repeated peer evidence / multiple distinct users raise a weak alias
    count_bonus = min(0.2, 0.05 * max(0, int(entry.get("evidence_count", 1)) - 1))
    users_bonus = min(0.15, 0.05 * max(0, len(entry.get("used_by_hashes", [])) - 1))
    if _STRONG_SOURCES.intersection(sources):
        return round(min(0.99, base + count_bonus), 3)
    return round(min(base + count_bonus + users_bonus, base if base < 0.5 else 0.85), 3)


def apply_self_evidence(member: dict[str, Any], evidence: list[dict[str, Any]], observed_at: str) -> None:
    """Apply self-referential evidence from the speaker's own message."""

    do_not_call = member.setdefault("do_not_call", [])
    for item in evidence:
        if item["subject"] != "self":
            continue
        normalized = item["normalized"]
        if item["reject"]:
            if normalized and normalized not in do_not_call:
                do_not_call.append(normalized)
            # also block any existing alias entry of that name
            for entry in member.get("aliases", []):
                if isinstance(entry, dict) and entry.get("normalized") == normalized:
                    entry["blocked_as_address"] = True
            continue
        if not item["promotable"]:
            continue
        update_member_alias(
            member,
            alias=normalized,
            source=item["source"],
            observed_at=observed_at,
            polarity=item["polarity"],
        )
    recompute_preferred_address(member)


def recompute_preferred_address(member: dict[str, Any]) -> None:
    do_not_call = set(member.get("do_not_call", []))
    candidates = [
        a
        for a in member.get("aliases", [])
        if isinstance(a, dict)
        and not a.get("blocked_as_address")
        and a.get("normalized") not in do_not_call
        and is_promotable_alias(a.get("normalized", ""))
    ]
    if not candidates:
        member["preferred_address"] = ""
        return
    # strong-source aliases outrank weak ones regardless of count
    def rank(a: dict[str, Any]) -> tuple:
        strong = bool(_STRONG_SOURCES.intersection(a.get("sources", [])))
        return (strong, float(a.get("confidence", 0)), int(a.get("evidence_count", 0)))

    best = max(candidates, key=rank)
    member["preferred_address"] = best["normalized"]

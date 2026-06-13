"""Resolve names / references in a group message to group members (plan §4.5 / §6.4).

Resolution priority:
1. reply-quote / @ target -> a concrete member.
2. exact, unique alias match in the current group.
3. "刚才/上面 ... 的人/那个" + recent-speaker window.
4. otherwise unresolved (never guess; ambiguous aliases stay unresolved).

This resolves *subject* only. Whether/how to address that member is decided by
xinyu_group_address_policy — an insult alias can resolve who is meant without
ever becoming an address.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from xinyu_group_alias_extractor import normalize_alias

_RECENT_REF_RE = re.compile(r"(刚才|刚刚|上面|前面).{0,8}(的人|那个|那位|说的|发的)")
_SECOND_PERSON_RE = re.compile(r"你")


@dataclass(frozen=True)
class ResolvedGroupEntity:
    member_hash: str
    alias_used: str
    confidence: float
    reason: str
    source: str
    ambiguous_candidates: tuple[str, ...] = field(default_factory=tuple)

    @property
    def resolved(self) -> bool:
        return bool(self.member_hash)


def _alias_index(members: dict[str, Any]) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for member_hash, member in members.items():
        if not isinstance(member, dict):
            continue
        names: set[str] = set()
        for alias in member.get("aliases", []):
            if isinstance(alias, dict):
                normalized = normalize_alias(alias.get("normalized") or alias.get("text"))
                if normalized:
                    names.add(normalized)
        preferred = normalize_alias(member.get("preferred_address"))
        if preferred:
            names.add(preferred)
        for name in names:
            index.setdefault(name, [])
            if member_hash not in index[name]:
                index[name].append(member_hash)
    return index


def _alias_confidence(member: dict[str, Any], normalized: str) -> float:
    for alias in member.get("aliases", []):
        if isinstance(alias, dict) and normalize_alias(alias.get("normalized") or alias.get("text")) == normalized:
            return float(alias.get("confidence", 0.6))
    return 0.6


def resolve_group_entities(
    text: str,
    *,
    group_state: dict[str, Any],
    actor_member_hash: str = "",
    rich_context: dict[str, Any] | None = None,
) -> list[ResolvedGroupEntity]:
    source_text = "" if text is None else str(text)
    members = group_state.get("members") if isinstance(group_state.get("members"), dict) else {}
    rich = rich_context or {}
    results: list[ResolvedGroupEntity] = []
    resolved_hashes: set[str] = set()

    # 1. reply quote / @ target
    reply_to = str(rich.get("reply_to_member_hash") or "")
    if reply_to and _SECOND_PERSON_RE.search(source_text):
        results.append(ResolvedGroupEntity(reply_to, "你", 0.85, "reply_quote_second_person", "reply_context"))
        resolved_hashes.add(reply_to)
    for at_hash in rich.get("at_member_hashes", []) or []:
        at_hash = str(at_hash)
        if at_hash and at_hash not in resolved_hashes:
            results.append(ResolvedGroupEntity(at_hash, "", 0.8, "at_mention", "at_mention"))
            resolved_hashes.add(at_hash)

    # 2. exact, unique alias match
    index = _alias_index(members)
    matched_any_name = False
    for alias, candidates in index.items():
        if alias not in source_text:
            continue
        matched_any_name = True
        if len(candidates) == 1:
            member_hash = candidates[0]
            if member_hash in resolved_hashes:
                continue
            conf = _alias_confidence(members.get(member_hash, {}), alias)
            results.append(ResolvedGroupEntity(member_hash, alias, conf, "exact_alias_unique", "alias_match"))
            resolved_hashes.add(member_hash)
        else:
            results.append(
                ResolvedGroupEntity("", alias, 0.0, "alias_collision_unresolved", "alias_match", tuple(candidates))
            )

    # 3. recent-speaker window for vague references (only if no concrete name matched)
    if not matched_any_name and _RECENT_REF_RE.search(source_text):
        member_hash = _last_distinct_speaker(group_state, exclude=actor_member_hash)
        if member_hash and member_hash not in resolved_hashes:
            results.append(ResolvedGroupEntity(member_hash, "", 0.55, "recent_speaker_window", "recent_window"))
            resolved_hashes.add(member_hash)

    return results


def _last_distinct_speaker(group_state: dict[str, Any], *, exclude: str) -> str:
    speakers = group_state.get("recent_speakers") if isinstance(group_state.get("recent_speakers"), list) else []
    for entry in reversed(speakers):
        if not isinstance(entry, dict):
            continue
        member_hash = str(entry.get("member_hash") or "")
        if member_hash and member_hash != exclude:
            return member_hash
    return ""

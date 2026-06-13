"""Compact group social context for the main model (plan §4.7 / §6.6).

Builds a short ``[group_social_context]`` block: current group topic, the current
speaker's group-local address, and resolved mentioned members with the address to
use. It never emits hashes, QQ numbers, or internal memory talk — only natural
addresses and short topic summaries.

Gated by ``XINYU_GROUP_SOCIAL_ENABLED`` (default off) so it is inert until rolled
out; with it off the assembler returns no lines and touches nothing.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from xinyu_group_address_policy import recommend_address
from xinyu_group_entity_resolver import resolve_group_entities
from xinyu_group_social_ids import group_hash, group_member_hash
from xinyu_group_social_store import read_social_state, safe_display_sample

_MAX_MENTIONS = 5


def group_social_enabled() -> bool:
    return os.environ.get("XINYU_GROUP_SOCIAL_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}


def build_group_social_sidecar(view: dict[str, Any]) -> list[str]:
    """Render a prepared view into the bracketed sidecar block (pure)."""

    speaker_address = safe_display_sample(view.get("speaker_address"))
    topic = safe_display_sample(view.get("recent_topic"))
    mentions = [
        m for m in (view.get("mentions") or []) if isinstance(m, dict) and safe_display_sample(m.get("address"))
    ][:_MAX_MENTIONS]
    if not (speaker_address or topic or mentions):
        return []

    lines = ["[group_social_context]"]
    if topic:
        lines.append(f"- 当前群最近在聊：{topic}")
    if speaker_address:
        lines.append(f"- 当前发言人本群可称呼：{speaker_address}")
    for m in mentions:
        addr = safe_display_sample(m.get("address"))
        unresolved = m.get("unresolved")
        if unresolved:
            lines.append("- 话里提到的某位群友未能唯一确认；用自然中性指代或自然追问，别猜。")
        else:
            lines.append(f"- 话里提到的群友可称呼：{addr}")
    lines.append("- 称呼约束：优先群内真实叫法；不要输出 QQ 号、内部 hash 或记忆机制；不确定就中性指代。")
    lines.append("[/group_social_context]")
    return lines


def assemble_group_social_view(root: Path, *, payload: dict[str, Any], text: str) -> dict[str, Any]:
    """Read social state for the current group, resolve mentions, choose
    addresses. Returns an empty view (no lines) when disabled or not a group."""

    if not group_social_enabled():
        return {"lines": [], "enabled": False}
    platform = str(payload.get("platform") or "qq")
    group_id = str(payload.get("group_id") or "").strip()
    if not group_id:
        return {"lines": [], "enabled": True, "is_group": False}

    g_hash = group_hash(platform, group_id)
    actor_hash = group_member_hash(platform, group_id, str(payload.get("user_id") or ""))
    state = read_social_state(root)
    group = state.get("groups", {}).get(g_hash, {}) if isinstance(state.get("groups"), dict) else {}
    members = group.get("members", {}) if isinstance(group.get("members"), dict) else {}

    rich = _rich_context(payload)
    entities = resolve_group_entities(text, group_state=group, actor_member_hash=actor_hash, rich_context=rich)

    speaker_address = recommend_address(members.get(actor_hash, {})).address
    mentions: list[dict[str, Any]] = []
    for entity in entities:
        if not entity.resolved:
            mentions.append({"unresolved": True})
            continue
        rec = recommend_address(
            members.get(entity.member_hash, {}),
            speaker_alias_for_member=entity.alias_used,
        )
        mentions.append({"address": rec.address, "member_hash": entity.member_hash, "source": rec.source})

    recent_topics = group.get("recent_topics") if isinstance(group.get("recent_topics"), list) else []
    recent_topic = ""
    if recent_topics and isinstance(recent_topics[-1], dict):
        recent_topic = str(recent_topics[-1].get("summary") or "")

    view = {
        "recent_topic": recent_topic,
        "speaker_address": speaker_address,
        "mentions": mentions,
        "enabled": True,
        "is_group": True,
    }
    view["lines"] = build_group_social_sidecar(view)
    return view


def _rich_context(payload: dict[str, Any]) -> dict[str, Any]:
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    return {
        "reply_to_member_hash": metadata.get("qq_reply_member_hash") or "",
        "at_member_hashes": metadata.get("qq_at_member_hashes") or [],
    }

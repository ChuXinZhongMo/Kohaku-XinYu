"""Group social observation entry point (plan §4.3 / §6.2).

Turns an incoming group message (triggered into the main turn, or shadow-only)
into an append-only social event and updates the derived group/member activity
state. It never writes owner-private memory and never triggers a reply.

Alias evidence extraction is layered on top in xinyu_group_alias_extractor; this
module only records presence/activity and a recent-speaker window for later
entity resolution.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_group_social_ids import group_hash, group_member_hash, message_hash
from xinyu_group_social_store import (
    append_social_event,
    read_social_state,
    safe_display_sample,
    write_social_state,
)

RECENT_SPEAKER_KEEP = 12
_EXCERPT_MAX = 260


def _safe_str(value: Any, default: str = "") -> str:
    return default if value is None else str(value)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _excerpt(text: Any, limit: int = _EXCERPT_MAX) -> str:
    clean = re.sub(r"\s+", " ", _safe_str(text)).strip()
    return clean if len(clean) <= limit else clean[: max(0, limit - 3)].rstrip() + "..."


def observe_group_social_event(
    root: Path,
    *,
    event: dict[str, Any],
    text: str,
    triggered: bool = False,
    max_text_chars: int = _EXCERPT_MAX,
) -> dict[str, Any]:
    """Record one observed group message. Returns diagnostic notes; a failure
    here returns notes rather than raising so the chat turn is never blocked."""

    platform = _safe_str(event.get("platform"), "qq")
    raw_group_id = _safe_str(event.get("group_id")).strip()
    raw_user_id = _safe_str(event.get("user_id")).strip()
    raw_message_id = _safe_str(event.get("message_id")).strip()
    if not raw_group_id:
        return {"recorded": False, "notes": ["group_social_skip_no_group_id"], "reply_policy": "no_reply"}

    g_hash = group_hash(platform, raw_group_id)
    m_hash = group_member_hash(platform, raw_group_id, raw_user_id)
    msg_hash = message_hash(platform, raw_group_id, raw_message_id)
    observed_at = _now_iso()
    excerpt = _excerpt(text, limit=max(40, int(max_text_chars)))

    metadata = event.get("metadata") if isinstance(event.get("metadata"), dict) else {}
    card_sample = safe_display_sample(metadata.get("qq_sender_card") or event.get("sender_card"))
    nickname_sample = safe_display_sample(metadata.get("qq_sender_nickname") or event.get("sender_nickname"))

    row = {
        "observed_at": observed_at,
        "source": "qq_group_social_observer",
        "reply_policy": "no_reply" if not triggered else "triggered_main_turn",
        "stable_memory_write": "blocked",
        "owner_relationship_write": "blocked",
        "privacy_scope": "group_context",
        "group_hash": g_hash,
        "actor_member_hash": m_hash,
        "message_hash": msg_hash,
        "triggered": bool(triggered),
        "text_excerpt": excerpt,
    }
    append_result = append_social_event(root, row)

    state = read_social_state(root)
    _update_activity(
        state,
        group_hash=g_hash,
        member_hash=m_hash,
        observed_at=observed_at,
        excerpt=excerpt,
        card_sample=card_sample,
        nickname_sample=nickname_sample,
    )
    write_result = write_social_state(root, state)

    notes = ["group_social_observed", "no_reply" if not triggered else "triggered"]
    notes.extend(append_result.get("notes", []))
    notes.extend(write_result.get("notes", []))
    return {
        "recorded": bool(append_result.get("recorded")),
        "group_hash": g_hash,
        "actor_member_hash": m_hash,
        "message_hash": msg_hash,
        "reply_policy": row["reply_policy"],
        "owner_relationship_write": "blocked",
        "notes": notes,
    }


def _update_activity(
    state: dict[str, Any],
    *,
    group_hash: str,
    member_hash: str,
    observed_at: str,
    excerpt: str,
    card_sample: str,
    nickname_sample: str,
) -> None:
    state["event_count"] = int(state.get("event_count", 0)) + 1
    groups = state.setdefault("groups", {})
    group = groups.setdefault(group_hash, {})
    group.setdefault("first_seen_at", observed_at)
    group["last_seen_at"] = observed_at

    members = group.setdefault("members", {})
    member = members.setdefault(member_hash, {})
    member.setdefault("first_seen_at", observed_at)
    member["last_seen_at"] = observed_at
    member["message_count"] = int(member.get("message_count", 0)) + 1
    member.setdefault("aliases", [])
    member.setdefault("do_not_call", [])
    _track_history(member, "card_history", card_sample, observed_at)
    _track_history(member, "nickname_history", nickname_sample, observed_at)

    group["active_member_count"] = len(members)
    speakers = group.setdefault("recent_speakers", [])
    speakers.append({"member_hash": member_hash, "observed_at": observed_at, "excerpt": excerpt})
    if len(speakers) > RECENT_SPEAKER_KEEP:
        del speakers[: len(speakers) - RECENT_SPEAKER_KEEP]


def _track_history(member: dict[str, Any], key: str, sample: str, observed_at: str) -> None:
    if not sample:
        return
    history = member.setdefault(key, [])
    for entry in history:
        if isinstance(entry, dict) and entry.get("display_sample") == sample:
            entry["last_seen_at"] = observed_at
            return
    history.append({"display_sample": sample, "first_seen_at": observed_at, "last_seen_at": observed_at})

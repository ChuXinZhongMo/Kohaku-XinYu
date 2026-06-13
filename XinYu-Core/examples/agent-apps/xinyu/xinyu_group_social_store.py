"""Append-only storage + derived state + Markdown projection for group social
memory (plan §4.2 / §5).

Boundaries enforced here:
- Long-term files keep only hashes and short sanitized display samples; raw QQ
  group/user/message ids and QQ-number-like display values are filtered out.
- Every write is wrapped so a disk failure returns diagnostic notes instead of
  breaking the live chat turn.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from state_service import append_jsonl, atomic_write_text

from xinyu_group_social_ids import path_segment

EVENTS_REL = Path("runtime/group_social/group_social_events.jsonl")
ALIAS_REL = Path("runtime/group_social/group_alias_evidence.jsonl")
STATE_REL = Path("runtime/group_social/group_social_state.json")
GROUPS_INDEX_REL = Path("memory/groups/index.md")

_QQ_NUMBER_RE = re.compile(r"^\d{5,}$")
_DISPLAY_MAX = 24


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _safe_str(value: Any, default: str = "") -> str:
    return default if value is None else str(value)


def safe_display_sample(value: Any) -> str:
    """A display sample safe to persist: short, no raw QQ-number-like strings."""

    text = re.sub(r"\s+", " ", _safe_str(value)).strip()
    if not text or _QQ_NUMBER_RE.match(text):
        return ""
    return text[:_DISPLAY_MAX]


def append_social_event(root: Path, event: dict[str, Any]) -> dict[str, Any]:
    return _safe_append(Path(root) / EVENTS_REL, event, kind="group_social_event")


def append_alias_evidence(root: Path, evidence: dict[str, Any]) -> dict[str, Any]:
    return _safe_append(Path(root) / ALIAS_REL, evidence, kind="group_alias_evidence")


def _safe_append(path: Path, row: dict[str, Any], *, kind: str) -> dict[str, Any]:
    try:
        append_jsonl(path, row)
        return {"recorded": True, "path": str(path), "notes": [f"{kind}_recorded"]}
    except OSError as exc:
        # Never block the chat turn on a disk error.
        print(f"[xinyu_core_bridge] {kind} append failed: {type(exc).__name__}: {exc}", flush=True)
        return {"recorded": False, "path": str(path), "notes": [f"{kind}_write_error:{type(exc).__name__}"]}


def read_social_state(root: Path) -> dict[str, Any]:
    path = Path(root) / STATE_REL
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {"groups": {}, "event_count": 0, "updated_at": ""}
    if not isinstance(data, dict):
        return {"groups": {}, "event_count": 0, "updated_at": ""}
    data.setdefault("groups", {})
    data.setdefault("event_count", 0)
    return data


def write_social_state(root: Path, state: dict[str, Any]) -> dict[str, Any]:
    path = Path(root) / STATE_REL
    payload = dict(state)
    payload["updated_at"] = _now_iso()
    try:
        atomic_write_text(path, json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2))
        return {"recorded": True, "path": str(path), "notes": ["group_social_state_written"]}
    except OSError as exc:
        print(f"[xinyu_core_bridge] group_social_state write failed: {exc}", flush=True)
        return {"recorded": False, "path": str(path), "notes": [f"group_social_state_write_error:{type(exc).__name__}"]}


def member_markdown_path(root: Path, group_hash: str, member_hash: str) -> Path:
    return Path(root) / "memory" / "groups" / path_segment(group_hash) / "members" / f"{path_segment(member_hash)}.md"


def group_markdown_path(root: Path, group_hash: str) -> Path:
    return Path(root) / "memory" / "groups" / path_segment(group_hash) / "group_profile.md"


def project_member_markdown(root: Path, group_hash: str, member_hash: str, profile: dict[str, Any]) -> dict[str, Any]:
    path = member_markdown_path(root, group_hash, member_hash)
    aliases = profile.get("aliases") if isinstance(profile.get("aliases"), list) else []
    alias_lines = [
        f"- {safe_display_sample(a.get('text')) or '(filtered)'} "
        f"(conf {float(a.get('confidence', 0)):.2f}, {a.get('evidence_count', 0)} 证据)"
        for a in aliases
        if isinstance(a, dict) and safe_display_sample(a.get("text"))
    ] or ["- (none)"]
    do_not_call = [safe_display_sample(x) for x in profile.get("do_not_call", []) if safe_display_sample(x)]
    content = "\n".join(
        [
            "---",
            "memory_type: group_member_profile",
            "privacy_scope: group_context",
            "owner_relationship_write: blocked",
            f"group_hash: {group_hash}",
            f"member_hash: {member_hash}",
            f"updated_at: {_now_iso()}",
            "---",
            "",
            "# Group Member Profile",
            f"- preferred_address: {safe_display_sample(profile.get('preferred_address')) or '(unset)'}",
            f"- message_count: {int(profile.get('message_count', 0))}",
            f"- first_seen_at: {_safe_str(profile.get('first_seen_at')) or 'unknown'}",
            f"- last_seen_at: {_safe_str(profile.get('last_seen_at')) or 'unknown'}",
            "",
            "## Aliases (group-local, evidence-backed)",
            *alias_lines,
            "",
            "## Do Not Call",
            *([f"- {x}" for x in do_not_call] or ["- (none)"]),
            "",
            "## Boundary",
            "- raw QQ id is never stored here; only group-local hashes and aliases.",
        ]
    )
    try:
        atomic_write_text(path, content)
        return {"recorded": True, "path": str(path), "notes": ["group_member_markdown_written"]}
    except OSError as exc:
        print(f"[xinyu_core_bridge] group member markdown write failed: {exc}", flush=True)
        return {"recorded": False, "path": str(path), "notes": [f"group_member_markdown_write_error:{type(exc).__name__}"]}


def project_group_markdown(root: Path, group_hash: str, profile: dict[str, Any]) -> dict[str, Any]:
    path = group_markdown_path(root, group_hash)
    topics = profile.get("recent_topics") if isinstance(profile.get("recent_topics"), list) else []
    topic_lines = [
        f"- {safe_display_sample(t.get('summary')) or '(filtered)'} (conf {float(t.get('confidence', 0)):.2f})"
        for t in topics
        if isinstance(t, dict)
    ] or ["- (none)"]
    content = "\n".join(
        [
            "---",
            "memory_type: group_profile",
            "privacy_scope: group_context",
            "owner_relationship_write: blocked",
            f"group_hash: {group_hash}",
            f"updated_at: {_now_iso()}",
            "---",
            "",
            "# Group Profile",
            f"- active_member_count: {int(profile.get('active_member_count', 0))}",
            f"- first_seen_at: {_safe_str(profile.get('first_seen_at')) or 'unknown'}",
            f"- last_seen_at: {_safe_str(profile.get('last_seen_at')) or 'unknown'}",
            "",
            "## Recent Topics",
            *topic_lines,
        ]
    )
    try:
        atomic_write_text(path, content)
        return {"recorded": True, "path": str(path), "notes": ["group_profile_markdown_written"]}
    except OSError as exc:
        print(f"[xinyu_core_bridge] group profile markdown write failed: {exc}", flush=True)
        return {"recorded": False, "path": str(path), "notes": [f"group_profile_markdown_write_error:{type(exc).__name__}"]}


def project_groups_index(root: Path, state: dict[str, Any]) -> dict[str, Any]:
    path = Path(root) / GROUPS_INDEX_REL
    groups = state.get("groups") if isinstance(state.get("groups"), dict) else {}
    lines = [
        f"- {group_hash} · 成员 {len(g.get('members', {}) if isinstance(g, dict) else {})} · "
        f"last_seen {_safe_str((g or {}).get('last_seen_at')) or 'unknown'}"
        for group_hash, g in groups.items()
    ] or ["- (no groups observed yet)"]
    content = "\n".join(
        [
            "---",
            "memory_type: group_index",
            "privacy_scope: group_context",
            f"updated_at: {_now_iso()}",
            "---",
            "",
            "# Group Index",
            *lines,
        ]
    )
    try:
        atomic_write_text(path, content)
        return {"recorded": True, "path": str(path), "notes": ["group_index_written"]}
    except OSError as exc:
        print(f"[xinyu_core_bridge] group index write failed: {exc}", flush=True)
        return {"recorded": False, "path": str(path), "notes": [f"group_index_write_error:{type(exc).__name__}"]}

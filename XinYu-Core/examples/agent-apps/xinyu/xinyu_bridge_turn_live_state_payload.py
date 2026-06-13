from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from xinyu_bridge_values import as_bool, safe_str


@dataclass(frozen=True)
class LiveTurnPayloadState:
    metadata: dict[str, Any]
    session_key: str
    is_owner: bool
    source_line: str
    relationship_line: str
    sender_name: str


def build_live_turn_payload_state(runtime: Any, payload: dict[str, Any]) -> LiveTurnPayloadState:
    metadata = payload.get("metadata")
    if not isinstance(metadata, dict):
        metadata = {}
    session_key = runtime._session_key(payload)
    is_owner = as_bool(metadata.get("is_owner_user"), default=False)
    is_trusted = as_bool(metadata.get("is_trusted_user"), default=False)
    message_type = safe_str(payload.get("message_type"))
    sender_name = safe_str(payload.get("sender_name")) or safe_str(payload.get("user_id"))
    source_line = "QQ group chat" if message_type.startswith("group_") else "QQ private chat"
    relationship_line = "owner" if is_owner else ("trusted contact" if is_trusted else "external contact")
    return LiveTurnPayloadState(
        metadata=metadata,
        session_key=session_key,
        is_owner=is_owner,
        source_line=source_line,
        relationship_line=relationship_line,
        sender_name=sender_name,
    )


def live_turn_pressure_line(visible_turn: Any, *, is_owner: bool) -> str:
    if visible_turn.owner_style_pressure and is_owner:
        return "style pressure: answer through the next line, not through a report."
    return "ordinary live turn."


def live_turn_residue_line(previous_residue: Any) -> str:
    if previous_residue.active:
        return (
            f"previous residue: {previous_residue.tone}, "
            f"{previous_residue.felt_residue}, strength={previous_residue.decayed_strength}"
        )
    return "previous residue: none"

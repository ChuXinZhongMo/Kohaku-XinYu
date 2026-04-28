"""Gateway domain models."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..types import (
    ActorScope,
    JSONValue,
    PrivacyScope,
    RawPayload,
    SourceChannel,
    TraceContext,
    TurnKind,
    safe_json_mapping,
)


@dataclass(frozen=True, slots=True)
class GatewayMetadata:
    platform: str = ""
    adapter: str = ""
    message_type: str = ""
    raw_message_id: str = ""
    raw_session_id: str = ""
    extra: dict[str, JSONValue] = field(default_factory=dict)

    def to_json(self) -> dict[str, JSONValue]:
        return {
            "platform": self.platform,
            "adapter": self.adapter,
            "message_type": self.message_type,
            "raw_message_id": self.raw_message_id,
            "raw_session_id": self.raw_session_id,
            "extra": dict(self.extra),
        }


@dataclass(frozen=True, slots=True)
class ActorContext:
    actor_id: str = ""
    display_name: str = ""
    session_id: str = ""
    group_id: str = ""
    source_channel: SourceChannel = SourceChannel.UNKNOWN
    actor_scope: ActorScope = ActorScope.UNKNOWN
    privacy_scope: PrivacyScope = PrivacyScope.UNKNOWN
    is_owner: bool = False
    priority_learning_group: bool = False

    def to_json(self) -> dict[str, JSONValue]:
        return {
            "actor_id": self.actor_id,
            "display_name": self.display_name,
            "session_id": self.session_id,
            "group_id": self.group_id,
            "source_channel": self.source_channel.value,
            "actor_scope": self.actor_scope.value,
            "privacy_scope": self.privacy_scope.value,
            "is_owner": self.is_owner,
            "priority_learning_group": self.priority_learning_group,
        }


@dataclass(frozen=True, slots=True)
class AttachmentRef:
    name: str = ""
    path: str = ""
    url: str = ""
    content_type: str = ""
    size_bytes: int | None = None

    @property
    def local_path(self) -> Path | None:
        if not self.path:
            return None
        return Path(self.path)

    def to_json(self) -> dict[str, JSONValue]:
        return {
            "name": self.name,
            "path": self.path,
            "url": self.url,
            "content_type": self.content_type,
            "size_bytes": self.size_bytes,
        }


@dataclass(frozen=True, slots=True)
class InboundTurn:
    text: str
    kind: TurnKind
    actor: ActorContext
    timestamp: str
    trace: TraceContext
    attachments: tuple[AttachmentRef, ...] = field(default_factory=tuple)
    metadata: GatewayMetadata = field(default_factory=GatewayMetadata)
    raw_payload: dict[str, JSONValue] = field(default_factory=dict)

    @property
    def has_text(self) -> bool:
        return bool(self.text.strip())

    @property
    def has_attachments(self) -> bool:
        return bool(self.attachments)

    @property
    def is_human(self) -> bool:
        return self.kind in {TurnKind.HUMAN_CHAT, TurnKind.OBSERVATION, TurnKind.FILE_ATTACHMENT}

    def compact_text(self, limit: int = 2000) -> str:
        clean = " ".join(self.text.split())
        return clean[:limit]

    def to_json(self, *, include_raw: bool = False) -> dict[str, JSONValue]:
        data: dict[str, JSONValue] = {
            "text": self.text,
            "kind": self.kind.value,
            "actor": self.actor.to_json(),
            "timestamp": self.timestamp,
            "trace": self.trace.to_json(),
            "attachments": [attachment.to_json() for attachment in self.attachments],
            "metadata": self.metadata.to_json(),
        }
        if include_raw:
            data["raw_payload"] = dict(self.raw_payload)
        return data


@dataclass(frozen=True, slots=True)
class BridgeReply:
    accepted: bool
    reply: str = ""
    memory_changed: bool | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)
    route: str = ""
    trace_id: str = ""
    claim_id: str = ""
    candidate_claimed: bool = False
    extra: dict[str, JSONValue] = field(default_factory=dict)

    def to_json(self) -> dict[str, JSONValue]:
        data: dict[str, JSONValue] = {
            "accepted": self.accepted,
            "reply": self.reply,
            "notes": list(self.notes),
        }
        if self.memory_changed is not None:
            data["memory_changed"] = self.memory_changed
        if self.route:
            data["route"] = self.route
        if self.trace_id:
            data["trace_id"] = self.trace_id
        if self.claim_id:
            data["claim_id"] = self.claim_id
        if self.candidate_claimed:
            data["candidate_claimed"] = self.candidate_claimed
        data.update(self.extra)
        return data


def payload_metadata(payload: RawPayload) -> dict[str, JSONValue]:
    metadata = payload.get("metadata")
    return safe_json_mapping(metadata if isinstance(metadata, dict) else {})


def payload_str(payload: RawPayload, *names: str, default: str = "") -> str:
    for name in names:
        value: Any = payload.get(name)
        if value is not None:
            return str(value)
    return default


def payload_bool(payload: RawPayload, *names: str, default: bool = False) -> bool:
    for name in names:
        value: Any = payload.get(name)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"1", "true", "yes", "on"}:
                return True
            if lowered in {"0", "false", "no", "off"}:
                return False
        if value is not None:
            return bool(value)
    return default


"""Normalize raw bridge payloads into canonical inbound turns."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

from ..clock import SystemClock
from ..types import ActorScope, PrivacyScope, SourceChannel, TraceContext, TurnKind, safe_json_mapping
from .models import ActorContext, AttachmentRef, GatewayMetadata, InboundTurn, payload_bool, payload_metadata, payload_str


class TurnNormalizer:
    def __init__(self, *, clock: SystemClock | None = None, owner_user_ids: set[str] | None = None) -> None:
        self._clock = clock or SystemClock()
        self._owner_user_ids = owner_user_ids or set()

    def normalize(self, payload: Mapping[str, Any], *, default_kind: TurnKind = TurnKind.HUMAN_CHAT) -> InboundTurn:
        metadata = payload_metadata(payload)
        text = self._extract_text(payload)
        kind = self._detect_kind(payload, default_kind=default_kind)
        actor = self._actor_context(payload, metadata, kind)
        timestamp = payload_str(payload, "observed_at", "timestamp", default=self._clock.now_iso()).strip()
        trace = self._trace_context(payload, actor, timestamp)
        attachments = self._attachments(payload)
        gateway_metadata = GatewayMetadata(
            platform=payload_str(payload, "platform", default=str(metadata.get("platform", ""))).strip(),
            adapter=payload_str(payload, "adapter", default="qq_gateway").strip(),
            message_type=payload_str(payload, "message_type", default=str(metadata.get("message_type", ""))).strip(),
            raw_message_id=payload_str(payload, "message_id", default=str(metadata.get("message_id", ""))).strip(),
            raw_session_id=payload_str(payload, "session_id").strip(),
            extra=metadata,
        )
        return InboundTurn(
            text=text,
            kind=kind,
            actor=actor,
            timestamp=timestamp or self._clock.now_iso(),
            trace=trace,
            attachments=attachments,
            metadata=gateway_metadata,
            raw_payload=safe_json_mapping(payload),
        )

    def _extract_text(self, payload: Mapping[str, Any]) -> str:
        for key in ("text", "message", "content", "raw_message"):
            value = payload.get(key)
            if value is not None:
                return str(value).replace("\r\n", "\n").strip()
        return ""

    def _detect_kind(self, payload: Mapping[str, Any], *, default_kind: TurnKind) -> TurnKind:
        explicit = str(payload.get("kind") or payload.get("turn_kind") or "").strip().lower()
        for kind in TurnKind:
            if explicit in {kind.value, kind.name.lower()}:
                return kind
        if payload_bool(payload, "probe", default=False):
            return TurnKind.PROBE
        if payload_bool(payload, "maintenance", default=False):
            return TurnKind.MAINTENANCE
        if payload.get("claim_id") is not None and payload.get("status") is not None:
            return TurnKind.PROACTIVE_ACK
        if payload_bool(payload, "proactive", default=False):
            return TurnKind.PROACTIVE_CLAIM
        if payload.get("file") is not None or payload.get("attachments") is not None:
            return TurnKind.FILE_ATTACHMENT
        return default_kind

    def _actor_context(self, payload: Mapping[str, Any], metadata: Mapping[str, Any], kind: TurnKind) -> ActorContext:
        user_id = payload_str(payload, "user_id", "sender_id", default=str(metadata.get("user_id", ""))).strip()
        group_id = payload_str(payload, "group_id", default=str(metadata.get("group_id", ""))).strip()
        session_id = payload_str(payload, "session_id", default=str(metadata.get("session_id", ""))).strip()
        message_type = payload_str(payload, "message_type", default=str(metadata.get("message_type", ""))).strip()
        if not session_id:
            session_id = self._fallback_session_id(
                payload=payload,
                metadata=metadata,
                user_id=user_id,
                group_id=group_id,
                message_type=message_type,
            )
        metadata_owner = str(metadata.get("is_owner_user", "")).strip().lower() in {"1", "true", "yes", "on"}
        is_owner = (
            payload_bool(payload, "is_owner_user", default=False)
            or metadata_owner
            or bool(user_id and user_id in self._owner_user_ids)
        )
        priority_group = payload_bool(payload, "priority_learning_group", default=False) or bool(
            metadata.get("priority_learning_group")
        )

        if kind in {TurnKind.MAINTENANCE, TurnKind.PROBE, TurnKind.PROACTIVE_CLAIM, TurnKind.PROACTIVE_ACK}:
            source_channel = SourceChannel.MAINTENANCE if kind is TurnKind.MAINTENANCE else SourceChannel.SYSTEM
            actor_scope = ActorScope.SYSTEM
            privacy_scope = PrivacyScope.SYSTEM_INTERNAL
        elif priority_group:
            source_channel = SourceChannel.PRIORITY_LEARNING_GROUP
            actor_scope = ActorScope.GROUP_MEMBER
            privacy_scope = PrivacyScope.GROUP_CONTEXT
        elif group_id or message_type.startswith("group"):
            source_channel = SourceChannel.QQ_GROUP
            actor_scope = ActorScope.GROUP_MEMBER
            privacy_scope = PrivacyScope.GROUP_CONTEXT
        elif is_owner:
            source_channel = SourceChannel.OWNER_PRIVATE
            actor_scope = ActorScope.OWNER
            privacy_scope = PrivacyScope.OWNER_PRIVATE
        else:
            source_channel = SourceChannel.QQ_PRIVATE
            actor_scope = ActorScope.EXTERNAL_CONTACT
            privacy_scope = PrivacyScope.EXTERNAL_PRIVATE

        return ActorContext(
            actor_id=user_id,
            display_name=payload_str(payload, "nickname", "display_name", default=str(metadata.get("nickname", ""))).strip(),
            session_id=session_id,
            group_id=group_id,
            source_channel=source_channel,
            actor_scope=actor_scope,
            privacy_scope=privacy_scope,
            is_owner=is_owner,
            priority_learning_group=priority_group,
        )

    def _fallback_session_id(
        self,
        *,
        payload: Mapping[str, Any],
        metadata: Mapping[str, Any],
        user_id: str,
        group_id: str,
        message_type: str,
    ) -> str:
        platform = payload_str(payload, "platform", default=str(metadata.get("platform", "qq"))).strip() or "qq"
        lowered_type = message_type.lower()
        if group_id:
            return f"{platform}:group:{group_id}"
        if lowered_type.startswith("group"):
            return f"{platform}:group:unknown:{user_id}" if user_id else ""
        if user_id:
            return f"{platform}:private:{user_id}"
        return ""

    def _attachments(self, payload: Mapping[str, Any]) -> tuple[AttachmentRef, ...]:
        raw_items: list[Any] = []
        attachments = payload.get("attachments")
        if isinstance(attachments, list):
            raw_items.extend(attachments)
        file_value = payload.get("file")
        if file_value is not None:
            raw_items.append(file_value)

        refs: list[AttachmentRef] = []
        for item in raw_items:
            if isinstance(item, Mapping):
                size_value = item.get("size_bytes") or item.get("size")
                try:
                    size = int(size_value) if size_value is not None else None
                except (TypeError, ValueError):
                    size = None
                refs.append(
                    AttachmentRef(
                        name=str(item.get("name") or item.get("filename") or "").strip(),
                        path=str(item.get("path") or item.get("file_path") or "").strip(),
                        url=str(item.get("url") or "").strip(),
                        content_type=str(item.get("content_type") or item.get("mime") or "").strip(),
                        size_bytes=size,
                    )
                )
            elif item:
                refs.append(AttachmentRef(path=str(item).strip()))
        return tuple(refs)

    def _trace_context(self, payload: Mapping[str, Any], actor: ActorContext, timestamp: str) -> TraceContext:
        trace_id = payload_str(payload, "trace_id").strip()
        request_id = payload_str(payload, "request_id").strip()
        seed = "|".join(
            [
                timestamp,
                actor.session_id,
                actor.actor_id,
                payload_str(payload, "message_id").strip(),
                self._extract_text(payload)[:120],
            ]
        )
        digest = hashlib.sha256(seed.encode("utf-8", errors="replace")).hexdigest()[:16]
        return TraceContext(
            trace_id=trace_id or f"tr-{digest}",
            request_id=request_id or f"req-{digest}",
            session_hash=self._hash(actor.session_id),
            actor_hash=self._hash(actor.actor_id),
            started_at=timestamp,
            tags=(actor.source_channel.value, actor.actor_scope.value),
        )

    @staticmethod
    def _hash(value: str) -> str:
        if not value:
            return ""
        return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()[:12]

from __future__ import annotations

import asyncio
import contextlib
import json
import re
import signal
import sys
import time
import traceback
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from state_service import append_jsonl, atomic_write_json
from xinyu_gateway_ack_spool import SentAckSpool
from xinyu_group_shadow_observer import record_group_shadow_observation
from xinyu_image_context import build_image_context, is_image_learning_payload
from xinyu_codex_delegate import looks_like_owner_local_write_request
import xinyu_qq_attachment_resolver
import xinyu_qq_command_router
from xinyu_qq_cli import build_gateway_parser
from xinyu_qq_config import (
    COMMAND_PREFIX_CHARS,
    GatewayConfig,
    as_bool as _as_bool,
    as_int as _as_int,
    as_str_list as _as_str_list,
    load_json_object as _load_json,
)
from xinyu_qq_core_client import BridgeError, CoreBridgeClient
import xinyu_qq_forward_context
from xinyu_qq_models import PendingAction, PreparedMessage, RecentStickerImportState, ReplyTarget
from xinyu_qq_gateway_utils import hash_id as _hash_id
from xinyu_qq_gateway_utils import maybe_int as _maybe_int
from xinyu_qq_gateway_utils import now_iso as _now_iso
from xinyu_qq_gateway_utils import quiet_websockets_handshake_noise as _quiet_websockets_handshake_noise
from xinyu_qq_gateway_utils import safe_str as _safe_str
import xinyu_qq_normalizer
import xinyu_qq_outbox_client
import xinyu_qq_outbox_dispatcher
import xinyu_qq_rich_context
import xinyu_qq_server
import xinyu_qq_sender
import xinyu_qq_sticker_semantics
import xinyu_qq_trust_policy
from xinyu_visible_reply_guard import dedupe_visible_reply

try:
    import websockets
except ImportError as exc:  # pragma: no cover - exercised by startup scripts
    raise SystemExit("Missing dependency: websockets. Run: python -m pip install -r requirements-minimal.txt") from exc


GATEWAY_VERSION = "0.1.24"
GATEWAY_NAME = "xinyu_native_qq_gateway"
QQ_INBOUND_TRACE_REL = Path("runtime") / "qq_inbound_trace.jsonl"
QQ_RICH_CONTEXT_TRACE_REL = Path("runtime") / "qq_rich_context_trace.jsonl"
QQ_STICKER_IMPORT_TRACE_REL = Path("runtime") / "qq_sticker_import_trace.jsonl"
QQ_RECENT_STICKER_STATE_REL = Path("runtime") / "qq_recent_sticker_state.json"
SUPPORTED_IMAGE_SUFFIXES = xinyu_qq_attachment_resolver.SUPPORTED_IMAGE_SUFFIXES


class NativeQQGateway:
    def __init__(self, config: GatewayConfig, *, config_path: Path | None = None) -> None:
        self.config = config
        self.config_path = config_path
        self.xinyu_dir = Path(__file__).resolve().parent
        self.gateway_version = GATEWAY_VERSION
        self.client = CoreBridgeClient(
            chat_url=config.core_chat_url,
            codex_execute_url=config.codex_execute_url,
            learning_ingest_url=config.learning_ingest_url,
            sticker_import_url=config.sticker_import_url,
            package_install_url=config.package_install_url,
            review_inbox_command_url=config.review_inbox_command_url,
            goldmark_mark_url=config.goldmark_mark_url,
            qq_outbox_claim_url=config.qq_outbox_claim_url,
            qq_outbox_ack_url=config.qq_outbox_ack_url,
            message_ack_url=config.message_ack_url,
            token=config.bridge_token,
            timeout_seconds=config.timeout_seconds,
            gateway_version=GATEWAY_VERSION,
        )
        self.ack_spool = SentAckSpool(Path(config.gateway_ack_spool_path))
        self._pending_actions: dict[str, PendingAction] = {}
        self._websocket_connection_ids: dict[int, str] = {}
        self._action_lock = asyncio.Lock()
        self._event_tasks: set[asyncio.Task[Any]] = set()
        self._inbound_queue_lock = asyncio.Lock()
        self._inbound_session_queues: dict[str, asyncio.Queue[tuple[int, Any, dict[str, Any]]]] = {}
        self._inbound_session_tasks: dict[str, asyncio.Task[Any]] = {}
        self._arrival_seq = 0
        self._prepared_seq = 0
        self._dispatch_seq = 0
        self._chat_coalesce_lock = asyncio.Lock()
        self._chat_coalesce_buffers: dict[str, dict[str, Any]] = {}
        self._recent_sticker_imports: dict[str, RecentStickerImportState] = {}
        self._connection_count = 0

    def _effective_whitelist_user_ids(self) -> set[str]:
        return xinyu_qq_trust_policy.effective_whitelist_user_ids(self.config)

    def _is_blocked_user_id(self, user_id: str) -> bool:
        return xinyu_qq_trust_policy.is_blocked_user_id(self.config, user_id)

    def _is_blocked_group_id(self, group_id: str) -> bool:
        return xinyu_qq_trust_policy.is_blocked_group_id(self.config, group_id)

    def _is_trusted_user_id(self, user_id: str) -> bool:
        return xinyu_qq_trust_policy.is_trusted_user_id(self.config, user_id)

    def _trust_level_for_user_id(self, user_id: str) -> str:
        return xinyu_qq_trust_policy.trust_level_for_user_id(self.config, user_id)

    _compact_command_text = staticmethod(xinyu_qq_trust_policy.compact_command_text)
    _looks_like_trust_command = staticmethod(xinyu_qq_trust_policy.is_trust_grant_command)
    _looks_like_trust_revoke_command = staticmethod(xinyu_qq_trust_policy.is_trust_revoke_command)

    def _trust_command_target(self, prepared: PreparedMessage) -> tuple[str, str]:
        return xinyu_qq_trust_policy.trust_command_target(
            prepared,
            owner_user_ids=self.config.owner_user_ids,
        )

    def _persist_trusted_user_ids(self, trusted_user_ids: set[str]) -> bool:
        if self.config_path is None:
            return False
        try:
            config_path = self.config_path.resolve()
            raw = _load_json(config_path)
            raw["trusted_user_ids"] = sorted(trusted_user_ids)
            atomic_write_json(config_path, raw, sort_keys=False)
            return True
        except OSError as exc:
            print(f"[xinyu_qq_gateway] trust config write failed: {type(exc).__name__}: {exc}", flush=True)
            return False

    def _set_trusted_user_id(self, user_id: str, *, trusted: bool) -> bool:
        user_id = _safe_str(user_id).strip()
        if not user_id:
            return False
        trusted_user_ids = set(self.config.trusted_user_ids)
        changed = False
        if trusted and user_id not in trusted_user_ids:
            trusted_user_ids.add(user_id)
            changed = True
        elif not trusted and user_id in trusted_user_ids:
            trusted_user_ids.remove(user_id)
            changed = True
        if changed:
            self.config = replace(self.config, trusted_user_ids=frozenset(trusted_user_ids))
            self._persist_trusted_user_ids(trusted_user_ids)
        return changed

    def _handle_owner_trust_command(self, prepared: PreparedMessage) -> str:
        if prepared.route != "chat" or prepared.local_reply:
            return ""
        if prepared.target.user_id not in self.config.owner_user_ids:
            return ""
        payload = prepared.payload if isinstance(prepared.payload, dict) else {}
        text = _safe_str(payload.get("text")).strip()
        grant = self._looks_like_trust_command(text)
        revoke = self._looks_like_trust_revoke_command(text)
        if not grant and not revoke:
            return ""
        target_user_id, target_name = self._trust_command_target(prepared)
        bot_id = _safe_str(payload.get("bot_id")).strip()
        if not target_user_id:
            return "要给谁权限，直接回复她那条消息再说“给个权限”。"
        if target_user_id in self.config.owner_user_ids:
            return "这个号本来就是 owner，不用再加信任。"
        if bot_id and target_user_id == bot_id:
            return "不能把我自己的号加进信任名单。"
        changed = self._set_trusted_user_id(target_user_id, trusted=grant and not revoke)
        label = target_name or target_user_id
        if grant and not revoke:
            return f"加上了。以后 {label} 可以正常找我聊天、让我读引用/转发、做公开搜索；本机代码和管理权限还是只认你。"
        if changed:
            return f"撤掉了。{label} 不再走信任用户权限。"
        return f"{label} 本来就不在信任名单里。"

    async def run(self) -> None:
        if not self.config.enabled:
            print("[xinyu_qq_gateway] disabled by config", flush=True)
            return
        stop_event = asyncio.Event()
        self._install_signal_handlers(stop_event)
        async with websockets.serve(
            self._handle_connection,
            self.config.onebot_host,
            self.config.onebot_port,
            max_size=8 * 1024 * 1024,
            ping_interval=20,
            ping_timeout=20,
        ):
            print(
                f"[xinyu_qq_gateway] listening on ws://{self.config.onebot_host}:"
                f"{self.config.onebot_port}{self.config.onebot_path} "
                f"(core={self.config.core_chat_url}, version={GATEWAY_VERSION})",
                flush=True,
            )
            await stop_event.wait()

        for task in list(self._event_tasks):
            task.cancel()
        if self._event_tasks:
            await asyncio.gather(*self._event_tasks, return_exceptions=True)
        self._inbound_session_queues.clear()
        self._inbound_session_tasks.clear()

    def _install_signal_handlers(self, stop_event: asyncio.Event) -> None:
        loop = asyncio.get_running_loop()
        for sig in (getattr(signal, "SIGINT", None), getattr(signal, "SIGTERM", None)):
            if sig is None:
                continue
            with contextlib.suppress(NotImplementedError):
                loop.add_signal_handler(sig, stop_event.set)

    async def _handle_connection(self, websocket: Any) -> None:
        path = xinyu_qq_server.websocket_path(websocket)
        if not xinyu_qq_server.websocket_path_allowed(path, self.config.onebot_path):
            print(f"[xinyu_qq_gateway] rejecting websocket path: {path}", flush=True)
            await websocket.close(code=1008, reason="invalid path")
            return

        self._connection_count += 1
        connection_id = xinyu_qq_server.connection_id("napcat", int(time.time()), self._connection_count)
        self._websocket_connection_ids[id(websocket)] = connection_id
        print(f"[xinyu_qq_gateway] NapCat connected: {connection_id} path={path or self.config.onebot_path}", flush=True)
        outbox_task: asyncio.Task[Any] | None = None
        ack_spool_task: asyncio.Task[Any] | None = None
        if self.config.qq_outbox_enabled and self.config.bridge_token:
            outbox_task = asyncio.create_task(
                self._poll_qq_outbox(websocket, connection_id),
                name=f"xinyu-qq-outbox-{connection_id}",
            )
        if self.config.bridge_token and self.client.message_ack_url:
            ack_spool_task = asyncio.create_task(
                self._poll_pending_message_acks(connection_id),
                name=f"xinyu-qq-ack-spool-{connection_id}",
            )
        try:
            async for raw_message in websocket:
                event = self._parse_ws_message(raw_message)
                if event is None:
                    continue
                if self._complete_action_response(event, connection_id):
                    continue
                await self._enqueue_onebot_event(websocket, event)
        except Exception as exc:
            print(f"[xinyu_qq_gateway] NapCat connection closed: {type(exc).__name__}: {exc}", flush=True)
        finally:
            self._websocket_connection_ids.pop(id(websocket), None)
            self._fail_pending_actions_for_connection(
                connection_id,
                BridgeError("NapCat connection closed before action response"),
            )
            if outbox_task is not None:
                outbox_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await outbox_task
            if ack_spool_task is not None:
                ack_spool_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await ack_spool_task

    async def _poll_qq_outbox(self, websocket: Any, connection_id: str) -> None:
        await xinyu_qq_outbox_dispatcher.poll_qq_outbox(
            self,
            websocket,
            connection_id,
            gateway_name=GATEWAY_NAME,
        )

    def _outbox_target(self, claim: dict[str, Any]) -> ReplyTarget | None:
        return xinyu_qq_outbox_client.outbox_target(self, claim, ReplyTarget)

    _onebot_action_result = xinyu_qq_outbox_client.onebot_action_result

    async def _ack_qq_outbox(
        self,
        claim: dict[str, Any],
        *,
        status: str,
        adapter_message_id: str = "",
        error: str = "",
    ) -> None:
        await xinyu_qq_outbox_client.ack_qq_outbox(
            self,
            claim,
            status=status,
            adapter_message_id=adapter_message_id,
            error=error,
        )

    async def _ack_sent_outbox_delivery(
        self,
        claim: dict[str, Any],
        *,
        target: ReplyTarget,
        visible_text: str,
        adapter_message_id: str,
        delivery_kind: str,
        adapter_error: str = "",
    ) -> None:
        await xinyu_qq_outbox_client.ack_sent_outbox_delivery(
            self,
            claim,
            target=target,
            visible_text=visible_text,
            adapter_message_id=adapter_message_id,
            delivery_kind=delivery_kind,
            adapter_error=adapter_error,
        )

    def _outbox_message_ack_payload(
        self,
        claim: dict[str, Any],
        *,
        target: ReplyTarget,
        visible_text: str,
        adapter_message_id: str,
        delivery_kind: str,
        adapter_error: str = "",
    ) -> dict[str, Any]:
        return xinyu_qq_outbox_client.outbox_message_ack_payload(
            self,
            claim,
            target=target,
            visible_text=visible_text,
            adapter_message_id=adapter_message_id,
            delivery_kind=delivery_kind,
            adapter_error=adapter_error,
        )

    _sent_outbox_delivery_route = staticmethod(xinyu_qq_outbox_client.sent_outbox_delivery_route)

    async def _poll_pending_message_acks(self, connection_id: str) -> None:
        await xinyu_qq_outbox_client.poll_pending_message_acks(self, connection_id)

    async def _ack_sent_visible_reply(
        self,
        prepared: PreparedMessage,
        *,
        reply: str,
        core_response: dict[str, Any],
        action_response: dict[str, Any] | None,
    ) -> None:
        await xinyu_qq_outbox_client.ack_sent_visible_reply(
            self,
            prepared,
            reply=reply,
            core_response=core_response,
            action_response=action_response,
        )

    async def _record_sent_message_ack_payload(self, payload: dict[str, Any]) -> bool:
        return await xinyu_qq_outbox_client.record_sent_message_ack_payload(self, payload)

    _spool_pending_message_ack = xinyu_qq_outbox_client.spool_pending_message_ack

    _spool_acked_message_ack = xinyu_qq_outbox_client.spool_acked_message_ack

    _sent_message_ack_payload = xinyu_qq_outbox_client.sent_message_ack_payload

    async def _send_message_ack_payload(
        self,
        payload: dict[str, Any],
        *,
        mark_acked: bool,
        spool_on_failure: bool,
    ) -> bool:
        return await xinyu_qq_outbox_client.send_message_ack_payload(
            self,
            payload,
            mark_acked=mark_acked,
            spool_on_failure=spool_on_failure,
        )

    _flush_pending_message_acks = xinyu_qq_outbox_client.flush_pending_message_acks

    async def _resolve_learning_ingest_payload(self, websocket: Any, payload: dict[str, Any]) -> dict[str, Any]:
        return await xinyu_qq_attachment_resolver.resolve_learning_ingest_payload(self, websocket, payload)

    async def _resolve_sticker_import_payload(self, websocket: Any, payload: dict[str, Any]) -> dict[str, Any]:
        return await xinyu_qq_attachment_resolver.resolve_sticker_import_payload(self, websocket, payload)

    async def _resolve_onebot_media(self, websocket: Any, *, file_id: str, metadata: dict[str, Any]) -> dict[str, Any]:
        return await xinyu_qq_attachment_resolver.resolve_onebot_media(
            self,
            websocket,
            file_id=file_id,
            metadata=metadata,
        )

    async def _resolve_onebot_file(self, websocket: Any, *, file_id: str, metadata: dict[str, Any]) -> dict[str, str]:
        return await xinyu_qq_attachment_resolver.resolve_onebot_file(
            self,
            websocket,
            file_id=file_id,
            metadata=metadata,
        )

    async def _onebot_file_url_action(self, websocket: Any, action: str, params: dict[str, Any]) -> str:
        return await xinyu_qq_attachment_resolver.onebot_file_url_action(self, websocket, action, params)

    async def _onebot_action_payload(self, websocket: Any, action: str, params: dict[str, Any]) -> Any:
        return await xinyu_qq_attachment_resolver.onebot_action_payload(self, websocket, action, params)

    async def _onebot_action_data(self, websocket: Any, action: str, params: dict[str, Any]) -> dict[str, Any]:
        return await xinyu_qq_attachment_resolver.onebot_action_data(self, websocket, action, params)

    _path_from_file_uri = staticmethod(xinyu_qq_attachment_resolver.path_from_file_uri)

    def _onebot_local_image_file(self, image_path: str) -> tuple[str, str]:
        return xinyu_qq_attachment_resolver.onebot_local_image_file(self, image_path)

    def _onebot_local_file(self, file_path: str, *, file_name: str = "") -> tuple[str, str, str]:
        return xinyu_qq_attachment_resolver.onebot_local_file(self, file_path, file_name=file_name)

    @staticmethod
    def _first_text_field(data: dict[str, Any], keys: tuple[str, ...]) -> str:
        return xinyu_qq_attachment_resolver.first_text_field(None, data, keys)

    async def _upgrade_reply_file_learning(
        self,
        websocket: Any,
        event: dict[str, Any],
        prepared: PreparedMessage | None,
    ) -> PreparedMessage | None:
        if prepared is None or prepared.local_reply or prepared.route != "chat":
            return prepared
        if not self.config.qq_file_learning_enabled:
            return prepared
        if self.config.qq_file_learning_private_owner_only and (
            prepared.target.message_kind != "private" or prepared.target.user_id not in self.config.owner_user_ids
        ):
            return prepared

        text = _safe_str(prepared.payload.get("text") or self._extract_text(event)).strip()
        if not self._reply_file_learning_intent(text):
            return prepared
        reply_message_id = self._extract_reply_message_id(event)
        if not reply_message_id:
            return prepared

        replied = await self._onebot_action_data(websocket, "get_msg", {"message_id": _maybe_int(reply_message_id)})
        if not replied:
            print(f"[xinyu_qq_gateway] could not fetch replied message id={reply_message_id}", flush=True)
            return prepared
        material = self._extract_learning_material(replied)
        if material is None:
            print(f"[xinyu_qq_gateway] replied message has no QQ file material id={reply_message_id}", flush=True)
            return prepared

        payload = self._build_learning_ingest_payload(
            event,
            target=prepared.target,
            material=material,
            text=text,
        )
        metadata = dict(payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {})
        metadata.update(
            {
                "source": "qq_reply_file_message",
                "replied_message_id": reply_message_id,
                "replied_raw_message": _safe_str(replied.get("raw_message"))[:1000],
            }
        )
        payload["metadata"] = metadata
        return PreparedMessage(target=prepared.target, payload=payload, route="learning_ingest")

    async def _enrich_reply_context(
        self,
        websocket: Any,
        event: dict[str, Any],
        prepared: PreparedMessage | None,
    ) -> PreparedMessage | None:
        if prepared is None or prepared.local_reply or prepared.route not in {"chat", "codex_execute", "package_install"}:
            return prepared
        reply_message_id = self._extract_reply_message_id(event)
        if not reply_message_id:
            return prepared
        metadata = prepared.payload.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
            prepared.payload["metadata"] = metadata
        metadata["qq_reply_message_id"] = reply_message_id
        prepared.payload["reply_message_id"] = reply_message_id

        replied = await self._onebot_action_data(websocket, "get_msg", {"message_id": _maybe_int(reply_message_id)})
        if not replied:
            metadata["qq_reply_context_available"] = False
            metadata["qq_reply_context_notes"] = ["reply_fetch_failed"]
            return prepared
        reply_context = self._summarize_replied_message(replied)
        metadata["qq_reply_context_available"] = True
        metadata["qq_reply_context"] = reply_context
        prepared.payload["quoted_message"] = reply_context
        return prepared

    async def _enrich_forward_context(
        self,
        websocket: Any,
        event: dict[str, Any],
        prepared: PreparedMessage | None,
    ) -> PreparedMessage | None:
        if prepared is None or prepared.local_reply or prepared.route not in {"chat", "codex_execute", "package_install"}:
            return prepared

        metadata = prepared.payload.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
            prepared.payload["metadata"] = metadata

        forward_ids = self._extract_forward_message_ids(event)
        reply_context = metadata.get("qq_reply_context")
        if isinstance(reply_context, dict):
            forward_ids.extend(_as_str_list(reply_context.get("forward_message_ids")))
        forward_ids = list(dict.fromkeys(item for item in forward_ids if item))

        messages = self._embedded_forward_messages_from_event(event)
        fetched_ids: list[str] = []
        failed_ids: list[str] = []
        for forward_id in forward_ids[:3]:
            fetched = await self._fetch_forward_messages(websocket, forward_id)
            if fetched:
                fetched_ids.append(forward_id)
                messages.extend(fetched)
            else:
                failed_ids.append(forward_id)

        messages = self._dedupe_forward_messages(messages)
        if not forward_ids and not messages:
            return prepared

        context = {
            "forward_ids": forward_ids,
            "message_count": len(messages),
            "messages": messages[:xinyu_qq_forward_context.QQ_FORWARD_CONTEXT_MAX_MESSAGES],
            "fetched_ids": fetched_ids,
            "failed_ids": failed_ids,
        }
        metadata["qq_forward_message_ids"] = forward_ids
        metadata["qq_forward_context_available"] = bool(messages)
        metadata["qq_forward_message_count"] = len(messages)
        metadata["qq_forward_context"] = context
        prepared.payload["forwarded_messages"] = context
        return prepared

    def _embedded_forward_messages_from_event(self, event: dict[str, Any]) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        for segment in self._message_segments(event):
            segment_type = _safe_str(segment.get("type")).strip().lower()
            data = self._segment_data(segment)
            if segment_type == "forward":
                for key in ("messages", "message", "content", "nodes", "data"):
                    value = data.get(key)
                    messages.extend(self._forward_messages_from_payload(value))
            elif segment_type in {"json", "xml"}:
                raw = _safe_str(data.get("data") or data.get("text") or data.get("content")).strip()
                if raw.startswith(("{", "[")):
                    messages.extend(self._forward_messages_from_payload(raw))
        return self._dedupe_forward_messages(messages)

    async def _fetch_forward_messages(self, websocket: Any, forward_id: str) -> list[dict[str, str]]:
        if not forward_id:
            return []
        payload = await self._onebot_action_payload(websocket, "get_forward_msg", {"message_id": _maybe_int(forward_id)})
        messages = self._forward_messages_from_payload(payload)
        if messages:
            return messages
        payload = await self._onebot_action_payload(websocket, "get_forward_msg", {"id": forward_id})
        return self._forward_messages_from_payload(payload)

    def _forward_messages_from_payload(self, payload: Any) -> list[dict[str, str]]:
        raw_items = self._forward_raw_items(payload)
        messages: list[dict[str, str]] = []
        used_chars = 0
        for item in raw_items:
            message = self._summarize_forward_item(item)
            if not message:
                continue
            text_len = len(_safe_str(message.get("text") or message.get("rich_summary") or message.get("raw_message")))
            if messages and used_chars + text_len > xinyu_qq_forward_context.QQ_FORWARD_CONTEXT_MAX_TEXT_CHARS:
                break
            used_chars += text_len
            messages.append(message)
            if len(messages) >= xinyu_qq_forward_context.QQ_FORWARD_CONTEXT_MAX_MESSAGES:
                break
        return messages

    _forward_raw_items = staticmethod(xinyu_qq_forward_context.forward_raw_items)

    def _summarize_forward_item(self, item: Any) -> dict[str, str]:
        if isinstance(item, str):
            text = self._clean_cq_text(item)
            return {"sender_name": "", "user_id": "", "text": text[:1200], "raw_message": item[:1200], "rich_summary": ""}
        if not isinstance(item, dict):
            return {}

        node = item
        data = item.get("data")
        if isinstance(data, dict) and not any(key in item for key in ("message", "content", "raw_message")):
            node = {**item, **data}

        event_like = dict(node)
        if "message" not in event_like and "content" in node:
            event_like["message"] = node.get("content")
        if "raw_message" not in event_like:
            message_value = event_like.get("message")
            if isinstance(message_value, str):
                event_like["raw_message"] = message_value

        text = self._clean_cq_text(self._extract_text(event_like).strip())
        raw_message = _safe_str(event_like.get("raw_message")).strip()
        rich = self._extract_rich_message_context(event_like)
        rich_summary = _safe_str(rich.get("summary")).strip()

        sender = event_like.get("sender")
        sender_name = ""
        user_id = ""
        if isinstance(sender, dict):
            sender_name = (
                _safe_str(sender.get("card")).strip()
                or _safe_str(sender.get("nickname")).strip()
                or _safe_str(sender.get("name")).strip()
                or _safe_str(sender.get("user_id")).strip()
            )
            user_id = _safe_str(sender.get("user_id")).strip()
        sender_name = (
            sender_name
            or _safe_str(event_like.get("nickname")).strip()
            or _safe_str(event_like.get("name")).strip()
            or _safe_str(event_like.get("user_id")).strip()
        )
        user_id = user_id or _safe_str(event_like.get("user_id")).strip()

        if not text and not rich_summary and not raw_message:
            return {}
        return {
            "message_id": _safe_str(event_like.get("message_id")).strip(),
            "sender_name": sender_name[:120],
            "user_id": user_id[:80],
            "text": text[:1200],
            "raw_message": raw_message[:1200],
            "rich_summary": rich_summary[:1200],
            "time": _safe_str(event_like.get("time")).strip(),
        }

    @staticmethod
    def _clean_cq_text(text: str) -> str:
        return xinyu_qq_normalizer.clean_cq_text(None, text)

    _dedupe_forward_messages = staticmethod(xinyu_qq_forward_context.dedupe_forward_messages)

    @staticmethod
    def _reply_file_learning_intent(text: str) -> bool:
        return xinyu_qq_attachment_resolver.reply_file_learning_intent(None, text)

    _extract_reply_message_id = staticmethod(xinyu_qq_forward_context.extract_reply_message_id)
    _extract_forward_message_ids = staticmethod(xinyu_qq_forward_context.extract_forward_message_ids)
    _extract_forward_ids_from_text = staticmethod(xinyu_qq_forward_context.extract_forward_ids_from_text)
    _forward_ids_from_json = staticmethod(xinyu_qq_forward_context.forward_ids_from_json)

    _parse_cq_params = staticmethod(xinyu_qq_normalizer.parse_cq_params)
    _decode_cq_value = staticmethod(xinyu_qq_normalizer.decode_cq_value)
    _cq_bracket_continues_params = staticmethod(xinyu_qq_normalizer.cq_bracket_continues_params)
    _parse_cq_segments = staticmethod(xinyu_qq_normalizer.parse_cq_segments)
    _strip_cq_segments = staticmethod(xinyu_qq_normalizer.strip_cq_segments)

    _parse_ws_message = xinyu_qq_normalizer.parse_ws_message

    def _complete_action_response(self, event: dict[str, Any], connection_id: str) -> bool:
        echo = _safe_str(event.get("echo")).strip()
        if not echo:
            return False
        pending = self._pending_actions.get(echo)
        if pending is None:
            return False
        if pending.connection_id != connection_id:
            return False
        self._pending_actions.pop(echo, None)
        future = pending.future
        if not future.done():
            future.set_result(event)
        return True

    def _fail_pending_actions_for_connection(self, connection_id: str, exc: BaseException) -> None:
        for echo, pending in list(self._pending_actions.items()):
            if pending.connection_id != connection_id:
                continue
            if not pending.future.done():
                pending.future.set_exception(exc)
            self._pending_actions.pop(echo, None)

    def _connection_id_for_websocket(self, websocket: Any) -> str:
        return self._websocket_connection_ids.get(id(websocket), f"ws-{id(websocket)}")

    def _next_arrival_seq(self) -> int:
        self._arrival_seq += 1
        return self._arrival_seq

    def _next_prepared_seq(self) -> int:
        self._prepared_seq += 1
        return self._prepared_seq

    def _next_dispatch_seq(self) -> int:
        self._dispatch_seq += 1
        return self._dispatch_seq

    def _event_session_queue_key(self, event: dict[str, Any]) -> str:
        message_kind = self._message_kind(event)
        if message_kind == "group":
            group_id = _safe_str(event.get("group_id")).strip()
            return f"group:{group_id or 'unknown'}"
        sender_id = _safe_str(event.get("user_id")).strip()
        return f"private:{sender_id or 'unknown'}"

    async def _enqueue_onebot_event(self, websocket: Any, event: dict[str, Any]) -> None:
        if _safe_str(event.get("post_type")).lower() != "message":
            return
        arrival_seq = self._next_arrival_seq()
        queue_key = self._event_session_queue_key(event)
        async with self._inbound_queue_lock:
            queue = self._inbound_session_queues.get(queue_key)
            if queue is None:
                queue = asyncio.Queue()
                self._inbound_session_queues[queue_key] = queue
                task = asyncio.create_task(
                    self._run_inbound_session_queue(queue_key),
                    name=f"xinyu-qq-inbound-{_hash_id(queue_key, length=10)}",
                )
                self._inbound_session_tasks[queue_key] = task
                self._event_tasks.add(task)
                task.add_done_callback(self._event_tasks.discard)
            await queue.put((arrival_seq, websocket, event))
            queue_depth = queue.qsize()
        self._trace_qq_inbound(
            event,
            stage="queued",
            arrival_seq=arrival_seq,
            session_queue_key=queue_key,
            queue_depth=queue_depth,
        )

    async def _run_inbound_session_queue(self, queue_key: str) -> None:
        queue = self._inbound_session_queues[queue_key]
        while True:
            arrival_seq, websocket, event = await queue.get()
            try:
                self._trace_qq_inbound(
                    event,
                    stage="dequeued",
                    arrival_seq=arrival_seq,
                    session_queue_key=queue_key,
                    queue_depth=queue.qsize(),
                )
                await self._handle_onebot_event(
                    websocket,
                    event,
                    arrival_seq=arrival_seq,
                    session_queue_key=queue_key,
                )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                self._trace_qq_inbound(
                    event,
                    stage="error",
                    arrival_seq=arrival_seq,
                    session_queue_key=queue_key,
                    queue_depth=queue.qsize(),
                    error=f"{type(exc).__name__}: {exc}",
                )
                print("[xinyu_qq_gateway] unexpected queued event handling error", flush=True)
                traceback.print_exception(type(exc), exc, exc.__traceback__)
            finally:
                queue.task_done()

    def _annotate_prepared_reception(
        self,
        prepared: PreparedMessage,
        event: dict[str, Any],
        *,
        arrival_seq: int,
        session_queue_key: str,
    ) -> PreparedMessage:
        prepared_seq = self._next_prepared_seq()
        payload = prepared.payload if isinstance(prepared.payload, dict) else {}
        metadata = payload.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        metadata.update(
            {
                "qq_arrival_seq": arrival_seq,
                "qq_prepared_seq": prepared_seq,
                "qq_session_queue_hash": _hash_id(session_queue_key),
                "qq_gateway_received_message_id": _safe_str(event.get("message_id")).strip(),
            }
        )
        payload["metadata"] = metadata
        prepared.payload["metadata"] = metadata
        return prepared

    def _annotate_dispatch_reception(self, prepared: PreparedMessage) -> int:
        dispatch_seq = self._next_dispatch_seq()
        payload = prepared.payload if isinstance(prepared.payload, dict) else {}
        metadata = payload.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        metadata["qq_dispatch_seq"] = dispatch_seq
        payload["metadata"] = metadata
        prepared.payload["metadata"] = metadata
        return dispatch_seq

    def _trace_qq_inbound(
        self,
        event: dict[str, Any],
        *,
        stage: str,
        arrival_seq: int = 0,
        prepared: PreparedMessage | None = None,
        session_queue_key: str = "",
        queue_depth: int | None = None,
        drop_reason: str = "",
        error: str = "",
    ) -> None:
        try:
            message_kind = self._message_kind(event)
            rich = self._extract_rich_message_context(event) if isinstance(event, dict) else {}
            metadata: dict[str, Any] = {}
            payload: dict[str, Any] = {}
            route = ""
            local_reply = False
            user_id = event.get("user_id")
            group_id = event.get("group_id")
            if prepared is not None:
                route = prepared.route
                local_reply = bool(prepared.local_reply)
                user_id = prepared.target.user_id or user_id
                group_id = prepared.target.group_id or group_id
                payload = prepared.payload if isinstance(prepared.payload, dict) else {}
                raw_metadata = payload.get("metadata")
                metadata = raw_metadata if isinstance(raw_metadata, dict) else {}
            row = {
                "recorded_at": datetime.now().astimezone().isoformat(),
                "stage": stage,
                "gateway_version": GATEWAY_VERSION,
                "arrival_seq": arrival_seq or _as_int(metadata.get("qq_arrival_seq"), 0),
                "prepared_seq": _as_int(metadata.get("qq_prepared_seq"), 0),
                "dispatch_seq": _as_int(metadata.get("qq_dispatch_seq"), 0),
                "session_queue_hash": _safe_str(metadata.get("qq_session_queue_hash")) or _hash_id(session_queue_key),
                "queue_depth": queue_depth,
                "message_kind": message_kind,
                "post_type": _safe_str(event.get("post_type")),
                "message_type": _safe_str(event.get("message_type")),
                "message_id": _safe_str(
                    event.get("message_id") or payload.get("message_id") or metadata.get("message_id")
                ).strip(),
                "user_id_hash": _hash_id(user_id),
                "group_id_hash": _hash_id(group_id),
                "route": route,
                "local_reply": local_reply,
                "text_len": len(self._extract_text(event).strip()),
                "rich_summary": _safe_str(rich.get("summary"))[:500],
                "sticker_count": int(rich.get("sticker_count") or 0),
                "image_count": int(rich.get("image_count") or 0),
                "forward_count": int(rich.get("forward_count") or 0),
                "reply_message_id": _safe_str(rich.get("reply_message_id")).strip(),
                "drop_reason": drop_reason,
                "error": error[:500],
            }
            trace_path = Path(__file__).resolve().parent / QQ_INBOUND_TRACE_REL
            append_jsonl(trace_path, row)
        except OSError as exc:
            print(f"[xinyu_qq_gateway] inbound trace write failed: {type(exc).__name__}: {exc}", flush=True)
        except Exception as exc:
            print(f"[xinyu_qq_gateway] inbound trace build failed: {type(exc).__name__}: {exc}", flush=True)

    async def _handle_onebot_event(
        self,
        websocket: Any,
        event: dict[str, Any],
        *,
        arrival_seq: int = 0,
        session_queue_key: str = "",
    ) -> None:
        if _safe_str(event.get("post_type")).lower() != "message":
            return
        if not arrival_seq:
            arrival_seq = self._next_arrival_seq()
        if not session_queue_key:
            session_queue_key = self._event_session_queue_key(event)
        self._maybe_record_group_shadow_event(event)
        prepared = self.prepare_message(event)
        prepared = await self._upgrade_reply_file_learning(websocket, event, prepared)
        prepared = await self._enrich_reply_context(websocket, event, prepared)
        prepared = await self._enrich_forward_context(websocket, event, prepared)
        if prepared is None:
            self._trace_qq_inbound(
                event,
                stage="dropped",
                arrival_seq=arrival_seq,
                session_queue_key=session_queue_key,
                drop_reason=self._prepare_none_reason(event),
            )
            return
        prepared = self._annotate_prepared_reception(
            prepared,
            event,
            arrival_seq=arrival_seq,
            session_queue_key=session_queue_key,
        )
        self._trace_qq_inbound(
            event,
            stage="prepared",
            arrival_seq=arrival_seq,
            prepared=prepared,
            session_queue_key=session_queue_key,
        )
        self._trace_qq_rich_context(event, prepared, stage="prepared")
        trust_reply = self._handle_owner_trust_command(prepared)
        if trust_reply:
            if self.config.send_replies:
                await self.send_reply(websocket, prepared.target, trust_reply)
            self._trace_qq_inbound(
                event,
                stage="local_reply_sent",
                arrival_seq=arrival_seq,
                prepared=prepared,
                session_queue_key=session_queue_key,
            )
            return
        if prepared.local_reply:
            if self.config.send_replies:
                await self.send_reply(websocket, prepared.target, prepared.local_reply)
            self._trace_qq_inbound(
                event,
                stage="local_reply_sent",
                arrival_seq=arrival_seq,
                prepared=prepared,
                session_queue_key=session_queue_key,
            )
            return

        if await self._enqueue_coalesced_owner_private_chat(websocket, prepared):
            self._trace_qq_inbound(
                event,
                stage="coalesced_wait",
                arrival_seq=arrival_seq,
                prepared=prepared,
                session_queue_key=session_queue_key,
            )
            return

        await self._dispatch_prepared_message(websocket, prepared, event=event)

    async def _dispatch_prepared_message(
        self,
        websocket: Any,
        prepared: PreparedMessage,
        *,
        event: dict[str, Any] | None = None,
    ) -> None:
        event_for_trace = event if isinstance(event, dict) else {}
        prepared = await self._maybe_enrich_recent_sticker_question(websocket, event_for_trace, prepared)
        self._annotate_dispatch_reception(prepared)
        payload = prepared.payload if isinstance(prepared.payload, dict) else {}
        metadata = payload.get("metadata")
        metadata = metadata if isinstance(metadata, dict) else {}
        self._trace_qq_inbound(
            event_for_trace,
            stage="dispatch_start",
            arrival_seq=_as_int(metadata.get("qq_arrival_seq"), 0),
            prepared=prepared,
            session_queue_key=_safe_str(metadata.get("qq_session_queue_hash")),
        )
        try:
            if prepared.route == "codex_execute":
                if not self.config.bridge_token:
                    await self.send_reply(
                        websocket,
                        prepared.target,
                        "Codex 辅助脑暂时没有启用：缺少 bridge token。请用同一个 token 重启 core bridge 和 QQ gateway。",
                    )
                    return
                response = await self.client.codex_execute(prepared.payload)
            elif prepared.route == "learning_ingest":
                if not self.config.bridge_token:
                    await self.send_reply(
                        websocket,
                        prepared.target,
                        "Learning ingest is not enabled: missing bridge token.",
                    )
                    return
                payload = await self._resolve_learning_ingest_payload(websocket, prepared.payload)
                response = await self.client.learning_ingest(payload)
                image_context = await asyncio.to_thread(
                    build_image_context,
                    Path(__file__).resolve().parent,
                    learning_payload=payload,
                    learning_response=response,
                    owner_text=_safe_str(payload.get("reason")).strip(),
                )
                followup_payload = self._build_attachment_followup_chat_payload(
                    event or {},
                    target=prepared.target,
                    learning_payload=payload,
                    learning_response=response,
                    image_context=image_context,
                )
                if followup_payload is not None:
                    self._trace_qq_rich_context(
                        event or {},
                        PreparedMessage(target=prepared.target, payload=followup_payload, route="chat"),
                        stage="attachment_followup",
                    )
                    response = await self.client.chat(followup_payload)
            elif prepared.route == "sticker_import":
                if not self.config.bridge_token:
                    await self.send_reply(
                        websocket,
                        prepared.target,
                        "Sticker import is not enabled: missing bridge token.",
                    )
                    return
                started = time.monotonic()
                payload = await self._resolve_sticker_import_payload(websocket, prepared.payload)
                if payload is not prepared.payload:
                    self._trace_sticker_import(
                        event or {},
                        target=prepared.target,
                        payload=payload,
                        stage="resolved",
                        elapsed_ms=int((time.monotonic() - started) * 1000),
                    )
                self._remember_recent_sticker_import(
                    target=prepared.target,
                    event=event or {},
                    payload=payload,
                    status="pending",
                )
                try:
                    import_response = await self.client.sticker_import(payload)
                except BridgeError as exc:
                    self._trace_sticker_import(
                        event or {},
                        target=prepared.target,
                        payload=payload,
                        stage="error",
                        elapsed_ms=int((time.monotonic() - started) * 1000),
                        error=str(exc),
                    )
                    self._remember_recent_sticker_import(
                        target=prepared.target,
                        event=event or {},
                        payload=payload,
                        status="error",
                        error=str(exc),
                    )
                    raise
                self._trace_sticker_import(
                    event or {},
                    target=prepared.target,
                    payload=payload,
                    response=import_response,
                    stage="completed",
                    elapsed_ms=int((time.monotonic() - started) * 1000),
                )
                self._remember_recent_sticker_import(
                    target=prepared.target,
                    event=event or {},
                    payload=payload,
                    status="completed",
                    response=import_response,
                )
                response = import_response
                followup_payload = self._build_sticker_followup_chat_payload(
                    event or {},
                    target=prepared.target,
                    sticker_payload=payload,
                    sticker_response=import_response,
                )
                if followup_payload is not None:
                    self._trace_qq_rich_context(
                        event or {},
                        PreparedMessage(target=prepared.target, payload=followup_payload, route="chat"),
                        stage="sticker_followup_after_import",
                    )
                    response = await self.client.chat(followup_payload)
            elif prepared.route == "package_install":
                if not self.config.bridge_token:
                    await self.send_reply(
                        websocket,
                        prepared.target,
                        "Package install is not enabled: missing bridge token.",
                    )
                    return
                response = await self.client.package_install(prepared.payload)
            elif prepared.route == "review_admin":
                if not self.config.bridge_token:
                    await self.send_reply(
                        websocket,
                        prepared.target,
                        "Review admin is not enabled: missing bridge token.",
                    )
                    return
                response = await self.client.review_inbox_command(prepared.payload)
            elif prepared.route == "goldmark_mark":
                if not self.config.bridge_token:
                    await self.send_reply(
                        websocket,
                        prepared.target,
                        "Goldmark 标记未启用：缺少 bridge token。",
                    )
                    return
                try:
                    response = await self.client.goldmark_mark_request(prepared.payload)
                except BridgeError as exc:
                    print(f"[xinyu_qq_gateway] goldmark mark error: {exc}", flush=True)
                    if self.config.send_replies:
                        await self.send_reply(websocket, prepared.target, self._goldmark_error_reply(str(exc)))
                    return
                if self.config.send_replies:
                    await self.send_reply(websocket, prepared.target, self._goldmark_result_reply(response))
                return
            else:
                response = await self.client.chat(prepared.payload)
        except BridgeError as exc:
            print(f"[xinyu_qq_gateway] core bridge error: {exc}", flush=True)
            self._trace_qq_inbound(
                event_for_trace,
                stage="dispatch_error",
                arrival_seq=_as_int(metadata.get("qq_arrival_seq"), 0),
                prepared=prepared,
                session_queue_key=_safe_str(metadata.get("qq_session_queue_hash")),
                error=f"BridgeError: {exc}",
            )
            if self.config.show_bridge_errors:
                await self.send_reply(websocket, prepared.target, f"XinYu core bridge error: {exc}")
            return
        except Exception as exc:
            print("[xinyu_qq_gateway] unexpected event handling error", flush=True)
            traceback.print_exception(type(exc), exc, exc.__traceback__)
            self._trace_qq_inbound(
                event_for_trace,
                stage="dispatch_error",
                arrival_seq=_as_int(metadata.get("qq_arrival_seq"), 0),
                prepared=prepared,
                session_queue_key=_safe_str(metadata.get("qq_session_queue_hash")),
                error=f"{type(exc).__name__}: {exc}",
            )
            if self.config.show_bridge_errors:
                await self.send_reply(websocket, prepared.target, f"XinYu gateway error: {exc}")
            return

        reply = self._visible_reply(_safe_str(response.get("reply"), ""))
        if self.config.send_replies and response.get("accepted", True) and reply:
            action_response = await self._send_visible_reply(websocket, prepared, reply, response)
            await self._ack_sent_visible_reply(
                prepared,
                reply=reply,
                core_response=response,
                action_response=action_response,
            )
            self._trace_qq_inbound(
                event_for_trace,
                stage="reply_sent",
                arrival_seq=_as_int(metadata.get("qq_arrival_seq"), 0),
                prepared=prepared,
                session_queue_key=_safe_str(metadata.get("qq_session_queue_hash")),
            )
        else:
            self._trace_qq_inbound(
                event_for_trace,
                stage="dispatch_done",
                arrival_seq=_as_int(metadata.get("qq_arrival_seq"), 0),
                prepared=prepared,
                session_queue_key=_safe_str(metadata.get("qq_session_queue_hash")),
                drop_reason="" if reply else "empty_visible_reply",
            )

    def _schedule_sticker_import_background(
        self,
        websocket: Any,
        event: dict[str, Any],
        *,
        target: ReplyTarget,
        sticker_payload: dict[str, Any],
    ) -> None:
        if not self.config.bridge_token:
            return
        task = asyncio.create_task(
            self._run_sticker_import_background(
                websocket,
                dict(event),
                target=target,
                sticker_payload=dict(sticker_payload),
            ),
            name=f"xinyu-qq-sticker-import-{_safe_str(sticker_payload.get('message_id') or event.get('message_id'))}",
        )
        self._event_tasks.add(task)
        task.add_done_callback(self._event_tasks.discard)

    async def _run_sticker_import_background(
        self,
        websocket: Any,
        event: dict[str, Any],
        *,
        target: ReplyTarget,
        sticker_payload: dict[str, Any],
    ) -> None:
        started = time.monotonic()
        self._trace_sticker_import(event, target=target, payload=sticker_payload, stage="queued")
        try:
            resolved_payload = await self._resolve_sticker_import_payload(websocket, sticker_payload)
            if resolved_payload is not sticker_payload:
                self._trace_sticker_import(
                    event,
                    target=target,
                    payload=resolved_payload,
                    stage="resolved",
                    elapsed_ms=int((time.monotonic() - started) * 1000),
                )
            response = await self.client.sticker_import(resolved_payload)
            self._trace_sticker_import(
                event,
                target=target,
                payload=resolved_payload,
                response=response,
                stage="completed",
                elapsed_ms=int((time.monotonic() - started) * 1000),
            )
        except BridgeError as exc:
            self._trace_sticker_import(
                event,
                target=target,
                payload=sticker_payload,
                stage="error",
                elapsed_ms=int((time.monotonic() - started) * 1000),
                error=str(exc),
            )
            print(f"[xinyu_qq_gateway] background sticker import error: {exc}", flush=True)
        except Exception as exc:
            self._trace_sticker_import(
                event,
                target=target,
                payload=sticker_payload,
                stage="error",
                elapsed_ms=int((time.monotonic() - started) * 1000),
                error=f"{type(exc).__name__}: {exc}",
            )
            print("[xinyu_qq_gateway] unexpected background sticker import error", flush=True)
            traceback.print_exception(type(exc), exc, exc.__traceback__)

    def _trace_sticker_import(
        self,
        event: dict[str, Any],
        *,
        target: ReplyTarget,
        payload: dict[str, Any],
        stage: str,
        response: dict[str, Any] | None = None,
        elapsed_ms: int | None = None,
        error: str = "",
    ) -> None:
        metadata = payload.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        response = response if isinstance(response, dict) else {}
        notes = response.get("notes")
        row = {
            "recorded_at": datetime.now().astimezone().isoformat(),
            "stage": stage,
            "message_kind": target.message_kind,
            "user_id_hash": _hash_id(target.user_id),
            "group_id_hash": _hash_id(target.group_id),
            "message_id": _safe_str(payload.get("message_id") or metadata.get("message_id") or event.get("message_id")),
            "source": _safe_str(metadata.get("source")),
            "file_id": _safe_str(payload.get("file_id") or metadata.get("file_id"))[:160],
            "has_file_url": bool(_safe_str(payload.get("file_url") or payload.get("url")).strip()),
            "has_file_path": bool(_safe_str(payload.get("file_path") or payload.get("path")).strip()),
            "file_resolution_status": _safe_str(metadata.get("file_resolution_status")),
            "file_resolved_by": _safe_str(metadata.get("file_resolved_by")),
            "file_resolution_attempts": metadata.get("file_resolution_attempts", [])[:8]
            if isinstance(metadata.get("file_resolution_attempts"), list)
            else [],
            "accepted": _as_bool(response.get("accepted"), default=False),
            "imported": _as_bool(response.get("imported"), default=False),
            "mood": _safe_str(response.get("mood")),
            "notes": notes[:8] if isinstance(notes, list) else [],
            "elapsed_ms": elapsed_ms,
            "error": _safe_str(error)[:500],
        }
        try:
            trace_path = Path(__file__).resolve().parent / QQ_STICKER_IMPORT_TRACE_REL
            append_jsonl(trace_path, row)
        except OSError as exc:
            print(f"[xinyu_qq_gateway] sticker import trace write failed: {type(exc).__name__}: {exc}", flush=True)

    def _recent_sticker_key(self, target: ReplyTarget) -> str:
        return self._session_id(target)

    @staticmethod
    def _sticker_response_import_completed(response: dict[str, Any] | None) -> bool:
        if not isinstance(response, dict):
            return False
        return any(key in response for key in ("accepted", "imported", "mood", "destination", "items", "failed"))

    def _remember_recent_sticker_import(
        self,
        *,
        target: ReplyTarget,
        event: dict[str, Any],
        payload: dict[str, Any],
        status: str,
        response: dict[str, Any] | None = None,
        error: str = "",
    ) -> RecentStickerImportState:
        state = RecentStickerImportState(
            target=target,
            event=dict(event) if isinstance(event, dict) else {},
            payload=dict(payload) if isinstance(payload, dict) else {},
            response=dict(response) if isinstance(response, dict) else {},
            status=status,
            error=_safe_str(error)[:500],
            updated_at=time.monotonic(),
        )
        key = self._recent_sticker_key(target)
        self._recent_sticker_imports[key] = state
        self._write_recent_sticker_state(key, state)
        return state

    def _write_recent_sticker_state(self, key: str, state: RecentStickerImportState) -> None:
        response = state.response if isinstance(state.response, dict) else {}
        payload = state.payload if isinstance(state.payload, dict) else {}
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
        item = self._first_sticker_import_item(response)
        row = {
            "updated_at": datetime.now().astimezone().isoformat(),
            "session_id_hash": _hash_id(key),
            "status": state.status,
            "error": state.error,
            "message_id": _safe_str(payload.get("message_id") or metadata.get("message_id")),
            "file_id": _safe_str(payload.get("file_id") or metadata.get("file_id"))[:160],
            "has_file_url": bool(_safe_str(payload.get("file_url") or payload.get("url")).strip()),
            "has_file_path": bool(_safe_str(payload.get("file_path") or payload.get("path")).strip()),
            "accepted": _as_bool(response.get("accepted"), default=False),
            "imported": _as_bool(response.get("imported"), default=False),
            "mood": _safe_str(item.get("mood") or response.get("mood")),
            "mood_label": _safe_str(response.get("mood_label") or item.get("mood") or response.get("mood")),
            "confidence": _safe_str(item.get("confidence") or response.get("confidence")),
            "destination": _safe_str(response.get("destination") or item.get("destination")),
        }
        try:
            path = Path(__file__).resolve().parent / QQ_RECENT_STICKER_STATE_REL
            atomic_write_json(path, row)
        except OSError as exc:
            print(f"[xinyu_qq_gateway] recent sticker state write failed: {type(exc).__name__}: {exc}", flush=True)

    @staticmethod
    def _looks_like_recent_sticker_question(text: str) -> bool:
        compact = re.sub(r"\s+", "", _safe_str(text))
        if not compact:
            return False
        exact_markers = (
            "我刚发的是什么",
            "刚发的是什么",
            "刚才发的是什么",
            "我刚发了什么",
            "刚发了什么",
            "刚才发了什么",
            "我发的是什么",
            "我发了什么",
            "刚那个表情是什么",
            "刚才那个表情是什么",
            "刚刚那个表情是什么",
        )
        if any(marker in compact for marker in exact_markers):
            return True
        return "刚" in compact and "表情" in compact and any(marker in compact for marker in ("什么", "啥", "内容"))

    def _recent_sticker_state_for_question(self, target: ReplyTarget) -> RecentStickerImportState | None:
        state = self._recent_sticker_imports.get(self._recent_sticker_key(target))
        if state is None:
            return None
        if time.monotonic() - state.updated_at > 600:
            return None
        return state

    async def _import_recent_sticker_state(
        self,
        websocket: Any,
        state: RecentStickerImportState,
    ) -> dict[str, Any]:
        if self._sticker_response_import_completed(state.response):
            return state.response
        started = time.monotonic()
        payload = await self._resolve_sticker_import_payload(websocket, state.payload)
        if payload is not state.payload:
            state.payload = payload
            self._trace_sticker_import(
                state.event,
                target=state.target,
                payload=payload,
                stage="resolved",
                elapsed_ms=int((time.monotonic() - started) * 1000),
            )
        self._remember_recent_sticker_import(
            target=state.target,
            event=state.event,
            payload=payload,
            status="retrying",
            response=state.response,
        )
        try:
            response = await self.client.sticker_import(payload)
        except BridgeError as exc:
            elapsed_ms = int((time.monotonic() - started) * 1000)
            self._trace_sticker_import(
                state.event,
                target=state.target,
                payload=payload,
                stage="error",
                elapsed_ms=elapsed_ms,
                error=str(exc),
            )
            self._remember_recent_sticker_import(
                target=state.target,
                event=state.event,
                payload=payload,
                status="error",
                response=state.response,
                error=str(exc),
            )
            raise
        self._trace_sticker_import(
            state.event,
            target=state.target,
            payload=payload,
            response=response,
            stage="completed",
            elapsed_ms=int((time.monotonic() - started) * 1000),
        )
        self._remember_recent_sticker_import(
            target=state.target,
            event=state.event,
            payload=payload,
            status="completed",
            response=response,
        )
        return response

    async def _maybe_enrich_recent_sticker_question(
        self,
        websocket: Any,
        event: dict[str, Any],
        prepared: PreparedMessage,
    ) -> PreparedMessage:
        if prepared.route != "chat":
            return prepared
        text = _safe_str(prepared.payload.get("text")).strip()
        if not self._looks_like_recent_sticker_question(text):
            return prepared
        if prepared.target.message_kind != "private" or prepared.target.user_id not in self.config.owner_user_ids:
            return prepared
        state = self._recent_sticker_state_for_question(prepared.target)
        if state is None:
            return prepared
        try:
            response = await self._import_recent_sticker_state(websocket, state)
        except BridgeError as exc:
            enriched = self._with_recent_sticker_unavailable(prepared, state, error=str(exc))
            self._trace_qq_rich_context(event or state.event, enriched, stage="recent_sticker_question_unavailable")
            return enriched
        enriched = self._with_recent_sticker_context(prepared, state, response)
        self._trace_qq_rich_context(event or state.event, enriched, stage="recent_sticker_question_context")
        return enriched

    def _with_recent_sticker_context(
        self,
        prepared: PreparedMessage,
        state: RecentStickerImportState,
        response: dict[str, Any],
    ) -> PreparedMessage:
        payload = dict(prepared.payload)
        metadata = dict(payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {})
        sticker_context = self._sticker_context_from_import_response(state.payload, response)
        metadata["qq_message_segments"] = self._enrich_sticker_segments_with_import_context(
            metadata.get("qq_message_segments")
            or self._extract_rich_message_context(state.event).get("segments")
            or [{"kind": "sticker", "summary": _safe_str(state.payload.get("summary") or "[动画表情]")}],
            sticker_context,
        )
        metadata.update(
            {
                "qq_rich_message": True,
                "qq_rich_summary": _safe_str(metadata.get("qq_rich_summary"))
                or _safe_str(self._extract_rich_message_context(state.event).get("summary"))
                or "最近收到的表情包",
                "qq_sticker_count": max(1, _as_int(metadata.get("qq_sticker_count"), 0)),
                "recent_sticker_question": True,
                "recent_sticker_source_message_id": _safe_str(state.payload.get("message_id")),
                "sticker_import_completed": _as_bool(sticker_context.get("import_completed"), default=False),
                "sticker_import_accepted": _as_bool(sticker_context.get("accepted"), default=False),
                "sticker_imported": _as_bool(sticker_context.get("imported"), default=False),
                "sticker_mood": _safe_str(sticker_context.get("mood")),
                "sticker_mood_label": _safe_str(sticker_context.get("mood_label")),
                "sticker_confidence": _safe_str(sticker_context.get("confidence")),
                "sticker_destination": _safe_str(sticker_context.get("destination")),
                "qq_image_context": sticker_context,
                "qq_image_context_available": _as_bool(sticker_context.get("available"), default=False),
                "qq_image_context_notes": sticker_context.get("notes", [])[:8]
                if isinstance(sticker_context.get("notes"), list)
                else [],
            }
        )
        payload["metadata"] = metadata
        return replace(prepared, payload=payload)

    def _with_recent_sticker_unavailable(
        self,
        prepared: PreparedMessage,
        state: RecentStickerImportState,
        *,
        error: str,
    ) -> PreparedMessage:
        payload = dict(prepared.payload)
        metadata = dict(payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {})
        rich = self._extract_rich_message_context(state.event)
        metadata.update(
            {
                "qq_rich_message": True,
                "qq_rich_summary": _safe_str(rich.get("summary")) or "最近收到的表情包",
                "qq_message_segments": rich.get("segments")
                if isinstance(rich.get("segments"), list)
                else [{"kind": "sticker", "summary": _safe_str(state.payload.get("summary") or "[动画表情]")}],
                "qq_sticker_count": max(1, _as_int(metadata.get("qq_sticker_count"), 0)),
                "recent_sticker_question": True,
                "recent_sticker_unavailable": True,
                "recent_sticker_source_message_id": _safe_str(state.payload.get("message_id")),
                "sticker_import_completed": False,
                "sticker_import_error": _safe_str(error)[:500],
                "qq_image_context": {
                    "available": False,
                    "kind": "sticker",
                    "notes": ["sticker_import_failed"],
                    "vision_summary": "QQ 表情导入失败，只拿到了动画表情占位，没拿到可分类的实际画面。",
                },
                "qq_image_context_available": False,
                "qq_image_context_notes": ["sticker_import_failed"],
            }
        )
        payload["metadata"] = metadata
        return replace(prepared, payload=payload)

    def _should_coalesce_owner_private_chat(self, prepared: PreparedMessage) -> bool:
        if self.config.owner_private_coalesce_seconds <= 0:
            return False
        if prepared.route != "chat" or prepared.local_reply:
            return False
        if prepared.target.message_kind != "private" or prepared.target.user_id not in self.config.owner_user_ids:
            return False
        text = _safe_str(prepared.payload.get("text")).strip()
        if not text:
            return False
        metadata = prepared.payload.get("metadata")
        if isinstance(metadata, dict) and _as_bool(metadata.get("control_plane"), default=False):
            return False
        return True

    async def _enqueue_coalesced_owner_private_chat(self, websocket: Any, prepared: PreparedMessage) -> bool:
        if not self._should_coalesce_owner_private_chat(prepared):
            return False
        key = self._session_id(prepared.target)
        async with self._chat_coalesce_lock:
            buffer = self._chat_coalesce_buffers.get(key)
            if buffer is None:
                task = asyncio.create_task(
                    self._flush_coalesced_owner_private_chat(websocket, key),
                    name=f"xinyu-qq-coalesce-{key}",
                )
                self._event_tasks.add(task)
                task.add_done_callback(self._event_tasks.discard)
                self._chat_coalesce_buffers[key] = {
                    "prepareds": [prepared],
                    "updated_at": time.monotonic(),
                    "task": task,
                }
            else:
                prepareds = buffer.setdefault("prepareds", [])
                prepareds.append(prepared)
                buffer["updated_at"] = time.monotonic()
        return True

    async def _flush_coalesced_owner_private_chat(self, websocket: Any, key: str) -> None:
        delay = max(0.0, self.config.owner_private_coalesce_seconds)
        while True:
            async with self._chat_coalesce_lock:
                buffer = self._chat_coalesce_buffers.get(key)
                if buffer is None:
                    return
                age = time.monotonic() - float(buffer.get("updated_at") or 0.0)
                wait_seconds = delay - age
                if wait_seconds <= 0:
                    self._chat_coalesce_buffers.pop(key, None)
                    prepared = self._build_coalesced_prepared_message(buffer.get("prepareds") or [])
                    break
            await asyncio.sleep(max(0.05, min(wait_seconds, delay or 0.05)))
        if prepared is not None:
            await self._dispatch_prepared_message(websocket, prepared)

    def _maybe_record_group_shadow_event(self, event: dict[str, Any]) -> dict[str, Any]:
        if not self.config.group_shadow_enabled:
            return {"recorded": False, "notes": ["group_shadow_disabled"]}
        if self._message_kind(event) != "group":
            return {"recorded": False, "notes": ["not_group_message"]}
        sender_id = _safe_str(event.get("user_id"), "unknown")
        self_id = _safe_str(event.get("self_id")).strip()
        if xinyu_qq_command_router.is_self_message_event(self, event, sender_id=sender_id, self_id=self_id):
            return {"recorded": False, "notes": ["self_message"]}
        if self._is_blocked_user_id(sender_id):
            return {"recorded": False, "notes": ["sender_blocked"]}
        group_id = _safe_str(event.get("group_id")).strip()
        if not group_id:
            return {"recorded": False, "notes": ["missing_group_id"]}
        if self._is_blocked_group_id(group_id):
            return {"recorded": False, "notes": ["group_blocked"]}
        if not self._group_shadow_group_allowed(group_id):
            return {"recorded": False, "notes": ["group_shadow_group_not_allowed"]}
        text = self._extract_text(event).strip()
        rich_context = self._extract_rich_message_context(event)
        if not text:
            text = _safe_str(rich_context.get("fallback_text")).strip()
        if not text:
            return {"recorded": False, "notes": ["group_shadow_empty_text"]}
        triggered, normalized_text, reason = xinyu_qq_command_router.group_trigger_result(self, event, text=text)
        try:
            return record_group_shadow_observation(
                self.xinyu_dir,
                event=event,
                text=text,
                normalized_text=normalized_text if triggered else text,
                triggered=triggered,
                trigger_reason=reason,
                allowed_group=True,
                prepare_reason=self._prepare_none_reason(event),
                max_text_chars=self.config.group_shadow_max_text_chars,
            )
        except Exception as exc:
            print(f"[xinyu_qq_gateway] group shadow observation failed: {type(exc).__name__}: {exc}", flush=True)
            return {"recorded": False, "notes": [f"group_shadow_error:{type(exc).__name__}"]}

    def _group_shadow_group_allowed(self, group_id: str) -> bool:
        return xinyu_qq_trust_policy.group_shadow_group_allowed(self.config, group_id)

    def _build_coalesced_prepared_message(self, prepareds: list[PreparedMessage]) -> PreparedMessage | None:
        items = [item for item in prepareds if item is not None]
        if not items:
            return None
        if len(items) == 1:
            return items[0]
        base = items[-1]
        payload = dict(base.payload)
        metadata = dict(payload.get("metadata")) if isinstance(payload.get("metadata"), dict) else {}
        texts = [_safe_str(item.payload.get("text")).strip() for item in items]
        texts = [text for text in texts if text]
        raw_messages = [_safe_str(item.payload.get("raw_message")).strip() for item in items]
        raw_messages = [text for text in raw_messages if text]
        message_ids = [_safe_str(item.payload.get("message_id")).strip() for item in items]
        message_ids = [text for text in message_ids if text]
        payload["text"] = "\n".join(texts)
        payload["raw_message"] = "\n".join(raw_messages or texts)
        payload["message_id"] = ",".join(message_ids)
        metadata.update(
            {
                "qq_coalesced_owner_messages": True,
                "qq_coalesced_message_count": len(items),
                "qq_coalesced_window_seconds": self.config.owner_private_coalesce_seconds,
            }
        )
        rich_segments: list[Any] = []
        forward_context: dict[str, Any] | None = None
        reply_context: dict[str, Any] | None = None
        forward_ids: list[str] = []
        arrival_seqs: list[int] = []
        prepared_seqs: list[int] = []
        for item in items:
            item_metadata = item.payload.get("metadata") if isinstance(item.payload, dict) else {}
            if not isinstance(item_metadata, dict):
                continue
            arrival_seq = _as_int(item_metadata.get("qq_arrival_seq"), 0)
            prepared_seq = _as_int(item_metadata.get("qq_prepared_seq"), 0)
            if arrival_seq:
                arrival_seqs.append(arrival_seq)
            if prepared_seq:
                prepared_seqs.append(prepared_seq)
            segments = item_metadata.get("qq_message_segments")
            if isinstance(segments, list):
                rich_segments.extend(segment for segment in segments if isinstance(segment, dict))
            forward_ids.extend(_as_str_list(item_metadata.get("qq_forward_message_ids")))
            candidate_forward = item_metadata.get("qq_forward_context")
            if isinstance(candidate_forward, dict):
                forward_context = candidate_forward
            candidate_reply = item_metadata.get("qq_reply_context")
            if isinstance(candidate_reply, dict):
                reply_context = candidate_reply
                reply_id = _safe_str(item_metadata.get("qq_reply_message_id")).strip()
                if reply_id:
                    metadata["qq_reply_message_id"] = reply_id
        if arrival_seqs:
            metadata["qq_arrival_seq"] = arrival_seqs[0]
            metadata["qq_arrival_seqs"] = arrival_seqs
        if prepared_seqs:
            metadata["qq_prepared_seqs"] = prepared_seqs
        if rich_segments:
            metadata["qq_rich_message"] = True
            metadata["qq_message_segments"] = rich_segments[:12]
            metadata["qq_sticker_count"] = sum(1 for segment in rich_segments if segment.get("kind") == "sticker")
            metadata["qq_image_count"] = sum(1 for segment in rich_segments if segment.get("kind") == "image")
            metadata["qq_rich_summary"] = "；".join(
                _safe_str(segment.get("summary") or segment.get("name") or segment.get("id")).strip()
                for segment in rich_segments[:6]
                if isinstance(segment, dict)
            )[:1200]
        if reply_context is not None:
            metadata["qq_reply_context_available"] = True
            metadata["qq_reply_context"] = reply_context
        if forward_ids:
            metadata["qq_forward_message_ids"] = list(dict.fromkeys(forward_ids))[:6]
        if forward_context is not None:
            metadata["qq_forward_context_available"] = True
            metadata["qq_forward_context"] = forward_context
            metadata["qq_forward_message_count"] = int(forward_context.get("message_count") or 0)
            metadata["qq_forward_count"] = int(forward_context.get("message_count") or 0)
            payload["forwarded_messages"] = forward_context
        payload["metadata"] = metadata
        return PreparedMessage(target=base.target, payload=payload, route=base.route, local_reply=base.local_reply)

    def _trace_qq_rich_context(self, event: dict[str, Any], prepared: PreparedMessage, *, stage: str) -> None:
        payload = prepared.payload if isinstance(prepared.payload, dict) else {}
        metadata = payload.get("metadata")
        metadata = metadata if isinstance(metadata, dict) else {}
        rich = self._extract_rich_message_context(event) if isinstance(event, dict) else {}
        segments = metadata.get("qq_message_segments")
        if not isinstance(segments, list):
            segments = rich.get("segments") if isinstance(rich.get("segments"), list) else []
        image_context = metadata.get("qq_image_context")
        image_context = image_context if isinstance(image_context, dict) else {}
        has_context = bool(
            segments
            or image_context
            or metadata.get("qq_reply_context")
            or metadata.get("qq_forward_context")
            or metadata.get("qq_rich_message")
        )
        if not has_context:
            return

        safe_segments: list[dict[str, Any]] = []
        for item in segments[:8]:
            if not isinstance(item, dict):
                continue
            safe_segments.append(
                {
                    "kind": _safe_str(item.get("kind")),
                    "segment_type": _safe_str(item.get("segment_type")),
                    "summary": _safe_str(item.get("summary") or item.get("name") or item.get("id"))[:240],
                    "mood": _safe_str(item.get("mood")),
                    "meaning": _safe_str(item.get("meaning"))[:240],
                    "confidence": _safe_str(item.get("confidence")),
                }
            )
        row = {
            "recorded_at": datetime.now().astimezone().isoformat(),
            "stage": stage,
            "route": prepared.route,
            "arrival_seq": _as_int(metadata.get("qq_arrival_seq"), 0),
            "prepared_seq": _as_int(metadata.get("qq_prepared_seq"), 0),
            "dispatch_seq": _as_int(metadata.get("qq_dispatch_seq"), 0),
            "message_kind": prepared.target.message_kind,
            "user_id_hash": _hash_id(prepared.target.user_id),
            "group_id_hash": _hash_id(prepared.target.group_id),
            "message_id": _safe_str(payload.get("message_id") or event.get("message_id")),
            "source": _safe_str(metadata.get("source")),
            "qq_rich_message": _as_bool(metadata.get("qq_rich_message"), default=bool(segments)),
            "qq_rich_summary": _safe_str(metadata.get("qq_rich_summary") or rich.get("summary"))[:800],
            "qq_sticker_count": _as_int(metadata.get("qq_sticker_count"), int(rich.get("sticker_count") or 0)),
            "qq_image_count": _as_int(metadata.get("qq_image_count"), int(rich.get("image_count") or 0)),
            "qq_forward_count": _as_int(metadata.get("qq_forward_count"), int(rich.get("forward_count") or 0)),
            "segments": safe_segments,
            "qq_image_context_available": _as_bool(metadata.get("qq_image_context_available"), default=False),
            "qq_image_context_notes": image_context.get("notes", [])[:8] if isinstance(image_context.get("notes"), list) else [],
            "qq_image_ocr_chars": len(_safe_str(image_context.get("ocr_text")).strip()),
            "qq_image_vision_chars": len(_safe_str(image_context.get("vision_summary")).strip()),
            "file_resolution_status": _safe_str(metadata.get("file_resolution_status")),
            "file_resolved_by": _safe_str(metadata.get("file_resolved_by")),
            "attachment_followup_after_ingest": _as_bool(metadata.get("attachment_followup_after_ingest"), default=False),
            "sticker_followup_after_import": _as_bool(metadata.get("sticker_followup_after_import"), default=False),
            "sticker_followup_before_import": _as_bool(metadata.get("sticker_followup_before_import"), default=False),
            "sticker_import_queued": _as_bool(metadata.get("sticker_import_queued"), default=False),
        }
        try:
            trace_path = Path(__file__).resolve().parent / QQ_RICH_CONTEXT_TRACE_REL
            append_jsonl(trace_path, row)
        except OSError as exc:
            print(f"[xinyu_qq_gateway] rich context trace write failed: {type(exc).__name__}: {exc}", flush=True)

    def prepare_message(self, event: dict[str, Any]) -> PreparedMessage | None:
        if not self.config.enabled:
            return None

        message_kind = self._message_kind(event)
        sender_id = _safe_str(event.get("user_id"), "unknown")
        self_id = _safe_str(event.get("self_id")).strip()
        group_id = _safe_str(event.get("group_id"), "")
        if xinyu_qq_command_router.is_self_message_event(self, event, sender_id=sender_id, self_id=self_id):
            return None
        if self._is_blocked_user_id(sender_id):
            print(f"[xinyu_qq_gateway] ignored blocked sender={sender_id} kind={message_kind}", flush=True)
            return None
        if message_kind == "group" and self._is_blocked_group_id(group_id):
            print(f"[xinyu_qq_gateway] ignored blocked group={group_id}", flush=True)
            return None
        text = self._extract_text(event).strip()
        rich_context = self._extract_rich_message_context(event)
        sticker_material = self._extract_sticker_import_material(event)
        learning_material = self._extract_learning_material(event)
        if not text and learning_material is None and sticker_material is None:
            text = _safe_str(rich_context.get("fallback_text")).strip()
        if not text and learning_material is None and sticker_material is None:
            return None

        if text and xinyu_qq_command_router.is_blocked_command(self, text):
            print(f"[xinyu_qq_gateway] blocked command: {text.split(maxsplit=1)[0]}", flush=True)
            return None

        if self.config.private_only and message_kind != "private":
            return None
        if message_kind == "group" and not self.config.allow_group_messages:
            return None
        if self.config.require_whitelist and sender_id not in self._effective_whitelist_user_ids():
            print(f"[xinyu_qq_gateway] ignored non-whitelisted sender={sender_id} kind={message_kind}", flush=True)
            return None

        target = ReplyTarget(message_kind=message_kind, user_id=sender_id, group_id=group_id)

        if sender_id in self.config.owner_user_ids and (
            self._looks_like_trust_command(text) or self._looks_like_trust_revoke_command(text)
        ):
            payload = self._build_chat_payload(event, target=target, text=text, rich_context=rich_context)
            metadata = payload.get("metadata")
            metadata = metadata if isinstance(metadata, dict) else {}
            metadata["source"] = "qq_gateway_trust_admin_command"
            metadata["control_plane"] = True
            payload["metadata"] = metadata
            return PreparedMessage(target=target, payload=payload, route="chat")

        if sticker_material is not None and self.config.qq_sticker_import_enabled:
            if self.config.qq_sticker_import_private_owner_only and (
                message_kind != "private" or sender_id not in self.config.owner_user_ids
            ):
                print("[xinyu_qq_gateway] ignored QQ sticker import outside owner private chat", flush=True)
                return None
            return PreparedMessage(
                target=target,
                payload=self._build_sticker_import_payload(
                    event,
                    target=target,
                    material=sticker_material,
                    text=text,
                ),
                route="sticker_import",
            )

        goldmark_command = xinyu_qq_command_router.extract_goldmark_command(self, text)
        if goldmark_command is not None:
            if message_kind != "private" or sender_id not in self.config.owner_user_ids:
                print("[xinyu_qq_gateway] ignored goldmark outside owner private chat", flush=True)
                return None
            reply_message_id = _safe_str(rich_context.get("reply_message_id") or self._extract_reply_message_id(event)).strip()
            if not reply_message_id:
                return PreparedMessage(
                    target=target,
                    payload={},
                    route="local_reply",
                    local_reply="要标记哪句，直接回复心玉发出的那条消息再发 !mark。",
                )
            return PreparedMessage(
                target=target,
                payload=self._build_goldmark_mark_payload(
                    event,
                    target=target,
                    reply_message_id=reply_message_id,
                    owner_note=_safe_str(goldmark_command.get("owner_note")).strip(),
                    text=text,
                ),
                route="goldmark_mark",
            )

        review_command = xinyu_qq_command_router.extract_review_admin_command(self, text)
        if review_command is not None:
            if message_kind != "private" or sender_id not in self.config.owner_user_ids:
                print("[xinyu_qq_gateway] ignored review admin outside owner private chat", flush=True)
                return None
            return PreparedMessage(
                target=target,
                payload=self._build_review_admin_payload(
                    event,
                    target=target,
                    text=text,
                    command=review_command,
                ),
                route="review_admin",
            )

        if learning_material is not None and self.config.qq_file_learning_enabled:
            if self.config.qq_file_learning_private_owner_only and (
                message_kind != "private" or sender_id not in self.config.owner_user_ids
            ):
                print("[xinyu_qq_gateway] ignored QQ file learning outside owner private chat", flush=True)
                return None
            return PreparedMessage(
                target=target,
                payload=self._build_learning_ingest_payload(
                    event,
                    target=target,
                    material=learning_material,
                    text=text,
                ),
                route="learning_ingest",
            )

        if message_kind == "group":
            group_ok, normalized_text, reason = xinyu_qq_command_router.group_trigger_result(self, event, text=text)
            if not group_ok:
                print(f"[xinyu_qq_gateway] ignored group message: {reason}", flush=True)
                return None
            text = normalized_text.strip()
            if not text:
                return None

        package_text = xinyu_qq_command_router.extract_package_install_command(self, text)
        if package_text is not None:
            if not self.config.package_install_enabled:
                print("[xinyu_qq_gateway] ignored package install command: disabled", flush=True)
                return None
            if self.config.package_install_owner_private_only and (
                message_kind != "private" or sender_id not in self.config.owner_user_ids
            ):
                print("[xinyu_qq_gateway] ignored package install outside owner private chat", flush=True)
                return None
            return PreparedMessage(
                target=target,
                payload=self._build_package_install_payload(
                    event,
                    target=target,
                    package_text=package_text.strip(),
                    text=text,
                ),
                route="package_install",
            )

        codex_task = xinyu_qq_command_router.extract_codex_command(self, text)
        if codex_task is not None:
            if not self.config.codex_command_enabled:
                print("[xinyu_qq_gateway] ignored Codex command: disabled", flush=True)
                return None
            if message_kind != "private":
                print("[xinyu_qq_gateway] ignored Codex command outside private chat", flush=True)
                return None
            if sender_id not in self.config.owner_user_ids:
                print(f"[xinyu_qq_gateway] ignored Codex command from non-owner sender={sender_id}", flush=True)
                return None
            if not codex_task.strip():
                return PreparedMessage(
                    target=target,
                    payload={},
                    route="local_reply",
                    local_reply="要交给 Codex 辅助脑的任务，需要写在 /codex 后面。",
                )
            return PreparedMessage(
                target=target,
                payload=self._build_codex_payload(event, target=target, task_text=codex_task.strip()),
                route="codex_execute",
            )

        if xinyu_qq_command_router.is_passthrough_command(self, text):
            return None

        return PreparedMessage(
            target=target,
            payload=self._build_chat_payload(event, target=target, text=text, rich_context=rich_context),
        )

    def _prepare_none_reason(self, event: dict[str, Any]) -> str:
        message_kind = self._message_kind(event)
        sender_id = _safe_str(event.get("user_id"), "unknown")
        self_id = _safe_str(event.get("self_id")).strip()
        group_id = _safe_str(event.get("group_id"), "")
        if xinyu_qq_command_router.is_self_message_event(self, event, sender_id=sender_id, self_id=self_id):
            return "self_message"
        if self._is_blocked_user_id(sender_id):
            return "sender_blocked"
        if message_kind == "group" and self._is_blocked_group_id(group_id):
            return "group_blocked"
        text = self._extract_text(event).strip()
        rich_context = self._extract_rich_message_context(event)
        sticker_material = self._extract_sticker_import_material(event)
        learning_material = self._extract_learning_material(event)
        if not text and learning_material is None and sticker_material is None:
            if rich_context.get("segments"):
                return "rich_message_without_supported_route"
            return "empty_message"
        if text and xinyu_qq_command_router.is_blocked_command(self, text):
            return "blocked_command"
        if self.config.private_only and message_kind != "private":
            return "private_only"
        if message_kind == "group" and not self.config.allow_group_messages:
            return "group_disabled"
        if self.config.require_whitelist and sender_id not in self._effective_whitelist_user_ids():
            return "sender_not_whitelisted"
        if sticker_material is not None and self.config.qq_sticker_import_enabled:
            if self.config.qq_sticker_import_private_owner_only and (
                message_kind != "private" or sender_id not in self.config.owner_user_ids
            ):
                return "sticker_import_private_owner_only"
        if learning_material is not None and self.config.qq_file_learning_enabled:
            if self.config.qq_file_learning_private_owner_only and (
                message_kind != "private" or sender_id not in self.config.owner_user_ids
            ):
                return "file_learning_private_owner_only"
        if message_kind == "group":
            group_ok, normalized_text, reason = xinyu_qq_command_router.group_trigger_result(self, event, text=text)
            if not group_ok:
                return reason
            if not normalized_text.strip():
                return "group_trigger_empty_text"
        package_text = xinyu_qq_command_router.extract_package_install_command(self, text)
        if package_text is not None:
            if not self.config.package_install_enabled:
                return "package_install_disabled"
            if self.config.package_install_owner_private_only and (
                message_kind != "private" or sender_id not in self.config.owner_user_ids
            ):
                return "package_install_private_owner_only"
        codex_task = xinyu_qq_command_router.extract_codex_command(self, text)
        if codex_task is not None:
            if not self.config.codex_command_enabled:
                return "codex_command_disabled"
            if message_kind != "private":
                return "codex_private_only"
            if sender_id not in self.config.owner_user_ids:
                return "codex_owner_only"
        if xinyu_qq_command_router.is_passthrough_command(self, text):
            return "passthrough_command"
        return "prepare_none"

    def _build_goldmark_mark_payload(
        self,
        event: dict[str, Any],
        *,
        target: ReplyTarget,
        reply_message_id: str,
        owner_note: str,
        text: str,
    ) -> dict[str, Any]:
        return {
            "platform": "qq",
            "adapter": GATEWAY_NAME,
            "adapter_message_id": reply_message_id,
            "route": "chat",
            "owner_note": owner_note[:500],
            "session_id": self._session_id(target),
            "user_id": target.user_id,
            "source_message_id": _safe_str(event.get("message_id")).strip(),
            "command_text": text,
            "timestamp": _as_int(event.get("time"), int(time.time())),
            "metadata": {
                "gateway": GATEWAY_NAME,
                "gateway_version": GATEWAY_VERSION,
                "source": "qq_gateway_goldmark_command",
                "onebot_post_type": _safe_str(event.get("post_type")),
                "onebot_message_type": _safe_str(event.get("message_type")),
                "is_owner_user": True,
                "control_plane": True,
            },
        }

    @staticmethod
    def _goldmark_result_reply(response: dict[str, Any]) -> str:
        if response.get("marked"):
            mark_id = _safe_str(response.get("mark_id")).strip()
            return f"标好了。{mark_id}" if mark_id else "标好了。"
        error = _safe_str(response.get("error")).strip()
        if error == "target_not_found":
            return "没找到这条回复的索引。确认你回复的是心玉刚发出的那条消息，再试一次。"
        if error == "invalid_target":
            return "这条不能标：目标回复没有有效 turn，或者被安全检查挡住了。"
        return "标记没写进去。"

    @staticmethod
    def _goldmark_error_reply(error_text: str) -> str:
        lowered = error_text.lower()
        if "target_not_found" in lowered or "404" in lowered:
            return "没找到这条回复的索引。确认你回复的是心玉刚发出的那条消息，再试一次。"
        if "invalid_target" in lowered or "409" in lowered:
            return "这条不能标：目标回复没有有效 turn，或者被安全检查挡住了。"
        return "标记失败，Core 没接住这次请求。"

    def _build_review_admin_payload(
        self,
        event: dict[str, Any],
        *,
        target: ReplyTarget,
        text: str,
        command: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "batch_id": "latest",
            "command": _safe_str(command.get("command")),
            "indices": command.get("indices", []),
            "mod_text": _safe_str(command.get("mod_text")),
            "raw_command": text,
            "platform": "qq",
            "adapter": GATEWAY_NAME,
            "message_type": "private_review_admin_command",
            "session_id": self._session_id(target),
            "user_id": target.user_id,
            "sender_name": self._sender_name(event),
            "message_id": _safe_str(event.get("message_id")),
            "timestamp": _as_int(event.get("time"), int(time.time())),
            "metadata": {
                "gateway": GATEWAY_NAME,
                "gateway_version": GATEWAY_VERSION,
                "source": "qq_gateway_review_admin_command",
                "is_owner_user": target.user_id in self.config.owner_user_ids,
                "control_plane": True,
            },
        }

    _message_kind = xinyu_qq_normalizer.message_kind

    @staticmethod
    def _message_segments(event: dict[str, Any]) -> list[dict[str, Any]]:
        return xinyu_qq_normalizer.message_segments(None, event)

    @staticmethod
    def _segment_data(segment: dict[str, Any]) -> dict[str, Any]:
        return xinyu_qq_normalizer.segment_data(None, segment)

    def _extract_rich_message_context(self, event: dict[str, Any]) -> dict[str, Any]:
        summaries: list[str] = []
        segment_records: list[dict[str, Any]] = []
        sticker_count = 0
        image_count = 0
        reply_message_id = self._extract_reply_message_id(event)
        forward_ids = self._extract_forward_message_ids(event)
        forward_count = 0

        for segment in self._message_segments(event):
            segment_type = _safe_str(segment.get("type")).strip().lower()
            if not xinyu_qq_rich_context.is_rich_context_segment(segment_type):
                continue
            record = self._summarize_segment(segment_type, self._segment_data(segment))
            if not record:
                continue
            segment_records.append(record)
            kind = _safe_str(record.get("kind"))
            label = _safe_str(record.get("summary") or record.get("name") or record.get("id")).strip()
            if kind == "sticker":
                sticker_count += 1
                summaries.append(f"表情包:{label or 'unknown'}")
            elif kind == "image":
                image_count += 1
                summaries.append(f"图片:{label or 'unknown'}")
            elif kind == "reply" and label:
                summaries.append(f"引用:{label}")
            elif kind == "forward":
                forward_count += 1
                summaries.append(f"转发聊天记录:{label or 'merged'}")
            elif kind in {"json", "xml"}:
                summaries.append(f"{kind}:{label or 'message'}")

        fallback_text = ""
        if not self._extract_text(event).strip() and forward_count:
            fallback_text = "我转发了一段聊天记录。"
        elif not self._extract_text(event).strip() and summaries:
            fallback_text = "我发了" + "，".join(summaries[:3])

        return {
            "segments": segment_records,
            "summary": "；".join(summaries[:6]),
            "fallback_text": fallback_text,
            "sticker_count": sticker_count,
            "image_count": image_count,
            "forward_count": forward_count,
            "forward_message_ids": forward_ids,
            "reply_message_id": reply_message_id,
        }

    _summarize_segment = staticmethod(xinyu_qq_rich_context.summarize_segment)

    _infer_received_sticker_semantics = staticmethod(xinyu_qq_sticker_semantics.infer_received_sticker_semantics)
    _image_segment_looks_like_sticker = staticmethod(xinyu_qq_sticker_semantics.image_segment_looks_like_sticker)

    def _summarize_replied_message(self, event: dict[str, Any]) -> dict[str, Any]:
        text = self._extract_text(event).strip()
        rich = self._extract_rich_message_context(event)
        return {
            "message_id": _safe_str(event.get("message_id")).strip(),
            "sender_name": self._sender_name(event),
            "user_id": _safe_str(event.get("user_id")).strip(),
            "text": text[:1200],
            "raw_message": _safe_str(event.get("raw_message"))[:1200],
            "rich_summary": _safe_str(rich.get("summary"))[:1200],
            "segments": rich.get("segments", [])[:8],
            "forward_message_ids": rich.get("forward_message_ids", [])[:6],
        }

    _extract_text = xinyu_qq_normalizer.extract_text

    def _extract_learning_material(self, event: dict[str, Any]) -> dict[str, str] | None:
        message = event.get("message")
        if isinstance(message, list):
            for segment in message:
                if not isinstance(segment, dict):
                    continue
                material = self._learning_material_from_segment(segment)
                if material is not None:
                    return material
        raw_message = _safe_str(event.get("raw_message") or message)
        if raw_message:
            return self._learning_material_from_cq(raw_message)
        return None

    def _extract_sticker_import_material(self, event: dict[str, Any]) -> dict[str, str] | None:
        for segment in self._message_segments(event):
            material = self._sticker_import_material_from_segment(segment)
            if material is not None:
                return material
        return None

    def _sticker_import_material_from_segment(self, segment: dict[str, Any]) -> dict[str, str] | None:
        segment_type = _safe_str(segment.get("type")).strip().lower()
        data = self._segment_data(segment)
        if segment_type == "image":
            if not self._image_segment_looks_like_sticker(data):
                return None
        elif not xinyu_qq_rich_context.is_sticker_segment(segment_type):
            return None
        return self._sticker_import_material_from_data(segment_type, data)

    _sticker_import_material_from_data = staticmethod(
        xinyu_qq_attachment_resolver.sticker_import_material_from_data
    )

    def _learning_material_from_segment(self, segment: dict[str, Any]) -> dict[str, str] | None:
        segment_type = _safe_str(segment.get("type")).strip().lower()
        if segment_type not in {"file", "image", "record", "video"}:
            return None
        data = segment.get("data")
        if not isinstance(data, dict):
            data = {}
        if segment_type == "image" and self._image_segment_looks_like_sticker(data):
            return None
        return self._learning_material_from_data(segment_type, data)

    _learning_material_from_data = staticmethod(xinyu_qq_attachment_resolver.learning_material_from_data)

    def _learning_material_from_cq(self, raw_message: str) -> dict[str, str] | None:
        for segment in self._parse_cq_segments(raw_message):
            segment_type = _safe_str(segment.get("type")).strip().lower()
            if segment_type not in {"file", "image", "record", "video"}:
                continue
            data = self._segment_data(segment)
            if segment_type == "image" and self._image_segment_looks_like_sticker(data):
                continue
            material = self._learning_material_from_data(segment_type, data)
            if material is not None:
                return material
        return None

    _looks_like_file_path = staticmethod(xinyu_qq_attachment_resolver.looks_like_file_path)

    _sender_name = xinyu_qq_normalizer.sender_name

    def _build_chat_payload(
        self,
        event: dict[str, Any],
        *,
        target: ReplyTarget,
        text: str,
        rich_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        session_id = self._session_id(target)
        message_type = f"{target.message_kind}_text"
        rich_context = rich_context or self._extract_rich_message_context(event)
        metadata = {
            "gateway": GATEWAY_NAME,
            "gateway_version": GATEWAY_VERSION,
            "source": "onebot_message_event",
            "onebot_post_type": _safe_str(event.get("post_type")),
            "onebot_message_type": _safe_str(event.get("message_type")),
            "is_owner_user": target.user_id in self.config.owner_user_ids,
            "is_trusted_user": self._is_trusted_user_id(target.user_id),
            "user_trust_level": self._trust_level_for_user_id(target.user_id),
        }
        if rich_context.get("segments"):
            metadata["qq_rich_message"] = True
            metadata["qq_rich_summary"] = _safe_str(rich_context.get("summary"))[:1200]
            metadata["qq_message_segments"] = rich_context.get("segments", [])[:12]
            metadata["qq_sticker_count"] = int(rich_context.get("sticker_count") or 0)
            metadata["qq_image_count"] = int(rich_context.get("image_count") or 0)
            metadata["qq_forward_count"] = int(rich_context.get("forward_count") or 0)
        reply_message_id = _safe_str(rich_context.get("reply_message_id")).strip()
        if reply_message_id:
            metadata["qq_reply_message_id"] = reply_message_id
        forward_ids = rich_context.get("forward_message_ids")
        if isinstance(forward_ids, list) and forward_ids:
            metadata["qq_forward_message_ids"] = forward_ids[:6]
        return {
            "platform": "qq",
            "adapter": GATEWAY_NAME,
            "message_type": message_type,
            "session_id": session_id,
            "user_id": target.user_id,
            "sender_name": self._sender_name(event),
            "group_id": target.group_id or None,
            "bot_id": _safe_str(event.get("self_id")),
            "message_id": _safe_str(event.get("message_id")),
            "text": text,
            "raw_message": _safe_str(event.get("raw_message"), text),
            "timestamp": _as_int(event.get("time"), int(time.time())),
            "metadata": metadata,
        }

    def _build_learning_ingest_payload(
        self,
        event: dict[str, Any],
        *,
        target: ReplyTarget,
        material: dict[str, str],
        text: str,
    ) -> dict[str, Any]:
        name = _safe_str(material.get("name"), "qq-file").strip() or "qq-file"
        reason_text = self._learning_reason_text(text)
        payload: dict[str, Any] = {
            "origin": "owner_supplied",
            "reason": reason_text,
            "question_id": "qq-file-learning",
            "title": name,
            "label": name,
            "file_name": name,
            "file_id": _safe_str(material.get("file_id")).strip(),
            "stage": self.config.qq_file_learning_stage,
            "curated": self.config.qq_file_learning_curated,
            "metadata": {
                "gateway": GATEWAY_NAME,
                "gateway_version": GATEWAY_VERSION,
                "source": "qq_file_message",
                "onebot_post_type": _safe_str(event.get("post_type")),
                "onebot_message_type": _safe_str(event.get("message_type")),
                "message_id": _safe_str(event.get("message_id")),
                "session_id": self._session_id(target),
                "user_id": target.user_id,
                "group_id": target.group_id or "",
                "sender_name": self._sender_name(event),
                "segment_type": _safe_str(material.get("segment_type")),
                "file_id": _safe_str(material.get("file_id")).strip(),
                "is_owner_user": target.user_id in self.config.owner_user_ids,
                "is_trusted_user": self._is_trusted_user_id(target.user_id),
                "user_trust_level": self._trust_level_for_user_id(target.user_id),
            },
        }
        file_url = _safe_str(material.get("url")).strip()
        file_path = _safe_str(material.get("path")).strip()
        if file_url:
            payload["file_url"] = file_url
        elif file_path:
            payload["file_path"] = file_path
        return payload

    def _build_sticker_import_payload(
        self,
        event: dict[str, Any],
        *,
        target: ReplyTarget,
        material: dict[str, str],
        text: str,
    ) -> dict[str, Any]:
        name = _safe_str(material.get("name"), "qq-sticker").strip() or "qq-sticker"
        payload: dict[str, Any] = {
            "origin": "qq_owner_sticker",
            "platform": "qq",
            "adapter": GATEWAY_NAME,
            "message_type": "private_sticker_import",
            "session_id": self._session_id(target),
            "user_id": target.user_id,
            "sender_name": self._sender_name(event),
            "group_id": target.group_id or "",
            "message_id": _safe_str(event.get("message_id")),
            "timestamp": _as_int(event.get("time"), int(time.time())),
            "file_name": name,
            "name": name,
            "summary": _safe_str(material.get("summary")).strip(),
            "file_id": _safe_str(material.get("file_id")).strip(),
            "owner_text": text.strip()[:500],
            "use_clip": self.config.qq_sticker_import_use_clip,
            "use_ocr": self.config.qq_sticker_import_use_ocr,
            "metadata": {
                "gateway": GATEWAY_NAME,
                "gateway_version": GATEWAY_VERSION,
                "source": "qq_sticker_message",
                "onebot_post_type": _safe_str(event.get("post_type")),
                "onebot_message_type": _safe_str(event.get("message_type")),
                "message_id": _safe_str(event.get("message_id")),
                "session_id": self._session_id(target),
                "user_id": target.user_id,
                "group_id": target.group_id or "",
                "sender_name": self._sender_name(event),
                "segment_type": _safe_str(material.get("segment_type")),
                "file_id": _safe_str(material.get("file_id")).strip(),
                "is_owner_user": target.user_id in self.config.owner_user_ids,
                "is_trusted_user": self._is_trusted_user_id(target.user_id),
                "user_trust_level": self._trust_level_for_user_id(target.user_id),
                "control_plane": True,
            },
        }
        file_url = _safe_str(material.get("url")).strip()
        file_path = _safe_str(material.get("path")).strip()
        if file_url:
            payload["file_url"] = file_url
        elif file_path:
            payload["file_path"] = file_path
        return payload

    @staticmethod
    def _learning_reason_text(text: str) -> str:
        stripped = text.strip()
        if not stripped:
            return "owner supplied QQ file"
        without_cq = NativeQQGateway._strip_cq_segments(stripped)
        return without_cq or "owner supplied QQ file"

    def _build_sticker_followup_chat_payload(
        self,
        event: dict[str, Any],
        *,
        target: ReplyTarget,
        sticker_payload: dict[str, Any],
        sticker_response: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        if target.message_kind != "private":
            return None
        sticker_response = sticker_response if isinstance(sticker_response, dict) else {}
        rich_context = self._extract_rich_message_context(event)
        if not rich_context.get("segments"):
            return None
        sticker_context = self._sticker_context_from_import_response(sticker_payload, sticker_response)
        text = self._sticker_followup_text(rich_context, sticker_payload, sticker_context)
        payload = self._build_chat_payload(event, target=target, text=text, rich_context=rich_context)
        metadata = dict(payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {})
        import_completed = _as_bool(sticker_context.get("import_completed"), default=False)
        if import_completed:
            metadata["qq_message_segments"] = self._enrich_sticker_segments_with_import_context(
                metadata.get("qq_message_segments"),
                sticker_context,
            )
        metadata.update(
            {
                "source": "qq_sticker_context_reaction",
                "sticker_followup_before_import": not import_completed,
                "sticker_followup_after_import": import_completed,
                "sticker_import_queued": not import_completed,
                "sticker_import_completed": import_completed,
                "sticker_import_accepted": _as_bool(sticker_context.get("accepted"), default=False),
                "sticker_imported": _as_bool(sticker_context.get("imported"), default=False),
                "sticker_mood": _safe_str(sticker_context.get("mood")),
                "sticker_mood_label": _safe_str(sticker_context.get("mood_label")),
                "sticker_confidence": _safe_str(sticker_context.get("confidence")),
                "sticker_destination": _safe_str(sticker_context.get("destination")),
                "sticker_import_material_id": _safe_str(sticker_response.get("material_id")),
                "sticker_import_item_id": _safe_str(sticker_response.get("learning_item_id")),
                "sticker_file_name": _safe_str(sticker_payload.get("file_name") or sticker_payload.get("name")),
                "attachment_followup_mode": "sticker_context_reaction",
            }
        )
        if import_completed:
            metadata["qq_image_context"] = sticker_context
            metadata["qq_image_context_available"] = _as_bool(sticker_context.get("available"), default=False)
            metadata["qq_image_context_notes"] = sticker_context.get("notes", [])[:8] if isinstance(sticker_context.get("notes"), list) else []
        payload["metadata"] = metadata
        return payload

    @staticmethod
    def _sticker_followup_text(
        rich_context: dict[str, Any],
        sticker_payload: dict[str, Any],
        sticker_context: dict[str, Any],
    ) -> str:
        if _as_bool(sticker_context.get("import_completed"), default=False):
            label = _safe_str(sticker_context.get("mood_label") or sticker_context.get("mood")).strip()
            meaning = _safe_str(sticker_context.get("meaning")).strip()
            summary = "我刚发了一张表情包。"
            if label:
                summary = f"我刚发了一张偏{label}的表情包。"
            if meaning:
                summary += f"大概是{meaning}。"
            return summary[:500]
        return (
            _safe_str(rich_context.get("fallback_text")).strip()
            or _safe_str(sticker_payload.get("summary") or sticker_payload.get("file_name")).strip()
            or "\u6211\u521a\u53d1\u4e86\u4e00\u4e2a\u8868\u60c5\u5305\u3002"
        )

    @staticmethod
    def _first_sticker_import_item(sticker_response: dict[str, Any]) -> dict[str, Any]:
        items = sticker_response.get("items")
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    return item
        return {}

    def _sticker_context_from_import_response(
        self,
        sticker_payload: dict[str, Any],
        sticker_response: dict[str, Any],
    ) -> dict[str, Any]:
        item = self._first_sticker_import_item(sticker_response)
        import_completed = any(
            key in sticker_response for key in ("accepted", "imported", "mood", "destination", "items", "failed")
        )
        accepted = _as_bool(sticker_response.get("accepted"), default=False)
        imported = _as_bool(sticker_response.get("imported"), default=False)
        mood = _safe_str(item.get("mood") or sticker_response.get("mood")).strip()
        mood_label = _safe_str(sticker_response.get("mood_label") or mood).strip()
        confidence = _safe_str(item.get("confidence") or sticker_response.get("confidence")).strip()
        meaning = _safe_str(item.get("meaning")).strip()
        destination = _safe_str(sticker_response.get("destination") or item.get("destination")).strip()
        ocr_text = _safe_str(item.get("ocr_text")).strip()
        clip_mood = _safe_str(item.get("clip_mood")).strip()
        clip_confidence = _safe_str(item.get("clip_confidence")).strip()
        file_name = _safe_str(sticker_payload.get("file_name") or sticker_payload.get("name")).strip()
        notes = ["sticker_import_completed" if import_completed else "sticker_import_pending"]
        if not accepted and import_completed:
            notes.append("sticker_import_not_accepted")
        if imported:
            notes.append("sticker_imported")
        summary_parts: list[str] = []
        if import_completed:
            if accepted and imported:
                summary_parts.append("这张 QQ 表情已经收进本地表情库")
            elif accepted:
                summary_parts.append("这张 QQ 表情已经接收，但还没有稳定分类")
            else:
                summary_parts.append("这张 QQ 表情暂时没有成功入库")
        if file_name:
            summary_parts.append(f"文件名/摘要：{file_name}")
        if mood_label or mood:
            summary_parts.append(f"分类：{mood_label or mood}")
        if confidence:
            summary_parts.append(f"置信度：{confidence}")
        if clip_mood:
            clip_note = f"CLIP 判断：{clip_mood}"
            if clip_confidence:
                clip_note += f" ({clip_confidence})"
            summary_parts.append(clip_note)
        if meaning:
            summary_parts.append(f"语义：{meaning}")
        if destination:
            summary_parts.append(f"入库位置：{destination}")
        available = bool(import_completed and (accepted or mood or ocr_text or clip_mood or destination))
        return {
            "available": available,
            "kind": "sticker",
            "import_completed": import_completed,
            "accepted": accepted,
            "imported": imported,
            "mood": mood,
            "mood_label": mood_label,
            "confidence": confidence,
            "meaning": meaning,
            "destination": destination,
            "ocr_text": ocr_text,
            "vision_summary": "；".join(summary_parts)[:1200],
            "notes": notes,
        }

    @staticmethod
    def _enrich_sticker_segments_with_import_context(value: Any, sticker_context: dict[str, Any]) -> list[dict[str, Any]]:
        segments = value if isinstance(value, list) else []
        enriched: list[dict[str, Any]] = []
        updated = False
        for item in segments:
            if not isinstance(item, dict):
                continue
            record = dict(item)
            if not updated and _safe_str(record.get("kind")) == "sticker":
                mood = _safe_str(sticker_context.get("mood")).strip()
                meaning = _safe_str(sticker_context.get("meaning")).strip()
                confidence = _safe_str(sticker_context.get("confidence")).strip()
                if mood:
                    record["mood"] = mood
                if meaning:
                    record["meaning"] = meaning
                if confidence:
                    record["confidence"] = confidence
                updated = True
            enriched.append(record)
        return enriched

    def _build_attachment_followup_chat_payload(
        self,
        event: dict[str, Any],
        *,
        target: ReplyTarget,
        learning_payload: dict[str, Any],
        learning_response: dict[str, Any],
        image_context: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        image_context = image_context if isinstance(image_context, dict) else {}
        is_image_attachment = is_image_learning_payload(learning_payload, learning_response)
        has_image_context = bool(image_context.get("available"))
        rich_context = self._extract_rich_message_context(event)
        has_rich_context = bool(rich_context.get("segments"))
        if not learning_response.get("extracted_text") and not has_image_context and not (
            is_image_attachment and has_rich_context
        ):
            return None
        if target.message_kind != "private":
            return None
        text = _safe_str(learning_payload.get("reason")).strip()
        if not text or text == "owner supplied QQ file":
            text = (
                _safe_str(rich_context.get("fallback_text")).strip()
                or (
                    "\u6211\u521a\u53d1\u4e86\u4e00\u5f20\u56fe\u7247\u3002"
                    if is_image_attachment
                    else "\u6211\u521a\u53d1\u4e86\u4e00\u4e2a\u9644\u4ef6\u3002"
                )
            )
        payload = self._build_chat_payload(event, target=target, text=text, rich_context=rich_context)
        metadata = dict(payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {})
        metadata.update(
            {
                "source": "qq_attachment_followup_after_learning_ingest",
                "attachment_learning_item_id": _safe_str(learning_response.get("learning_item_id")),
                "attachment_material_id": _safe_str(learning_response.get("material_id")),
                "attachment_extracted_text_path": _safe_str(learning_response.get("extracted_text_path")),
                "attachment_followup_after_ingest": True,
                "attachment_followup_mode": "read_then_natural_reaction",
            }
        )
        if image_context or is_image_attachment:
            if not image_context:
                image_context = {"available": False, "kind": "image", "notes": ["image_context_unavailable"]}
            metadata["qq_image_context"] = image_context
            metadata["qq_image_context_available"] = bool(image_context.get("available"))
            metadata["qq_image_context_notes"] = image_context.get("notes", [])[:8]
        payload["metadata"] = metadata
        return payload

    def _build_package_install_payload(
        self,
        event: dict[str, Any],
        *,
        target: ReplyTarget,
        package_text: str,
        text: str,
    ) -> dict[str, Any]:
        session_id = self._session_id(target)
        return {
            "packages": package_text,
            "current_text": text,
            "session_id": session_id,
            "source": "qq_gateway_package_install_message",
            "requested_by": target.user_id,
            "message_id": _safe_str(event.get("message_id")),
            "timestamp": _as_int(event.get("time"), int(time.time())),
            "metadata": {
                "gateway": GATEWAY_NAME,
                "gateway_version": GATEWAY_VERSION,
                "source": "qq_gateway_package_install_message",
                "onebot_post_type": _safe_str(event.get("post_type")),
                "onebot_message_type": _safe_str(event.get("message_type")),
                "session_id": session_id,
                "user_id": target.user_id,
                "sender_name": self._sender_name(event),
                "is_owner_user": target.user_id in self.config.owner_user_ids,
                "is_trusted_user": self._is_trusted_user_id(target.user_id),
                "user_trust_level": self._trust_level_for_user_id(target.user_id),
            },
        }

    def _build_codex_payload(self, event: dict[str, Any], *, target: ReplyTarget, task_text: str) -> dict[str, Any]:
        session_id = self._session_id(target)
        metadata = {
            "gateway": GATEWAY_NAME,
            "gateway_version": GATEWAY_VERSION,
            "source": "qq_gateway_codex_execute_message",
            "onebot_post_type": _safe_str(event.get("post_type")),
            "onebot_message_type": _safe_str(event.get("message_type")),
            "is_owner_user": True,
            "owner_local_write_approved": looks_like_owner_local_write_request(task_text),
            "codex_auxiliary_brain": True,
            "direct_cli_execution": False,
        }
        return {
            "platform": "qq",
            "adapter": GATEWAY_NAME,
            "message_type": "private_codex_command",
            "session_id": session_id,
            "user_id": target.user_id,
            "sender_name": self._sender_name(event),
            "group_id": None,
            "bot_id": _safe_str(event.get("self_id")),
            "message_id": _safe_str(event.get("message_id")),
            "text": f"用 Codex 辅助慢脑处理这个任务：{task_text}",
            "raw_owner_task": task_text,
            "source": "qq_gateway_codex_execute_message",
            "background": self.config.codex_background,
            "auto_study": self.config.codex_auto_study,
            "timeout_seconds": self.config.codex_timeout_seconds,
            "visible_window": self.config.codex_visible_window,
            "window_title": self.config.codex_window_title,
            "network_access": self.config.codex_network_access,
            "timestamp": _as_int(event.get("time"), int(time.time())),
            "metadata": metadata,
        }

    def _session_id(self, target: ReplyTarget) -> str:
        if target.message_kind == "group":
            return f"qq:group:{target.group_id or 'unknown'}:{target.user_id}"
        return f"qq:private:{target.user_id}"

    def _visible_reply(self, text: str) -> str:
        reply = text.strip()
        if reply in {"[WAITING]", "WAITING"}:
            return ""
        reply = dedupe_visible_reply(reply).text
        if self.config.max_reply_chars and len(reply) > self.config.max_reply_chars:
            return reply[: self.config.max_reply_chars].rstrip() + "\n[truncated]"
        return reply

    async def _send_visible_reply(
        self,
        websocket: Any,
        prepared: PreparedMessage,
        reply: str,
        core_response: dict[str, Any],
    ) -> dict[str, Any] | None:
        bubbles = self._visible_reply_bubbles(prepared, reply, core_response)
        if not bubbles:
            return None
        responses: list[dict[str, Any] | None] = []
        for index, bubble in enumerate(bubbles):
            if index > 0:
                delay = max(0.0, self.config.reply_bubble_delay_seconds)
                if delay:
                    await asyncio.sleep(delay)
            responses.append(await self.send_reply(websocket, prepared.target, bubble))
        return self._combined_reply_action_response(responses)

    def _visible_reply_bubbles(
        self,
        prepared: PreparedMessage,
        reply: str,
        core_response: dict[str, Any] | None = None,
    ) -> list[str]:
        text = reply.strip()
        if not text:
            return []
        forced = self._forced_reply_bubble_units(core_response or {})
        if forced:
            return forced
        if not self._should_split_visible_reply(prepared, text, core_response or {}):
            return [text]
        bubbles = self._split_visible_reply_bubbles(text)
        return bubbles if len(bubbles) > 1 else [text]

    def _outbox_visible_reply_bubbles(
        self,
        target: ReplyTarget,
        reply: str,
        claim: dict[str, Any],
    ) -> list[str]:
        text = reply.strip()
        if not text:
            return []
        metadata = claim.get("metadata")
        metadata = metadata if isinstance(metadata, dict) else {}
        forced = self._forced_reply_bubble_units({"reply_bubble_force_units": metadata.get("reply_bubble_force_units")})
        if forced:
            return forced
        if not self.config.reply_bubble_split_enabled:
            return [text]
        if self.config.reply_bubble_private_only and target.message_kind != "private":
            return [text]
        if len(text) < self.config.reply_bubble_min_chars:
            return [text]
        if _as_bool(metadata.get("qq_reply_bubble_disable"), False):
            return [text]
        source = _safe_str(claim.get("source") or metadata.get("source")).strip()
        if source in {
            "qq_attachment_followup_after_learning_ingest",
            "qq_sticker_context_reaction",
        }:
            return [text]
        if self._looks_like_structured_visible_reply(text):
            return [text]
        bubbles = self._split_visible_reply_bubbles(text)
        return bubbles if len(bubbles) > 1 else [text]

    def _forced_reply_bubble_units(self, source: dict[str, Any]) -> list[str]:
        raw_units = source.get("reply_bubble_force_units")
        if not isinstance(raw_units, list):
            return []
        units: list[str] = []
        for raw in raw_units:
            text = _safe_str(raw).strip()
            if not text:
                continue
            if "\n" in text or "\r" in text:
                return []
            if len(text) > 80:
                return []
            units.append(text)
            if len(units) >= self.config.reply_bubble_force_max_bubbles:
                break
        return units if len(units) >= 2 else []

    def _should_split_visible_reply(
        self,
        prepared: PreparedMessage,
        reply: str,
        core_response: dict[str, Any],
    ) -> bool:
        if not self.config.reply_bubble_split_enabled:
            return False
        if prepared.route != "chat":
            return False
        if self.config.reply_bubble_private_only and prepared.target.message_kind != "private":
            return False
        if len(reply) < self.config.reply_bubble_min_chars:
            return False
        payload = prepared.payload if isinstance(prepared.payload, dict) else {}
        metadata = payload.get("metadata")
        metadata = metadata if isinstance(metadata, dict) else {}
        if _as_bool(metadata.get("qq_reply_bubble_disable"), False):
            return False
        source = _safe_str(metadata.get("source")).strip()
        if source in {
            "qq_attachment_followup_after_learning_ingest",
            "qq_sticker_context_reaction",
        }:
            return False
        if self._looks_like_structured_visible_reply(reply):
            return False
        return True

    @staticmethod
    def _looks_like_structured_visible_reply(text: str) -> bool:
        lowered = text.lower()
        structured_markers = (
            "```",
            "http://",
            "https://",
            "file://",
            "traceback",
            "exception",
            "error:",
            "exit code",
            "powershell",
            "pytest",
            "codex",
            "runtime/",
            "runtime\\",
            ".py",
            ".ps1",
            ".json",
            ".md",
            ".log",
        )
        if any(marker in lowered for marker in structured_markers):
            return True
        if any(marker in text for marker in ("\u62a5\u544a\u540d", "\u9000\u51fa\u7801", "\u9519\u8bef:")):
            return True
        if re.search(r"(?m)^\s*(?:[-*+]|\d+[.)])\s+\S", text):
            return True
        return text.count("|") >= 4 and "\n" in text

    def _split_visible_reply_bubbles(self, text: str) -> list[str]:
        max_bubbles = max(2, min(5, self.config.reply_bubble_max_bubbles))
        soft_max = max(60, self.config.reply_bubble_soft_max_chars)
        min_piece = max(12, soft_max // 4)
        units = self._reply_sentence_units(text)
        chunks: list[str] = []
        current = ""
        for unit in units:
            if not unit.strip():
                continue
            candidate = current + unit if current else unit
            if (
                current.strip()
                and len(candidate.strip()) > soft_max
                and len(current.strip()) >= min_piece
                and len(chunks) < max_bubbles - 1
            ):
                chunks.append(current.strip())
                current = unit.lstrip()
            else:
                current = candidate
        if current.strip():
            chunks.append(current.strip())
        if len(chunks) <= 1:
            chunks = self._hard_split_reply_text(text, soft_max=soft_max, max_bubbles=max_bubbles)
        chunks = self._merge_tiny_reply_chunks(chunks, min_piece=min_piece)
        if len(chunks) <= 1:
            return [text]
        if any(not chunk.strip() for chunk in chunks):
            return [text]
        return chunks[:max_bubbles]

    @staticmethod
    def _reply_sentence_units(text: str) -> list[str]:
        pattern = re.compile(
            r"\S[\s\S]*?(?:[\u3002\uff01\uff1f\uff1b]+[\)\]\}\"'\u201d\u2019]*|[.!?;]+[\)\]\}\"'\u201d\u2019]*(?:\s+|$)|\n+|$)"
        )
        units = [match.group(0) for match in pattern.finditer(text.strip()) if match.group(0).strip()]
        return units or [text.strip()]

    def _hard_split_reply_text(self, text: str, *, soft_max: int, max_bubbles: int) -> list[str]:
        chunks: list[str] = []
        rest = text.strip()
        min_cut = max(30, soft_max // 2)
        separators = ("\n", "\u3002", "\uff01", "\uff1f", "\uff1b", ";", ".", "!", "?", "\uff0c", ",", "\u3001", " ")
        while len(rest) > soft_max and len(chunks) < max_bubbles - 1:
            window = rest[: soft_max + 20]
            cut = -1
            for separator in separators:
                position = rest[: soft_max + 1].rfind(separator)
                candidate = position + len(separator)
                if position >= 0 and len(rest) - candidate >= max(8, soft_max // 5):
                    cut = max(cut, candidate)
            if cut < min_cut:
                for separator in separators:
                    position = window.rfind(separator)
                    candidate = position + len(separator)
                    if position >= 0 and len(rest) - candidate >= max(8, soft_max // 5):
                        cut = max(cut, candidate)
            if cut < min_cut:
                cut = soft_max
            chunks.append(rest[:cut].strip())
            rest = rest[cut:].strip()
        if rest:
            chunks.append(rest)
        return chunks

    def _merge_tiny_reply_chunks(self, chunks: list[str], *, min_piece: int) -> list[str]:
        merged = [chunk.strip() for chunk in chunks if chunk.strip()]
        while len(merged) > 1 and len(merged[-1]) < min_piece:
            tail = merged.pop()
            merged[-1] = self._join_reply_fragments(merged[-1], tail)
        while len(merged) > 1 and len(merged[0]) < min_piece:
            head = merged.pop(0)
            merged[0] = self._join_reply_fragments(head, merged[0])
        return merged

    @staticmethod
    def _join_reply_fragments(left: str, right: str) -> str:
        left = left.rstrip()
        right = right.lstrip()
        if not left:
            return right
        if not right:
            return left
        separator = " " if re.search(r"[A-Za-z0-9]$", left) and re.match(r"[A-Za-z0-9]", right) else ""
        return f"{left}{separator}{right}".strip()

    def _combined_reply_action_response(self, responses: list[dict[str, Any] | None]) -> dict[str, Any] | None:
        if not responses:
            return None
        if len(responses) == 1:
            return responses[0]
        message_ids: list[str] = []
        errors: list[str] = []
        for response in responses:
            ok, adapter_message_id, adapter_error = self._onebot_action_result(response)
            if ok and adapter_message_id:
                message_ids.append(adapter_message_id)
            elif adapter_error:
                errors.append(adapter_error)
        if message_ids:
            return {
                "status": "ok",
                "retcode": 0,
                "data": {
                    "message_id": ",".join(message_ids),
                    "reply_bubble_message_ids": message_ids,
                    "reply_bubble_count": len(responses),
                },
                "message": "; ".join(errors),
            }
        return responses[-1]

    async def send_reply(self, websocket: Any, target: ReplyTarget, text: str) -> dict[str, Any] | None:
        action, params = xinyu_qq_sender.text_message_action(target, text)
        return await self.send_action(websocket, action, params)

    async def send_image(
        self,
        websocket: Any,
        target: ReplyTarget,
        image_file: str,
        *,
        caption: str = "",
    ) -> dict[str, Any] | None:
        action, params = xinyu_qq_sender.image_message_action(target, image_file)
        return await self.send_action(websocket, action, params)

    async def send_file(
        self,
        websocket: Any,
        target: ReplyTarget,
        file_path: str,
        *,
        name: str,
    ) -> dict[str, Any] | None:
        action, params = xinyu_qq_sender.file_upload_action(target, file_path, name=name)
        return await self.send_action(websocket, action, params)

    async def send_action(self, websocket: Any, action: str, params: dict[str, Any]) -> dict[str, Any] | None:
        connection_id = self._connection_id_for_websocket(websocket)
        echo = f"xinyu-{connection_id}-{int(time.time() * 1000)}-{id(params)}"
        payload = {"action": action, "params": params, "echo": echo}
        future: asyncio.Future[dict[str, Any]] = asyncio.get_running_loop().create_future()
        try:
            async with self._action_lock:
                self._pending_actions[echo] = PendingAction(connection_id=connection_id, future=future)
                await websocket.send(json.dumps(payload, ensure_ascii=False))
        except Exception as exc:
            self._pending_actions.pop(echo, None)
            if not future.done():
                future.cancel()
            print(f"[xinyu_qq_gateway] OneBot action send failed: {action}: {type(exc).__name__}: {exc}", flush=True)
            return None
        try:
            return await asyncio.wait_for(future, timeout=15)
        except TimeoutError:
            print(f"[xinyu_qq_gateway] OneBot action timed out: {action}", flush=True)
            self._pending_actions.pop(echo, None)
            return None
        except BridgeError as exc:
            print(f"[xinyu_qq_gateway] OneBot action failed: {action}: {exc}", flush=True)
            return None


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    _quiet_websockets_handshake_noise()

    args = build_gateway_parser(Path(__file__).resolve().with_name("xinyu_qq_gateway.config.json")).parse_args()
    config = GatewayConfig.from_file(args.config).with_overrides(
        host=args.host or None,
        port=args.port or None,
        path=args.path or None,
        core_chat_url=args.core_url or None,
        bridge_token=args.bridge_token,
    )
    gateway = NativeQQGateway(config, config_path=args.config)
    asyncio.run(gateway.run())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

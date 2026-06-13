from __future__ import annotations

import asyncio
import contextlib
import json
import mimetypes
import re
import sys
import tempfile
import time
import traceback
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import Any

from state_service import append_jsonl, atomic_write_json
from xinyu_gateway_ack_spool import SentAckSpool
from xinyu_group_interest_memory import group_interest_metadata, observe_group_interest, record_group_interest_reply
from xinyu_group_shadow_observer import record_group_shadow_observation
from xinyu_group_social_observer import observe_group_social_event
from xinyu_group_social_sidecar import group_social_enabled
from xinyu_image_context import build_image_context, build_image_context_from_path, is_image_learning_payload
from xinyu_codex_delegate import looks_like_owner_local_write_request
from xinyu_behavior_shadow_client import record_behavior_shadow_log
import xinyu_qq_attachment_resolver
import xinyu_qq_command_router
import xinyu_qq_gateway_context_enrichment
from xinyu_qq_cli import build_gateway_parser
from xinyu_qq_config import (
    GatewayConfig,
    as_bool as _as_bool,
    as_int as _as_int,
    as_str_list as _as_str_list,
    load_json_object as _load_json,
)
from xinyu_qq_bridge_errors import BRIDGE_TIMEOUT_OWNER_REPLY, BRIDGE_UNAVAILABLE_OWNER_REPLY
import xinyu_qq_bridge_errors
from xinyu_qq_core_client import BridgeError, CoreBridgeClient
from xinyu_qq_event_time import event_time_iso as _event_time_iso
from xinyu_qq_event_time import event_timestamp_seconds as _event_timestamp_seconds
import xinyu_qq_forward_context
from xinyu_qq_models import PendingAction, PreparedMessage, RecentStickerImportState, ReplyTarget
from xinyu_qq_gateway_utils import hash_id as _hash_id
from xinyu_qq_gateway_utils import maybe_int as _maybe_int
from xinyu_qq_gateway_utils import quiet_websockets_handshake_noise as _quiet_websockets_handshake_noise
from xinyu_qq_gateway_utils import safe_str as _safe_str
import xinyu_qq_normalizer
import xinyu_qq_outbox_client
import xinyu_qq_outbox_dispatcher
import xinyu_qq_reception_metadata
import xinyu_qq_reply_bubbles
import xinyu_qq_rich_context
import xinyu_qq_session_flow
import xinyu_qq_server
import xinyu_qq_sender
import xinyu_qq_sticker_semantics
import xinyu_qq_trust_policy
import xinyu_qq_visible_dispatch
import xinyu_qq_voice_reply
import xinyu_qq_voice_transcript
from xinyu_turn_completion import TurnCompletionDecision, evaluate_turn_completion

try:
    import websockets
except ImportError as exc:  # pragma: no cover - exercised by startup scripts
    raise SystemExit("Missing dependency: websockets. Run: python -m pip install -r requirements-minimal.txt") from exc


GATEWAY_VERSION = "0.1.31"
GATEWAY_NAME = "xinyu_native_qq_gateway"
QQ_INBOUND_TRACE_REL = Path("runtime") / "qq_inbound_trace.jsonl"
QQ_RICH_CONTEXT_TRACE_REL = Path("runtime") / "qq_rich_context_trace.jsonl"
QQ_STICKER_IMPORT_TRACE_REL = Path("runtime") / "qq_sticker_import_trace.jsonl"
QQ_RECENT_STICKER_STATE_REL = Path("runtime") / "qq_recent_sticker_state.json"
SUPPORTED_IMAGE_SUFFIXES = xinyu_qq_attachment_resolver.SUPPORTED_IMAGE_SUFFIXES
CORE_CHAT_RETRY_DELAY_SECONDS = 1.0


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
        self._latest_inbound_arrival_by_session_hash: dict[str, int] = {}
        self._chat_coalesce_lock = asyncio.Lock()
        self._chat_coalesce_buffers: dict[str, dict[str, Any]] = {}
        self._recent_sticker_imports: dict[str, RecentStickerImportState] = {}
        self._recent_group_reply_message_ids: dict[str, dict[str, Any]] = {}
        self._group_followup_windows: dict[str, dict[str, Any]] = {}
        self._behavior_shadow_tasks: set[asyncio.Task[Any]] = set()
        self._connection_count = 0
        self._shadow_fail_count: int = 0
        self._shadow_circuit_open_until: float = 0.0
        self._last_napcat_connected_at: float = 0.0

    _effective_whitelist_user_ids = xinyu_qq_trust_policy.gateway_effective_whitelist_user_ids

    _is_blocked_user_id = xinyu_qq_trust_policy.gateway_is_blocked_user_id

    _is_blocked_group_id = xinyu_qq_trust_policy.gateway_is_blocked_group_id

    _is_trusted_user_id = xinyu_qq_trust_policy.gateway_is_trusted_user_id

    _trust_level_for_user_id = xinyu_qq_trust_policy.gateway_trust_level_for_user_id

    _compact_command_text = staticmethod(xinyu_qq_trust_policy.compact_command_text)
    _looks_like_trust_command = staticmethod(xinyu_qq_trust_policy.is_trust_grant_command)
    _looks_like_trust_revoke_command = staticmethod(xinyu_qq_trust_policy.is_trust_revoke_command)

    _trust_command_target = xinyu_qq_trust_policy.gateway_trust_command_target

    def _group_followup_key(self, target: ReplyTarget) -> str:
        return f"{target.group_id}:{target.user_id}"

    def _prune_group_reply_state(self) -> None:
        now = time.monotonic()
        for key, state in list(self._recent_group_reply_message_ids.items()):
            if float(state.get("expires_at") or 0.0) <= now:
                self._recent_group_reply_message_ids.pop(key, None)
        for key, state in list(self._group_followup_windows.items()):
            if float(state.get("expires_at") or 0.0) <= now or _as_int(state.get("remaining"), 0) <= 0:
                self._group_followup_windows.pop(key, None)

    def _group_reply_quote_trigger_reason(self, event: dict[str, Any], target: ReplyTarget) -> str:
        if target.message_kind != "group":
            return ""
        reply_message_id = _safe_str(self._extract_reply_message_id(event)).strip()
        if not reply_message_id:
            return ""
        self._prune_group_reply_state()
        state = self._recent_group_reply_message_ids.get(reply_message_id)
        if not state:
            return ""
        if _safe_str(state.get("group_id")).strip() != _safe_str(target.group_id).strip():
            return ""
        return "group_reply_quote"

    def _group_followup_trigger_reason(self, target: ReplyTarget, *, consume: bool) -> str:
        if target.message_kind != "group" or self.config.group_followup_window_seconds <= 0:
            return ""
        self._prune_group_reply_state()
        key = self._group_followup_key(target)
        state = self._group_followup_windows.get(key)
        if not state:
            return ""
        if consume:
            state["remaining"] = max(0, _as_int(state.get("remaining"), 0) - 1)
            state["expires_at"] = time.monotonic() + self.config.group_followup_window_seconds
        return "group_followup_window"

    def _remember_group_followup_window(self, target: ReplyTarget) -> None:
        if target.message_kind != "group" or self.config.group_followup_window_seconds <= 0:
            return
        self._group_followup_windows[self._group_followup_key(target)] = {
            "expires_at": time.monotonic() + self.config.group_followup_window_seconds,
            "remaining": self.config.group_followup_max_turns,
        }

    @staticmethod
    def _message_ids_from_action_response(action_response: dict[str, Any] | None) -> list[str]:
        if not isinstance(action_response, dict):
            return []
        data = action_response.get("data")
        if not isinstance(data, dict):
            return []
        ids: list[str] = []
        bubble_ids = data.get("reply_bubble_message_ids")
        if isinstance(bubble_ids, list):
            ids.extend(_safe_str(item).strip() for item in bubble_ids)
        ids.extend(part.strip() for part in _safe_str(data.get("message_id")).replace("，", ",").split(","))
        return list(dict.fromkeys(item for item in ids if item))

    def _group_interest_reply_group_allowed(self, group_id: str) -> bool:
        clean_group_id = _safe_str(group_id).strip()
        if not clean_group_id:
            return False
        if self.config.allowed_group_ids and clean_group_id not in self.config.allowed_group_ids:
            return False
        allowed = getattr(self.config, "group_interest_reply_allowed_group_ids", frozenset())
        if allowed:
            return clean_group_id in allowed
        return self._group_shadow_group_allowed(clean_group_id)

    def _group_interest_reply_enabled_for_group(self, group_id: str) -> bool:
        return bool(getattr(self.config, "group_interest_reply_enabled", False)) and self._group_interest_reply_group_allowed(
            group_id
        )

    def _file_learning_group_allowed(self, group_id: str) -> bool:
        clean_group_id = _safe_str(group_id).strip()
        if not clean_group_id:
            return False
        if self.config.allowed_group_ids and clean_group_id not in self.config.allowed_group_ids:
            return False
        allowed = getattr(self.config, "qq_file_learning_allowed_group_ids", frozenset())
        return bool(allowed and clean_group_id in allowed)

    def _file_learning_scope_reject_reason(self, *, message_kind: str, sender_id: str, group_id: str) -> str:
        if not self.config.qq_file_learning_private_owner_only:
            return ""
        clean_sender_id = _safe_str(sender_id).strip()
        if message_kind == "private":
            return "" if clean_sender_id in self.config.owner_user_ids else "file_learning_private_owner_only"
        if message_kind != "group":
            return "file_learning_private_owner_only"
        if not self._file_learning_group_allowed(group_id):
            return "file_learning_group_not_allowed"
        if clean_sender_id in self.config.owner_user_ids or self._is_trusted_user_id(clean_sender_id):
            return ""
        return "file_learning_sender_not_trusted"

    @staticmethod
    def _event_group_interest_observation(event: dict[str, Any]) -> dict[str, Any]:
        observed = event.get("_xinyu_group_interest_observation")
        return observed if isinstance(observed, dict) else {}

    def _group_interest_decision_allows_reply(self, event: dict[str, Any], *, group_id: str, reject_reason: str) -> bool:
        if reject_reason == "group_not_allowed" or not self._group_interest_reply_enabled_for_group(group_id):
            return False
        observed = self._event_group_interest_observation(event)
        return bool(observed.get("should_reply"))

    def _remember_group_visible_reply(
        self,
        prepared: PreparedMessage,
        action_response: dict[str, Any] | None,
        *,
        reply: str = "",
    ) -> None:
        if prepared.target.message_kind != "group":
            return
        self._remember_group_followup_window(prepared.target)
        payload = prepared.payload if isinstance(prepared.payload, dict) else {}
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
        if metadata.get("qq_group_interest_reply"):
            try:
                record_group_interest_reply(
                    self.xinyu_dir,
                    payload=payload,
                    reply=reply,
                    followup_max_turns=getattr(self.config, "group_interest_followup_max_turns", 2),
                )
            except Exception as exc:
                print(f"[xinyu_qq_gateway] group interest reply record failed: {type(exc).__name__}: {exc}", flush=True)
        expires_at = time.monotonic() + max(600, self.config.group_followup_window_seconds)
        for message_id in self._message_ids_from_action_response(action_response):
            self._recent_group_reply_message_ids[message_id] = {
                "group_id": prepared.target.group_id,
                "user_id": prepared.target.user_id,
                "expires_at": expires_at,
            }

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

    async def _watchdog_napcat(self, stop_event: asyncio.Event) -> None:
        DISCONNECT_THRESHOLD = 60
        RESTART_COOLDOWN = 300
        last_restart_at = 0.0
        while not stop_event.is_set():
            try:
                await asyncio.wait_for(asyncio.shield(stop_event.wait()), timeout=30)
                break
            except asyncio.TimeoutError:
                pass
            if self._websocket_connection_ids:
                continue
            if not self._last_napcat_connected_at:
                continue
            since = time.time() - self._last_napcat_connected_at
            if since < DISCONNECT_THRESHOLD:
                continue
            if time.time() - last_restart_at < RESTART_COOLDOWN:
                continue
            restart_bat = self.config.napcat_restart_bat
            if restart_bat and Path(restart_bat).is_file():
                last_restart_at = time.time()
                print(
                    f"[xinyu_qq_gateway] NapCat disconnected for {int(since)}s, restarting: {restart_bat}",
                    flush=True,
                )
                try:
                    import subprocess
                    subprocess.Popen(
                        ["cmd.exe", "/c", restart_bat],
                        cwd=str(Path(restart_bat).parent),
                        creationflags=subprocess.CREATE_NEW_CONSOLE,
                    )
                except Exception as exc:
                    print(f"[xinyu_qq_gateway] NapCat restart failed: {exc}", flush=True)
            else:
                print(
                    f"[xinyu_qq_gateway] WARNING: NapCat disconnected for {int(since)}s"
                    " — set napcat_restart_bat in gateway config to enable auto-restart.",
                    flush=True,
                )
                last_restart_at = time.time()

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
            watchdog_task = asyncio.create_task(
                self._watchdog_napcat(stop_event), name="xinyu-napcat-watchdog"
            )
            try:
                await stop_event.wait()
            finally:
                watchdog_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await watchdog_task

        for task in list(self._event_tasks):
            task.cancel()
        if self._event_tasks:
            await asyncio.gather(*self._event_tasks, return_exceptions=True)
        self._inbound_session_queues.clear()
        self._inbound_session_tasks.clear()

    _install_signal_handlers = staticmethod(xinyu_qq_server.install_signal_handlers)

    async def _handle_connection(self, websocket: Any) -> None:
        path = xinyu_qq_server.websocket_path(websocket)
        if not xinyu_qq_server.websocket_path_allowed(path, self.config.onebot_path):
            print(f"[xinyu_qq_gateway] rejecting websocket path: {path}", flush=True)
            await websocket.close(code=1008, reason="invalid path")
            return

        self._connection_count += 1
        connection_id = xinyu_qq_server.connection_id("napcat", int(time.time()), self._connection_count)
        self._websocket_connection_ids[id(websocket)] = connection_id
        self._last_napcat_connected_at = time.time()
        print(f"[xinyu_qq_gateway] NapCat connected: {connection_id} path={path or self.config.onebot_path}", flush=True)
        outbox_task: asyncio.Task[Any] | None = None
        ack_spool_task: asyncio.Task[Any] | None = None
        if self.config.qq_outbox_enabled and self.config.bridge_token and self.config.send_replies:
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

    _poll_qq_outbox = xinyu_qq_outbox_dispatcher.gateway_poll_qq_outbox

    _outbox_target = xinyu_qq_outbox_client.gateway_outbox_target

    _onebot_action_result = xinyu_qq_outbox_client.onebot_action_result

    _ack_qq_outbox = xinyu_qq_outbox_client.ack_qq_outbox

    _ack_sent_outbox_delivery = xinyu_qq_outbox_client.ack_sent_outbox_delivery

    _outbox_message_ack_payload = xinyu_qq_outbox_client.outbox_message_ack_payload

    _sent_outbox_delivery_route = staticmethod(xinyu_qq_outbox_client.sent_outbox_delivery_route)

    _poll_pending_message_acks = xinyu_qq_outbox_client.poll_pending_message_acks

    _ack_sent_visible_reply = xinyu_qq_outbox_client.ack_sent_visible_reply

    _record_sent_message_ack_payload = xinyu_qq_outbox_client.record_sent_message_ack_payload

    _spool_pending_message_ack = xinyu_qq_outbox_client.spool_pending_message_ack

    _spool_acked_message_ack = xinyu_qq_outbox_client.spool_acked_message_ack

    _sent_message_ack_payload = xinyu_qq_outbox_client.sent_message_ack_payload

    _send_message_ack_payload = xinyu_qq_outbox_client.send_message_ack_payload

    _flush_pending_message_acks = xinyu_qq_outbox_client.flush_pending_message_acks

    _resolve_learning_ingest_payload = xinyu_qq_attachment_resolver.resolve_learning_ingest_payload

    _resolve_sticker_import_payload = xinyu_qq_attachment_resolver.resolve_sticker_import_payload

    _resolve_onebot_media = xinyu_qq_attachment_resolver.resolve_onebot_media

    _resolve_onebot_file = xinyu_qq_attachment_resolver.resolve_onebot_file

    _onebot_file_url_action = xinyu_qq_attachment_resolver.onebot_file_url_action

    _onebot_action_payload = xinyu_qq_attachment_resolver.onebot_action_payload

    _onebot_action_data = xinyu_qq_attachment_resolver.onebot_action_data

    _path_from_file_uri = staticmethod(xinyu_qq_attachment_resolver.path_from_file_uri)

    _onebot_local_image_file = xinyu_qq_attachment_resolver.onebot_local_image_file

    _onebot_local_file = xinyu_qq_attachment_resolver.onebot_local_file

    _first_text_field = staticmethod(xinyu_qq_attachment_resolver.first_text_field_value)

    async def _upgrade_reply_file_learning(
        self,
        websocket: Any,
        event: dict[str, Any],
        prepared: PreparedMessage | None,
    ) -> PreparedMessage | None:
        return await xinyu_qq_gateway_context_enrichment.upgrade_reply_file_learning(
            self,
            websocket,
            event,
            prepared,
        )

    async def _enrich_reply_context(
        self,
        websocket: Any,
        event: dict[str, Any],
        prepared: PreparedMessage | None,
    ) -> PreparedMessage | None:
        return await xinyu_qq_gateway_context_enrichment.enrich_reply_context(self, websocket, event, prepared)

    async def _enrich_forward_context(
        self,
        websocket: Any,
        event: dict[str, Any],
        prepared: PreparedMessage | None,
    ) -> PreparedMessage | None:
        return await xinyu_qq_gateway_context_enrichment.enrich_forward_context(self, websocket, event, prepared)

    def _embedded_forward_messages_from_event(self, event: dict[str, Any]) -> list[dict[str, str]]:
        return xinyu_qq_gateway_context_enrichment.embedded_forward_messages_from_event(self, event)

    async def _fetch_forward_messages(self, websocket: Any, forward_id: str) -> list[dict[str, str]]:
        return await xinyu_qq_gateway_context_enrichment.fetch_forward_messages(self, websocket, forward_id)

    def _forward_messages_from_payload(self, payload: Any) -> list[dict[str, str]]:
        return xinyu_qq_gateway_context_enrichment.forward_messages_from_payload(self, payload)

    _forward_raw_items = staticmethod(xinyu_qq_forward_context.forward_raw_items)

    def _summarize_forward_item(self, item: Any) -> dict[str, str]:
        return xinyu_qq_gateway_context_enrichment.summarize_forward_item(self, item)

    _clean_cq_text = staticmethod(xinyu_qq_normalizer.clean_cq_text_value)

    _dedupe_forward_messages = staticmethod(xinyu_qq_forward_context.dedupe_forward_messages)

    _reply_file_learning_intent = staticmethod(xinyu_qq_attachment_resolver.reply_file_learning_intent_text)

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
        return xinyu_qq_session_flow.event_session_queue_key(
            message_kind=self._message_kind(event),
            group_id=event.get("group_id"),
            user_id=event.get("user_id"),
        )

    def _event_supersedes_pending_visible_reply(self, event: dict[str, Any]) -> bool:
        if _safe_str(event.get("post_type")).lower() != "message":
            return False
        if self._message_kind(event) != "private":
            return False
        sender_id = _safe_str(event.get("user_id"), "").strip()
        if sender_id not in self.config.owner_user_ids:
            return False
        text = self._extract_text(event).strip()
        if text:
            return True
        if self.config.qq_sticker_import_enabled and self._extract_sticker_import_material(event) is not None:
            return False
        learning_material = self._learning_material_for_route(
            event,
            message_kind=self._message_kind(event),
            sender_id=sender_id,
            group_id=_safe_str(event.get("group_id"), ""),
        )
        if self.config.qq_file_learning_enabled and learning_material is not None:
            return False
        rich_context = self._extract_rich_message_context(event)
        return bool(_safe_str(rich_context.get("fallback_text")).strip())

    def _mark_latest_session_arrival(self, session_queue_key: str, arrival_seq: int) -> None:
        xinyu_qq_session_flow.mark_latest_session_arrival(
            self._latest_inbound_arrival_by_session_hash,
            session_queue_key,
            arrival_seq,
        )

    @staticmethod
    def _prepared_arrival_waterline(prepared: PreparedMessage) -> int:
        payload = prepared.payload if isinstance(prepared.payload, dict) else {}
        return xinyu_qq_session_flow.prepared_arrival_waterline(payload)

    def _visible_reply_stale_waterline(self, prepared: PreparedMessage) -> tuple[bool, int, int]:
        payload = prepared.payload if isinstance(prepared.payload, dict) else {}
        return xinyu_qq_session_flow.visible_reply_stale_waterline(
            route=prepared.route,
            target_message_kind=prepared.target.message_kind,
            target_user_id=prepared.target.user_id,
            owner_user_ids=self.config.owner_user_ids,
            payload=payload,
            latest_by_session_hash=self._latest_inbound_arrival_by_session_hash,
        )

    async def _enqueue_onebot_event(self, websocket: Any, event: dict[str, Any]) -> None:
        if _safe_str(event.get("post_type")).lower() != "message":
            return
        arrival_seq = self._next_arrival_seq()
        queue_key = self._event_session_queue_key(event)
        if self._event_supersedes_pending_visible_reply(event):
            self._mark_latest_session_arrival(queue_key, arrival_seq)
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
        metadata = xinyu_qq_reception_metadata.annotate_prepared_reception_metadata(
            payload,
            event_message_id=event.get("message_id"),
            arrival_seq=arrival_seq,
            prepared_seq=prepared_seq,
            session_queue_key=session_queue_key,
        )
        prepared.payload["metadata"] = metadata
        return prepared

    def _annotate_dispatch_reception(self, prepared: PreparedMessage) -> int:
        dispatch_seq = self._next_dispatch_seq()
        payload = prepared.payload if isinstance(prepared.payload, dict) else {}
        metadata = xinyu_qq_reception_metadata.annotate_dispatch_reception_metadata(
            payload,
            dispatch_seq=dispatch_seq,
        )
        prepared.payload["metadata"] = metadata
        return dispatch_seq

    @staticmethod
    def _is_bridge_request_timeout_error(error: str) -> bool:
        return xinyu_qq_bridge_errors.is_bridge_request_timeout_error(error)

    def _bridge_timeout_fallback_reply(self, prepared: PreparedMessage) -> str:
        return xinyu_qq_bridge_errors.owner_private_chat_fallback_reply(
            route=prepared.route,
            target_message_kind=prepared.target.message_kind,
            target_user_id=prepared.target.user_id,
            owner_user_ids=self.config.owner_user_ids,
            reply_text=BRIDGE_TIMEOUT_OWNER_REPLY,
        )

    def _bridge_unavailable_fallback_reply(self, prepared: PreparedMessage) -> str:
        return xinyu_qq_bridge_errors.owner_private_chat_fallback_reply(
            route=prepared.route,
            target_message_kind=prepared.target.message_kind,
            target_user_id=prepared.target.user_id,
            owner_user_ids=self.config.owner_user_ids,
            reply_text=BRIDGE_UNAVAILABLE_OWNER_REPLY,
        )

    @staticmethod
    def _is_retryable_core_chat_connection_error(error: str) -> bool:
        return xinyu_qq_bridge_errors.is_retryable_core_chat_connection_error(error)

    @staticmethod
    def _is_bridge_connection_unavailable_error(error: str) -> bool:
        return xinyu_qq_bridge_errors.is_bridge_connection_unavailable_error(error)

    async def _sleep_before_core_chat_retry(self) -> None:
        await asyncio.sleep(CORE_CHAT_RETRY_DELAY_SECONDS)

    async def _chat_with_core_retry(
        self,
        payload: dict[str, Any],
        *,
        prepared: PreparedMessage,
        event: dict[str, Any],
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            return await self.client.chat(payload)
        except BridgeError as exc:
            error = str(exc)
            if not self._is_retryable_core_chat_connection_error(error):
                raise
            self._trace_qq_inbound(
                event,
                stage="core_chat_retry_after_connection_reset",
                arrival_seq=_as_int(metadata.get("qq_arrival_seq"), 0),
                prepared=prepared,
                session_queue_key=_safe_str(metadata.get("qq_session_queue_hash")),
                drop_reason="core_bridge_connection_reset_retry",
                error=f"BridgeError: {exc}",
            )
            await self._sleep_before_core_chat_retry()
            return await self.client.chat(payload)

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
        delivery_kind: str = "",
        adapter_message_id: str = "",
        adapter_error: str = "",
        voice_fallback_reason: str = "",
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
                "voice_count": int(rich.get("voice_count") or 0),
                "audio_count": int(rich.get("audio_count") or 0),
                "record_count": int(rich.get("record_count") or 0),
                "forward_count": int(rich.get("forward_count") or 0),
                "reply_message_id": _safe_str(rich.get("reply_message_id")).strip(),
                "supersedes_visible_reply": self._event_supersedes_pending_visible_reply(event),
                "drop_reason": drop_reason,
                "error": error[:500],
                "delivery_kind": delivery_kind,
                "adapter_message_id": adapter_message_id,
                "adapter_error": adapter_error[:500],
                "voice_fallback_reason": voice_fallback_reason[:500],
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
        if self._event_supersedes_pending_visible_reply(event):
            self._mark_latest_session_arrival(session_queue_key, arrival_seq)
        self._maybe_record_group_shadow_event(event)
        prepared = self.prepare_message(event)
        prepared = await self._upgrade_reply_file_learning(websocket, event, prepared)
        prepared = await self._enrich_reply_context(websocket, event, prepared)
        prepared = await self._enrich_forward_context(websocket, event, prepared)
        prepared = await self._maybe_transcribe_owner_private_voice(websocket, event, prepared)
        prepared = await self._maybe_enrich_current_image_context(websocket, event, prepared)
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

        await self._dispatch_intent_gated_prepared_message(
            websocket,
            prepared,
            event=event,
            arrival_seq=arrival_seq,
            session_queue_key=session_queue_key,
        )

    @staticmethod
    def _image_context_suffix(filename: str, content_type: str) -> str:
        suffix = Path(filename).suffix.lower()
        if suffix in SUPPORTED_IMAGE_SUFFIXES:
            return suffix
        guessed = mimetypes.guess_extension((content_type or "").split(";", 1)[0].strip().lower())
        return guessed if guessed in SUPPORTED_IMAGE_SUFFIXES else ".png"

    def _build_direct_image_context(self, image_payload: dict[str, Any], *, owner_text: str) -> dict[str, Any]:
        file_path = _safe_str(image_payload.get("file_path") or image_payload.get("path")).strip()
        if file_path:
            path = self._path_from_file_uri(file_path) if file_path.lower().startswith("file://") else Path(file_path)
            return build_image_context_from_path(
                self.xinyu_dir,
                image_path=path,
                image_payload=image_payload,
                owner_text=owner_text,
                image_only=not owner_text.strip(),
            )

        file_url = _safe_str(image_payload.get("file_url") or image_payload.get("url")).strip()
        if not file_url:
            return {"available": False, "kind": "image", "notes": ["image_context_no_resolved_media"]}
        try:
            from xinyu_learning_library import download_bytes

            data, _final_url, content_type = download_bytes(file_url, max_bytes=10 * 1024 * 1024)
        except Exception as exc:
            return {
                "available": False,
                "kind": "image",
                "notes": [f"image_context_download_failed:{type(exc).__name__}"],
            }

        filename = _safe_str(image_payload.get("file_name") or image_payload.get("title") or image_payload.get("label")).strip()
        suffix = self._image_context_suffix(filename, content_type)
        tmp_root = self.xinyu_dir / "runtime" / "qq_image_context_tmp"
        tmp_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="xinyu-qq-image-", dir=tmp_root) as tmp:
            path = Path(tmp) / f"image{suffix}"
            path.write_bytes(data)
            enriched_payload = dict(image_payload)
            enriched_payload["file_name"] = filename or path.name
            return build_image_context_from_path(
                self.xinyu_dir,
                image_path=path,
                image_payload=enriched_payload,
                owner_text=owner_text,
                image_only=True,
            )

    async def _maybe_enrich_current_image_context(
        self,
        websocket: Any,
        event: dict[str, Any],
        prepared: PreparedMessage | None,
    ) -> PreparedMessage | None:
        if prepared is None or prepared.route != "chat":
            return prepared
        payload = prepared.payload if isinstance(prepared.payload, dict) else {}
        metadata = payload.get("metadata")
        metadata = metadata if isinstance(metadata, dict) else {}
        if _as_int(metadata.get("qq_image_count"), 0) <= 0:
            return prepared
        if isinstance(metadata.get("qq_image_context"), dict):
            return prepared

        material = self._extract_image_context_material(event)
        if material is None:
            return prepared
        image_payload = self._build_learning_ingest_payload(
            event,
            target=prepared.target,
            material=material,
            text=_safe_str(payload.get("text") or self._extract_text(event)).strip(),
        )
        image_payload = await self._resolve_learning_ingest_payload(websocket, image_payload)
        image_metadata = image_payload.get("metadata")
        image_metadata = image_metadata if isinstance(image_metadata, dict) else {}
        context = await asyncio.to_thread(
            self._build_direct_image_context,
            image_payload,
            owner_text=_safe_str(payload.get("text")).strip(),
        )

        updated_metadata = dict(metadata)
        updated_metadata["qq_image_context"] = context
        updated_metadata["qq_image_context_available"] = _as_bool(context.get("available"), False)
        updated_metadata["qq_image_context_notes"] = context.get("notes", [])[:8] if isinstance(context.get("notes"), list) else []
        if image_metadata.get("file_resolution_status"):
            updated_metadata["file_resolution_status"] = image_metadata.get("file_resolution_status")
        if image_metadata.get("file_resolved_by"):
            updated_metadata["file_resolved_by"] = image_metadata.get("file_resolved_by")
        if image_metadata.get("file_resolution_attempts"):
            updated_metadata["file_resolution_attempts"] = image_metadata.get("file_resolution_attempts")
        updated_metadata["qq_image_context_route"] = "direct_current_turn"
        payload["metadata"] = updated_metadata
        return replace(prepared, payload=payload)

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
        self._schedule_behavior_shadow_log(prepared)
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
                    response = await self._chat_with_core_retry(
                        followup_payload,
                        prepared=prepared,
                        event=event_for_trace,
                        metadata=metadata,
                    )
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
                self._trace_sticker_import(
                    event or {},
                    target=prepared.target,
                    payload=payload,
                    stage="background_queued",
                    elapsed_ms=int((time.monotonic() - started) * 1000),
                )
                self._schedule_sticker_import_background(
                    websocket,
                    event or {},
                    target=prepared.target,
                    sticker_payload=payload,
                )
                response = {
                    "accepted": True,
                    "reply": "",
                    "route": "sticker_import",
                    "notes": ["sticker_import_background_queued"],
                }
            elif prepared.route == "package_install":
                if not self.config.bridge_token:
                    await self.send_reply(
                        websocket,
                        prepared.target,
                        "Package install is not enabled: missing bridge token.",
                    )
                    return
                response = await self.client.package_install(prepared.payload)
            elif prepared.route == "self_action_approval":
                if not self.config.bridge_token:
                    await self.send_reply(
                        websocket,
                        prepared.target,
                        "自行动作审批未启用：缺少 bridge token。",
                    )
                    return
                response = await self.client.self_action_approval(prepared.payload)
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
                response = await self._chat_with_core_retry(
                    prepared.payload,
                    prepared=prepared,
                    event=event_for_trace,
                    metadata=metadata,
                )
        except BridgeError as exc:
            print(f"[xinyu_qq_gateway] core bridge error: {exc}", flush=True)
            error_text = str(exc)
            bridge_timed_out = self._is_bridge_request_timeout_error(error_text)
            bridge_unavailable = (
                not bridge_timed_out and self._is_bridge_connection_unavailable_error(error_text)
            )
            fallback_reply = ""
            fallback_stage = ""
            if bridge_timed_out:
                fallback_reply = self._bridge_timeout_fallback_reply(prepared)
                fallback_stage = "bridge_timeout_fallback_sent"
            elif bridge_unavailable:
                fallback_reply = self._bridge_unavailable_fallback_reply(prepared)
                fallback_stage = "bridge_unavailable_fallback_sent"
            drop_reason = (
                "bridge_request_timeout"
                if bridge_timed_out
                else "core_bridge_connection_unavailable"
                if bridge_unavailable
                else ""
            )
            self._trace_qq_inbound(
                event_for_trace,
                stage="dispatch_error",
                arrival_seq=_as_int(metadata.get("qq_arrival_seq"), 0),
                prepared=prepared,
                session_queue_key=_safe_str(metadata.get("qq_session_queue_hash")),
                drop_reason=drop_reason,
                error=f"BridgeError: {exc}",
            )
            if fallback_reply and self.config.send_replies:
                stale, generation_waterline, latest_arrival = self._visible_reply_stale_waterline(prepared)
                if stale:
                    self._trace_qq_inbound(
                        event_for_trace,
                        stage="stale_reply_dropped",
                        arrival_seq=_as_int(metadata.get("qq_arrival_seq"), 0),
                        prepared=prepared,
                        session_queue_key=_safe_str(metadata.get("qq_session_queue_hash")),
                        drop_reason=(
                            f"newer_input_before_{fallback_stage}:"
                            f"{generation_waterline}->{latest_arrival}"
                        ),
                    )
                    return
                await self.send_reply(websocket, prepared.target, fallback_reply)
                self._trace_qq_inbound(
                    event_for_trace,
                    stage=fallback_stage,
                    arrival_seq=_as_int(metadata.get("qq_arrival_seq"), 0),
                    prepared=prepared,
                    session_queue_key=_safe_str(metadata.get("qq_session_queue_hash")),
                    drop_reason=drop_reason,
                )
            elif self.config.show_bridge_errors:
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
            stale, generation_waterline, latest_arrival = self._visible_reply_stale_waterline(prepared)
            if stale:
                drop_reason = f"newer_input_before_visible_send:{generation_waterline}->{latest_arrival}"
                await self._drop_unsent_visible_reply(
                    prepared,
                    reply=reply,
                    core_response=response,
                    drop_reason=drop_reason,
                )
                self._trace_qq_inbound(
                    event_for_trace,
                    stage="stale_reply_dropped",
                    arrival_seq=_as_int(metadata.get("qq_arrival_seq"), 0),
                    prepared=prepared,
                    session_queue_key=_safe_str(metadata.get("qq_session_queue_hash")),
                    drop_reason=drop_reason,
                )
                return
            self._record_direct_visible_send_shadow(prepared, reply, response)
            action_response = await self._send_visible_reply(websocket, prepared, reply, response)
            self._remember_group_visible_reply(prepared, action_response, reply=reply)
            await self._ack_sent_visible_reply(
                prepared,
                reply=reply,
                core_response=response,
                action_response=action_response,
            )
            ok, adapter_message_id, adapter_error = self._onebot_action_result(action_response)
            delivery_kind = ""
            voice_fallback_reason = ""
            if isinstance(action_response, dict):
                delivery_kind = _safe_str(action_response.get("xinyu_delivery_kind")).strip()
                voice_fallback_reason = _safe_str(action_response.get("xinyu_voice_fallback_reason")).strip()
                data = action_response.get("data")
                if not delivery_kind and isinstance(data, dict):
                    delivery_kind = _safe_str(data.get("delivery_kind")).strip()
            self._trace_qq_inbound(
                event_for_trace,
                stage="reply_sent",
                arrival_seq=_as_int(metadata.get("qq_arrival_seq"), 0),
                prepared=prepared,
                session_queue_key=_safe_str(metadata.get("qq_session_queue_hash")),
                delivery_kind=delivery_kind,
                adapter_message_id=adapter_message_id if ok else "",
                adapter_error=adapter_error,
                voice_fallback_reason=voice_fallback_reason,
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

    def _schedule_behavior_shadow_log(self, prepared: PreparedMessage) -> None:
        if not self.config.behavior_shadow_log_enabled:
            return
        if time.time() < self._shadow_circuit_open_until:
            return
        payload = prepared.payload if isinstance(prepared.payload, dict) else {}
        if not payload:
            return
        target = {
            "message_kind": prepared.target.message_kind,
            "user_id_hash": _hash_id(prepared.target.user_id),
            "group_id_hash": _hash_id(prepared.target.group_id),
        }
        task = asyncio.create_task(
            self._record_behavior_shadow_log(prepared, target=target),
            name=f"xinyu-behavior-shadow-{_safe_str(payload.get('message_id')) or 'turn'}",
        )
        self._behavior_shadow_tasks.add(task)
        task.add_done_callback(self._behavior_shadow_tasks.discard)

    async def _record_behavior_shadow_log(
        self,
        prepared: PreparedMessage,
        *,
        target: dict[str, Any],
    ) -> None:
        try:
            result = await asyncio.to_thread(
                record_behavior_shadow_log,
                prepared.payload,
                route=prepared.route,
                target=target,
                enabled=True,
                endpoint=self.config.behavior_shadow_log_url,
                include_text=self.config.behavior_shadow_include_text,
                timeout_seconds=self.config.behavior_shadow_timeout_seconds,
            )
        except Exception as exc:
            self._shadow_fail_count += 1
            if self._shadow_fail_count >= 5:
                self._shadow_circuit_open_until = time.time() + 120.0
                self._shadow_fail_count = 0
                print("[xinyu_qq_gateway] behavior shadow log: circuit open, pausing 120s after repeated failures", flush=True)
            else:
                print(f"[xinyu_qq_gateway] behavior shadow log failed: {type(exc).__name__}: {exc}", flush=True)
            return
        if result.get("ok") is True or "behavior_shadow_log_disabled" in result.get("notes", []):
            self._shadow_fail_count = 0
            return
        notes = ",".join(_safe_str(note) for note in result.get("notes", [])[:3])
        error = _safe_str(result.get("error")).strip()
        suffix = f": {error}" if error else (f": {notes}" if notes else "")
        self._shadow_fail_count += 1
        if self._shadow_fail_count >= 5:
            self._shadow_circuit_open_until = time.time() + 120.0
            self._shadow_fail_count = 0
            print("[xinyu_qq_gateway] behavior shadow log: circuit open, pausing 120s after repeated failures", flush=True)
        else:
            print(f"[xinyu_qq_gateway] behavior shadow log failed{suffix}", flush=True)

    async def _dispatch_intent_gated_prepared_message(
        self,
        websocket: Any,
        prepared: PreparedMessage,
        *,
        event: dict[str, Any] | None = None,
        arrival_seq: int = 0,
        session_queue_key: str = "",
    ) -> bool:
        prepared, decision = self._apply_owner_private_segmented_intent_gate(prepared)
        if decision.get("applies") and not _as_bool(decision.get("should_reply"), default=True):
            payload = prepared.payload if isinstance(prepared.payload, dict) else {}
            metadata = payload.get("metadata")
            metadata = metadata if isinstance(metadata, dict) else {}
            action = _safe_str(decision.get("action"), "silent").strip() or "silent"
            self._trace_qq_inbound(
                event if isinstance(event, dict) else {},
                stage="dropped",
                arrival_seq=arrival_seq or _as_int(metadata.get("qq_arrival_seq"), 0),
                prepared=prepared,
                session_queue_key=session_queue_key,
                drop_reason=f"owner_private_intent_{action}",
            )
            return False
        await self._dispatch_prepared_message(websocket, prepared, event=event)
        return True

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
        self._remember_recent_sticker_import(
            target=target,
            event=event,
            payload=sticker_payload,
            status="pending",
        )
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
            self._remember_recent_sticker_import(
                target=target,
                event=event,
                payload=resolved_payload,
                status="completed",
                response=response,
            )
            await self._dispatch_sticker_import_followup(
                websocket,
                event,
                target=target,
                sticker_payload=resolved_payload,
                sticker_response=response,
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
            self._remember_recent_sticker_import(
                target=target,
                event=event,
                payload=sticker_payload,
                status="error",
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
            self._remember_recent_sticker_import(
                target=target,
                event=event,
                payload=sticker_payload,
                status="error",
                error=f"{type(exc).__name__}: {exc}",
            )
            print("[xinyu_qq_gateway] unexpected background sticker import error", flush=True)
            traceback.print_exception(type(exc), exc, exc.__traceback__)

    async def _dispatch_sticker_import_followup(
        self,
        websocket: Any,
        event: dict[str, Any],
        *,
        target: ReplyTarget,
        sticker_payload: dict[str, Any],
        sticker_response: dict[str, Any],
    ) -> None:
        followup_payload = self._build_sticker_followup_chat_payload(
            event,
            target=target,
            sticker_payload=sticker_payload,
            sticker_response=sticker_response,
        )
        if followup_payload is None:
            return
        metadata = followup_payload.get("metadata")
        metadata = metadata if isinstance(metadata, dict) else {}
        source_metadata = sticker_payload.get("metadata")
        source_metadata = source_metadata if isinstance(source_metadata, dict) else {}
        for key in (
            "qq_arrival_seq",
            "qq_arrival_seqs",
            "qq_prepared_seq",
            "qq_session_queue_hash",
            "qq_gateway_received_message_id",
        ):
            if key in source_metadata and key not in metadata:
                metadata[key] = source_metadata[key]
        followup_payload["metadata"] = metadata
        followup = PreparedMessage(target=target, payload=followup_payload, route="chat")
        self._trace_qq_rich_context(event, followup, stage="sticker_followup")
        await self._dispatch_prepared_message(websocket, followup, event=event)

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

    def _owner_private_intent_gate_applies(self, prepared: PreparedMessage) -> bool:
        if prepared.route != "chat" or prepared.local_reply:
            return False
        if prepared.target.message_kind != "private" or prepared.target.user_id not in self.config.owner_user_ids:
            return False
        payload = prepared.payload if isinstance(prepared.payload, dict) else {}
        text = _safe_str(payload.get("text")).strip()
        if not text:
            return False
        metadata = payload.get("metadata")
        if isinstance(metadata, dict) and _as_bool(metadata.get("control_plane"), default=False):
            return False
        return True

    @staticmethod
    def _owner_private_intent_compact(text: str) -> str:
        return re.sub(r"\s+", "", _safe_str(text)).strip(
            " \t\r\n,.;:!?~`'\"()[]{}<>\u3002\uff0c\uff01\uff1f\uff1b\uff1a\u3001\u2026\u2014-"
        ).lower()

    @staticmethod
    def _owner_private_contains_any(text: str, markers: tuple[str, ...]) -> bool:
        lowered = _safe_str(text).lower()
        return any(marker and marker in lowered for marker in markers)

    def _owner_private_is_low_info_unit(
        self,
        unit: str,
        *,
        has_question: bool,
        has_task: bool,
        has_technical: bool,
    ) -> bool:
        compact = self._owner_private_intent_compact(unit)
        if not compact:
            return True
        low_info_exact = (
            "\u55ef",
            "\u55ef\u55ef",
            "\u54e6",
            "\u597d",
            "\u597d\u7684",
            "\u884c",
            "\u53ef\u4ee5",
            "\u77e5\u9053\u4e86",
            "\u7b49\u4e00\u4e0b",
            "\u7b49\u4e0b",
            "\u7b49\u4f1a",
            "\u6211\u60f3\u60f3",
            "\u518d\u60f3\u60f3",
            "\u6211\u770b\u770b",
        )
        if compact in low_info_exact:
            return True
        thinking_markers = (
            "\u6211\u60f3\u60f3",
            "\u518d\u60f3\u60f3",
            "\u7b49\u6211\u60f3\u60f3",
            "\u60f3\u60f3\u529e\u6cd5",
            "\u6211\u770b\u770b",
            "\u5148\u60f3\u60f3",
        )
        return (
            len(compact) <= 18
            and not has_question
            and not has_task
            and not has_technical
            and self._owner_private_contains_any(compact, thinking_markers)
        )

    def _owner_private_looks_like_fragment_continuation(self, text: str) -> bool:
        stripped = _safe_str(text).strip()
        if not stripped:
            return False
        continuation_suffixes = (",", "\uff0c", "\u3001", "...", "\u2026", "\u2026\u2026")
        if stripped.endswith(continuation_suffixes):
            return True
        compact = self._owner_private_intent_compact(stripped)
        continuation_words = (
            "\u8fd8\u6709",
            "\u7136\u540e",
            "\u4f46\u662f",
            "\u4e0d\u8fc7",
            "\u800c\u4e14",
            "\u56e0\u4e3a",
        )
        return any(compact.endswith(word) for word in continuation_words)

    def _owner_private_segmented_intent_decision(self, prepared: PreparedMessage) -> dict[str, Any]:
        if not self._owner_private_intent_gate_applies(prepared):
            return {"applies": False, "action": "reply_now", "should_reply": True, "notes": []}

        payload = prepared.payload if isinstance(prepared.payload, dict) else {}
        metadata = payload.get("metadata")
        metadata = metadata if isinstance(metadata, dict) else {}
        text = _safe_str(payload.get("text")).strip()
        fragments = [part.strip() for part in re.split(r"[\r\n]+", text) if part.strip()]
        units = [part.strip() for part in re.split(r"[\r\n,;\uff0c\uff1b\u3001]+", text) if part.strip()]
        if not fragments:
            fragments = [text]
        if not units:
            units = fragments

        notes: list[str] = []
        coalesced_count = _as_int(metadata.get("qq_coalesced_message_count"), len(fragments))
        if _as_bool(metadata.get("qq_coalesced_owner_messages"), default=False) or coalesced_count > 1:
            notes.append("coalesced_owner_fragments")
        turn_completion_should_generate = _as_bool(
            metadata.get("qq_turn_completion_should_generate"),
            default=False,
        )

        correction_markers = (
            "\u4e0d\u662f",
            "\u4e0d\u5bf9",
            "\u6211\u7684\u610f\u601d\u662f",
            "\u6211\u662f\u8bf4",
            "\u521a\u624d",
            "\u6ca1\u63a5\u4e0a",
        )
        task_markers = (
            "\u4fee\u590d",
            "\u4fee\u4e00\u4e0b",
            "\u6539",
            "\u6dfb\u52a0",
            "\u52a0\u4e2a",
            "\u5b9e\u73b0",
            "\u5199",
            "\u6574\u7406",
            "\u67e5\u770b",
            "\u68c0\u67e5",
            "\u6d4b\u8bd5",
            "\u8dd1",
            "\u8fd0\u884c",
            "\u542f\u52a8",
            "\u7ee7\u7eed",
            "\u5f00\u59cb",
            "\u5220",
            "\u66ff\u6362",
            "\u63a5\u5165",
            "\u63a5\u4e0a",
            "\u4e0b\u8f7d",
            "\u5b89\u88c5",
            "\u66f4\u65b0",
            "\u90e8\u7f72",
            "\u6c49\u5316",
            "plan",
            "api",
            "ui",
            "codex",
            "kohaku",
            "mcp",
            "plugin",
        )
        question_markers = (
            "?",
            "\uff1f",
            "\u4ec0\u4e48",
            "\u4e3a\u4ec0\u4e48",
            "\u600e\u4e48",
            "\u80fd\u4e0d\u80fd",
            "\u662f\u4e0d\u662f",
            "\u6709\u6ca1\u6709",
            "\u54ea",
            "\u5982\u4f55",
            "\u591a\u5c11",
            "\u5417",
        )
        emotion_markers = (
            "\u6211\u8d85",
            "\u5367\u69fd",
            "\u70e6",
            "\u5d29",
            "\u7206\u4e86",
            "\u5b8c\u4e86",
            "\u96be\u53d7",
            "\u7b11\u6b7b",
            "\u6c14\u6b7b",
        )
        technical_markers = (
            "api",
            "qq",
            "xinyu",
            "\u5fc3\u7389",
            "\u524d\u7aef",
            "\u6a21\u578b",
            "\u63d2\u4ef6",
            "\u6d4b\u8bd5",
            "\u62a5\u9519",
            "fast path",
            "\u672c\u5730",
            "\u989d\u5ea6",
            "\u7a7a\u56de\u590d",
            "\u4e0d\u56de\u590d",
        )
        social_markers = (
            "\u4f60\u597d",
            "\u65e9",
            "\u665a\u5b89",
            "\u56de\u6765",
            "\u5230\u5bb6",
            "\u8c22\u8c22",
            "\u8f9b\u82e6",
            "\u60f3\u4f60",
            "\u751f\u65e5",
        )
        status_markers = (
            "\u5750",
            "\u8d70",
            "\u5403",
            "\u7761",
            "\u5730\u94c1",
            "\u516c\u4ea4",
            "\u5f00\u8f66",
            "\u51fa\u95e8",
            "\u4e0a\u73ed",
            "\u4e0b\u73ed",
            "\u6d17\u6fa1",
            "\u5fd9",
        )

        has_correction = self._owner_private_contains_any(text, correction_markers)
        has_task = self._owner_private_contains_any(text, task_markers)
        has_question = self._owner_private_contains_any(text, question_markers)
        has_emotion = self._owner_private_contains_any(text, emotion_markers)
        has_technical = self._owner_private_contains_any(text, technical_markers)
        has_social = self._owner_private_contains_any(text, social_markers)
        all_low_info = bool(units) and all(
            self._owner_private_is_low_info_unit(
                unit,
                has_question=has_question,
                has_task=has_task,
                has_technical=has_technical,
            )
            for unit in units
        )

        compact = self._owner_private_intent_compact(text)
        short_status_update = (
            len(compact) <= 8
            and not has_question
            and not has_task
            and not has_technical
            and not has_social
            and self._owner_private_contains_any(compact, status_markers)
        )

        action = "reply_now"
        should_reply = True
        if has_correction:
            action = "correction"
            notes.append("owner_correction_or_repair")
        elif has_task:
            action = "task_instruction"
            notes.append("owner_task_instruction")
        elif has_question or has_emotion or has_technical or has_social:
            action = "reply_now"
        elif all_low_info:
            if turn_completion_should_generate:
                action = "reply_now"
                notes.append("turn_completion_ready_overrides_silent")
            else:
                action = "silent"
                should_reply = False
                notes.append("low_info_owner_turn")
        elif self._owner_private_looks_like_fragment_continuation(fragments[-1]):
            if turn_completion_should_generate:
                action = "reply_now"
                notes.append("turn_completion_ready_overrides_fragment_wait")
            else:
                action = "wait_more"
                should_reply = False
                notes.append("fragment_continuation_marker")
        elif short_status_update:
            if turn_completion_should_generate:
                action = "reply_now"
                notes.append("turn_completion_ready_overrides_silent")
            else:
                action = "silent"
                should_reply = False
                notes.append("short_status_update")

        return {
            "applies": True,
            "action": action,
            "should_reply": should_reply,
            "notes": notes,
            "fragment_count": max(1, coalesced_count),
        }

    def _apply_owner_private_segmented_intent_gate(
        self,
        prepared: PreparedMessage,
    ) -> tuple[PreparedMessage, dict[str, Any]]:
        decision = self._owner_private_segmented_intent_decision(prepared)
        if not decision.get("applies"):
            return prepared, decision
        payload = dict(prepared.payload if isinstance(prepared.payload, dict) else {})
        metadata = dict(payload.get("metadata")) if isinstance(payload.get("metadata"), dict) else {}
        action = _safe_str(decision.get("action"), "reply_now").strip() or "reply_now"
        metadata.update(
            {
                "qq_segmented_intent_gate": True,
                "qq_segmented_intent_action": action,
                "qq_segmented_intent_notes": list(decision.get("notes") or [])[:8],
                "qq_segmented_fragment_count": _as_int(decision.get("fragment_count"), 1),
                "qq_should_reply": bool(decision.get("should_reply", True)),
            }
        )
        payload["metadata"] = metadata
        return replace(prepared, payload=payload), decision

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
                    "updated_monotonic_at": time.monotonic(),
                    "task": task,
                }
            else:
                prepareds = buffer.setdefault("prepareds", [])
                prepareds.append(prepared)
                buffer["updated_monotonic_at"] = time.monotonic()
        return True

    def _owner_private_turn_completion_decision(self, prepareds: list[PreparedMessage]) -> TurnCompletionDecision:
        texts: list[str] = []
        for item in prepareds:
            payload = item.payload if isinstance(item.payload, dict) else {}
            text = _safe_str(payload.get("text")).strip()
            if text:
                texts.append(text)
        return evaluate_turn_completion(
            texts,
            base_wait_seconds=self.config.owner_private_coalesce_seconds,
            max_fragments=self.config.owner_private_coalesce_max_fragments,
        )

    def _with_turn_completion_metadata(
        self,
        prepared: PreparedMessage,
        decision: TurnCompletionDecision,
    ) -> PreparedMessage:
        payload = dict(prepared.payload if isinstance(prepared.payload, dict) else {})
        metadata = dict(payload.get("metadata")) if isinstance(payload.get("metadata"), dict) else {}
        metadata.update(
            {
                "qq_turn_completion_state": decision.state,
                "qq_turn_completion_reason": decision.reason,
                "qq_turn_completion_wait_seconds": decision.wait_seconds,
                "qq_turn_completion_should_generate": decision.should_generate,
                "qq_turn_completion_notes": list(decision.notes)[:8],
            }
        )
        payload["metadata"] = metadata
        return replace(prepared, payload=payload)

    async def _flush_coalesced_owner_private_chat(self, websocket: Any, key: str) -> None:
        prepared: PreparedMessage | None = None
        decision: TurnCompletionDecision | None = None
        while True:
            async with self._chat_coalesce_lock:
                buffer = self._chat_coalesce_buffers.get(key)
                if buffer is None:
                    return
                prepareds = list(buffer.get("prepareds") or [])
                decision = self._owner_private_turn_completion_decision(prepareds)
                age = time.monotonic() - float(buffer.get("updated_monotonic_at") or buffer.get("updated_at") or 0.0)
                wait_seconds = max(0.0, decision.wait_seconds) - age
                if wait_seconds <= 0:
                    self._chat_coalesce_buffers.pop(key, None)
                    prepared = self._build_coalesced_prepared_message(prepareds)
                    break
            await asyncio.sleep(max(0.05, min(wait_seconds, 1.0)))
        if prepared is not None and decision is not None:
            prepared = self._with_turn_completion_metadata(prepared, decision)
            if not decision.should_generate:
                self._trace_qq_inbound(
                    {},
                    stage="dropped",
                    prepared=prepared,
                    session_queue_key=key,
                    drop_reason=f"turn_completion_{decision.reason}",
                )
                return
            await self._dispatch_intent_gated_prepared_message(
                websocket,
                prepared,
                session_queue_key=key,
            )

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
        if group_social_enabled():
            # Write-side wiring: feed group social memory (gated). Isolated so a
            # failure here never affects the shadow observation or the reply path.
            try:
                observe_group_social_event(
                    self.xinyu_dir,
                    event=event,
                    text=normalized_text if triggered else text,
                    triggered=triggered,
                    max_text_chars=self.config.group_shadow_max_text_chars,
                )
            except Exception as exc:
                print(f"[xinyu_qq_gateway] group social observe failed: {type(exc).__name__}: {exc}", flush=True)
        interest_result: dict[str, Any] = {}
        try:
            interest_result = observe_group_interest(
                self.xinyu_dir,
                event=event,
                text=text,
                normalized_text=normalized_text if triggered else text,
                triggered=triggered,
                reply_enabled=self._group_interest_reply_enabled_for_group(group_id),
                reply_min_score=getattr(self.config, "group_interest_reply_min_score", 7),
                reply_cooldown_seconds=getattr(self.config, "group_interest_reply_cooldown_seconds", 900),
                followup_max_turns=getattr(self.config, "group_interest_followup_max_turns", 2),
                max_text_chars=self.config.group_shadow_max_text_chars,
            )
            event["_xinyu_group_interest_observation"] = interest_result
        except Exception as exc:
            interest_result = {"recorded": False, "notes": [f"group_interest_error:{type(exc).__name__}"]}
            event["_xinyu_group_interest_observation"] = interest_result
            print(f"[xinyu_qq_gateway] group interest observe failed: {type(exc).__name__}: {exc}", flush=True)
        try:
            shadow_result = record_group_shadow_observation(
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
            notes = shadow_result.setdefault("notes", [])
            if isinstance(notes, list):
                notes.extend(str(note) for note in interest_result.get("notes", [])[:4])
                if interest_result.get("should_reply"):
                    notes.append("group_interest_reply_candidate")
            shadow_result["group_interest"] = {
                "recorded": bool(interest_result.get("recorded")),
                "should_reply": bool(interest_result.get("should_reply")),
                "reply_reason": _safe_str(interest_result.get("reply_reason")),
                "interest_score": int(interest_result.get("interest_score") or 0),
            }
            return shadow_result
        except Exception as exc:
            print(f"[xinyu_qq_gateway] group shadow observation failed: {type(exc).__name__}: {exc}", flush=True)
            return {"recorded": False, "notes": [f"group_shadow_error:{type(exc).__name__}"]}

    _group_shadow_group_allowed = xinyu_qq_trust_policy.gateway_group_shadow_group_allowed

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
            metadata["qq_voice_count"] = sum(1 for segment in rich_segments if segment.get("kind") == "voice")
            metadata["qq_record_count"] = sum(
                1
                for segment in rich_segments
                if segment.get("kind") == "voice" and _safe_str(segment.get("segment_type")).lower() == "record"
            )
            metadata["qq_audio_count"] = sum(
                1
                for segment in rich_segments
                if segment.get("kind") == "voice" and _safe_str(segment.get("segment_type")).lower() in {"audio", "voice"}
            )
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
            "qq_voice_count": _as_int(metadata.get("qq_voice_count"), int(rich.get("voice_count") or 0)),
            "qq_audio_count": _as_int(metadata.get("qq_audio_count"), int(rich.get("audio_count") or 0)),
            "qq_record_count": _as_int(metadata.get("qq_record_count"), int(rich.get("record_count") or 0)),
            "qq_forward_count": _as_int(metadata.get("qq_forward_count"), int(rich.get("forward_count") or 0)),
            "qq_voice_transcript_available": _as_bool(
                metadata.get("qq_voice_transcript_available"),
                default=False,
            ),
            "qq_voice_transcript_status": _safe_str(metadata.get("qq_voice_transcript_status")),
            "qq_voice_transcript_engine": _safe_str(metadata.get("qq_voice_transcript_engine")),
            "qq_voice_transcript_text_len": _as_int(metadata.get("qq_voice_transcript_text_len"), 0),
            "qq_voice_transcript_trace_ref": _safe_str(metadata.get("qq_voice_transcript_trace_ref")),
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
        original_text = text
        rich_context = self._extract_rich_message_context(event)
        sticker_material = self._extract_sticker_import_material(event)
        learning_material = self._learning_material_for_route(
            event,
            message_kind=message_kind,
            sender_id=sender_id,
            group_id=group_id,
        )
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
        if self._is_owner_private_untranscribed_voice(
            target,
            original_text=original_text,
            rich_context=rich_context,
            learning_material=learning_material,
            sticker_material=sticker_material,
        ):
            return PreparedMessage(
                target=target,
                payload={},
                route="local_reply",
                local_reply=self._untranscribed_voice_local_reply(),
            )

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

        self_action_quote_command = xinyu_qq_command_router.extract_self_action_quote_approval_command(self, text)
        if self_action_quote_command is not None:
            if message_kind != "private" or sender_id not in self.config.owner_user_ids:
                print("[xinyu_qq_gateway] ignored quoted self action approval outside owner private chat", flush=True)
                return None
            reply_message_id = _safe_str(rich_context.get("reply_message_id") or self._extract_reply_message_id(event)).strip()
            outbox_metadata = self._self_action_outbox_metadata_for_reply(reply_message_id)
            if not outbox_metadata:
                return PreparedMessage(
                    target=target,
                    payload={},
                    route="local_reply",
                    local_reply="这条引用没有对应到心玉推送的自行动作审批消息。",
                )
            command = dict(self_action_quote_command)
            command["queue_id"] = _safe_str(outbox_metadata.get("self_action_queue_id"), "latest") or "latest"
            command["reason"] = _safe_str(command.get("reason") or f"quoted_qq_message:{reply_message_id}")
            command["authorize_existing"] = _safe_str(outbox_metadata.get("self_action_authorize_existing"))
            return PreparedMessage(
                target=target,
                payload=self._build_self_action_approval_payload(
                    event,
                    target=target,
                    text=text,
                    command=command,
                    reply_message_id=reply_message_id,
                ),
                route="self_action_approval",
            )

        self_action_command = xinyu_qq_command_router.extract_self_action_approval_command(self, text)
        if self_action_command is not None:
            if message_kind != "private" or sender_id not in self.config.owner_user_ids:
                print("[xinyu_qq_gateway] ignored self action approval outside owner private chat", flush=True)
                return None
            return PreparedMessage(
                target=target,
                payload=self._build_self_action_approval_payload(
                    event,
                    target=target,
                    text=text,
                    command=self_action_command,
                ),
                route="self_action_approval",
            )

        if learning_material is not None and self.config.qq_file_learning_enabled:
            file_learning_reject_reason = self._file_learning_scope_reject_reason(
                message_kind=message_kind,
                sender_id=sender_id,
                group_id=group_id,
            )
            if file_learning_reject_reason:
                print(
                    f"[xinyu_qq_gateway] ignored QQ file learning: {file_learning_reject_reason}",
                    flush=True,
                )
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

        group_trigger_reason = ""
        group_interest_observation: dict[str, Any] = {}
        if message_kind == "group":
            group_ok, normalized_text, reason = xinyu_qq_command_router.group_trigger_result(self, event, text=text)
            if not group_ok:
                quote_reason = self._group_reply_quote_trigger_reason(event, target)
                followup_reason = "" if quote_reason else self._group_followup_trigger_reason(target, consume=True)
                if quote_reason or followup_reason:
                    group_ok = True
                    normalized_text = text
                    reason = quote_reason or followup_reason
                elif self._group_interest_decision_allows_reply(event, group_id=group_id, reject_reason=reason):
                    group_interest_observation = self._event_group_interest_observation(event)
                    group_ok = True
                    normalized_text = text
                    reason = _safe_str(group_interest_observation.get("reply_reason")) or "group_interest_open"
                else:
                    suffix = f" group_id={group_id}" if reason == "group_not_allowed" else ""
                    print(f"[xinyu_qq_gateway] ignored group message: {reason}{suffix}", flush=True)
                    return None
            text = normalized_text.strip()
            if not text:
                return None
            group_trigger_reason = reason

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

        chat_payload = self._build_chat_payload(event, target=target, text=text, rich_context=rich_context)
        if group_trigger_reason:
            metadata = chat_payload.get("metadata")
            metadata = metadata if isinstance(metadata, dict) else {}
            metadata["qq_group_trigger_reason"] = group_trigger_reason
            metadata["qq_group_followup_window_seconds"] = self.config.group_followup_window_seconds
            metadata.update(group_interest_metadata(group_interest_observation))
            chat_payload["metadata"] = metadata
        return PreparedMessage(
            target=target,
            payload=chat_payload,
        )

    async def _maybe_transcribe_owner_private_voice(
        self,
        websocket: Any,
        event: dict[str, Any],
        prepared: PreparedMessage | None,
    ) -> PreparedMessage | None:
        if prepared is None:
            return None
        if prepared.route != "local_reply" or not prepared.local_reply:
            return prepared
        rich_context = self._extract_rich_message_context(event)
        if not self._is_owner_private_untranscribed_voice(
            prepared.target,
            original_text=self._extract_text(event).strip(),
            rich_context=rich_context,
            learning_material=self._extract_learning_material(event),
            sticker_material=self._extract_sticker_import_material(event),
        ):
            return prepared
        result = await xinyu_qq_voice_transcript.transcribe_owner_private_voice(
            self,
            websocket,
            event,
            target=prepared.target,
        )
        if not result.transcribed:
            print(
                "[xinyu_qq_gateway] owner private voice transcription unavailable: "
                f"status={result.status} error={result.error}",
                flush=True,
            )
            return prepared

        payload = self._build_chat_payload(
            event,
            target=prepared.target,
            text=result.transcript,
            rich_context=rich_context,
        )
        metadata = payload.get("metadata")
        metadata = metadata if isinstance(metadata, dict) else {}
        metadata.update(
            {
                "source": "qq_voice_transcript_message",
                "qq_voice_transcript_available": True,
                "qq_voice_transcript_status": result.status,
                "qq_voice_transcript_engine": result.engine,
                "qq_voice_transcript_model": result.model,
                "qq_voice_transcript_language": result.language,
                "qq_voice_transcript_text_len": len(result.transcript.strip()),
                "qq_voice_transcript_trace_ref": result.trace_ref,
                "qq_voice_audio_resolution_status": result.audio_ref.status if result.audio_ref else "payload",
                "qq_voice_audio_resolved_by": result.audio_ref.resolved_by if result.audio_ref else "onebot_payload",
            }
        )
        if result.confidence is not None:
            metadata["qq_voice_transcript_confidence"] = result.confidence
        payload["metadata"] = metadata
        payload["raw_message"] = result.transcript
        return PreparedMessage(target=prepared.target, payload=payload, route="chat")

    def _is_owner_private_untranscribed_voice(
        self,
        target: ReplyTarget,
        *,
        original_text: str,
        rich_context: dict[str, Any],
        learning_material: Any,
        sticker_material: Any,
    ) -> bool:
        if target.message_kind != "private" or target.user_id not in self.config.owner_user_ids:
            return False
        if original_text.strip() or learning_material is not None or sticker_material is not None:
            return False
        return _as_int(rich_context.get("voice_count"), 0) > 0

    @staticmethod
    def _untranscribed_voice_local_reply() -> str:
        return (
            "\u6211\u6536\u5230\u8bed\u97f3\u4e86\uff0c"
            "\u4f46\u73b0\u5728\u8fd8\u6ca1\u6709\u8f6c\u5199\u5185\u5bb9\uff0c"
            "\u6211\u4e0d\u80fd\u786e\u5b9a\u4f60\u8bf4\u4e86\u4ec0\u4e48\u3002"
            "\u4f60\u53ef\u4ee5\u518d\u53d1\u4e00\u53e5\u6587\u5b57\uff0c"
            "\u6211\u5c31\u63a5\u7740\u56de\u3002"
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
        learning_material = self._learning_material_for_route(
            event,
            message_kind=message_kind,
            sender_id=sender_id,
            group_id=group_id,
        )
        if not text and learning_material is None and sticker_material is None:
            text = _safe_str(rich_context.get("fallback_text")).strip()
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
            file_learning_reject_reason = self._file_learning_scope_reject_reason(
                message_kind=message_kind,
                sender_id=sender_id,
                group_id=group_id,
            )
            if file_learning_reject_reason:
                return file_learning_reject_reason
        if message_kind == "group":
            group_ok, normalized_text, reason = xinyu_qq_command_router.group_trigger_result(self, event, text=text)
            if not group_ok:
                target = ReplyTarget(message_kind=message_kind, user_id=sender_id, group_id=group_id)
                return (
                    self._group_reply_quote_trigger_reason(event, target)
                    or self._group_followup_trigger_reason(target, consume=False)
                    or reason
                )
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
        event_timestamp = _event_timestamp_seconds(event)
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
            "timestamp": event_timestamp,
            "metadata": {
                "gateway": GATEWAY_NAME,
                "gateway_version": GATEWAY_VERSION,
                "source": "qq_gateway_goldmark_command",
                "qq_event_time_iso": _event_time_iso(event_timestamp),
                "qq_event_time_unix": event_timestamp,
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

    def _self_action_outbox_metadata_for_reply(self, reply_message_id: str) -> dict[str, Any]:
        reply_message_id = _safe_str(reply_message_id).strip()
        if not reply_message_id:
            return {}
        queue_path = self.xinyu_dir / "memory/context/qq_outbox_queue.json"
        try:
            data = json.loads(queue_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            return {}
        items = data.get("items") if isinstance(data, dict) else []
        if not isinstance(items, list):
            return {}
        for item in reversed(items):
            if not isinstance(item, dict):
                continue
            metadata = item.get("metadata") if isinstance(item.get("metadata"), dict) else {}
            if not metadata.get("self_action_approval_request"):
                continue
            adapter_message_ids = [
                part.strip()
                for part in _safe_str(item.get("adapter_message_id")).replace("，", ",").split(",")
                if part.strip()
            ]
            if reply_message_id in adapter_message_ids:
                return dict(metadata)
        return {}

    def _build_self_action_approval_payload(
        self,
        event: dict[str, Any],
        *,
        target: ReplyTarget,
        text: str,
        command: dict[str, str],
        reply_message_id: str = "",
    ) -> dict[str, Any]:
        event_timestamp = _event_timestamp_seconds(event)
        decision = _safe_str(command.get("decision"), "approved")
        authorize_existing = _as_bool(command.get("authorize_existing"), default=decision != "denied")
        return {
            "queueId": _safe_str(command.get("queue_id"), "latest") or "latest",
            "decision": "denied" if decision == "denied" else "approved",
            "reason": _safe_str(command.get("reason")),
            "execute": decision != "denied",
            "authorizeCodex": decision != "denied",
            "authorizeExisting": authorize_existing,
            "decidedBy": "owner_qq",
            "platform": "qq",
            "adapter": GATEWAY_NAME,
            "message_type": "private_self_action_approval_command",
            "session_id": self._session_id(target),
            "user_id": target.user_id,
            "sender_name": self._sender_name(event),
            "message_id": _safe_str(event.get("message_id")),
            "reply_message_id": reply_message_id,
            "raw_command": text,
            "timestamp": event_timestamp,
            "metadata": {
                "gateway": GATEWAY_NAME,
                "gateway_version": GATEWAY_VERSION,
                "source": "qq_gateway_self_action_approval_command",
                "qq_event_time_iso": _event_time_iso(event_timestamp),
                "qq_event_time_unix": event_timestamp,
                "is_owner_user": target.user_id in self.config.owner_user_ids,
                "control_plane": True,
                "quoted_self_action_message": bool(reply_message_id),
                "qq_reply_message_id": reply_message_id,
            },
        }

    def _build_review_admin_payload(
        self,
        event: dict[str, Any],
        *,
        target: ReplyTarget,
        text: str,
        command: dict[str, Any],
    ) -> dict[str, Any]:
        event_timestamp = _event_timestamp_seconds(event)
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
            "timestamp": event_timestamp,
            "metadata": {
                "gateway": GATEWAY_NAME,
                "gateway_version": GATEWAY_VERSION,
                "source": "qq_gateway_review_admin_command",
                "qq_event_time_iso": _event_time_iso(event_timestamp),
                "qq_event_time_unix": event_timestamp,
                "is_owner_user": target.user_id in self.config.owner_user_ids,
                "control_plane": True,
            },
        }

    _message_kind = xinyu_qq_normalizer.message_kind

    _message_segments = staticmethod(xinyu_qq_normalizer.message_segments_from_event)

    _segment_data = staticmethod(xinyu_qq_normalizer.segment_data_value)

    def _extract_rich_message_context(self, event: dict[str, Any]) -> dict[str, Any]:
        summaries: list[str] = []
        segment_records: list[dict[str, Any]] = []
        sticker_count = 0
        image_count = 0
        voice_count = 0
        audio_count = 0
        record_count = 0
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
            elif kind == "voice":
                voice_count += 1
                segment_type = _safe_str(record.get("segment_type")).strip().lower()
                if segment_type == "record":
                    record_count += 1
                if segment_type in {"audio", "voice"}:
                    audio_count += 1
                summaries.append(f"语音:{label or 'voice_audio'}")
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
        elif not self._extract_text(event).strip() and voice_count:
            fallback_text = "我发了一条语音。"
        elif not self._extract_text(event).strip() and summaries:
            fallback_text = "我发了" + "，".join(summaries[:3])

        return {
            "segments": segment_records,
            "summary": "；".join(summaries[:6]),
            "fallback_text": fallback_text,
            "sticker_count": sticker_count,
            "image_count": image_count,
            "voice_count": voice_count,
            "audio_count": audio_count,
            "record_count": record_count,
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

    @staticmethod
    def _material_segment_type(material: dict[str, str] | None) -> str:
        return _safe_str((material or {}).get("segment_type")).strip().lower()

    def _image_learning_falls_through_to_chat(self, material: dict[str, str] | None) -> bool:
        return self._material_segment_type(material) == "image"

    def _learning_material_for_route(
        self,
        event: dict[str, Any],
        *,
        message_kind: str,
        sender_id: str,
        group_id: str,
    ) -> dict[str, str] | None:
        material = self._extract_learning_material(event)
        if self._image_learning_falls_through_to_chat(material):
            return None
        return material

    def _extract_image_context_material(self, event: dict[str, Any]) -> dict[str, str] | None:
        for segment in self._message_segments(event):
            segment_type = _safe_str(segment.get("type")).strip().lower()
            if segment_type != "image":
                continue
            data = self._segment_data(segment)
            if self._image_segment_looks_like_sticker(data):
                continue
            return self._learning_material_from_data(segment_type, data)
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
        if segment_type not in {"file", "image", "video"}:
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
            if segment_type not in {"file", "image", "video"}:
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
        event_timestamp = _event_timestamp_seconds(event)
        metadata = {
            "gateway": GATEWAY_NAME,
            "gateway_version": GATEWAY_VERSION,
            "source": "onebot_message_event",
            "qq_event_time_iso": _event_time_iso(event_timestamp),
            "qq_event_time_unix": event_timestamp,
            "source_channel": (
                "owner_private"
                if target.message_kind == "private" and target.user_id in self.config.owner_user_ids
                else ("qq_group" if target.message_kind == "group" else "qq_private")
            ),
            "qq_gateway_live_current_turn": True,
            "qq_current_turn_transport": GATEWAY_NAME,
            "qq_current_turn_message_kind": target.message_kind,
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
            metadata["qq_voice_count"] = int(rich_context.get("voice_count") or 0)
            metadata["qq_audio_count"] = int(rich_context.get("audio_count") or 0)
            metadata["qq_record_count"] = int(rich_context.get("record_count") or 0)
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
            "timestamp": event_timestamp,
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
        event_timestamp = _event_timestamp_seconds(event)
        payload: dict[str, Any] = {
            "origin": "owner_supplied",
            "reason": reason_text,
            "question_id": "qq-file-learning",
            "title": name,
            "label": name,
            "file_name": name,
            "file_id": _safe_str(material.get("file_id")).strip(),
            "busid": _safe_str(material.get("busid")).strip(),
            "stage": self.config.qq_file_learning_stage,
            "curated": self.config.qq_file_learning_curated,
            "timestamp": event_timestamp,
            "metadata": {
                "gateway": GATEWAY_NAME,
                "gateway_version": GATEWAY_VERSION,
                "source": "qq_file_message",
                "qq_event_time_iso": _event_time_iso(event_timestamp),
                "qq_event_time_unix": event_timestamp,
                "onebot_post_type": _safe_str(event.get("post_type")),
                "onebot_message_type": _safe_str(event.get("message_type")),
                "message_id": _safe_str(event.get("message_id")),
                "session_id": self._session_id(target),
                "user_id": target.user_id,
                "group_id": target.group_id or "",
                "sender_name": self._sender_name(event),
                "segment_type": _safe_str(material.get("segment_type")),
                "file_id": _safe_str(material.get("file_id")).strip(),
                "busid": _safe_str(material.get("busid")).strip(),
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
        event_timestamp = _event_timestamp_seconds(event)
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
            "timestamp": event_timestamp,
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
                "qq_event_time_iso": _event_time_iso(event_timestamp),
                "qq_event_time_unix": event_timestamp,
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
        event_timestamp = _event_timestamp_seconds(event)
        return {
            "packages": package_text,
            "current_text": text,
            "session_id": session_id,
            "source": "qq_gateway_package_install_message",
            "requested_by": target.user_id,
            "message_id": _safe_str(event.get("message_id")),
            "timestamp": event_timestamp,
            "metadata": {
                "gateway": GATEWAY_NAME,
                "gateway_version": GATEWAY_VERSION,
                "source": "qq_gateway_package_install_message",
                "qq_event_time_iso": _event_time_iso(event_timestamp),
                "qq_event_time_unix": event_timestamp,
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
        event_timestamp = _event_timestamp_seconds(event)
        metadata = {
            "gateway": GATEWAY_NAME,
            "gateway_version": GATEWAY_VERSION,
            "source": "qq_gateway_codex_execute_message",
            "qq_event_time_iso": _event_time_iso(event_timestamp),
            "qq_event_time_unix": event_timestamp,
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
            "timestamp": event_timestamp,
            "metadata": metadata,
        }

    def _session_id(self, target: ReplyTarget) -> str:
        return xinyu_qq_visible_dispatch.session_id(target)

    def _visible_reply(self, text: str) -> str:
        return xinyu_qq_visible_dispatch.visible_reply(self, text)

    async def _send_visible_reply(
        self,
        websocket: Any,
        prepared: PreparedMessage,
        reply: str,
        core_response: dict[str, Any],
    ) -> dict[str, Any] | None:
        return await xinyu_qq_visible_dispatch.send_visible_reply(self, websocket, prepared, reply, core_response)

    _visible_reply_bubbles = xinyu_qq_reply_bubbles.gateway_visible_reply_bubbles

    _outbox_visible_reply_bubbles = xinyu_qq_reply_bubbles.gateway_outbox_visible_reply_bubbles

    _forced_reply_bubble_units = xinyu_qq_reply_bubbles.gateway_forced_reply_bubble_units

    _should_split_visible_reply = xinyu_qq_reply_bubbles.gateway_should_split_visible_reply

    _should_split_outbox_visible_reply = xinyu_qq_reply_bubbles.gateway_should_split_outbox_visible_reply

    _looks_like_structured_visible_reply = staticmethod(xinyu_qq_reply_bubbles.looks_like_structured_visible_reply)

    _split_visible_reply_bubbles = xinyu_qq_reply_bubbles.gateway_split_visible_reply_bubbles

    _reply_sentence_units = staticmethod(xinyu_qq_reply_bubbles.reply_sentence_units)

    _hard_split_reply_text = staticmethod(xinyu_qq_reply_bubbles.hard_split_reply_text)

    _merge_tiny_reply_chunks = staticmethod(xinyu_qq_reply_bubbles.merge_tiny_reply_chunks)

    _join_reply_fragments = staticmethod(xinyu_qq_reply_bubbles.join_reply_fragments)

    def _record_direct_visible_send_shadow(
        self,
        prepared: PreparedMessage,
        reply: str,
        core_response: dict[str, Any],
    ) -> dict[str, Any]:
        return xinyu_qq_visible_dispatch.record_direct_visible_send_shadow(self, prepared, reply, core_response)

    def _record_outbox_visible_send_shadow(
        self,
        claim: dict[str, Any],
        target: ReplyTarget,
        message: str,
        *,
        delivery_kind: str,
    ) -> dict[str, Any]:
        return xinyu_qq_visible_dispatch.record_outbox_visible_send_shadow(
            self,
            claim,
            target,
            message,
            delivery_kind=delivery_kind,
        )

    def _combined_reply_action_response(self, responses: list[dict[str, Any] | None]) -> dict[str, Any] | None:
        return xinyu_qq_visible_dispatch.combined_reply_action_response(self, responses)

    @staticmethod
    def _annotate_delivery_response(
        response: dict[str, Any] | None,
        *,
        delivery_kind: str,
        voice_fallback_reason: str = "",
    ) -> dict[str, Any] | None:
        if not isinstance(response, dict):
            return response
        annotated = dict(response)
        clean_kind = _safe_str(delivery_kind).strip() or "text"
        annotated["xinyu_delivery_kind"] = clean_kind
        if voice_fallback_reason:
            annotated["xinyu_voice_fallback_reason"] = voice_fallback_reason
        data = annotated.get("data")
        if isinstance(data, dict):
            copied_data = dict(data)
            copied_data["delivery_kind"] = clean_kind
            annotated["data"] = copied_data
        return annotated

    def _voice_failed_response(self, *, reason: str) -> dict[str, Any]:
        return self._annotate_delivery_response(
            {
                "status": "failed",
                "retcode": -1,
                "message": reason,
                "xinyu_voice_strict_drop": True,
            },
            delivery_kind="voice_failed",
            voice_fallback_reason=reason,
        ) or {"status": "failed", "retcode": -1, "message": reason}

    async def send_reply(self, websocket: Any, target: ReplyTarget, text: str) -> dict[str, Any] | None:
        # Owner-toggled (desktop): speak the reply as a QQ voice clip. Private
        # chats default to strict voice mode so a TTS outage does not silently
        # turn a voice conversation back into text.
        fallback_reason = ""
        if xinyu_qq_voice_reply.voice_reply_enabled(target.message_kind):
            strict_voice = xinyu_qq_voice_reply.strict_voice_reply_enabled(target.message_kind)
            result = await asyncio.to_thread(xinyu_qq_voice_reply.synth_voice_b64_result, text)
            if result.ok:
                action, params = xinyu_qq_sender.record_message_action(target, result.record_file)
                response = await self.send_action(websocket, action, params)
                ok, adapter_message_id, adapter_error = self._onebot_action_result(response)
                if ok:
                    local_playback = xinyu_qq_voice_reply.play_voice_result_locally(result)
                    print(
                        "[xinyu_qq_gateway] QQ voice reply sent: "
                        f"kind={target.message_kind} message_id={adapter_message_id or '-'} "
                        f"bytes={result.audio_bytes} elapsed_ms={result.elapsed_ms} "
                        f"local_playback={local_playback.get('played')} "
                        f"local_reason={local_playback.get('reason', '')}",
                        flush=True,
                    )
                    return self._annotate_delivery_response(response, delivery_kind="voice")
                fallback_reason = adapter_error or "record_send_failed"
                if strict_voice:
                    print(
                        "[xinyu_qq_gateway] QQ voice reply send failed; strict voice mode suppressed text fallback: "
                        f"kind={target.message_kind} error={adapter_error or response}",
                        flush=True,
                    )
                    return self._voice_failed_response(reason=fallback_reason)
                print(
                    "[xinyu_qq_gateway] QQ voice reply send failed; falling back to text: "
                    f"kind={target.message_kind} error={adapter_error or response}",
                    flush=True,
                )
            else:
                fallback_reason = result.reason or "voice_synthesis_failed"
                if strict_voice:
                    print(
                        "[xinyu_qq_gateway] QQ voice synthesis failed; strict voice mode suppressed text fallback: "
                        f"kind={target.message_kind} reason={result.reason} status={result.status_code} "
                        f"bytes={result.audio_bytes} elapsed_ms={result.elapsed_ms} base_url={result.base_url}",
                        flush=True,
                    )
                    return self._voice_failed_response(reason=fallback_reason)
                print(
                    "[xinyu_qq_gateway] QQ voice synthesis failed; falling back to text: "
                    f"kind={target.message_kind} reason={result.reason} status={result.status_code} "
                    f"bytes={result.audio_bytes} elapsed_ms={result.elapsed_ms} base_url={result.base_url}",
                    flush=True,
                )
        action, params = xinyu_qq_sender.text_message_action(target, text)
        response = await self.send_action(websocket, action, params)
        return self._annotate_delivery_response(
            response,
            delivery_kind="text",
            voice_fallback_reason=fallback_reason,
        )

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

    async def _drop_unsent_visible_reply(
        self,
        prepared: PreparedMessage,
        *,
        reply: str,
        core_response: dict[str, Any],
        drop_reason: str,
    ) -> None:
        if not self.config.bridge_token:
            return
        source_payload = prepared.payload if isinstance(prepared.payload, dict) else {}
        payload = {
            "adapter": GATEWAY_NAME,
            "gateway": GATEWAY_NAME,
            "route": _safe_str(core_response.get("route") or prepared.route or "chat").strip() or "chat",
            "source_route": prepared.route or "chat",
            "session_id": _safe_str(core_response.get("session_id") or source_payload.get("session_id")).strip(),
            "turn_id": _safe_str(core_response.get("turn_id")).strip(),
            "archive_message_ids": core_response.get("archive_message_ids")
            if isinstance(core_response.get("archive_message_ids"), list)
            else [],
            "archive_assistant_message_id": _safe_str(core_response.get("archive_assistant_message_id")).strip(),
            "source_message_id": _safe_str(source_payload.get("message_id")).strip(),
            "message_type": prepared.target.message_kind,
            "target": {
                "message_kind": prepared.target.message_kind,
                "user_id": prepared.target.user_id,
                "group_id": prepared.target.group_id or "",
            },
            "reply": reply,
            "visible_text": reply,
            "reply_hash": _safe_str(core_response.get("reply_hash")).strip(),
            "drop_reason": drop_reason,
            "metadata": {
                "gateway_version": getattr(self, "gateway_version", GATEWAY_VERSION),
                "source": "qq_gateway_stale_reply_drop",
            },
        }
        try:
            await self.client.message_drop(payload)
        except Exception as exc:
            print(f"[xinyu_qq_gateway] stale reply drop notice failed: {type(exc).__name__}: {exc}", flush=True)


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

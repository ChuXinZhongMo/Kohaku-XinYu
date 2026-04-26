from __future__ import annotations

import asyncio
import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, MessageChain, filter
from astrbot.api.star import Context, Star, register


PLUGIN_NAME = "xinyu_bridge"
SHELL_VERSION = "0.2.0"


class BridgeError(RuntimeError):
    pass


@dataclass(frozen=True)
class BridgeResponse:
    accepted: bool
    reply: str
    memory_changed: bool | None
    notes: list[str]


@dataclass(frozen=True)
class ProactiveResponse:
    accepted: bool
    reply: str
    claim_id: str
    candidate_claimed: bool
    notes: list[str]


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    if value is None:
        return default
    return bool(value)


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()] if str(value).strip() else []


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _event_attr(event: AstrMessageEvent, path: str, default: Any = None) -> Any:
    current: Any = event
    for name in path.split("."):
        current = getattr(current, name, None)
        if current is None:
            return default
    return current


def _maybe_call(obj: Any, name: str, default: Any = None) -> Any:
    func = getattr(obj, name, None)
    if not callable(func):
        return default
    try:
        return func()
    except Exception:
        return default


class XinYuBridgeClient:
    def __init__(
        self,
        url: str,
        token: str = "",
        timeout_seconds: int = 120,
        proactive_url: str = "",
        proactive_ack_url: str = "",
    ) -> None:
        self.url = url.strip()
        self.proactive_url = proactive_url.strip() or self._derive_url("/proactive")
        self.proactive_ack_url = proactive_ack_url.strip() or self._derive_url("/proactive/ack")
        self.token = token.strip()
        self.timeout_seconds = timeout_seconds

    async def chat(self, payload: dict[str, Any]) -> BridgeResponse:
        data = await asyncio.to_thread(self._post_json, self.url, payload)
        if not isinstance(data, dict):
            raise BridgeError("XinYu bridge returned non-object JSON")

        notes = data.get("notes", [])
        if isinstance(notes, str):
            notes = [notes]
        elif not isinstance(notes, list):
            notes = []

        return BridgeResponse(
            accepted=_as_bool(data.get("accepted"), default=True),
            reply=_safe_str(data.get("reply", "")).strip(),
            memory_changed=data.get("memory_changed") if isinstance(data.get("memory_changed"), bool) else None,
            notes=[_safe_str(item) for item in notes],
        )

    async def proactive(self, payload: dict[str, Any]) -> ProactiveResponse:
        data = await asyncio.to_thread(self._post_json, self.proactive_url, payload)
        if not isinstance(data, dict):
            raise BridgeError("XinYu proactive bridge returned non-object JSON")
        notes = self._notes(data)
        return ProactiveResponse(
            accepted=_as_bool(data.get("accepted"), default=True),
            reply=_safe_str(data.get("reply", "")).strip(),
            claim_id=_safe_str(data.get("claim_id", "")).strip(),
            candidate_claimed=_as_bool(data.get("candidate_claimed"), default=False),
            notes=notes,
        )

    async def proactive_ack(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = await asyncio.to_thread(self._post_json, self.proactive_ack_url, payload)
        if not isinstance(data, dict):
            raise BridgeError("XinYu proactive ack returned non-object JSON")
        return data

    def _derive_url(self, path: str) -> str:
        if not self.url:
            return ""
        parts = urlsplit(self.url)
        return urlunsplit((parts.scheme, parts.netloc, path, "", ""))

    def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not url:
            raise BridgeError("bridge URL is empty")

        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
            "User-Agent": f"XinYu-AstrBot-Shell/{SHELL_VERSION}",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
            headers["X-XinYu-Bridge-Token"] = self.token

        request = urllib.request.Request(url, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                status = getattr(response, "status", 200)
                response_body = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            raise BridgeError(f"XinYu bridge HTTP {exc.code}: {error_body[:300]}") from exc
        except urllib.error.URLError as exc:
            raise BridgeError(f"XinYu bridge connection failed: {exc.reason}") from exc
        except TimeoutError as exc:
            raise BridgeError("XinYu bridge request timed out") from exc

        if status < 200 or status >= 300:
            raise BridgeError(f"XinYu bridge HTTP {status}: {response_body[:300]}")

        try:
            return json.loads(response_body)
        except json.JSONDecodeError as exc:
            raise BridgeError(f"XinYu bridge returned invalid JSON: {response_body[:300]}") from exc

    def _notes(self, data: dict[str, Any]) -> list[str]:
        notes = data.get("notes", [])
        if isinstance(notes, str):
            notes = [notes]
        elif not isinstance(notes, list):
            notes = []
        return [_safe_str(item) for item in notes]


@register(
    PLUGIN_NAME,
    "XinYu",
    "Thin AstrBot shell plugin that forwards whitelisted private text to a local XinYu core bridge.",
    SHELL_VERSION,
)
class XinYuBridgePlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig) -> None:
        super().__init__(context)
        self.config = config
        self.enabled = _as_bool(config.get("enabled"), default=True)
        self.bridge_url = _safe_str(config.get("bridge_url"), "http://127.0.0.1:8765/chat")
        self.bridge_token = _safe_str(config.get("bridge_token"), "")
        self.timeout_seconds = _as_int(config.get("timeout_seconds"), 120)
        self.proactive_enabled = _as_bool(config.get("proactive_enabled"), default=False)
        self.proactive_url = _safe_str(config.get("proactive_url"), "")
        self.proactive_ack_url = _safe_str(config.get("proactive_ack_url"), "")
        self.proactive_poll_seconds = max(30, _as_int(config.get("proactive_poll_seconds"), 300))
        self.proactive_initial_delay_seconds = max(0, _as_int(config.get("proactive_initial_delay_seconds"), 30))
        self.proactive_min_interval_seconds = max(0, _as_int(config.get("proactive_min_interval_seconds"), 21600))
        self.proactive_target_session = _safe_str(config.get("proactive_target_session"), "")
        self.proactive_platform_id = _safe_str(config.get("proactive_platform_id"), "")
        self.require_whitelist = _as_bool(config.get("require_whitelist"), default=True)
        self.whitelist_user_ids = set(_as_str_list(config.get("whitelist_user_ids")))
        self.owner_user_ids = set(_as_str_list(config.get("owner_user_ids")))
        self.private_only = _as_bool(config.get("private_only"), default=True)
        self.allow_group_messages = _as_bool(config.get("allow_group_messages"), default=False)
        self.stop_astrbot_pipeline = _as_bool(config.get("stop_astrbot_pipeline"), default=True)
        self.stop_blocked_private_events = _as_bool(config.get("stop_blocked_private_events"), default=True)
        self.deny_message = _safe_str(config.get("deny_message"), "")
        self.show_bridge_errors = _as_bool(config.get("show_bridge_errors"), default=True)
        self.ignore_prefixes = tuple(_as_str_list(config.get("ignore_prefixes")) or ["/", "!", "."])
        self.passthrough_commands = {
            command.strip().lstrip("/!.").lower()
            for command in (
                _as_str_list(config.get("passthrough_commands"))
                or ["sid", "help", "xinyu_shell_status", "plugin", "cmd", "provider"]
            )
            if command.strip().lstrip("/!.")
        }
        self.client = XinYuBridgeClient(
            url=self.bridge_url,
            token=self.bridge_token,
            timeout_seconds=self.timeout_seconds,
            proactive_url=self.proactive_url,
            proactive_ack_url=self.proactive_ack_url,
        )
        self._proactive_task: asyncio.Task | None = None
        self._last_owner_session = ""
        logger.info(
            "XinYu bridge shell loaded: enabled=%s private_only=%s whitelist=%d bridge_url=%s proactive=%s",
            self.enabled,
            self.private_only,
            len(self.whitelist_user_ids),
            self.bridge_url,
            self.proactive_enabled,
        )

    async def initialize(self) -> None:
        stored_session = await self.get_kv_data("last_owner_private_session", "")
        self._last_owner_session = _safe_str(stored_session, "")
        if self.enabled and self.proactive_enabled:
            self._proactive_task = asyncio.create_task(self._proactive_loop())

    async def terminate(self) -> None:
        task = self._proactive_task
        self._proactive_task = None
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    @filter.command("xinyu_shell_status", priority=20)
    async def status(self, event: AstrMessageEvent):
        target_session = self._target_session()
        lines = [
            "XinYu shell status",
            f"enabled: {self.enabled}",
            f"bridge_url: {self.bridge_url}",
            f"proactive_enabled: {self.proactive_enabled}",
            f"proactive_url: {self.client.proactive_url}",
            f"proactive_ack_url: {self.client.proactive_ack_url}",
            f"proactive_target_session: {target_session or 'not_ready'}",
            f"proactive_task_running: {bool(self._proactive_task and not self._proactive_task.done())}",
            f"private_only: {self.private_only}",
            f"allow_group_messages: {self.allow_group_messages}",
            f"require_whitelist: {self.require_whitelist}",
            f"whitelist_count: {len(self.whitelist_user_ids)}",
            f"stop_astrbot_pipeline: {self.stop_astrbot_pipeline}",
        ]
        yield event.plain_result("\n".join(lines))
        event.stop_event()

    @filter.command("xinyu_proactive_once", priority=20)
    async def proactive_once(self, event: AstrMessageEvent):
        if not self.enabled:
            yield event.plain_result("XinYu shell is disabled.")
            event.stop_event()
            return
        sent = await self._poll_proactive_once(reason="manual_command")
        yield event.plain_result(f"XinYu proactive poll: {'sent' if sent else 'no message'}")
        event.stop_event()

    @filter.event_message_type(filter.EventMessageType.ALL, priority=5)
    async def on_message(self, event: AstrMessageEvent):
        if not self.enabled:
            return

        text = _safe_str(getattr(event, "message_str", "")).strip()
        if not text:
            return

        if self._is_passthrough_command(text):
            return

        message_kind = self._message_kind(event)
        if self.private_only and message_kind != "private":
            return
        if message_kind == "group" and not self.allow_group_messages:
            return

        sender_id = self._sender_id(event)
        if message_kind == "private" and sender_id in self.owner_user_ids:
            await self._remember_owner_session(event)
        if self.require_whitelist and sender_id not in self.whitelist_user_ids:
            logger.info("XinYu bridge blocked non-whitelisted user_id=%s kind=%s", sender_id, message_kind)
            if message_kind == "private" and self.deny_message:
                yield event.plain_result(self.deny_message)
            if message_kind == "private" and self.stop_blocked_private_events:
                event.stop_event()
            return

        payload = self._build_payload(event, text=text, message_kind=message_kind, sender_id=sender_id)
        try:
            response = await self.client.chat(payload)
        except BridgeError as exc:
            logger.error("XinYu bridge error: %s", exc)
            if self.show_bridge_errors:
                yield event.plain_result(f"XinYu bridge error: {exc}")
            if self.stop_astrbot_pipeline:
                event.stop_event()
            return

        for note in response.notes:
            logger.info("XinYu bridge note: %s", note)

        if response.accepted and response.reply:
            yield event.plain_result(response.reply)

        if response.accepted and self.stop_astrbot_pipeline:
            event.stop_event()

    def _message_kind(self, event: AstrMessageEvent) -> str:
        group_id = self._group_id(event)
        if group_id:
            return "group"

        event_type = _safe_str(_event_attr(event, "message_obj.type", "")).lower()
        if "group" in event_type:
            return "group"
        return "private"

    def _is_passthrough_command(self, text: str) -> bool:
        if self.ignore_prefixes and text.startswith(self.ignore_prefixes):
            return True

        command = text.split(maxsplit=1)[0].lstrip("/!.").lower()
        return command in self.passthrough_commands

    def _sender_id(self, event: AstrMessageEvent) -> str:
        sender_id = _maybe_call(event, "get_sender_id")
        if sender_id is None:
            sender_id = _event_attr(event, "message_obj.sender.user_id")
        if sender_id is None:
            sender_id = _event_attr(event, "message_obj.sender_id")
        return _safe_str(sender_id, "unknown")

    def _sender_name(self, event: AstrMessageEvent) -> str:
        sender_name = _maybe_call(event, "get_sender_name")
        if sender_name is None:
            sender_name = _event_attr(event, "message_obj.sender.nickname")
        if sender_name is None:
            sender_name = _event_attr(event, "message_obj.sender_name")
        return _safe_str(sender_name, "")

    def _group_id(self, event: AstrMessageEvent) -> str:
        group_id = _event_attr(event, "message_obj.group_id")
        if group_id is None:
            group_id = _event_attr(event, "message_obj.group.id")
        value = _safe_str(group_id, "")
        return "" if value in {"None", "0"} else value

    def _bot_id(self, event: AstrMessageEvent) -> str:
        bot_id = _event_attr(event, "message_obj.self_id")
        if bot_id is None:
            bot_id = _event_attr(event, "message_obj.bot_id")
        return _safe_str(bot_id, "")

    def _message_id(self, event: AstrMessageEvent) -> str:
        message_id = _event_attr(event, "message_obj.message_id")
        if message_id is None:
            message_id = _event_attr(event, "message_obj.id")
        return _safe_str(message_id, "")

    async def _remember_owner_session(self, event: AstrMessageEvent) -> None:
        session = _safe_str(getattr(event, "unified_msg_origin", "")).strip()
        if not session:
            session = _safe_str(getattr(event, "session", "")).strip()
        if not session:
            return
        self._last_owner_session = session
        try:
            await self.put_kv_data("last_owner_private_session", session)
        except Exception as exc:
            logger.warning("XinYu bridge failed to persist owner session: %s", exc)

    def _target_session(self) -> str:
        if self.proactive_target_session:
            return self.proactive_target_session
        if self._last_owner_session:
            return self._last_owner_session

        if len(self.owner_user_ids) != 1:
            return ""
        owner_id = next(iter(self.owner_user_ids))
        platform_id = self.proactive_platform_id or self._single_platform_id()
        if not platform_id:
            return ""
        return f"{platform_id}:FriendMessage:{owner_id}"

    def _single_platform_id(self) -> str:
        platform_manager = getattr(self.context, "platform_manager", None)
        platform_insts = getattr(platform_manager, "platform_insts", None)
        if not platform_insts or len(platform_insts) != 1:
            return ""
        platform = platform_insts[0]
        meta = platform.meta() if callable(getattr(platform, "meta", None)) else None
        return _safe_str(getattr(meta, "id", ""), "")

    async def _proactive_loop(self) -> None:
        if self.proactive_initial_delay_seconds:
            await asyncio.sleep(self.proactive_initial_delay_seconds)
        while True:
            try:
                await self._poll_proactive_once(reason="background_loop")
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("XinYu proactive loop error: %s", exc, exc_info=True)
            await asyncio.sleep(self.proactive_poll_seconds)

    async def _poll_proactive_once(self, *, reason: str) -> bool:
        if not self.proactive_enabled:
            logger.info("XinYu proactive poll skipped: disabled")
            return False

        target_session = self._target_session()
        if not target_session:
            logger.warning("XinYu proactive poll skipped: no target session")
            return False

        claim_id = f"astrbot-{int(time.time())}"
        try:
            response = await self.client.proactive(
                {
                    "claim": True,
                    "claim_id": claim_id,
                    "min_interval_seconds": self.proactive_min_interval_seconds,
                    "source": reason,
                }
            )
        except BridgeError as exc:
            logger.error("XinYu proactive bridge error: %s", exc)
            return False

        for note in response.notes:
            logger.info("XinYu proactive note: %s", note)

        if not response.accepted or not response.reply:
            return False

        ack_payload = {
            "claim_id": response.claim_id or claim_id,
            "status": "sent",
            "message_id": f"astrbot:{target_session}:{int(time.time())}",
        }
        try:
            sent = await self.context.send_message(target_session, MessageChain().message(response.reply))
            if not sent:
                ack_payload = {
                    "claim_id": response.claim_id or claim_id,
                    "status": "failed",
                    "error": f"target session not found: {target_session}",
                }
                logger.warning("XinYu proactive send failed: target session not found: %s", target_session)
                return False
            logger.info("XinYu proactive message sent to %s", target_session)
            return True
        except Exception as exc:
            ack_payload = {
                "claim_id": response.claim_id or claim_id,
                "status": "failed",
                "error": str(exc)[:500],
            }
            logger.error("XinYu proactive send failed: %s", exc, exc_info=True)
            return False
        finally:
            try:
                await self.client.proactive_ack(ack_payload)
            except BridgeError as exc:
                logger.error("XinYu proactive ack failed: %s", exc)

    def _build_payload(
        self,
        event: AstrMessageEvent,
        *,
        text: str,
        message_kind: str,
        sender_id: str,
    ) -> dict[str, Any]:
        group_id = self._group_id(event) or None
        session_id = self._session_id(message_kind=message_kind, sender_id=sender_id, group_id=group_id)
        platform_session_id = _safe_str(_event_attr(event, "message_obj.session_id"), session_id)
        unified_msg_origin = _safe_str(getattr(event, "unified_msg_origin", ""))

        return {
            "platform": "astrbot",
            "message_type": f"{message_kind}_text",
            "session_id": session_id,
            "user_id": sender_id,
            "sender_name": self._sender_name(event),
            "group_id": group_id,
            "bot_id": self._bot_id(event),
            "message_id": self._message_id(event),
            "text": text,
            "raw_message": text,
            "timestamp": int(time.time()),
            "metadata": {
                "plugin": PLUGIN_NAME,
                "shell_version": SHELL_VERSION,
                "platform_session_id": platform_session_id,
                "unified_msg_origin": unified_msg_origin,
                "is_owner_user": sender_id in self.owner_user_ids,
                "source": "astrbot_message_event",
            },
        }

    def _session_id(self, *, message_kind: str, sender_id: str, group_id: str | None) -> str:
        if message_kind == "group":
            return f"astrbot:group:{group_id or 'unknown'}:{sender_id}"
        return f"astrbot:private:{sender_id}"

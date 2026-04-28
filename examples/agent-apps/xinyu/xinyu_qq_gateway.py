from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import signal
import sys
import time
import traceback
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import websockets
except ImportError as exc:  # pragma: no cover - exercised by startup scripts
    raise SystemExit("Missing dependency: websockets. Run: python -m pip install -r requirements-minimal.txt") from exc


GATEWAY_VERSION = "0.1.0"
GATEWAY_NAME = "xinyu_native_qq_gateway"


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


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
    text = str(value).strip()
    return [text] if text else []


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def _maybe_int(value: str) -> int | str:
    return int(value) if value.isdigit() else value


@dataclass(frozen=True)
class GatewayConfig:
    enabled: bool = True
    onebot_host: str = "127.0.0.1"
    onebot_port: int = 6199
    onebot_path: str = "/ws"
    core_chat_url: str = "http://127.0.0.1:8765/chat"
    bridge_token: str = ""
    timeout_seconds: int = 300
    require_whitelist: bool = True
    whitelist_user_ids: frozenset[str] = frozenset()
    owner_user_ids: frozenset[str] = frozenset()
    private_only: bool = False
    allow_group_messages: bool = True
    allowed_group_ids: frozenset[str] = frozenset()
    group_trigger_mode: str = "mention_or_prefix"
    group_trigger_prefixes: tuple[str, ...] = ()
    ignore_prefixes: tuple[str, ...] = ("/", "!", ".")
    blocked_commands: frozenset[str] = frozenset({"#napcat"})
    passthrough_commands: frozenset[str] = frozenset({"sid", "help", "xinyu_qq_status"})
    send_replies: bool = True
    show_bridge_errors: bool = False
    max_reply_chars: int = 3500

    @classmethod
    def from_file(cls, path: Path) -> "GatewayConfig":
        raw = _load_json(path)
        prefixes = tuple(_as_str_list(raw.get("group_trigger_prefixes")))
        if not prefixes:
            prefixes = ("心玉", "@心玉", "小心玉")
        return cls(
            enabled=_as_bool(raw.get("enabled"), True),
            onebot_host=_safe_str(raw.get("onebot_host"), "127.0.0.1"),
            onebot_port=_as_int(raw.get("onebot_port"), 6199),
            onebot_path=_safe_str(raw.get("onebot_path"), "/ws") or "/ws",
            core_chat_url=_safe_str(raw.get("core_chat_url"), "http://127.0.0.1:8765/chat"),
            bridge_token=_safe_str(raw.get("bridge_token"), ""),
            timeout_seconds=max(5, _as_int(raw.get("timeout_seconds"), 300)),
            require_whitelist=_as_bool(raw.get("require_whitelist"), True),
            whitelist_user_ids=frozenset(_as_str_list(raw.get("whitelist_user_ids"))),
            owner_user_ids=frozenset(_as_str_list(raw.get("owner_user_ids"))),
            private_only=_as_bool(raw.get("private_only"), False),
            allow_group_messages=_as_bool(raw.get("allow_group_messages"), True),
            allowed_group_ids=frozenset(_as_str_list(raw.get("allowed_group_ids"))),
            group_trigger_mode=_safe_str(raw.get("group_trigger_mode"), "mention_or_prefix").strip().lower(),
            group_trigger_prefixes=prefixes,
            ignore_prefixes=tuple(_as_str_list(raw.get("ignore_prefixes")) or ["/", "!", "."]),
            blocked_commands=frozenset(
                item.lower() for item in (_as_str_list(raw.get("blocked_commands")) or ["#napcat"])
            ),
            passthrough_commands=frozenset(
                item.strip().lstrip("/!.").lower()
                for item in (_as_str_list(raw.get("passthrough_commands")) or ["sid", "help", "xinyu_qq_status"])
                if item.strip().lstrip("/!.")
            ),
            send_replies=_as_bool(raw.get("send_replies"), True),
            show_bridge_errors=_as_bool(raw.get("show_bridge_errors"), False),
            max_reply_chars=max(200, _as_int(raw.get("max_reply_chars"), 3500)),
        )

    def with_overrides(
        self,
        *,
        host: str | None = None,
        port: int | None = None,
        path: str | None = None,
        core_chat_url: str | None = None,
        bridge_token: str | None = None,
    ) -> "GatewayConfig":
        return GatewayConfig(
            enabled=self.enabled,
            onebot_host=host or self.onebot_host,
            onebot_port=port if port is not None else self.onebot_port,
            onebot_path=path or self.onebot_path,
            core_chat_url=core_chat_url or self.core_chat_url,
            bridge_token=bridge_token if bridge_token is not None else self.bridge_token,
            timeout_seconds=self.timeout_seconds,
            require_whitelist=self.require_whitelist,
            whitelist_user_ids=self.whitelist_user_ids,
            owner_user_ids=self.owner_user_ids,
            private_only=self.private_only,
            allow_group_messages=self.allow_group_messages,
            allowed_group_ids=self.allowed_group_ids,
            group_trigger_mode=self.group_trigger_mode,
            group_trigger_prefixes=self.group_trigger_prefixes,
            ignore_prefixes=self.ignore_prefixes,
            blocked_commands=self.blocked_commands,
            passthrough_commands=self.passthrough_commands,
            send_replies=self.send_replies,
            show_bridge_errors=self.show_bridge_errors,
            max_reply_chars=self.max_reply_chars,
        )


@dataclass(frozen=True)
class ReplyTarget:
    message_kind: str
    user_id: str
    group_id: str


@dataclass(frozen=True)
class PreparedMessage:
    target: ReplyTarget
    payload: dict[str, Any]


class BridgeError(RuntimeError):
    pass


class CoreBridgeClient:
    def __init__(self, *, url: str, token: str, timeout_seconds: int) -> None:
        self.url = url.strip()
        self.token = token.strip()
        self.timeout_seconds = timeout_seconds

    async def chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self._post_json, self.url, payload)

    def _post_json(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not url:
            raise BridgeError("core chat URL is empty")
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": f"XinYu-QQ-Gateway/{GATEWAY_VERSION}",
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
            raise BridgeError(f"core bridge HTTP {exc.code}: {error_body[:300]}") from exc
        except urllib.error.URLError as exc:
            raise BridgeError(f"core bridge connection failed: {exc.reason}") from exc
        except TimeoutError as exc:
            raise BridgeError("core bridge request timed out") from exc
        if status < 200 or status >= 300:
            raise BridgeError(f"core bridge HTTP {status}: {response_body[:300]}")
        try:
            data = json.loads(response_body)
        except json.JSONDecodeError as exc:
            raise BridgeError(f"core bridge returned invalid JSON: {response_body[:300]}") from exc
        if not isinstance(data, dict):
            raise BridgeError("core bridge returned non-object JSON")
        return data


class NativeQQGateway:
    def __init__(self, config: GatewayConfig) -> None:
        self.config = config
        self.client = CoreBridgeClient(
            url=config.core_chat_url,
            token=config.bridge_token,
            timeout_seconds=config.timeout_seconds,
        )
        self._pending_actions: dict[str, asyncio.Future[dict[str, Any]]] = {}
        self._action_lock = asyncio.Lock()
        self._event_tasks: set[asyncio.Task[Any]] = set()
        self._connection_count = 0

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

    def _install_signal_handlers(self, stop_event: asyncio.Event) -> None:
        loop = asyncio.get_running_loop()
        for sig in (getattr(signal, "SIGINT", None), getattr(signal, "SIGTERM", None)):
            if sig is None:
                continue
            with contextlib.suppress(NotImplementedError):
                loop.add_signal_handler(sig, stop_event.set)

    async def _handle_connection(self, websocket: Any) -> None:
        path = _websocket_path(websocket)
        if self.config.onebot_path and path not in {"", self.config.onebot_path}:
            print(f"[xinyu_qq_gateway] rejecting websocket path: {path}", flush=True)
            await websocket.close(code=1008, reason="invalid path")
            return

        self._connection_count += 1
        connection_id = f"napcat-{int(time.time())}-{self._connection_count}"
        print(f"[xinyu_qq_gateway] NapCat connected: {connection_id} path={path or self.config.onebot_path}", flush=True)
        try:
            async for raw_message in websocket:
                event = self._parse_ws_message(raw_message)
                if event is None:
                    continue
                if self._complete_action_response(event):
                    continue
                task = asyncio.create_task(self._handle_onebot_event(websocket, event), name="xinyu-qq-event")
                self._event_tasks.add(task)
                task.add_done_callback(self._event_tasks.discard)
        except Exception as exc:
            print(f"[xinyu_qq_gateway] NapCat connection closed: {type(exc).__name__}: {exc}", flush=True)
        finally:
            for echo, future in list(self._pending_actions.items()):
                if not future.done():
                    future.set_exception(BridgeError("NapCat connection closed before action response"))
                self._pending_actions.pop(echo, None)

    def _parse_ws_message(self, raw_message: Any) -> dict[str, Any] | None:
        if isinstance(raw_message, bytes):
            raw_message = raw_message.decode("utf-8", errors="replace")
        try:
            data = json.loads(str(raw_message))
        except json.JSONDecodeError:
            print("[xinyu_qq_gateway] ignored non-json websocket message", flush=True)
            return None
        if not isinstance(data, dict):
            return None
        return data

    def _complete_action_response(self, event: dict[str, Any]) -> bool:
        echo = _safe_str(event.get("echo")).strip()
        if not echo:
            return False
        future = self._pending_actions.pop(echo, None)
        if future is None:
            return False
        if not future.done():
            future.set_result(event)
        return True

    async def _handle_onebot_event(self, websocket: Any, event: dict[str, Any]) -> None:
        if _safe_str(event.get("post_type")).lower() != "message":
            return
        prepared = self.prepare_message(event)
        if prepared is None:
            return

        try:
            response = await self.client.chat(prepared.payload)
        except BridgeError as exc:
            print(f"[xinyu_qq_gateway] core bridge error: {exc}", flush=True)
            if self.config.show_bridge_errors:
                await self.send_reply(websocket, prepared.target, f"XinYu core bridge error: {exc}")
            return
        except Exception as exc:
            print("[xinyu_qq_gateway] unexpected event handling error", flush=True)
            traceback.print_exception(type(exc), exc, exc.__traceback__)
            if self.config.show_bridge_errors:
                await self.send_reply(websocket, prepared.target, f"XinYu gateway error: {exc}")
            return

        reply = self._visible_reply(_safe_str(response.get("reply"), ""))
        if self.config.send_replies and response.get("accepted", True) and reply:
            await self.send_reply(websocket, prepared.target, reply)

    def prepare_message(self, event: dict[str, Any]) -> PreparedMessage | None:
        if not self.config.enabled:
            return None

        message_kind = self._message_kind(event)
        sender_id = _safe_str(event.get("user_id"), "unknown")
        group_id = _safe_str(event.get("group_id"), "")
        text = self._extract_text(event).strip()
        if not text:
            return None

        if self._is_blocked_command(text):
            print(f"[xinyu_qq_gateway] blocked command: {text.split(maxsplit=1)[0]}", flush=True)
            return None

        if self.config.private_only and message_kind != "private":
            return None
        if message_kind == "group" and not self.config.allow_group_messages:
            return None
        if self.config.require_whitelist and sender_id not in self.config.whitelist_user_ids:
            print(f"[xinyu_qq_gateway] ignored non-whitelisted sender={sender_id} kind={message_kind}", flush=True)
            return None

        if message_kind == "group":
            group_ok, normalized_text, reason = self._group_trigger_result(event, text=text)
            if not group_ok:
                print(f"[xinyu_qq_gateway] ignored group message: {reason}", flush=True)
                return None
            text = normalized_text.strip()
            if not text:
                return None

        if self._is_passthrough_command(text):
            return None

        target = ReplyTarget(message_kind=message_kind, user_id=sender_id, group_id=group_id)
        return PreparedMessage(target=target, payload=self._build_chat_payload(event, target=target, text=text))

    def _message_kind(self, event: dict[str, Any]) -> str:
        message_type = _safe_str(event.get("message_type")).lower()
        if message_type == "group" or event.get("group_id") not in {None, "", 0, "0"}:
            return "group"
        return "private"

    def _extract_text(self, event: dict[str, Any]) -> str:
        message = event.get("message")
        if isinstance(message, list):
            parts: list[str] = []
            for segment in message:
                if not isinstance(segment, dict):
                    continue
                if _safe_str(segment.get("type")).lower() != "text":
                    continue
                data = segment.get("data")
                if isinstance(data, dict):
                    parts.append(_safe_str(data.get("text")))
            text = "".join(parts).strip()
            if text:
                return text
        if isinstance(message, str):
            return message
        return _safe_str(event.get("raw_message"))

    def _sender_name(self, event: dict[str, Any]) -> str:
        sender = event.get("sender")
        if not isinstance(sender, dict):
            return ""
        return (
            _safe_str(sender.get("card")).strip()
            or _safe_str(sender.get("nickname")).strip()
            or _safe_str(sender.get("user_id")).strip()
        )

    def _group_trigger_result(self, event: dict[str, Any], *, text: str) -> tuple[bool, str, str]:
        group_id = _safe_str(event.get("group_id"), "")
        if self.config.allowed_group_ids and group_id not in self.config.allowed_group_ids:
            return False, text, "group_not_allowed"

        mode = self.config.group_trigger_mode or "mention_or_prefix"
        if mode in {"always", "all"}:
            return True, text, "group_always"

        mentioned = self._bot_was_mentioned(event, text=text)
        prefix_matched, stripped = self._strip_group_trigger_prefix(text)
        if mode in {"mention", "at"}:
            return (True, stripped or text, "group_mention") if mentioned else (False, text, "group_mention_required")
        if mode in {"prefix", "wake_prefix"}:
            return (True, stripped, "group_prefix") if prefix_matched else (False, text, "group_prefix_required")
        if mode in {"off", "disabled", "none"}:
            return False, text, "group_trigger_disabled"
        if mentioned or prefix_matched:
            return True, stripped if prefix_matched else text, "group_mention_or_prefix"
        return False, text, "group_trigger_required"

    def _strip_group_trigger_prefix(self, text: str) -> tuple[bool, str]:
        stripped = text.strip()
        separators = " \t\r\n,，。:：;；!！?？~～"
        for prefix in self.config.group_trigger_prefixes:
            marker = prefix.strip()
            if not marker:
                continue
            if stripped == marker:
                return True, ""
            if not stripped.startswith(marker):
                continue
            rest = stripped[len(marker):]
            if rest and rest[0] not in separators:
                continue
            return True, rest.lstrip(separators).strip()
        return False, text

    def _bot_was_mentioned(self, event: dict[str, Any], *, text: str) -> bool:
        self_id = _safe_str(event.get("self_id")).strip()
        message = event.get("message")
        if self_id and isinstance(message, list):
            for segment in message:
                if not isinstance(segment, dict) or _safe_str(segment.get("type")).lower() != "at":
                    continue
                data = segment.get("data")
                if isinstance(data, dict) and _safe_str(data.get("qq")).strip() == self_id:
                    return True
        compact = text.replace(" ", "")
        if self_id and (f"[CQ:at,qq={self_id}]" in compact or f"qq={self_id}" in compact):
            return True
        lowered_names = {prefix.strip().lower().lstrip("@") for prefix in self.config.group_trigger_prefixes}
        lowered_text = text.lower()
        return any(f"@{name}" in lowered_text for name in lowered_names if name)

    def _is_passthrough_command(self, text: str) -> bool:
        if self.config.ignore_prefixes and text.startswith(self.config.ignore_prefixes):
            return True
        command = text.split(maxsplit=1)[0].lstrip("/!.").lower()
        return command in self.config.passthrough_commands

    def _is_blocked_command(self, text: str) -> bool:
        token = text.split(maxsplit=1)[0].strip().lower()
        if not token:
            return False
        bare = token.lstrip("/!.#")
        for command in self.config.blocked_commands:
            normalized = command.strip().lower()
            if token == normalized or bare == normalized.lstrip("/!.#"):
                return True
        return False

    def _build_chat_payload(self, event: dict[str, Any], *, target: ReplyTarget, text: str) -> dict[str, Any]:
        session_id = self._session_id(target)
        message_type = f"{target.message_kind}_text"
        metadata = {
            "gateway": GATEWAY_NAME,
            "gateway_version": GATEWAY_VERSION,
            "source": "onebot_message_event",
            "onebot_post_type": _safe_str(event.get("post_type")),
            "onebot_message_type": _safe_str(event.get("message_type")),
            "is_owner_user": target.user_id in self.config.owner_user_ids,
        }
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

    def _session_id(self, target: ReplyTarget) -> str:
        if target.message_kind == "group":
            return f"qq:group:{target.group_id or 'unknown'}:{target.user_id}"
        return f"qq:private:{target.user_id}"

    def _visible_reply(self, text: str) -> str:
        reply = text.strip()
        if reply in {"[WAITING]", "WAITING"}:
            return ""
        if self.config.max_reply_chars and len(reply) > self.config.max_reply_chars:
            return reply[: self.config.max_reply_chars].rstrip() + "\n[truncated]"
        return reply

    async def send_reply(self, websocket: Any, target: ReplyTarget, text: str) -> dict[str, Any] | None:
        action = "send_group_msg" if target.message_kind == "group" else "send_private_msg"
        params: dict[str, Any] = {
            "message": [{"type": "text", "data": {"text": text}}],
            "auto_escape": False,
        }
        if target.message_kind == "group":
            params["group_id"] = _maybe_int(target.group_id)
        else:
            params["user_id"] = _maybe_int(target.user_id)
        return await self.send_action(websocket, action, params)

    async def send_action(self, websocket: Any, action: str, params: dict[str, Any]) -> dict[str, Any] | None:
        echo = f"xinyu-{int(time.time() * 1000)}-{id(params)}"
        payload = {"action": action, "params": params, "echo": echo}
        future: asyncio.Future[dict[str, Any]] = asyncio.get_running_loop().create_future()
        async with self._action_lock:
            self._pending_actions[echo] = future
            await websocket.send(json.dumps(payload, ensure_ascii=False))
        try:
            return await asyncio.wait_for(future, timeout=15)
        except TimeoutError:
            print(f"[xinyu_qq_gateway] OneBot action timed out: {action}", flush=True)
            self._pending_actions.pop(echo, None)
            return None


def _websocket_path(websocket: Any) -> str:
    request = getattr(websocket, "request", None)
    path = getattr(request, "path", "") if request is not None else ""
    if path:
        return str(path)
    return _safe_str(getattr(websocket, "path", ""))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Native XinYu QQ gateway for NapCat OneBot reverse WebSocket.")
    parser.add_argument("--config", type=Path, default=Path(__file__).resolve().with_name("xinyu_qq_gateway.config.json"))
    parser.add_argument("--host", default="")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--path", default="")
    parser.add_argument("--core-url", default="")
    parser.add_argument("--bridge-token", default=None)
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    args = _build_parser().parse_args()
    config = GatewayConfig.from_file(args.config).with_overrides(
        host=args.host or None,
        port=args.port or None,
        path=args.path or None,
        core_chat_url=args.core_url or None,
        bridge_token=args.bridge_token,
    )
    gateway = NativeQQGateway(config)
    asyncio.run(gateway.run())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

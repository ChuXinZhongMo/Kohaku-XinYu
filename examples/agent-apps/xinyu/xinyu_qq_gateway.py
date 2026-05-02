from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import os
import re
import signal
import sys
import time
import traceback
import urllib.error
import urllib.request
from urllib.parse import unquote
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import websockets
except ImportError as exc:  # pragma: no cover - exercised by startup scripts
    raise SystemExit("Missing dependency: websockets. Run: python -m pip install -r requirements-minimal.txt") from exc


GATEWAY_VERSION = "0.1.8"
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


def _derive_codex_execute_url(core_chat_url: str) -> str:
    return _derive_core_route_url(core_chat_url, "/codex/execute")


def _derive_learning_ingest_url(core_chat_url: str) -> str:
    return _derive_core_route_url(core_chat_url, "/learning/ingest")


def _derive_package_install_url(core_chat_url: str) -> str:
    return _derive_core_route_url(core_chat_url, "/package/install")


def _derive_core_route_url(core_chat_url: str, route: str) -> str:
    url = (core_chat_url or "").strip()
    if url:
        trimmed = url.rstrip("/")
        if trimmed.endswith("/chat"):
            return trimmed[: -len("/chat")] + route
    return "http://127.0.0.1:8765" + route


@dataclass(frozen=True)
class GatewayConfig:
    enabled: bool = True
    onebot_host: str = "127.0.0.1"
    onebot_port: int = 6199
    onebot_path: str = "/ws"
    core_chat_url: str = "http://127.0.0.1:8765/chat"
    bridge_token: str = ""
    codex_command_enabled: bool = True
    codex_execute_url: str = "http://127.0.0.1:8765/codex/execute"
    codex_command_prefixes: tuple[str, ...] = ("/codex",)
    codex_background: bool = True
    codex_auto_study: bool = True
    codex_timeout_seconds: int = 3600
    codex_visible_window: bool = True
    codex_window_title: str = "Xinyu codex"
    codex_network_access: bool = True
    qq_outbox_enabled: bool = True
    qq_outbox_claim_url: str = "http://127.0.0.1:8765/qq/outbox/claim"
    qq_outbox_ack_url: str = "http://127.0.0.1:8765/qq/outbox/ack"
    qq_outbox_poll_seconds: int = 5
    learning_ingest_url: str = "http://127.0.0.1:8765/learning/ingest"
    qq_file_learning_enabled: bool = True
    qq_file_learning_private_owner_only: bool = True
    qq_file_learning_stage: bool = True
    qq_file_learning_curated: bool = True
    package_install_enabled: bool = True
    package_install_url: str = "http://127.0.0.1:8765/package/install"
    package_install_prefixes: tuple[str, ...] = ("/pkg", "/pip")
    package_install_owner_private_only: bool = True
    package_install_natural_language: bool = True
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
        core_chat_url = _safe_str(raw.get("core_chat_url"), "http://127.0.0.1:8765/chat")
        bridge_token = _safe_str(raw.get("bridge_token"), "") or os.environ.get("XINYU_BRIDGE_TOKEN", "")
        codex_execute_url = _safe_str(raw.get("codex_execute_url"), "") or _derive_codex_execute_url(core_chat_url)
        learning_ingest_url = _safe_str(raw.get("learning_ingest_url"), "") or _derive_learning_ingest_url(core_chat_url)
        package_install_url = _safe_str(raw.get("package_install_url"), "") or _derive_package_install_url(core_chat_url)
        qq_outbox_claim_url = _safe_str(raw.get("qq_outbox_claim_url"), "") or _derive_core_route_url(core_chat_url, "/qq/outbox/claim")
        qq_outbox_ack_url = _safe_str(raw.get("qq_outbox_ack_url"), "") or _derive_core_route_url(core_chat_url, "/qq/outbox/ack")
        prefixes = tuple(_as_str_list(raw.get("group_trigger_prefixes")))
        prefixes = prefixes or ("心玉", "@心玉", "小心玉")
        if not prefixes:
            prefixes = ("心玉", "@心玉", "小心玉")
        return cls(
            enabled=_as_bool(raw.get("enabled"), True),
            onebot_host=_safe_str(raw.get("onebot_host"), "127.0.0.1"),
            onebot_port=_as_int(raw.get("onebot_port"), 6199),
            onebot_path=_safe_str(raw.get("onebot_path"), "/ws") or "/ws",
            core_chat_url=core_chat_url,
            bridge_token=bridge_token,
            codex_command_enabled=_as_bool(raw.get("codex_command_enabled"), True),
            codex_execute_url=codex_execute_url,
            codex_command_prefixes=tuple(_as_str_list(raw.get("codex_command_prefixes")) or ["/codex"]),
            codex_background=_as_bool(raw.get("codex_background"), True),
            codex_auto_study=_as_bool(raw.get("codex_auto_study"), True),
            codex_timeout_seconds=max(30, _as_int(raw.get("codex_timeout_seconds"), 3600)),
            codex_visible_window=_as_bool(raw.get("codex_visible_window"), True),
            codex_window_title=_safe_str(raw.get("codex_window_title"), "Xinyu codex").strip() or "Xinyu codex",
            codex_network_access=_as_bool(raw.get("codex_network_access"), True),
            qq_outbox_enabled=_as_bool(raw.get("qq_outbox_enabled"), True),
            qq_outbox_claim_url=qq_outbox_claim_url,
            qq_outbox_ack_url=qq_outbox_ack_url,
            qq_outbox_poll_seconds=max(2, _as_int(raw.get("qq_outbox_poll_seconds"), 5)),
            learning_ingest_url=learning_ingest_url,
            qq_file_learning_enabled=_as_bool(raw.get("qq_file_learning_enabled"), True),
            qq_file_learning_private_owner_only=_as_bool(raw.get("qq_file_learning_private_owner_only"), True),
            qq_file_learning_stage=_as_bool(raw.get("qq_file_learning_stage"), True),
            qq_file_learning_curated=_as_bool(raw.get("qq_file_learning_curated"), True),
            package_install_enabled=_as_bool(raw.get("package_install_enabled"), True),
            package_install_url=package_install_url,
            package_install_prefixes=tuple(_as_str_list(raw.get("package_install_prefixes")) or ["/pkg", "/pip"]),
            package_install_owner_private_only=_as_bool(raw.get("package_install_owner_private_only"), True),
            package_install_natural_language=_as_bool(raw.get("package_install_natural_language"), True),
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
        new_core_chat_url = core_chat_url or self.core_chat_url
        default_codex_url = _derive_codex_execute_url(self.core_chat_url)
        codex_execute_url = self.codex_execute_url
        if core_chat_url and self.codex_execute_url == default_codex_url:
            codex_execute_url = _derive_codex_execute_url(new_core_chat_url)
        default_learning_url = _derive_learning_ingest_url(self.core_chat_url)
        learning_ingest_url = self.learning_ingest_url
        if core_chat_url and self.learning_ingest_url == default_learning_url:
            learning_ingest_url = _derive_learning_ingest_url(new_core_chat_url)
        default_package_url = _derive_package_install_url(self.core_chat_url)
        package_install_url = self.package_install_url
        if core_chat_url and self.package_install_url == default_package_url:
            package_install_url = _derive_package_install_url(new_core_chat_url)
        default_claim_url = _derive_core_route_url(self.core_chat_url, "/qq/outbox/claim")
        default_ack_url = _derive_core_route_url(self.core_chat_url, "/qq/outbox/ack")
        qq_outbox_claim_url = self.qq_outbox_claim_url
        qq_outbox_ack_url = self.qq_outbox_ack_url
        if core_chat_url and self.qq_outbox_claim_url == default_claim_url:
            qq_outbox_claim_url = _derive_core_route_url(new_core_chat_url, "/qq/outbox/claim")
        if core_chat_url and self.qq_outbox_ack_url == default_ack_url:
            qq_outbox_ack_url = _derive_core_route_url(new_core_chat_url, "/qq/outbox/ack")
        return GatewayConfig(
            enabled=self.enabled,
            onebot_host=host or self.onebot_host,
            onebot_port=port if port is not None else self.onebot_port,
            onebot_path=path or self.onebot_path,
            core_chat_url=new_core_chat_url,
            bridge_token=bridge_token if bridge_token is not None else self.bridge_token,
            codex_command_enabled=self.codex_command_enabled,
            codex_execute_url=codex_execute_url,
            codex_command_prefixes=self.codex_command_prefixes,
            codex_background=self.codex_background,
            codex_auto_study=self.codex_auto_study,
            codex_timeout_seconds=self.codex_timeout_seconds,
            codex_visible_window=self.codex_visible_window,
            codex_window_title=self.codex_window_title,
            codex_network_access=self.codex_network_access,
            qq_outbox_enabled=self.qq_outbox_enabled,
            qq_outbox_claim_url=qq_outbox_claim_url,
            qq_outbox_ack_url=qq_outbox_ack_url,
            qq_outbox_poll_seconds=self.qq_outbox_poll_seconds,
            learning_ingest_url=learning_ingest_url,
            qq_file_learning_enabled=self.qq_file_learning_enabled,
            qq_file_learning_private_owner_only=self.qq_file_learning_private_owner_only,
            qq_file_learning_stage=self.qq_file_learning_stage,
            qq_file_learning_curated=self.qq_file_learning_curated,
            package_install_enabled=self.package_install_enabled,
            package_install_url=package_install_url,
            package_install_prefixes=self.package_install_prefixes,
            package_install_owner_private_only=self.package_install_owner_private_only,
            package_install_natural_language=self.package_install_natural_language,
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
    route: str = "chat"
    local_reply: str = ""


class BridgeError(RuntimeError):
    pass


class CoreBridgeClient:
    def __init__(
        self,
        *,
        chat_url: str,
        codex_execute_url: str,
        learning_ingest_url: str,
        package_install_url: str,
        qq_outbox_claim_url: str,
        qq_outbox_ack_url: str,
        token: str,
        timeout_seconds: int,
    ) -> None:
        self.chat_url = chat_url.strip()
        self.codex_execute_url = codex_execute_url.strip()
        self.learning_ingest_url = learning_ingest_url.strip()
        self.package_install_url = package_install_url.strip()
        self.qq_outbox_claim_url = qq_outbox_claim_url.strip()
        self.qq_outbox_ack_url = qq_outbox_ack_url.strip()
        self.token = token.strip()
        self.timeout_seconds = timeout_seconds

    async def chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self._post_json, self.chat_url, payload)

    async def codex_execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self._post_json, self.codex_execute_url, payload)

    async def learning_ingest(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self._post_json, self.learning_ingest_url, payload)

    async def package_install(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self._post_json, self.package_install_url, payload)

    async def qq_outbox_claim(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self._post_json, self.qq_outbox_claim_url, payload)

    async def qq_outbox_ack(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self._post_json, self.qq_outbox_ack_url, payload)

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
            chat_url=config.core_chat_url,
            codex_execute_url=config.codex_execute_url,
            learning_ingest_url=config.learning_ingest_url,
            package_install_url=config.package_install_url,
            qq_outbox_claim_url=config.qq_outbox_claim_url,
            qq_outbox_ack_url=config.qq_outbox_ack_url,
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
        outbox_task: asyncio.Task[Any] | None = None
        if self.config.qq_outbox_enabled and self.config.bridge_token:
            outbox_task = asyncio.create_task(
                self._poll_qq_outbox(websocket, connection_id),
                name=f"xinyu-qq-outbox-{connection_id}",
            )
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
            if outbox_task is not None:
                outbox_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await outbox_task

    async def _poll_qq_outbox(self, websocket: Any, connection_id: str) -> None:
        await asyncio.sleep(1)
        while True:
            try:
                claim_id = f"{connection_id}-{int(time.time() * 1000)}"
                claim = await self.client.qq_outbox_claim(
                    {
                        "claim_id": claim_id,
                        "adapter": GATEWAY_NAME,
                    }
                )
                if not claim.get("message_claimed"):
                    await asyncio.sleep(self.config.qq_outbox_poll_seconds)
                    continue

                target = self._outbox_target(claim)
                message = self._visible_reply(_safe_str(claim.get("message"), ""))
                if target is None or not message:
                    await self._ack_qq_outbox(
                        claim,
                        status="failed",
                        error="invalid target or empty message",
                    )
                    continue

                action_response = await self.send_reply(websocket, target, message)
                ok, adapter_message_id, adapter_error = self._onebot_action_result(action_response)
                await self._ack_qq_outbox(
                    claim,
                    status="sent" if ok else "failed",
                    adapter_message_id=adapter_message_id,
                    error=adapter_error,
                )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                print(f"[xinyu_qq_gateway] QQ outbox poll error: {type(exc).__name__}: {exc}", flush=True)
                await asyncio.sleep(max(5, self.config.qq_outbox_poll_seconds))

    def _outbox_target(self, claim: dict[str, Any]) -> ReplyTarget | None:
        target = claim.get("target")
        if not isinstance(target, dict):
            return None
        message_kind = _safe_str(target.get("message_kind"), "private").strip().lower()
        user_id = _safe_str(target.get("user_id")).strip()
        group_id = _safe_str(target.get("group_id")).strip()
        if message_kind != "private" or not user_id:
            return None
        return ReplyTarget(message_kind="private", user_id=user_id, group_id=group_id)

    def _onebot_action_result(self, response: dict[str, Any] | None) -> tuple[bool, str, str]:
        if not response:
            return False, "", "onebot_action_timeout"
        status = _safe_str(response.get("status")).lower()
        retcode = response.get("retcode")
        ok = status in {"ok", "async"} or retcode == 0 or str(retcode) == "0"
        data = response.get("data")
        adapter_message_id = ""
        if isinstance(data, dict):
            adapter_message_id = _safe_str(data.get("message_id")).strip()
        if ok:
            return True, adapter_message_id, ""
        return False, adapter_message_id, _safe_str(response.get("message") or response.get("wording") or response)[:300]

    async def _ack_qq_outbox(
        self,
        claim: dict[str, Any],
        *,
        status: str,
        adapter_message_id: str = "",
        error: str = "",
    ) -> None:
        try:
            await self.client.qq_outbox_ack(
                {
                    "message_id": _safe_str(claim.get("message_id")),
                    "claim_id": _safe_str(claim.get("claim_id")),
                    "ack_status": status,
                    "adapter_message_id": adapter_message_id,
                    "adapter_error": error,
                }
            )
        except Exception as exc:
            print(f"[xinyu_qq_gateway] QQ outbox ack error: {type(exc).__name__}: {exc}", flush=True)

    async def _resolve_learning_ingest_payload(self, websocket: Any, payload: dict[str, Any]) -> dict[str, Any]:
        if payload.get("file_url") or payload.get("file_path"):
            return payload
        metadata = payload.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
        file_id = _safe_str(payload.get("file_id") or metadata.get("file_id")).strip()
        if not file_id:
            return payload

        resolved = await self._resolve_onebot_file(websocket, file_id=file_id, metadata=metadata)
        if not resolved:
            print(f"[xinyu_qq_gateway] could not resolve QQ file_id={file_id}", flush=True)
            return payload
        enriched = dict(payload)
        resolved_metadata = dict(metadata)
        if resolved.get("file_url"):
            enriched["file_url"] = resolved["file_url"]
        if resolved.get("file_path"):
            enriched["file_path"] = resolved["file_path"]
        resolved_metadata.update(
            {
                "file_resolved_by": resolved.get("resolved_by", ""),
                "file_resolution_status": "resolved",
            }
        )
        enriched["metadata"] = resolved_metadata
        return enriched

    async def _resolve_onebot_file(self, websocket: Any, *, file_id: str, metadata: dict[str, Any]) -> dict[str, str]:
        group_id = _safe_str(metadata.get("group_id")).strip()
        if group_id:
            group_url = await self._onebot_file_url_action(
                websocket,
                "get_group_file_url",
                {"group_id": _maybe_int(group_id), "file_id": file_id},
            )
            if group_url:
                return {"file_url": group_url, "resolved_by": "get_group_file_url"}

        private_url = await self._onebot_file_url_action(websocket, "get_private_file_url", {"file_id": file_id})
        if private_url:
            return {"file_url": private_url, "resolved_by": "get_private_file_url"}

        file_data = await self._onebot_action_data(websocket, "get_file", {"file_id": file_id})
        if not file_data:
            return {}
        url = self._first_text_field(file_data, ("url", "file_url", "download_url"))
        if url:
            return {"file_url": url, "resolved_by": "get_file"}
        path = self._first_text_field(file_data, ("file", "file_path", "path", "real_path"))
        if path:
            return {"file_path": path, "resolved_by": "get_file"}
        return {}

    async def _onebot_file_url_action(self, websocket: Any, action: str, params: dict[str, Any]) -> str:
        data = await self._onebot_action_data(websocket, action, params)
        return self._first_text_field(data, ("url", "file_url", "download_url")) if data else ""

    async def _onebot_action_data(self, websocket: Any, action: str, params: dict[str, Any]) -> dict[str, Any]:
        response = await self.send_action(websocket, action, params)
        if not isinstance(response, dict):
            return {}
        status = _safe_str(response.get("status")).lower()
        retcode = response.get("retcode")
        if status and status != "ok":
            return {}
        if retcode not in {None, 0, "0"}:
            return {}
        data = response.get("data")
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _first_text_field(data: dict[str, Any], keys: tuple[str, ...]) -> str:
        for key in keys:
            value = _safe_str(data.get(key)).strip()
            if value:
                return value
        return ""

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

    @staticmethod
    def _reply_file_learning_intent(text: str) -> bool:
        stripped = text.strip()
        if not stripped:
            return False
        lowered = stripped.lower()
        deny_markers = ("不用读", "别读", "不读", "先别读", "do not read", "don't read")
        if any(marker in lowered or marker in stripped for marker in deny_markers):
            return False
        intent_markers = (
            "读",
            "阅读",
            "看",
            "看看",
            "学习",
            "研究",
            "解析",
            "总结",
            "讲讲",
            "提取",
            "导入",
            "收一下",
            "这个",
            "附件",
            "文件",
            "截图",
            "图片",
            "照片",
            "图像",
            "这张",
            "那张",
            "看图",
            "pdf",
            "paper",
            "read",
            "open",
            "parse",
            "summarize",
            "summarise",
            "study",
            "learn",
            "file",
            "image",
            "picture",
            "screenshot",
            "this",
        )
        return any(marker in lowered or marker in stripped for marker in intent_markers)

    def _extract_reply_message_id(self, event: dict[str, Any]) -> str:
        for key in ("reply_message_id", "reply_id", "source_message_id"):
            value = _safe_str(event.get(key)).strip()
            if value:
                return value

        message = event.get("message")
        if isinstance(message, list):
            for segment in message:
                if not isinstance(segment, dict):
                    continue
                if _safe_str(segment.get("type")).strip().lower() != "reply":
                    continue
                data = segment.get("data")
                if not isinstance(data, dict):
                    continue
                for key in ("id", "message_id", "reply_id"):
                    value = _safe_str(data.get(key)).strip()
                    if value:
                        return value

        raw_message = _safe_str(event.get("raw_message") or message)
        for match in re.finditer(r"\[CQ:reply,([^\]]+)\]", raw_message, re.I):
            params = self._parse_cq_params(match.group(1))
            for key in ("id", "message_id", "reply_id"):
                value = _safe_str(params.get(key)).strip()
                if value:
                    return value
        return ""

    @staticmethod
    def _parse_cq_params(raw_params: str) -> dict[str, str]:
        data: dict[str, str] = {}
        for raw_part in raw_params.split(","):
            if "=" not in raw_part:
                continue
            key, value = raw_part.split("=", 1)
            data[key.strip()] = unquote(value.strip())
        return data

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
        prepared = await self._upgrade_reply_file_learning(websocket, event, prepared)
        if prepared is None:
            return
        if prepared.local_reply:
            if self.config.send_replies:
                await self.send_reply(websocket, prepared.target, prepared.local_reply)
            return

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
                followup_payload = self._build_attachment_followup_chat_payload(
                    event,
                    target=prepared.target,
                    learning_payload=payload,
                    learning_response=response,
                )
                if followup_payload is not None:
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
            else:
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
        learning_material = self._extract_learning_material(event)
        if not text and learning_material is None:
            return None

        if text and self._is_blocked_command(text):
            print(f"[xinyu_qq_gateway] blocked command: {text.split(maxsplit=1)[0]}", flush=True)
            return None

        if self.config.private_only and message_kind != "private":
            return None
        if message_kind == "group" and not self.config.allow_group_messages:
            return None
        if self.config.require_whitelist and sender_id not in self.config.whitelist_user_ids:
            print(f"[xinyu_qq_gateway] ignored non-whitelisted sender={sender_id} kind={message_kind}", flush=True)
            return None

        target = ReplyTarget(message_kind=message_kind, user_id=sender_id, group_id=group_id)
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
            group_ok, normalized_text, reason = self._group_trigger_result(event, text=text)
            if not group_ok:
                print(f"[xinyu_qq_gateway] ignored group message: {reason}", flush=True)
                return None
            text = normalized_text.strip()
            if not text:
                return None

        package_text = self._extract_package_install_command(text)
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

        codex_task = self._extract_codex_command(text)
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

        if self._is_passthrough_command(text):
            return None

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

    def _learning_material_from_segment(self, segment: dict[str, Any]) -> dict[str, str] | None:
        segment_type = _safe_str(segment.get("type")).strip().lower()
        if segment_type not in {"file", "image", "record", "video"}:
            return None
        data = segment.get("data")
        if not isinstance(data, dict):
            data = {}
        return self._learning_material_from_data(segment_type, data)

    def _learning_material_from_data(self, segment_type: str, data: dict[str, Any]) -> dict[str, str] | None:
        name = (
            _safe_str(data.get("name")).strip()
            or _safe_str(data.get("file_name")).strip()
            or _safe_str(data.get("filename")).strip()
            or _safe_str(data.get("file")).strip()
            or f"qq-{segment_type}"
        )
        url = _safe_str(data.get("url")).strip()
        path = (
            _safe_str(data.get("file_path")).strip()
            or _safe_str(data.get("path")).strip()
            or _safe_str(data.get("local_path")).strip()
        )
        file_value = _safe_str(data.get("file")).strip()
        file_id = (
            _safe_str(data.get("file_id")).strip()
            or _safe_str(data.get("id")).strip()
            or _safe_str(data.get("fid")).strip()
        )
        if not path and self._looks_like_file_path(file_value):
            path = file_value
        if not file_id and file_value and not path:
            file_id = file_value
        if not url and not path and not file_id:
            return None
        return {
            "segment_type": segment_type,
            "name": name,
            "url": url,
            "path": path,
            "file_id": file_id,
        }

    def _learning_material_from_cq(self, raw_message: str) -> dict[str, str] | None:
        for match in re.finditer(r"\[CQ:(file|image|record|video),([^\]]+)\]", raw_message, re.I):
            segment_type = match.group(1).lower()
            data = self._parse_cq_params(match.group(2))
            material = self._learning_material_from_data(segment_type, data)
            if material is not None:
                return material
        return None

    @staticmethod
    def _looks_like_file_path(value: str) -> bool:
        text = value.strip()
        if not text:
            return False
        if text.lower().startswith("file://"):
            return True
        if len(text) > 2 and text[1] == ":" and text[2] in {"\\", "/"}:
            return True
        return "\\" in text or "/" in text

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
        separators = " \t\r\n,，、。:：;；!！?？"
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
        without_cq = re.sub(r"\[CQ:(?:file|image|record|video),[^\]]+\]", "", stripped, flags=re.I).strip()
        return without_cq or "owner supplied QQ file"

    def _build_attachment_followup_chat_payload(
        self,
        event: dict[str, Any],
        *,
        target: ReplyTarget,
        learning_payload: dict[str, Any],
        learning_response: dict[str, Any],
    ) -> dict[str, Any] | None:
        if not learning_response.get("extracted_text"):
            return None
        if target.message_kind != "private":
            return None
        text = _safe_str(learning_payload.get("reason")).strip()
        if not text or text == "owner supplied QQ file":
            text = "我刚发了一个附件。"
        payload = self._build_chat_payload(event, target=target, text=text)
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

    def _extract_codex_command(self, text: str) -> str | None:
        stripped = text.strip()
        lowered = stripped.lower()
        separators = " \t\r\n:：,，"
        for prefix in self.config.codex_command_prefixes:
            marker = prefix.strip()
            if not marker:
                continue
            marker_lower = marker.lower()
            if lowered == marker_lower:
                return ""
            if not lowered.startswith(marker_lower):
                continue
            rest = stripped[len(marker):]
            if rest and rest[0] not in separators:
                continue
            return rest.lstrip(separators).strip()
        return None

    def _extract_package_install_command(self, text: str) -> str | None:
        stripped = text.strip()
        lowered = stripped.lower()
        separators = " \t\r\n:：,，"
        for prefix in self.config.package_install_prefixes:
            marker = prefix.strip()
            if not marker:
                continue
            marker_lower = marker.lower()
            if lowered == marker_lower:
                return ""
            if not lowered.startswith(marker_lower):
                continue
            rest = stripped[len(marker):]
            if rest and rest[0] not in separators:
                continue
            return rest.lstrip(separators).strip()
        if not self.config.package_install_natural_language:
            return None
        return self._extract_natural_language_package_install(text)

    def _extract_natural_language_package_install(self, text: str) -> str | None:
        stripped = text.strip()
        lowered = stripped.lower()
        install_markers = (
            "pip install",
            "装库",
            "装个库",
            "装一下",
            "帮她装",
            "帮你装",
            "自己装",
            "把这个库装了",
            "缺什么库",
            "缺哪个库",
            "缺库",
        )
        if not any(marker in lowered or marker in stripped for marker in install_markers):
            return None
        return self._package_text_from_natural_language(stripped)

    @staticmethod
    def _package_text_from_natural_language(text: str) -> str:
        for marker in ("`", "“", "”", "\"", "'", "‘", "’"):
            text = text.replace(marker, " ")
        normalized = text.replace("，", " ").replace("。", " ").replace("、", " ").replace("：", " ")
        parts = [part.strip() for part in normalized.split() if part.strip()]
        stopwords = {
            "pip",
            "install",
            "python",
            "库",
            "装",
            "装库",
            "装一下",
            "帮她装",
            "帮你装",
            "自己装",
            "缺什么库",
            "缺哪个库",
            "缺库",
            "吗",
            "吧",
            "一下",
            "这个",
            "那个",
            "给她",
            "给你",
            "缺",
            "权限",
        }
        candidates: list[str] = []
        for part in parts:
            token = part.strip().strip(".,;:!?()[]{}<>")
            if not token:
                continue
            lowered = token.lower()
            if lowered in stopwords:
                continue
            if any("\u4e00" <= ch <= "\u9fff" for ch in token):
                continue
            if not any(ch.isalpha() for ch in token):
                continue
            candidates.append(token)
        return " ".join(candidates)

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

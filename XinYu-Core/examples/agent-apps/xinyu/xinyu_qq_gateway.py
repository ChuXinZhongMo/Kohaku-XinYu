from __future__ import annotations

import argparse
import asyncio
import contextlib
import hashlib
import json
import logging
import os
import re
import signal
import sys
import time
import traceback
import urllib.error
import urllib.request
from dataclasses import dataclass, field, replace
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from xinyu_gateway_ack_spool import SentAckSpool
from xinyu_group_shadow_observer import record_group_shadow_observation
from xinyu_image_context import build_image_context, is_image_learning_payload
from xinyu_codex_delegate import looks_like_owner_local_write_request
import xinyu_qq_attachment_resolver
import xinyu_qq_command_router
import xinyu_qq_normalizer
import xinyu_qq_outbox_client
import xinyu_qq_outbox_dispatcher
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
SUPPORTED_IMAGE_SUFFIXES = frozenset({".bmp", ".gif", ".jfif", ".jpeg", ".jpg", ".png", ".webp"})
COMMAND_PREFIX_CHARS = "/!.！#"
STICKER_SEGMENT_TYPES = frozenset({"face", "mface", "dice", "rps"})
RICH_CONTEXT_SEGMENT_TYPES = frozenset({"reply", "forward", "face", "mface", "dice", "rps", "image", "json", "xml", "at"})
QQ_FORWARD_CONTEXT_MAX_MESSAGES = 12
QQ_FORWARD_CONTEXT_MAX_TEXT_CHARS = 5000
RECEIVED_STICKER_MOOD_MARKERS: dict[str, tuple[str, ...]] = {
    "laugh": ("哈哈", "笑死", "乐", "绷不住", "lol", "laugh"),
    "happy": ("开心", "高兴", "好耶", "可爱", "喜欢", "happy", "joy"),
    "confused": ("疑惑", "问号", "懵", "啊？", "啊?", "what", "confused"),
    "deadpan": ("无语", "沉默", "面无表情", "冷漠", "stare", "blank"),
    "awkward": ("尴尬", "流汗", "汗", "embarrassed", "sweat"),
    "sad": ("难过", "委屈", "低落", "哭", "sad", "cry"),
    "comfort": ("抱抱", "安慰", "摸摸", "hug", "comfort"),
    "annoyed": ("烦", "嫌弃", "不爽", "哼", "angry", "annoyed"),
    "surprised": ("震惊", "惊了", "意外", "真的假的", "wow", "shock"),
    "thinking": ("思考", "想想", "疑问", "thinking"),
}
RECEIVED_STICKER_MOOD_MEANING: dict[str, str] = {
    "laugh": "大笑、觉得好笑、跟着一起乐",
    "happy": "开心、轻松、正向回应",
    "confused": "疑惑、没看懂、觉得哪里不对",
    "deadpan": "无语、沉默、冷静看着",
    "awkward": "尴尬、流汗、卡住",
    "sad": "难过、委屈、低落",
    "comfort": "安慰、抱抱、陪一下",
    "annoyed": "嫌弃、不爽、被烦到",
    "surprised": "震惊、惊讶、没想到",
    "thinking": "思考、暂停判断",
}
TRUST_GRANT_TEXT_MARKERS = (
    "给个权限",
    "给权限",
    "加权限",
    "开权限",
    "给她权限",
    "给他权限",
    "信任这个人",
    "信任她",
    "信任他",
    "允许她搜",
    "允许他搜",
    "让她搜",
    "让他搜",
    "给她搜索权限",
    "给他搜索权限",
    "trusted user",
    "trust this user",
)
TRUST_REVOKE_TEXT_MARKERS = (
    "取消权限",
    "撤销权限",
    "别信任",
    "不信任这个人",
    "取消信任",
    "revoke trust",
)


def _quiet_websockets_handshake_noise() -> None:
    for logger_name in ("websockets.server", "websockets.protocol"):
        logging.getLogger(logger_name).setLevel(logging.CRITICAL)


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _hash_id(value: Any, *, length: int = 16) -> str:
    text = _safe_str(value).strip()
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:length]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


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


def _as_float(value: Any, default: float) -> float:
    try:
        return float(value)
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


def _env_str_list(*names: str) -> list[str]:
    values: list[str] = []
    for name in names:
        values.extend(_as_str_list(os.environ.get(name)))
    return list(dict.fromkeys(values))


def _merge_str_lists(*values: Any) -> list[str]:
    merged: list[str] = []
    for value in values:
        merged.extend(_as_str_list(value))
    return list(dict.fromkeys(item for item in merged if item))


def _with_required_prefixes(prefixes: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    values = [item for item in prefixes if item]
    for required in ("/", "!", "！", "."):
        if required not in values:
            values.append(required)
    return tuple(dict.fromkeys(values))


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


def _derive_sticker_import_url(core_chat_url: str) -> str:
    return _derive_core_route_url(core_chat_url, "/sticker/import")


def _derive_package_install_url(core_chat_url: str) -> str:
    return _derive_core_route_url(core_chat_url, "/package/install")


def _derive_review_inbox_command_url(core_chat_url: str) -> str:
    return _derive_core_route_url(core_chat_url, "/review/inbox/command")


def _derive_goldmark_mark_url(core_chat_url: str) -> str:
    return _derive_core_route_url(core_chat_url, "/review/goldmark/mark_request")


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
    message_ack_url: str = "http://127.0.0.1:8765/internal/message/ack"
    gateway_ack_spool_path: str = str(Path(__file__).resolve().parent / "runtime/gateway_ack_spool.jsonl")
    review_inbox_command_url: str = "http://127.0.0.1:8765/review/inbox/command"
    goldmark_mark_url: str = "http://127.0.0.1:8765/review/goldmark/mark_request"
    qq_outbox_poll_seconds: int = 5
    qq_outbox_image_enabled: bool = True
    qq_outbox_file_enabled: bool = True
    learning_ingest_url: str = "http://127.0.0.1:8765/learning/ingest"
    sticker_import_url: str = "http://127.0.0.1:8765/sticker/import"
    qq_file_learning_enabled: bool = True
    qq_file_learning_private_owner_only: bool = True
    qq_file_learning_stage: bool = True
    qq_file_learning_curated: bool = True
    qq_sticker_import_enabled: bool = True
    qq_sticker_import_private_owner_only: bool = True
    qq_sticker_import_use_clip: bool = True
    qq_sticker_import_use_ocr: bool = True
    package_install_enabled: bool = True
    package_install_url: str = "http://127.0.0.1:8765/package/install"
    package_install_prefixes: tuple[str, ...] = ("/pkg", "/pip")
    package_install_owner_private_only: bool = True
    package_install_natural_language: bool = True
    timeout_seconds: int = 300
    require_whitelist: bool = True
    whitelist_user_ids: frozenset[str] = frozenset()
    owner_user_ids: frozenset[str] = frozenset()
    trusted_user_ids: frozenset[str] = frozenset()
    blocked_user_ids: frozenset[str] = frozenset()
    blocked_group_ids: frozenset[str] = frozenset()
    private_only: bool = False
    allow_group_messages: bool = True
    allowed_group_ids: frozenset[str] = frozenset()
    group_trigger_mode: str = "mention_or_prefix"
    group_trigger_prefixes: tuple[str, ...] = ()
    group_shadow_enabled: bool = False
    group_shadow_allowed_group_ids: frozenset[str] = frozenset()
    group_shadow_max_text_chars: int = 260
    ignore_prefixes: tuple[str, ...] = ("/", "!", "！", ".")
    blocked_commands: frozenset[str] = frozenset({"#napcat"})
    passthrough_commands: frozenset[str] = frozenset({"sid", "help", "xinyu_qq_status"})
    send_replies: bool = True
    show_bridge_errors: bool = False
    max_reply_chars: int = 3500
    reply_bubble_split_enabled: bool = True
    reply_bubble_private_only: bool = False
    reply_bubble_min_chars: int = 72
    reply_bubble_soft_max_chars: int = 96
    reply_bubble_max_bubbles: int = 3
    reply_bubble_force_max_bubbles: int = 20
    reply_bubble_delay_seconds: float = 0.6
    owner_private_coalesce_seconds: float = 2.0
    owner_private_coalesce_max_fragments: int = 8

    @classmethod
    def from_file(cls, path: Path) -> "GatewayConfig":
        raw = _load_json(path)
        core_chat_url = _safe_str(raw.get("core_chat_url"), "http://127.0.0.1:8765/chat")
        bridge_token = _safe_str(raw.get("bridge_token"), "") or os.environ.get("XINYU_BRIDGE_TOKEN", "")
        codex_execute_url = _safe_str(raw.get("codex_execute_url"), "") or _derive_codex_execute_url(core_chat_url)
        learning_ingest_url = _safe_str(raw.get("learning_ingest_url"), "") or _derive_learning_ingest_url(core_chat_url)
        sticker_import_url = _safe_str(raw.get("sticker_import_url"), "") or _derive_sticker_import_url(core_chat_url)
        package_install_url = _safe_str(raw.get("package_install_url"), "") or _derive_package_install_url(core_chat_url)
        review_inbox_command_url = _safe_str(raw.get("review_inbox_command_url"), "") or _derive_review_inbox_command_url(core_chat_url)
        goldmark_mark_url = _safe_str(raw.get("goldmark_mark_url"), "") or _derive_goldmark_mark_url(core_chat_url)
        qq_outbox_claim_url = _safe_str(raw.get("qq_outbox_claim_url"), "") or _derive_core_route_url(core_chat_url, "/qq/outbox/claim")
        qq_outbox_ack_url = _safe_str(raw.get("qq_outbox_ack_url"), "") or _derive_core_route_url(core_chat_url, "/qq/outbox/ack")
        message_ack_url = _safe_str(raw.get("message_ack_url"), "") or _derive_core_route_url(core_chat_url, "/internal/message/ack")
        gateway_ack_spool_path = _safe_str(raw.get("gateway_ack_spool_path"), "").strip()
        if not gateway_ack_spool_path:
            gateway_ack_spool_path = str(path.resolve().parent / "runtime/gateway_ack_spool.jsonl")
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
            message_ack_url=message_ack_url,
            gateway_ack_spool_path=gateway_ack_spool_path,
            review_inbox_command_url=review_inbox_command_url,
            goldmark_mark_url=goldmark_mark_url,
            qq_outbox_poll_seconds=max(2, _as_int(raw.get("qq_outbox_poll_seconds"), 5)),
            qq_outbox_image_enabled=_as_bool(raw.get("qq_outbox_image_enabled"), True),
            qq_outbox_file_enabled=_as_bool(raw.get("qq_outbox_file_enabled"), True),
            learning_ingest_url=learning_ingest_url,
            sticker_import_url=sticker_import_url,
            qq_file_learning_enabled=_as_bool(raw.get("qq_file_learning_enabled"), True),
            qq_file_learning_private_owner_only=_as_bool(raw.get("qq_file_learning_private_owner_only"), True),
            qq_file_learning_stage=_as_bool(raw.get("qq_file_learning_stage"), True),
            qq_file_learning_curated=_as_bool(raw.get("qq_file_learning_curated"), True),
            qq_sticker_import_enabled=_as_bool(raw.get("qq_sticker_import_enabled"), True),
            qq_sticker_import_private_owner_only=_as_bool(raw.get("qq_sticker_import_private_owner_only"), True),
            qq_sticker_import_use_clip=_as_bool(raw.get("qq_sticker_import_use_clip"), True),
            qq_sticker_import_use_ocr=_as_bool(raw.get("qq_sticker_import_use_ocr"), True),
            package_install_enabled=_as_bool(raw.get("package_install_enabled"), True),
            package_install_url=package_install_url,
            package_install_prefixes=tuple(_as_str_list(raw.get("package_install_prefixes")) or ["/pkg", "/pip"]),
            package_install_owner_private_only=_as_bool(raw.get("package_install_owner_private_only"), True),
            package_install_natural_language=_as_bool(raw.get("package_install_natural_language"), True),
            timeout_seconds=max(5, _as_int(raw.get("timeout_seconds"), 300)),
            require_whitelist=_as_bool(raw.get("require_whitelist"), True),
            whitelist_user_ids=frozenset(
                _merge_str_lists(
                    raw.get("whitelist_user_ids"),
                    _env_str_list("XINYU_QQ_WHITELIST_USER_IDS", "XINYU_WHITELIST_USER_IDS"),
                )
            ),
            owner_user_ids=frozenset(
                _merge_str_lists(raw.get("owner_user_ids"), _env_str_list("XINYU_OWNER_USER_IDS"))
            ),
            trusted_user_ids=frozenset(
                _merge_str_lists(
                    raw.get("trusted_user_ids"),
                    _env_str_list("XINYU_QQ_TRUSTED_USER_IDS", "XINYU_TRUSTED_USER_IDS"),
                )
            ),
            blocked_user_ids=frozenset(_as_str_list(raw.get("blocked_user_ids"))),
            blocked_group_ids=frozenset(_as_str_list(raw.get("blocked_group_ids"))),
            private_only=_as_bool(raw.get("private_only"), False),
            allow_group_messages=_as_bool(raw.get("allow_group_messages"), True),
            allowed_group_ids=frozenset(_as_str_list(raw.get("allowed_group_ids"))),
            group_trigger_mode=_safe_str(raw.get("group_trigger_mode"), "mention_or_prefix").strip().lower(),
            group_trigger_prefixes=prefixes,
            group_shadow_enabled=_as_bool(raw.get("group_shadow_enabled"), False),
            group_shadow_allowed_group_ids=frozenset(_as_str_list(raw.get("group_shadow_allowed_group_ids"))),
            group_shadow_max_text_chars=max(80, min(1000, _as_int(raw.get("group_shadow_max_text_chars"), 260))),
            ignore_prefixes=_with_required_prefixes(_as_str_list(raw.get("ignore_prefixes")) or ["/", "!", "！", "."]),
            blocked_commands=frozenset(
                item.lower() for item in (_as_str_list(raw.get("blocked_commands")) or ["#napcat"])
            ),
            passthrough_commands=frozenset(
                item.strip().lstrip(COMMAND_PREFIX_CHARS).lower()
                for item in (_as_str_list(raw.get("passthrough_commands")) or ["sid", "help", "xinyu_qq_status"])
                if item.strip().lstrip(COMMAND_PREFIX_CHARS)
            ),
            send_replies=_as_bool(raw.get("send_replies"), True),
            show_bridge_errors=_as_bool(raw.get("show_bridge_errors"), False),
            max_reply_chars=max(200, _as_int(raw.get("max_reply_chars"), 3500)),
            reply_bubble_split_enabled=_as_bool(raw.get("reply_bubble_split_enabled"), True),
            reply_bubble_private_only=_as_bool(raw.get("reply_bubble_private_only"), False),
            reply_bubble_min_chars=max(40, _as_int(raw.get("reply_bubble_min_chars"), 72)),
            reply_bubble_soft_max_chars=max(60, _as_int(raw.get("reply_bubble_soft_max_chars"), 96)),
            reply_bubble_max_bubbles=max(2, min(5, _as_int(raw.get("reply_bubble_max_bubbles"), 3))),
            reply_bubble_force_max_bubbles=max(2, min(20, _as_int(raw.get("reply_bubble_force_max_bubbles"), 20))),
            reply_bubble_delay_seconds=max(0.0, min(3.0, _as_float(raw.get("reply_bubble_delay_seconds"), 0.6))),
            owner_private_coalesce_seconds=max(0.0, min(5.0, _as_float(raw.get("owner_private_coalesce_seconds"), 2.0))),
            owner_private_coalesce_max_fragments=max(2, _as_int(raw.get("owner_private_coalesce_max_fragments"), 8)),
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
        default_sticker_import_url = _derive_sticker_import_url(self.core_chat_url)
        sticker_import_url = self.sticker_import_url
        if core_chat_url and self.sticker_import_url == default_sticker_import_url:
            sticker_import_url = _derive_sticker_import_url(new_core_chat_url)
        default_package_url = _derive_package_install_url(self.core_chat_url)
        package_install_url = self.package_install_url
        if core_chat_url and self.package_install_url == default_package_url:
            package_install_url = _derive_package_install_url(new_core_chat_url)
        default_review_url = _derive_review_inbox_command_url(self.core_chat_url)
        review_inbox_command_url = self.review_inbox_command_url
        if core_chat_url and self.review_inbox_command_url == default_review_url:
            review_inbox_command_url = _derive_review_inbox_command_url(new_core_chat_url)
        default_goldmark_url = _derive_goldmark_mark_url(self.core_chat_url)
        goldmark_mark_url = self.goldmark_mark_url
        if core_chat_url and self.goldmark_mark_url == default_goldmark_url:
            goldmark_mark_url = _derive_goldmark_mark_url(new_core_chat_url)
        default_claim_url = _derive_core_route_url(self.core_chat_url, "/qq/outbox/claim")
        default_ack_url = _derive_core_route_url(self.core_chat_url, "/qq/outbox/ack")
        default_message_ack_url = _derive_core_route_url(self.core_chat_url, "/internal/message/ack")
        qq_outbox_claim_url = self.qq_outbox_claim_url
        qq_outbox_ack_url = self.qq_outbox_ack_url
        message_ack_url = self.message_ack_url
        if core_chat_url and self.qq_outbox_claim_url == default_claim_url:
            qq_outbox_claim_url = _derive_core_route_url(new_core_chat_url, "/qq/outbox/claim")
        if core_chat_url and self.qq_outbox_ack_url == default_ack_url:
            qq_outbox_ack_url = _derive_core_route_url(new_core_chat_url, "/qq/outbox/ack")
        if core_chat_url and self.message_ack_url == default_message_ack_url:
            message_ack_url = _derive_core_route_url(new_core_chat_url, "/internal/message/ack")
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
            message_ack_url=message_ack_url,
            gateway_ack_spool_path=self.gateway_ack_spool_path,
            review_inbox_command_url=review_inbox_command_url,
            goldmark_mark_url=goldmark_mark_url,
            qq_outbox_poll_seconds=self.qq_outbox_poll_seconds,
            qq_outbox_image_enabled=self.qq_outbox_image_enabled,
            qq_outbox_file_enabled=self.qq_outbox_file_enabled,
            learning_ingest_url=learning_ingest_url,
            sticker_import_url=sticker_import_url,
            qq_file_learning_enabled=self.qq_file_learning_enabled,
            qq_file_learning_private_owner_only=self.qq_file_learning_private_owner_only,
            qq_file_learning_stage=self.qq_file_learning_stage,
            qq_file_learning_curated=self.qq_file_learning_curated,
            qq_sticker_import_enabled=self.qq_sticker_import_enabled,
            qq_sticker_import_private_owner_only=self.qq_sticker_import_private_owner_only,
            qq_sticker_import_use_clip=self.qq_sticker_import_use_clip,
            qq_sticker_import_use_ocr=self.qq_sticker_import_use_ocr,
            package_install_enabled=self.package_install_enabled,
            package_install_url=package_install_url,
            package_install_prefixes=self.package_install_prefixes,
            package_install_owner_private_only=self.package_install_owner_private_only,
            package_install_natural_language=self.package_install_natural_language,
            timeout_seconds=self.timeout_seconds,
            require_whitelist=self.require_whitelist,
            whitelist_user_ids=self.whitelist_user_ids,
            owner_user_ids=self.owner_user_ids,
            trusted_user_ids=self.trusted_user_ids,
            blocked_user_ids=self.blocked_user_ids,
            blocked_group_ids=self.blocked_group_ids,
            private_only=self.private_only,
            allow_group_messages=self.allow_group_messages,
            allowed_group_ids=self.allowed_group_ids,
            group_trigger_mode=self.group_trigger_mode,
            group_trigger_prefixes=self.group_trigger_prefixes,
            group_shadow_enabled=self.group_shadow_enabled,
            group_shadow_allowed_group_ids=self.group_shadow_allowed_group_ids,
            group_shadow_max_text_chars=self.group_shadow_max_text_chars,
            ignore_prefixes=self.ignore_prefixes,
            blocked_commands=self.blocked_commands,
            passthrough_commands=self.passthrough_commands,
            send_replies=self.send_replies,
            show_bridge_errors=self.show_bridge_errors,
            max_reply_chars=self.max_reply_chars,
            reply_bubble_split_enabled=self.reply_bubble_split_enabled,
            reply_bubble_private_only=self.reply_bubble_private_only,
            reply_bubble_min_chars=self.reply_bubble_min_chars,
            reply_bubble_soft_max_chars=self.reply_bubble_soft_max_chars,
            reply_bubble_max_bubbles=self.reply_bubble_max_bubbles,
            reply_bubble_force_max_bubbles=self.reply_bubble_force_max_bubbles,
            reply_bubble_delay_seconds=self.reply_bubble_delay_seconds,
            owner_private_coalesce_seconds=self.owner_private_coalesce_seconds,
            owner_private_coalesce_max_fragments=self.owner_private_coalesce_max_fragments,
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


@dataclass
class PendingAction:
    connection_id: str
    future: asyncio.Future[dict[str, Any]]


@dataclass
class RecentStickerImportState:
    target: ReplyTarget
    event: dict[str, Any]
    payload: dict[str, Any]
    response: dict[str, Any] = field(default_factory=dict)
    status: str = "pending"
    error: str = ""
    updated_at: float = field(default_factory=time.time)


class BridgeError(RuntimeError):
    pass


class CoreBridgeClient:
    def __init__(
        self,
        *,
        chat_url: str,
        codex_execute_url: str,
        learning_ingest_url: str,
        sticker_import_url: str,
        package_install_url: str,
        review_inbox_command_url: str,
        goldmark_mark_url: str,
        qq_outbox_claim_url: str,
        qq_outbox_ack_url: str,
        message_ack_url: str,
        token: str,
        timeout_seconds: int,
    ) -> None:
        self.chat_url = chat_url.strip()
        self.codex_execute_url = codex_execute_url.strip()
        self.learning_ingest_url = learning_ingest_url.strip()
        self.sticker_import_url = sticker_import_url.strip()
        self.package_install_url = package_install_url.strip()
        self.review_inbox_command_url = review_inbox_command_url.strip()
        self.goldmark_mark_url = goldmark_mark_url.strip()
        self.qq_outbox_claim_url = qq_outbox_claim_url.strip()
        self.qq_outbox_ack_url = qq_outbox_ack_url.strip()
        self.message_ack_url = message_ack_url.strip()
        self.token = token.strip()
        self.timeout_seconds = timeout_seconds

    async def chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self._post_json, self.chat_url, payload)

    async def codex_execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self._post_json, self.codex_execute_url, payload)

    async def learning_ingest(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self._post_json, self.learning_ingest_url, payload)

    async def sticker_import(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self._post_json, self.sticker_import_url, payload)

    async def package_install(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self._post_json, self.package_install_url, payload)

    async def review_inbox_command(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self._post_json, self.review_inbox_command_url, payload)

    async def goldmark_mark_request(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self._post_json, self.goldmark_mark_url, payload)

    async def qq_outbox_claim(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self._post_json, self.qq_outbox_claim_url, payload)

    async def qq_outbox_ack(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self._post_json, self.qq_outbox_ack_url, payload)

    async def message_ack(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await asyncio.to_thread(self._post_json, self.message_ack_url, payload)

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

    @staticmethod
    def _compact_command_text(text: str) -> str:
        return xinyu_qq_trust_policy.compact_command_text(text)

    def _looks_like_trust_command(self, text: str) -> bool:
        return xinyu_qq_trust_policy.marker_command_matches(text, TRUST_GRANT_TEXT_MARKERS)

    def _looks_like_trust_revoke_command(self, text: str) -> bool:
        return xinyu_qq_trust_policy.marker_command_matches(text, TRUST_REVOKE_TEXT_MARKERS)

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
            tmp_path = config_path.with_suffix(config_path.suffix + ".tmp")
            tmp_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            tmp_path.replace(config_path)
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
        path = _websocket_path(websocket)
        if self.config.onebot_path and path not in {"", self.config.onebot_path}:
            print(f"[xinyu_qq_gateway] rejecting websocket path: {path}", flush=True)
            await websocket.close(code=1008, reason="invalid path")
            return

        self._connection_count += 1
        connection_id = f"napcat-{int(time.time())}-{self._connection_count}"
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

    def _onebot_action_result(self, response: dict[str, Any] | None) -> tuple[bool, str, str]:
        return xinyu_qq_outbox_client.onebot_action_result(self, response)

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

    @staticmethod
    def _sent_outbox_delivery_route(outbox_message_id: str, delivery_kind: str) -> str:
        return xinyu_qq_outbox_client.sent_outbox_delivery_route(outbox_message_id, delivery_kind)

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

    def _spool_pending_message_ack(self, payload: dict[str, Any]) -> bool:
        return xinyu_qq_outbox_client.spool_pending_message_ack(self, payload)

    def _spool_acked_message_ack(self, payload: dict[str, Any]) -> bool:
        return xinyu_qq_outbox_client.spool_acked_message_ack(self, payload)

    def _sent_message_ack_payload(
        self,
        prepared: PreparedMessage,
        *,
        reply: str,
        core_response: dict[str, Any],
        action_response: dict[str, Any] | None,
    ) -> dict[str, Any]:
        return xinyu_qq_outbox_client.sent_message_ack_payload(
            self,
            prepared,
            reply=reply,
            core_response=core_response,
            action_response=action_response,
        )

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

    async def _flush_pending_message_acks(self, *, limit: int = 20) -> dict[str, Any]:
        return await xinyu_qq_outbox_client.flush_pending_message_acks(self, limit=limit)

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

    @staticmethod
    def _path_from_file_uri(value: str) -> Path:
        return xinyu_qq_attachment_resolver.path_from_file_uri(value)

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
            "messages": messages[:QQ_FORWARD_CONTEXT_MAX_MESSAGES],
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
            if messages and used_chars + text_len > QQ_FORWARD_CONTEXT_MAX_TEXT_CHARS:
                break
            used_chars += text_len
            messages.append(message)
            if len(messages) >= QQ_FORWARD_CONTEXT_MAX_MESSAGES:
                break
        return messages

    def _forward_raw_items(self, payload: Any) -> list[Any]:
        if payload is None:
            return []
        if isinstance(payload, str):
            stripped = payload.strip()
            if not stripped:
                return []
            try:
                return self._forward_raw_items(json.loads(stripped))
            except json.JSONDecodeError:
                return [stripped]
        if isinstance(payload, list):
            return payload
        if not isinstance(payload, dict):
            return []
        for key in ("messages", "message", "content", "nodes", "node", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
            if isinstance(value, dict):
                nested = self._forward_raw_items(value)
                if nested:
                    return nested
            if isinstance(value, str) and value.strip().startswith(("[", "{")):
                nested = self._forward_raw_items(value)
                if nested:
                    return nested
        if any(key in payload for key in ("sender", "user_id", "nickname", "message", "content", "raw_message")):
            return [payload]
        return []

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

    @staticmethod
    def _dedupe_forward_messages(messages: list[dict[str, str]]) -> list[dict[str, str]]:
        deduped: list[dict[str, str]] = []
        seen: set[tuple[str, str, str]] = set()
        for item in messages:
            key = (
                _safe_str(item.get("message_id")).strip(),
                _safe_str(item.get("sender_name") or item.get("user_id")).strip(),
                _safe_str(item.get("text") or item.get("rich_summary") or item.get("raw_message")).strip(),
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped

    @staticmethod
    def _reply_file_learning_intent(text: str) -> bool:
        return xinyu_qq_attachment_resolver.reply_file_learning_intent(None, text)

    def _extract_reply_message_id(self, event: dict[str, Any]) -> str:
        for key in ("reply_message_id", "reply_id", "source_message_id", "quoted_message_id", "quote_message_id"):
            value = _safe_str(event.get(key)).strip()
            if value:
                return value
        reply = event.get("reply")
        if isinstance(reply, dict):
            for key in ("message_id", "id", "reply_id", "source_message_id"):
                value = _safe_str(reply.get(key)).strip()
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
        for segment in self._parse_cq_segments(raw_message):
            if _safe_str(segment.get("type")).strip().lower() != "reply":
                continue
            params = self._segment_data(segment)
            for key in ("id", "message_id", "reply_id"):
                value = _safe_str(params.get(key)).strip()
                if value:
                    return value
        return ""

    def _extract_forward_message_ids(self, event: dict[str, Any]) -> list[str]:
        ids: list[str] = []
        for key in ("forward_message_id", "forward_id", "forward_msg_id", "resid", "res_id"):
            ids.extend(_as_str_list(event.get(key)))

        for segment in self._message_segments(event):
            segment_type = _safe_str(segment.get("type")).strip().lower()
            data = self._segment_data(segment)
            if segment_type == "forward":
                for key in ("id", "message_id", "forward_id", "forward_msg_id", "resid", "res_id"):
                    ids.extend(_as_str_list(data.get(key)))
                continue
            if segment_type in {"json", "xml"}:
                ids.extend(
                    self._extract_forward_ids_from_text(
                        _safe_str(data.get("data") or data.get("text") or data.get("content"))
                    )
                )

        raw_message = _safe_str(event.get("raw_message") or event.get("message"))
        ids.extend(self._extract_forward_ids_from_text(raw_message))
        return list(dict.fromkeys(item.strip() for item in ids if item and item.strip()))

    def _extract_forward_ids_from_text(self, text: str) -> list[str]:
        if not text:
            return []
        candidates = []
        current = text.strip()
        for _ in range(2):
            if current and current not in candidates:
                candidates.append(current)
            decoded = unquote(current)
            if decoded == current:
                break
            current = decoded

        ids: list[str] = []
        for candidate in candidates:
            lowered = candidate.lower()
            if not any(marker in lowered for marker in ("multimsg", "forward", "resid", "m_resid")):
                continue
            try:
                decoded_json = json.loads(candidate)
            except json.JSONDecodeError:
                decoded_json = None
            ids.extend(self._forward_ids_from_json(decoded_json))
            for match in re.finditer(
                r"""(?ix)
                ["']?(?:m_)?resid["']?\s*[:=]\s*["']?([^"',}\]\s]+)
                |["']?forward(?:_msg)?_id["']?\s*[:=]\s*["']?([^"',}\]\s]+)
                """,
                candidate,
            ):
                ids.append(_safe_str(match.group(1) or match.group(2)).strip())
        return list(dict.fromkeys(item for item in ids if item))

    def _forward_ids_from_json(self, value: Any) -> list[str]:
        ids: list[str] = []
        if isinstance(value, dict):
            for key, item in value.items():
                lowered_key = _safe_str(key).lower()
                if lowered_key in {"resid", "m_resid", "forward_id", "forward_msg_id"}:
                    ids.extend(_as_str_list(item))
                else:
                    ids.extend(self._forward_ids_from_json(item))
        elif isinstance(value, list):
            for item in value:
                ids.extend(self._forward_ids_from_json(item))
        return ids

    @staticmethod
    def _parse_cq_params(raw_params: str) -> dict[str, str]:
        return xinyu_qq_normalizer.parse_cq_params(raw_params)

    @staticmethod
    def _decode_cq_value(value: str) -> str:
        return xinyu_qq_normalizer.decode_cq_value(value)

    @staticmethod
    def _cq_bracket_continues_params(raw_message: str, bracket_index: int) -> bool:
        return xinyu_qq_normalizer.cq_bracket_continues_params(raw_message, bracket_index)

    @staticmethod
    def _parse_cq_segments(raw_message: str) -> list[dict[str, Any]]:
        return xinyu_qq_normalizer.parse_cq_segments(raw_message)

    @staticmethod
    def _strip_cq_segments(text: str) -> str:
        return xinyu_qq_normalizer.strip_cq_segments(text)

    def _parse_ws_message(self, raw_message: Any) -> dict[str, Any] | None:
        return xinyu_qq_normalizer.parse_ws_message(self, raw_message)

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
            trace_path.parent.mkdir(parents=True, exist_ok=True)
            with trace_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
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
            trace_path.parent.mkdir(parents=True, exist_ok=True)
            with trace_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
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
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(row, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
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
        if self._is_self_message_event(event, sender_id=sender_id, self_id=self_id):
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
        triggered, normalized_text, reason = self._group_trigger_result(event, text=text)
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
            trace_path.parent.mkdir(parents=True, exist_ok=True)
            with trace_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        except OSError as exc:
            print(f"[xinyu_qq_gateway] rich context trace write failed: {type(exc).__name__}: {exc}", flush=True)

    def prepare_message(self, event: dict[str, Any]) -> PreparedMessage | None:
        if not self.config.enabled:
            return None

        message_kind = self._message_kind(event)
        sender_id = _safe_str(event.get("user_id"), "unknown")
        self_id = _safe_str(event.get("self_id")).strip()
        group_id = _safe_str(event.get("group_id"), "")
        if self._is_self_message_event(event, sender_id=sender_id, self_id=self_id):
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

        if text and self._is_blocked_command(text):
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

        goldmark_command = self._extract_goldmark_command(text)
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

        review_command = self._extract_review_admin_command(text)
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

        return PreparedMessage(
            target=target,
            payload=self._build_chat_payload(event, target=target, text=text, rich_context=rich_context),
        )

    def _prepare_none_reason(self, event: dict[str, Any]) -> str:
        message_kind = self._message_kind(event)
        sender_id = _safe_str(event.get("user_id"), "unknown")
        self_id = _safe_str(event.get("self_id")).strip()
        group_id = _safe_str(event.get("group_id"), "")
        if self._is_self_message_event(event, sender_id=sender_id, self_id=self_id):
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
        if text and self._is_blocked_command(text):
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
            group_ok, normalized_text, reason = self._group_trigger_result(event, text=text)
            if not group_ok:
                return reason
            if not normalized_text.strip():
                return "group_trigger_empty_text"
        package_text = self._extract_package_install_command(text)
        if package_text is not None:
            if not self.config.package_install_enabled:
                return "package_install_disabled"
            if self.config.package_install_owner_private_only and (
                message_kind != "private" or sender_id not in self.config.owner_user_ids
            ):
                return "package_install_private_owner_only"
        codex_task = self._extract_codex_command(text)
        if codex_task is not None:
            if not self.config.codex_command_enabled:
                return "codex_command_disabled"
            if message_kind != "private":
                return "codex_private_only"
            if sender_id not in self.config.owner_user_ids:
                return "codex_owner_only"
        if self._is_passthrough_command(text):
            return "passthrough_command"
        return "prepare_none"

    @staticmethod
    def _is_self_message_event(event: dict[str, Any], *, sender_id: str, self_id: str) -> bool:
        return xinyu_qq_command_router.is_self_message_event(None, event, sender_id=sender_id, self_id=self_id)

    def _extract_goldmark_command(self, text: str) -> dict[str, str] | None:
        return xinyu_qq_command_router.extract_goldmark_command(self, text)

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

    def _extract_review_admin_command(self, text: str) -> dict[str, Any] | None:
        return xinyu_qq_command_router.extract_review_admin_command(self, text)

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

    def _message_kind(self, event: dict[str, Any]) -> str:
        return xinyu_qq_normalizer.message_kind(self, event)

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
            if segment_type not in RICH_CONTEXT_SEGMENT_TYPES:
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

    def _summarize_segment(self, segment_type: str, data: dict[str, Any]) -> dict[str, Any]:
        if segment_type == "reply":
            reply_id = (
                _safe_str(data.get("id")).strip()
                or _safe_str(data.get("message_id")).strip()
                or _safe_str(data.get("reply_id")).strip()
            )
            return {"kind": "reply", "id": reply_id, "summary": reply_id}
        if segment_type == "forward":
            forward_id = (
                _safe_str(data.get("id")).strip()
                or _safe_str(data.get("message_id")).strip()
                or _safe_str(data.get("forward_id")).strip()
                or _safe_str(data.get("forward_msg_id")).strip()
                or _safe_str(data.get("resid")).strip()
                or _safe_str(data.get("res_id")).strip()
            )
            return {"kind": "forward", "id": forward_id, "summary": forward_id or "merged_forward"}
        if segment_type in STICKER_SEGMENT_TYPES:
            summary = (
                _safe_str(data.get("summary")).strip()
                or _safe_str(data.get("text")).strip()
                or _safe_str(data.get("name")).strip()
                or _safe_str(data.get("id")).strip()
                or _safe_str(data.get("emoji_id")).strip()
                or segment_type
            )
            semantic = self._infer_received_sticker_semantics(summary)
            return {"kind": "sticker", "segment_type": segment_type, "summary": summary, **semantic}
        if segment_type == "image":
            if self._image_segment_looks_like_sticker(data):
                summary = (
                    _safe_str(data.get("summary")).strip()
                    or _safe_str(data.get("name")).strip()
                    or _safe_str(data.get("file")).strip()
                    or "image_sticker"
                )
                semantic = self._infer_received_sticker_semantics(summary)
                return {"kind": "sticker", "segment_type": "image", "summary": summary, **semantic}
            name = (
                _safe_str(data.get("summary")).strip()
                or _safe_str(data.get("name")).strip()
                or _safe_str(data.get("file")).strip()
                or "image"
            )
            return {"kind": "image", "segment_type": "image", "name": name, "summary": name}
        if segment_type in {"json", "xml"}:
            text = _safe_str(data.get("data") or data.get("text") or data.get("content")).strip()
            summary = text[:120] if text else segment_type
            return {"kind": segment_type, "segment_type": segment_type, "summary": summary}
        if segment_type == "at":
            qq = _safe_str(data.get("qq")).strip()
            return {"kind": "at", "segment_type": "at", "summary": qq}
        return {}

    @staticmethod
    def _infer_received_sticker_semantics(summary: str) -> dict[str, str]:
        text = _safe_str(summary).strip()
        lowered = text.lower()
        for mood, markers in RECEIVED_STICKER_MOOD_MARKERS.items():
            if any(marker.lower() in lowered or marker in text for marker in markers):
                return {
                    "mood": mood,
                    "meaning": RECEIVED_STICKER_MOOD_MEANING.get(mood, ""),
                    "confidence": "medium",
                }
        return {"mood": "unclear", "meaning": "QQ 只给了表情摘要，具体语气不确定", "confidence": "low"}

    @staticmethod
    def _image_segment_looks_like_sticker(data: dict[str, Any]) -> bool:
        compact = " ".join(
            _safe_str(data.get(key)).strip().lower()
            for key in ("summary", "subType", "sub_type", "type", "image_type", "name")
            if _safe_str(data.get(key)).strip()
        )
        if not compact:
            return False
        return any(marker in compact for marker in ("表情", "mface", "sticker", "marketface", "emoji"))

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

    def _extract_text(self, event: dict[str, Any]) -> str:
        return xinyu_qq_normalizer.extract_text(self, event)

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
        elif segment_type not in STICKER_SEGMENT_TYPES:
            return None
        return self._sticker_import_material_from_data(segment_type, data)

    def _sticker_import_material_from_data(self, segment_type: str, data: dict[str, Any]) -> dict[str, str] | None:
        name = (
            _safe_str(data.get("name")).strip()
            or _safe_str(data.get("file_name")).strip()
            or _safe_str(data.get("filename")).strip()
            or _safe_str(data.get("file")).strip()
            or _safe_str(data.get("summary")).strip()
            or _safe_str(data.get("text")).strip()
            or f"qq-{segment_type}-sticker"
        )
        url = (
            _safe_str(data.get("url")).strip()
            or _safe_str(data.get("file_url")).strip()
            or _safe_str(data.get("download_url")).strip()
        )
        path = (
            _safe_str(data.get("file_path")).strip()
            or _safe_str(data.get("path")).strip()
            or _safe_str(data.get("local_path")).strip()
        )
        file_value = _safe_str(data.get("file")).strip()
        file_id = (
            _safe_str(data.get("file_id")).strip()
            or _safe_str(data.get("fileId")).strip()
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
            "summary": _safe_str(data.get("summary") or data.get("text") or name).strip(),
            "url": url,
            "path": path,
            "file_id": file_id,
        }

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
        return xinyu_qq_normalizer.sender_name(self, event)

    def _group_trigger_result(self, event: dict[str, Any], *, text: str) -> tuple[bool, str, str]:
        return xinyu_qq_command_router.group_trigger_result(self, event, text=text)

    def _strip_group_trigger_prefix(self, text: str) -> tuple[bool, str]:
        return xinyu_qq_command_router.strip_group_trigger_prefix(self, text)

    def _bot_was_mentioned(self, event: dict[str, Any], *, text: str) -> bool:
        return xinyu_qq_command_router.bot_was_mentioned(self, event, text=text)

    def _is_passthrough_command(self, text: str) -> bool:
        return xinyu_qq_command_router.is_passthrough_command(self, text)

    def _is_blocked_command(self, text: str) -> bool:
        return xinyu_qq_command_router.is_blocked_command(self, text)

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

    def _extract_codex_command(self, text: str) -> str | None:
        return xinyu_qq_command_router.extract_codex_command(self, text)

    def _extract_package_install_command(self, text: str) -> str | None:
        return xinyu_qq_command_router.extract_package_install_command(self, text)

    def _extract_natural_language_package_install(self, text: str) -> str | None:
        return xinyu_qq_command_router.extract_natural_language_package_install(self, text)

    @staticmethod
    def _package_text_from_natural_language(text: str) -> str:
        return xinyu_qq_command_router.package_text_from_natural_language(text)

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

    async def send_image(
        self,
        websocket: Any,
        target: ReplyTarget,
        image_file: str,
        *,
        caption: str = "",
    ) -> dict[str, Any] | None:
        action = "send_group_msg" if target.message_kind == "group" else "send_private_msg"
        segments: list[dict[str, Any]] = [{"type": "image", "data": {"file": image_file}}]
        params: dict[str, Any] = {
            "message": segments,
            "auto_escape": False,
        }
        if target.message_kind == "group":
            params["group_id"] = _maybe_int(target.group_id)
        else:
            params["user_id"] = _maybe_int(target.user_id)
        return await self.send_action(websocket, action, params)

    async def send_file(
        self,
        websocket: Any,
        target: ReplyTarget,
        file_path: str,
        *,
        name: str,
    ) -> dict[str, Any] | None:
        action = "upload_group_file" if target.message_kind == "group" else "upload_private_file"
        params: dict[str, Any] = {
            "file": file_path,
            "name": name,
        }
        if target.message_kind == "group":
            params["group_id"] = _maybe_int(target.group_id)
        else:
            params["user_id"] = _maybe_int(target.user_id)
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
    _quiet_websockets_handshake_noise()

    args = _build_parser().parse_args()
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

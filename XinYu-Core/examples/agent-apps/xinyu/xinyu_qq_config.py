from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any


DEFAULT_CORE_BASE_URL = "http://127.0.0.1:8765"


def derive_core_route_url(core_chat_url: str, route: str) -> str:
    url = (core_chat_url or "").strip()
    if url:
        trimmed = url.rstrip("/")
        if trimmed.endswith("/chat"):
            return trimmed[: -len("/chat")] + route
    return DEFAULT_CORE_BASE_URL + route


def derive_codex_execute_url(core_chat_url: str) -> str:
    return derive_core_route_url(core_chat_url, "/codex/execute")


def derive_learning_ingest_url(core_chat_url: str) -> str:
    return derive_core_route_url(core_chat_url, "/learning/ingest")


def derive_sticker_import_url(core_chat_url: str) -> str:
    return derive_core_route_url(core_chat_url, "/sticker/import")


def derive_package_install_url(core_chat_url: str) -> str:
    return derive_core_route_url(core_chat_url, "/package/install")


def derive_review_inbox_command_url(core_chat_url: str) -> str:
    return derive_core_route_url(core_chat_url, "/review/inbox/command")


def derive_goldmark_mark_url(core_chat_url: str) -> str:
    return derive_core_route_url(core_chat_url, "/review/goldmark/mark_request")


def as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    if value is None:
        return default
    return bool(value)


def as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def as_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def as_str_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def env_str_list(*names: str) -> list[str]:
    values: list[str] = []
    for name in names:
        values.extend(as_str_list(os.environ.get(name)))
    return list(dict.fromkeys(values))


def merge_str_lists(*values: Any) -> list[str]:
    merged: list[str] = []
    for value in values:
        merged.extend(as_str_list(value))
    return list(dict.fromkeys(item for item in merged if item))


def with_required_prefixes(prefixes: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    values = [item for item in prefixes if item]
    for required in ("/", "!", "\uff01", "."):
        if required not in values:
            values.append(required)
    return tuple(dict.fromkeys(values))


def load_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


COMMAND_PREFIX_CHARS = "/!.！#"


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
    qq_file_learning_allowed_group_ids: frozenset[str] = frozenset()
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
    group_followup_window_seconds: int = 0
    group_followup_max_turns: int = 1
    group_shadow_enabled: bool = False
    group_shadow_allowed_group_ids: frozenset[str] = frozenset()
    group_shadow_max_text_chars: int = 260
    group_interest_reply_enabled: bool = False
    group_interest_reply_allowed_group_ids: frozenset[str] = frozenset()
    group_interest_reply_min_score: int = 7
    group_interest_reply_cooldown_seconds: int = 900
    group_interest_followup_max_turns: int = 2
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
    behavior_shadow_log_enabled: bool = False
    behavior_shadow_log_url: str = "http://127.0.0.1:8877/behavior_shadow_log"
    behavior_shadow_include_text: bool = False
    behavior_shadow_timeout_seconds: float = 1.0
    napcat_restart_bat: str = ""

    @classmethod
    def from_file(cls, path: Path) -> "GatewayConfig":
        raw = load_json_object(path)
        core_chat_url = _safe_str(raw.get("core_chat_url"), "http://127.0.0.1:8765/chat")
        bridge_token = _safe_str(raw.get("bridge_token"), "") or os.environ.get("XINYU_BRIDGE_TOKEN", "")
        codex_execute_url = _safe_str(raw.get("codex_execute_url"), "") or derive_codex_execute_url(core_chat_url)
        learning_ingest_url = _safe_str(raw.get("learning_ingest_url"), "") or derive_learning_ingest_url(core_chat_url)
        sticker_import_url = _safe_str(raw.get("sticker_import_url"), "") or derive_sticker_import_url(core_chat_url)
        package_install_url = _safe_str(raw.get("package_install_url"), "") or derive_package_install_url(core_chat_url)
        review_inbox_command_url = _safe_str(raw.get("review_inbox_command_url"), "") or derive_review_inbox_command_url(core_chat_url)
        goldmark_mark_url = _safe_str(raw.get("goldmark_mark_url"), "") or derive_goldmark_mark_url(core_chat_url)
        qq_outbox_claim_url = _safe_str(raw.get("qq_outbox_claim_url"), "") or derive_core_route_url(core_chat_url, "/qq/outbox/claim")
        qq_outbox_ack_url = _safe_str(raw.get("qq_outbox_ack_url"), "") or derive_core_route_url(core_chat_url, "/qq/outbox/ack")
        message_ack_url = _safe_str(raw.get("message_ack_url"), "") or derive_core_route_url(core_chat_url, "/internal/message/ack")
        gateway_ack_spool_path = _safe_str(raw.get("gateway_ack_spool_path"), "").strip()
        if not gateway_ack_spool_path:
            gateway_ack_spool_path = str(path.resolve().parent / "runtime/gateway_ack_spool.jsonl")
        prefixes = tuple(as_str_list(raw.get("group_trigger_prefixes")))
        prefixes = prefixes or ("心玉", "@心玉", "小心玉")
        if not prefixes:
            prefixes = ("心玉", "@心玉", "小心玉")
        return cls(
            enabled=as_bool(raw.get("enabled"), True),
            onebot_host=_safe_str(raw.get("onebot_host"), "127.0.0.1"),
            onebot_port=as_int(raw.get("onebot_port"), 6199),
            onebot_path=_safe_str(raw.get("onebot_path"), "/ws") or "/ws",
            core_chat_url=core_chat_url,
            bridge_token=bridge_token,
            codex_command_enabled=as_bool(raw.get("codex_command_enabled"), True),
            codex_execute_url=codex_execute_url,
            codex_command_prefixes=tuple(as_str_list(raw.get("codex_command_prefixes")) or ["/codex"]),
            codex_background=as_bool(raw.get("codex_background"), True),
            codex_auto_study=as_bool(raw.get("codex_auto_study"), True),
            codex_timeout_seconds=max(30, as_int(raw.get("codex_timeout_seconds"), 3600)),
            codex_visible_window=as_bool(raw.get("codex_visible_window"), True),
            codex_window_title=_safe_str(raw.get("codex_window_title"), "Xinyu codex").strip() or "Xinyu codex",
            codex_network_access=as_bool(raw.get("codex_network_access"), True),
            qq_outbox_enabled=as_bool(raw.get("qq_outbox_enabled"), True),
            qq_outbox_claim_url=qq_outbox_claim_url,
            qq_outbox_ack_url=qq_outbox_ack_url,
            message_ack_url=message_ack_url,
            gateway_ack_spool_path=gateway_ack_spool_path,
            review_inbox_command_url=review_inbox_command_url,
            goldmark_mark_url=goldmark_mark_url,
            qq_outbox_poll_seconds=max(2, as_int(raw.get("qq_outbox_poll_seconds"), 5)),
            qq_outbox_image_enabled=as_bool(raw.get("qq_outbox_image_enabled"), True),
            qq_outbox_file_enabled=as_bool(raw.get("qq_outbox_file_enabled"), True),
            learning_ingest_url=learning_ingest_url,
            sticker_import_url=sticker_import_url,
            qq_file_learning_enabled=as_bool(raw.get("qq_file_learning_enabled"), True),
            qq_file_learning_private_owner_only=as_bool(raw.get("qq_file_learning_private_owner_only"), True),
            qq_file_learning_allowed_group_ids=frozenset(as_str_list(raw.get("qq_file_learning_allowed_group_ids"))),
            qq_file_learning_stage=as_bool(raw.get("qq_file_learning_stage"), True),
            qq_file_learning_curated=as_bool(raw.get("qq_file_learning_curated"), True),
            qq_sticker_import_enabled=as_bool(raw.get("qq_sticker_import_enabled"), True),
            qq_sticker_import_private_owner_only=as_bool(raw.get("qq_sticker_import_private_owner_only"), True),
            qq_sticker_import_use_clip=as_bool(raw.get("qq_sticker_import_use_clip"), True),
            qq_sticker_import_use_ocr=as_bool(raw.get("qq_sticker_import_use_ocr"), True),
            package_install_enabled=as_bool(raw.get("package_install_enabled"), True),
            package_install_url=package_install_url,
            package_install_prefixes=tuple(as_str_list(raw.get("package_install_prefixes")) or ["/pkg", "/pip"]),
            package_install_owner_private_only=as_bool(raw.get("package_install_owner_private_only"), True),
            package_install_natural_language=as_bool(raw.get("package_install_natural_language"), True),
            timeout_seconds=max(5, as_int(raw.get("timeout_seconds"), 300)),
            require_whitelist=as_bool(raw.get("require_whitelist"), True),
            whitelist_user_ids=frozenset(
                merge_str_lists(
                    raw.get("whitelist_user_ids"),
                    env_str_list("XINYU_QQ_WHITELIST_USER_IDS", "XINYU_WHITELIST_USER_IDS"),
                )
            ),
            owner_user_ids=frozenset(
                merge_str_lists(raw.get("owner_user_ids"), env_str_list("XINYU_OWNER_USER_IDS"))
            ),
            trusted_user_ids=frozenset(
                merge_str_lists(
                    raw.get("trusted_user_ids"),
                    env_str_list("XINYU_QQ_TRUSTED_USER_IDS", "XINYU_TRUSTED_USER_IDS"),
                )
            ),
            blocked_user_ids=frozenset(as_str_list(raw.get("blocked_user_ids"))),
            blocked_group_ids=frozenset(as_str_list(raw.get("blocked_group_ids"))),
            private_only=as_bool(raw.get("private_only"), False),
            allow_group_messages=as_bool(raw.get("allow_group_messages"), True),
            allowed_group_ids=frozenset(as_str_list(raw.get("allowed_group_ids"))),
            group_trigger_mode=_safe_str(raw.get("group_trigger_mode"), "mention_or_prefix").strip().lower(),
            group_trigger_prefixes=prefixes,
            group_followup_window_seconds=max(0, min(600, as_int(raw.get("group_followup_window_seconds"), 0))),
            group_followup_max_turns=max(1, min(20, as_int(raw.get("group_followup_max_turns"), 1))),
            group_shadow_enabled=as_bool(raw.get("group_shadow_enabled"), False),
            group_shadow_allowed_group_ids=frozenset(as_str_list(raw.get("group_shadow_allowed_group_ids"))),
            group_shadow_max_text_chars=max(80, min(1000, as_int(raw.get("group_shadow_max_text_chars"), 260))),
            group_interest_reply_enabled=as_bool(raw.get("group_interest_reply_enabled"), False),
            group_interest_reply_allowed_group_ids=frozenset(
                as_str_list(raw.get("group_interest_reply_allowed_group_ids"))
            ),
            group_interest_reply_min_score=max(1, min(20, as_int(raw.get("group_interest_reply_min_score"), 7))),
            group_interest_reply_cooldown_seconds=max(
                0,
                min(86400, as_int(raw.get("group_interest_reply_cooldown_seconds"), 900)),
            ),
            group_interest_followup_max_turns=max(
                0,
                min(5, as_int(raw.get("group_interest_followup_max_turns"), 2)),
            ),
            ignore_prefixes=with_required_prefixes(as_str_list(raw.get("ignore_prefixes")) or ["/", "!", "！", "."]),
            blocked_commands=frozenset(
                item.lower() for item in (as_str_list(raw.get("blocked_commands")) or ["#napcat"])
            ),
            passthrough_commands=frozenset(
                item.strip().lstrip(COMMAND_PREFIX_CHARS).lower()
                for item in (as_str_list(raw.get("passthrough_commands")) or ["sid", "help", "xinyu_qq_status"])
                if item.strip().lstrip(COMMAND_PREFIX_CHARS)
            ),
            send_replies=as_bool(raw.get("send_replies"), True),
            show_bridge_errors=as_bool(raw.get("show_bridge_errors"), False),
            max_reply_chars=max(200, as_int(raw.get("max_reply_chars"), 3500)),
            reply_bubble_split_enabled=as_bool(raw.get("reply_bubble_split_enabled"), True),
            reply_bubble_private_only=as_bool(raw.get("reply_bubble_private_only"), False),
            reply_bubble_min_chars=max(40, as_int(raw.get("reply_bubble_min_chars"), 72)),
            reply_bubble_soft_max_chars=max(60, as_int(raw.get("reply_bubble_soft_max_chars"), 96)),
            reply_bubble_max_bubbles=max(2, min(5, as_int(raw.get("reply_bubble_max_bubbles"), 3))),
            reply_bubble_force_max_bubbles=max(2, min(20, as_int(raw.get("reply_bubble_force_max_bubbles"), 20))),
            reply_bubble_delay_seconds=max(0.0, min(3.0, as_float(raw.get("reply_bubble_delay_seconds"), 0.6))),
            owner_private_coalesce_seconds=max(0.0, min(5.0, as_float(raw.get("owner_private_coalesce_seconds"), 2.0))),
            owner_private_coalesce_max_fragments=max(2, as_int(raw.get("owner_private_coalesce_max_fragments"), 8)),
            behavior_shadow_log_enabled=as_bool(
                os.environ.get("XINYU_BEHAVIOR_SHADOW_LOG_ENABLED", raw.get("behavior_shadow_log_enabled")),
                False,
            ),
            behavior_shadow_log_url=(
                _safe_str(
                    os.environ.get("XINYU_BEHAVIOR_SHADOW_LOG_URL")
                    or os.environ.get("XINYU_BEHAVIOR_SHADOW_LOG_ENDPOINT")
                    or raw.get("behavior_shadow_log_url"),
                    "http://127.0.0.1:8877/behavior_shadow_log",
                ).strip()
                or "http://127.0.0.1:8877/behavior_shadow_log"
            ),
            behavior_shadow_include_text=as_bool(
                os.environ.get("XINYU_BEHAVIOR_SHADOW_INCLUDE_TEXT", raw.get("behavior_shadow_include_text")),
                False,
            ),
            behavior_shadow_timeout_seconds=max(
                0.1,
                min(
                    10.0,
                    as_float(
                        os.environ.get(
                            "XINYU_BEHAVIOR_SHADOW_TIMEOUT_SECONDS",
                            raw.get("behavior_shadow_timeout_seconds"),
                        ),
                        1.0,
                    ),
                ),
            ),
            napcat_restart_bat=_safe_str(
                os.environ.get("XINYU_NAPCAT_RESTART_BAT") or raw.get("napcat_restart_bat"), ""
            ).strip(),
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
        default_codex_url = derive_codex_execute_url(self.core_chat_url)
        codex_execute_url = self.codex_execute_url
        if core_chat_url and self.codex_execute_url == default_codex_url:
            codex_execute_url = derive_codex_execute_url(new_core_chat_url)
        default_learning_url = derive_learning_ingest_url(self.core_chat_url)
        learning_ingest_url = self.learning_ingest_url
        if core_chat_url and self.learning_ingest_url == default_learning_url:
            learning_ingest_url = derive_learning_ingest_url(new_core_chat_url)
        default_sticker_import_url = derive_sticker_import_url(self.core_chat_url)
        sticker_import_url = self.sticker_import_url
        if core_chat_url and self.sticker_import_url == default_sticker_import_url:
            sticker_import_url = derive_sticker_import_url(new_core_chat_url)
        default_package_url = derive_package_install_url(self.core_chat_url)
        package_install_url = self.package_install_url
        if core_chat_url and self.package_install_url == default_package_url:
            package_install_url = derive_package_install_url(new_core_chat_url)
        default_review_url = derive_review_inbox_command_url(self.core_chat_url)
        review_inbox_command_url = self.review_inbox_command_url
        if core_chat_url and self.review_inbox_command_url == default_review_url:
            review_inbox_command_url = derive_review_inbox_command_url(new_core_chat_url)
        default_goldmark_url = derive_goldmark_mark_url(self.core_chat_url)
        goldmark_mark_url = self.goldmark_mark_url
        if core_chat_url and self.goldmark_mark_url == default_goldmark_url:
            goldmark_mark_url = derive_goldmark_mark_url(new_core_chat_url)
        default_claim_url = derive_core_route_url(self.core_chat_url, "/qq/outbox/claim")
        default_ack_url = derive_core_route_url(self.core_chat_url, "/qq/outbox/ack")
        default_message_ack_url = derive_core_route_url(self.core_chat_url, "/internal/message/ack")
        qq_outbox_claim_url = self.qq_outbox_claim_url
        qq_outbox_ack_url = self.qq_outbox_ack_url
        message_ack_url = self.message_ack_url
        if core_chat_url and self.qq_outbox_claim_url == default_claim_url:
            qq_outbox_claim_url = derive_core_route_url(new_core_chat_url, "/qq/outbox/claim")
        if core_chat_url and self.qq_outbox_ack_url == default_ack_url:
            qq_outbox_ack_url = derive_core_route_url(new_core_chat_url, "/qq/outbox/ack")
        if core_chat_url and self.message_ack_url == default_message_ack_url:
            message_ack_url = derive_core_route_url(new_core_chat_url, "/internal/message/ack")
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
            qq_file_learning_allowed_group_ids=self.qq_file_learning_allowed_group_ids,
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
            group_followup_window_seconds=self.group_followup_window_seconds,
            group_followup_max_turns=self.group_followup_max_turns,
            group_shadow_enabled=self.group_shadow_enabled,
            group_shadow_allowed_group_ids=self.group_shadow_allowed_group_ids,
            group_shadow_max_text_chars=self.group_shadow_max_text_chars,
            group_interest_reply_enabled=self.group_interest_reply_enabled,
            group_interest_reply_allowed_group_ids=self.group_interest_reply_allowed_group_ids,
            group_interest_reply_min_score=self.group_interest_reply_min_score,
            group_interest_reply_cooldown_seconds=self.group_interest_reply_cooldown_seconds,
            group_interest_followup_max_turns=self.group_interest_followup_max_turns,
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
            behavior_shadow_log_enabled=self.behavior_shadow_log_enabled,
            behavior_shadow_log_url=self.behavior_shadow_log_url,
            behavior_shadow_include_text=self.behavior_shadow_include_text,
            behavior_shadow_timeout_seconds=self.behavior_shadow_timeout_seconds,
            napcat_restart_bat=self.napcat_restart_bat,
        )

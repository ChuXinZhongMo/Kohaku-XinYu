from __future__ import annotations

import re
from typing import Any


COMMAND_PREFIX_CHARS = "/!.！#"


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def is_self_message_event(gateway: Any, event: dict[str, Any], *, sender_id: str, self_id: str) -> bool:
    if not self_id:
        return False
    if sender_id == self_id:
        return True
    sender = event.get("sender")
    if isinstance(sender, dict) and _safe_str(sender.get("user_id")).strip() == self_id:
        return True
    return False


def extract_goldmark_command(gateway: Any, text: str) -> dict[str, str] | None:
    stripped = text.strip()
    if stripped.startswith("！"):
        stripped = "!" + stripped[1:].lstrip()
    lowered = stripped.lower()
    if lowered == "!mark":
        return {"owner_note": ""}
    if not lowered.startswith("!mark"):
        return None
    rest = stripped[len("!mark") :]
    separators = " \t\r\n:：,，、"
    if rest and rest[0] not in separators:
        return None
    return {"owner_note": rest.lstrip(separators).strip()}


def extract_review_admin_command(gateway: Any, text: str) -> dict[str, Any] | None:
    stripped = text.strip()
    if stripped.startswith("！"):
        stripped = "!" + stripped[1:].lstrip()
    if not stripped.startswith("!"):
        return None
    mod_match = re.match(r"(?is)^!mod\b(?:\s+(\d+)(?:\s+(.+))?)?\s*$", stripped)
    if mod_match:
        index = _safe_str(mod_match.group(1)).strip()
        mod_text = _safe_str(mod_match.group(2)).strip()
        return {
            "command": "mod",
            "indices": [index] if index else [],
            "mod_text": mod_text,
        }
    match = re.match(r"(?is)^!(ok|accept|approve|rej|reject|deny)\b(?:\s+(.+))?\s*$", stripped)
    if not match:
        return None
    raw_indices = _safe_str(match.group(2)).strip()
    if raw_indices.lower() == "all":
        indices: list[str] | str = "all"
    else:
        indices = [part for part in re.split(r"[\s,]+", raw_indices) if part]
    return {
        "command": match.group(1).lower(),
        "indices": indices,
        "mod_text": "",
    }


def extract_self_action_approval_command(gateway: Any, text: str) -> dict[str, str] | None:
    stripped = text.strip()
    if stripped.startswith("！"):
        stripped = "!" + stripped[1:].lstrip()
    normalized = stripped.replace("：", ":").strip()
    match = re.match(r"(?is)^/(?:sa|self-action|self_action)\s+(approve|approved|ok|accept|deny|denied|reject)\b(?:\s+([A-Za-z0-9:_./-]+))?(?:\s+(.+))?\s*$", normalized)
    if match:
        command = _safe_str(match.group(1)).lower()
        queue_id = _safe_str(match.group(2)).strip() or "latest"
        reason = _safe_str(match.group(3)).strip()
        return {
            "decision": "denied" if command in {"deny", "denied", "reject"} else "approved",
            "queue_id": queue_id,
            "reason": reason,
        }
    chinese_match = re.match(r"(?s)^(批准|同意|拒绝|否决)自行动作(?:\s+([A-Za-z0-9:_./-]+))?(?:\s+(.+))?\s*$", normalized)
    if chinese_match:
        command = _safe_str(chinese_match.group(1))
        queue_id = _safe_str(chinese_match.group(2)).strip() or "latest"
        reason = _safe_str(chinese_match.group(3)).strip()
        return {
            "decision": "denied" if command in {"拒绝", "否决"} else "approved",
            "queue_id": queue_id,
            "reason": reason,
        }
    return None


def extract_self_action_quote_approval_command(gateway: Any, text: str) -> dict[str, str] | None:
    del gateway
    stripped = re.sub(r"\s+", "", text.strip().lower())
    stripped = stripped.replace("！", "!").replace("：", ":")
    if not stripped:
        return None
    approve_markers = {
        "批准",
        "同意",
        "可以",
        "授权",
        "授权执行",
        "执行",
        "批准执行",
        "approve",
        "approved",
        "accept",
        "ok",
        "yes",
        "y",
    }
    deny_markers = {
        "拒绝",
        "否决",
        "不批准",
        "不同意",
        "别执行",
        "不要执行",
        "deny",
        "denied",
        "reject",
        "no",
        "n",
    }
    if stripped in deny_markers:
        return {"decision": "denied", "queue_id": "latest", "reason": "quoted_self_action_message"}
    if stripped in approve_markers:
        return {"decision": "approved", "queue_id": "latest", "reason": "quoted_self_action_message"}
    return None


def group_trigger_result(gateway: Any, event: dict[str, Any], *, text: str) -> tuple[bool, str, str]:
    group_id = _safe_str(event.get("group_id"), "")
    if gateway.config.allowed_group_ids and group_id not in gateway.config.allowed_group_ids:
        return False, text, "group_not_allowed"

    mode = gateway.config.group_trigger_mode or "mention_or_prefix"
    if mode in {"always", "all"}:
        return True, text, "group_always"

    mentioned = bot_was_mentioned(gateway, event, text=text)
    prefix_matched, stripped = strip_group_trigger_prefix(gateway, text)
    if mode in {"mention", "at"}:
        return (True, stripped or text, "group_mention") if mentioned else (False, text, "group_mention_required")
    if mode in {"prefix", "wake_prefix"}:
        return (True, stripped, "group_prefix") if prefix_matched else (False, text, "group_prefix_required")
    if mode in {"off", "disabled", "none"}:
        return False, text, "group_trigger_disabled"
    if mentioned or prefix_matched:
        return True, stripped if prefix_matched else text, "group_mention_or_prefix"
    return False, text, "group_trigger_required"


def strip_group_trigger_prefix(gateway: Any, text: str) -> tuple[bool, str]:
    stripped = text.strip()
    separators = " \t\r\n,，、。:：;；!！?？"
    for prefix in gateway.config.group_trigger_prefixes:
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


def bot_was_mentioned(gateway: Any, event: dict[str, Any], *, text: str) -> bool:
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
    lowered_names = {prefix.strip().lower().lstrip("@") for prefix in gateway.config.group_trigger_prefixes}
    lowered_text = text.lower()
    return any(f"@{name}" in lowered_text for name in lowered_names if name)


def is_passthrough_command(gateway: Any, text: str) -> bool:
    token = text.strip().split(maxsplit=1)[0].strip()
    command = token.lstrip(COMMAND_PREFIX_CHARS).lower()
    if command in gateway.config.passthrough_commands:
        return True
    if not gateway.config.ignore_prefixes or not token.startswith(gateway.config.ignore_prefixes):
        return False
    return bool(command) and command.isascii() and command.replace("_", "").isalnum()


def is_blocked_command(gateway: Any, text: str) -> bool:
    token = text.split(maxsplit=1)[0].strip().lower()
    if not token:
        return False
    bare = token.lstrip(COMMAND_PREFIX_CHARS)
    for command in gateway.config.blocked_commands:
        normalized = command.strip().lower()
        if token == normalized or bare == normalized.lstrip(COMMAND_PREFIX_CHARS):
            return True
    return False


def extract_codex_command(gateway: Any, text: str) -> str | None:
    stripped = text.strip()
    lowered = stripped.lower()
    separators = " \t\r\n:：,，"
    for prefix in gateway.config.codex_command_prefixes:
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


def extract_package_install_command(gateway: Any, text: str) -> str | None:
    stripped = text.strip()
    lowered = stripped.lower()
    separators = " \t\r\n:：,，"
    for prefix in gateway.config.package_install_prefixes:
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
    if not gateway.config.package_install_natural_language:
        return None
    return extract_natural_language_package_install(gateway, text)


def extract_natural_language_package_install(gateway: Any, text: str) -> str | None:
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
    return package_text_from_natural_language(text)


def package_text_from_natural_language(text: str) -> str:
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

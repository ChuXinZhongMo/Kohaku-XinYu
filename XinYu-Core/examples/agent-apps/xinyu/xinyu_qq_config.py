from __future__ import annotations

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

from __future__ import annotations


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

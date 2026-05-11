from __future__ import annotations

import os
import hashlib
from pathlib import Path
from urllib.parse import urlparse


TRUTHY = {"1", "true", "yes", "on"}


def env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in TRUTHY


def is_loopback_host(host: str) -> bool:
    normalized = (host or "").strip().lower()
    if normalized in {"", "localhost", "127.0.0.1", "::1"}:
        return True
    if normalized.startswith("127."):
        return True
    return False


def enforce_llm_http_guard() -> None:
    """Fail startup when an API key would be sent over silent plain HTTP."""
    api_key = os.environ.get("XINYU_API_KEY", "").strip()
    base_url = os.environ.get("XINYU_BASE_URL", "").strip()
    if not api_key or not base_url:
        return

    parsed = urlparse(base_url)
    if parsed.scheme.lower() != "http":
        return
    if env_truthy("XINYU_ALLOW_INSECURE_LLM_HTTP"):
        return
    raise RuntimeError(
        "XINYU_BASE_URL uses plain HTTP while XINYU_API_KEY is configured. "
        "Set XINYU_ALLOW_INSECURE_LLM_HTTP=1 only for an explicit local/test override, "
        "or switch XINYU_BASE_URL to HTTPS."
    )


def enforce_bridge_token_guard(host: str, token: str) -> None:
    if is_loopback_host(host):
        return
    if token.strip():
        return
    raise RuntimeError(
        "Non-loopback XinYu core bridge host requires a non-empty "
        "XINYU_BRIDGE_TOKEN or --bridge-token."
    )


def bridge_source_version(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("BRIDGE_VERSION"):
            continue
        _name, _eq, value = stripped.partition("=")
        return value.strip().strip('"').strip("'")
    return "unknown"


def source_file_digest(path: Path, *, length: int = 16) -> str:
    try:
        data = path.read_bytes()
    except OSError:
        return "unknown"
    digest = hashlib.sha256(data).hexdigest()
    return digest[: max(8, length)]


def source_files_digest(paths: list[Path] | tuple[Path, ...], *, length: int = 16) -> str:
    digest = hashlib.sha256()
    try:
        sorted_paths = sorted((path.resolve() for path in paths), key=lambda item: str(item).lower())
        for path in sorted_paths:
            digest.update(path.name.encode("utf-8", errors="replace"))
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    except OSError:
        return "unknown"
    return digest.hexdigest()[: max(8, length)]

from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlparse


def read_text_safe(path: Path) -> str:
    try:
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


def state_field(text: str, field: str, default: str = "") -> str:
    match = re.search(rf"(?m)^-\s+{re.escape(field)}:\s*(.*)$", text or "")
    if not match:
        return default
    return re.sub(r"\s+", " ", match.group(1).strip()) or default


def parse_iso(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def seconds_since_iso(value: str, *, default: float = 999999.0) -> float:
    parsed = parse_iso(value)
    if parsed is None:
        return default
    return max(0.0, (datetime.now().astimezone() - parsed).total_seconds())


def iso_from_timestamp(value: float) -> str:
    return datetime.fromtimestamp(value).astimezone().isoformat()


def payload_path(value: str) -> Path:
    text = value.strip()
    if text.lower().startswith("file://"):
        parsed = urlparse(text)
        path_text = parsed.path
        if os.name == "nt" and len(path_text) > 2 and path_text[0] == "/" and path_text[2] == ":":
            path_text = path_text[1:]
        return Path(unquote(path_text))
    return Path(text)

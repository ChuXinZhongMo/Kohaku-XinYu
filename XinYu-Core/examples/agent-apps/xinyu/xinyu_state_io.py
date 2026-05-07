from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Any


def read_text(path: Path, default: str = "") -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except OSError:
        return default


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def extract_value(text: str, field: str, default: str = "unknown") -> str:
    match = re.search(rf"(?m)^- {re.escape(field)}:\s*(.+)$", text)
    return match.group(1).strip() if match else default


def replace_field(text: str, field: str, value: Any) -> str:
    replacement = f"- {field}: {one_line(value)}"
    pattern = re.compile(rf"(?m)^- {re.escape(field)}:\s*.*$")
    if pattern.search(text):
        return pattern.sub(replacement, text, count=1)
    suffix = "" if text.endswith("\n") else "\n"
    return text + suffix + replacement + "\n"


def append_section(text: str, heading: str, body: str) -> str:
    section = f"{heading.rstrip()}\n{body.strip()}\n"
    if not text.strip():
        return section
    return text.rstrip() + "\n\n" + section


def one_line(value: Any, limit: int = 1000) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return (text[:limit] if limit > 0 else text) or "none"

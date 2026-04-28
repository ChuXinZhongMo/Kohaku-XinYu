"""Maintenance report writers."""

from __future__ import annotations

import json
from pathlib import Path

from ..storage.atomic import atomic_write_text
from ..types import JSONValue


def write_report(path: Path, title: str, payload: dict[str, JSONValue]) -> None:
    text = f"# {title}\n\n```json\n{json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)}\n```\n"
    atomic_write_text(path, text)


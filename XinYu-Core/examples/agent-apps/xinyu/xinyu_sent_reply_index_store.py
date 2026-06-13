from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from state_service import atomic_write_json
from state_service import read_json


def _empty_sent_reply_index() -> dict[str, Any]:
    return {"version": 1, "entries": []}


def read_sent_reply_index_data(path: Path) -> dict[str, Any]:
    data = read_json(Path(path), default=None)
    if not isinstance(data, dict):
        return _empty_sent_reply_index()
    if not isinstance(data.get("entries"), list):
        data["entries"] = []
    data.setdefault("version", 1)
    return data


def write_sent_reply_index_data(path: Path, data: dict[str, Any]) -> None:
    for attempt in range(6):
        try:
            atomic_write_json(Path(path), data, sort_keys=False, indent=2)
            return
        except PermissionError:
            if attempt >= 5:
                raise
            time.sleep(0.05 * (attempt + 1))

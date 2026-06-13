from __future__ import annotations

from pathlib import Path
from typing import Any

from state_service import append_jsonl


def append_proactive_lifecycle_trace_event(path: Path, payload: dict[str, Any]) -> None:
    append_jsonl(Path(path), payload, sort_keys=True)

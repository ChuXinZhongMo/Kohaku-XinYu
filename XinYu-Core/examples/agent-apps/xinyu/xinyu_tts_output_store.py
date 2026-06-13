from __future__ import annotations

from pathlib import Path
from typing import Any

from state_service import append_jsonl


def append_tts_output_trace(path: Path, row: dict[str, Any]) -> None:
    append_jsonl(path, row)

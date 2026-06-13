from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from state_service import atomic_write_json
from state_service import read_text_safe


def voice_trial_overlay_state_exists(path: Path) -> bool:
    return Path(path).exists()


def read_voice_trial_overlay_state(path: Path) -> dict[str, Any]:
    text = read_text_safe(Path(path), default="")
    if not text:
        return {}
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def write_voice_trial_overlay_state(path: Path, state: dict[str, Any]) -> None:
    atomic_write_json(Path(path), state, sort_keys=True, indent=2)

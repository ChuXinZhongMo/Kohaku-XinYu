from __future__ import annotations

from pathlib import Path

from state_service import atomic_write_text
from state_service import read_text_safe


RECENT_CONTEXT_REL = Path("memory/context/recent_context.md")
EMOTION_STATE_REL = Path("memory/emotions/current_state.md")
STATE_REL = Path("memory/context/current_life_posture.md")


def life_posture_recent_context_path(root: Path) -> Path:
    return Path(root) / RECENT_CONTEXT_REL


def life_posture_emotion_state_path(root: Path) -> Path:
    return Path(root) / EMOTION_STATE_REL


def life_posture_state_path(root: Path) -> Path:
    return Path(root) / STATE_REL


def read_life_posture_context_text(path: Path, *, limit: int = 1800) -> str:
    text = read_text_safe(Path(path), default="").strip()
    return text if len(text) <= limit else text[-limit:]


def write_life_posture_state_text(root: Path, text: str) -> None:
    atomic_write_text(life_posture_state_path(root), text, final_newline=False)

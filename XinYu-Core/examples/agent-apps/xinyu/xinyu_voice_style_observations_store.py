from __future__ import annotations

from pathlib import Path

from state_service import atomic_write_text


OBSERVATIONS_REL = Path("memory/self/voice_style_observations.md")


def voice_style_observations_path(root: Path) -> Path:
    return Path(root).resolve() / OBSERVATIONS_REL


def write_voice_style_observations_text(root: Path, text: str) -> Path:
    path = voice_style_observations_path(root)
    atomic_write_text(path, text, final_newline=False)
    return path

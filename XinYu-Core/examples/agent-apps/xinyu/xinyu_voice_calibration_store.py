from __future__ import annotations

from pathlib import Path

from state_service import atomic_write_text
from state_service import read_text_safe


VOICE_CALIBRATION_LOG_REL = Path("memory/self/voice_calibration_log.md")
VOICE_PROFILE_REVIEW_STATE_REL = Path("memory/self/voice_profile_review_state.md")


def voice_calibration_log_path(root: Path) -> Path:
    return Path(root) / VOICE_CALIBRATION_LOG_REL


def voice_profile_review_state_path(root: Path) -> Path:
    return Path(root) / VOICE_PROFILE_REVIEW_STATE_REL


def voice_calibration_text_exists(path: Path) -> bool:
    return Path(path).exists()


def read_voice_calibration_text(path: Path) -> str:
    return read_text_safe(Path(path), default="")


def write_voice_calibration_text(path: Path, text: str) -> None:
    atomic_write_text(Path(path), text.rstrip(), final_newline=True)

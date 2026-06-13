from __future__ import annotations

from pathlib import Path

from xinyu_voice_calibration_store import (
    VOICE_CALIBRATION_LOG_REL,
    VOICE_PROFILE_REVIEW_STATE_REL,
    read_voice_calibration_text,
    voice_calibration_log_path,
    voice_calibration_text_exists,
    voice_profile_review_state_path,
    write_voice_calibration_text,
)


def test_voice_calibration_store_reads_log_text_safely(tmp_path: Path) -> None:
    path = voice_calibration_log_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\ufeff# Voice Calibration\n", encoding="utf-8")

    assert path == tmp_path / VOICE_CALIBRATION_LOG_REL
    assert voice_calibration_text_exists(path) is True
    assert read_voice_calibration_text(path) == "# Voice Calibration\n"
    assert voice_calibration_text_exists(tmp_path / "missing.md") is False
    assert read_voice_calibration_text(tmp_path / "missing.md") == ""


def test_voice_calibration_store_writes_text_with_single_final_newline(tmp_path: Path) -> None:
    path = voice_profile_review_state_path(tmp_path)

    write_voice_calibration_text(path, "# Review\n\n")

    assert path == tmp_path / VOICE_PROFILE_REVIEW_STATE_REL
    assert path.read_text(encoding="utf-8") == "# Review\n"
    assert not (tmp_path / "memory/self/voice_profile_zh.md").exists()

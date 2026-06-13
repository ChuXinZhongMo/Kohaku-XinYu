from __future__ import annotations

from pathlib import Path

from xinyu_life_posture_store import (
    EMOTION_STATE_REL,
    RECENT_CONTEXT_REL,
    STATE_REL,
    life_posture_emotion_state_path,
    life_posture_recent_context_path,
    life_posture_state_path,
    read_life_posture_context_text,
    write_life_posture_state_text,
)


def test_life_posture_store_reads_bom_text_and_keeps_tail_limit(tmp_path: Path) -> None:
    path = life_posture_recent_context_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\ufeff0123456789", encoding="utf-8")

    assert path == tmp_path / RECENT_CONTEXT_REL
    assert read_life_posture_context_text(path, limit=4) == "6789"
    assert read_life_posture_context_text(tmp_path / "missing.md") == ""


def test_life_posture_store_paths_and_state_write(tmp_path: Path) -> None:
    assert life_posture_emotion_state_path(tmp_path) == tmp_path / EMOTION_STATE_REL

    write_life_posture_state_text(tmp_path, "# Current Life Posture\n- posture: hot_daily")

    path = life_posture_state_path(tmp_path)
    assert path == tmp_path / STATE_REL
    assert path.read_text(encoding="utf-8") == "# Current Life Posture\n- posture: hot_daily"

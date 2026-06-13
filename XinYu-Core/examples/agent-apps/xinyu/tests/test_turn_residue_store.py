from __future__ import annotations

from pathlib import Path

from xinyu_turn_residue_store import (
    STATE_REL,
    read_turn_residue_state,
    turn_residue_state_path,
    write_turn_residue_state,
)


def test_turn_residue_store_returns_none_for_missing_state(tmp_path: Path) -> None:
    assert read_turn_residue_state(tmp_path) is None


def test_turn_residue_store_reads_bom_and_writes_state_text(tmp_path: Path) -> None:
    path = turn_residue_state_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\ufeff- last_tone: guarded\n", encoding="utf-8")

    assert path == tmp_path / STATE_REL
    assert read_turn_residue_state(tmp_path) == "- last_tone: guarded\n"

    write_turn_residue_state(tmp_path, "# Persona Surface State\n- last_tone: compact")
    assert path.read_text(encoding="utf-8") == "# Persona Surface State\n- last_tone: compact"

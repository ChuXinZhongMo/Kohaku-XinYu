from __future__ import annotations

from pathlib import Path

from xinyu_thought_seeds_store import (
    DREAM_WEIGHT_REL,
    STATE_REL,
    read_thought_seed_text,
    read_thought_seeds_state,
    thought_seeds_source_path,
    thought_seeds_state_path,
    write_thought_seeds_state,
)


def test_thought_seeds_store_reads_source_text_safely(tmp_path: Path) -> None:
    path = thought_seeds_source_path(tmp_path, DREAM_WEIGHT_REL)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\ufeff- source_seed: dream-1\n", encoding="utf-8")

    assert path == tmp_path / DREAM_WEIGHT_REL
    assert read_thought_seed_text(path) == "- source_seed: dream-1\n"
    assert read_thought_seed_text(tmp_path / "missing.md") == ""


def test_thought_seeds_store_writes_state_text(tmp_path: Path) -> None:
    assert read_thought_seeds_state(tmp_path) == ""

    write_thought_seeds_state(tmp_path, "# Thought Seeds\n- seed_id: thought-seed-1")

    path = thought_seeds_state_path(tmp_path)
    assert path == tmp_path / STATE_REL
    assert path.read_text(encoding="utf-8") == "# Thought Seeds\n- seed_id: thought-seed-1"
    assert read_thought_seeds_state(tmp_path) == "# Thought Seeds\n- seed_id: thought-seed-1"

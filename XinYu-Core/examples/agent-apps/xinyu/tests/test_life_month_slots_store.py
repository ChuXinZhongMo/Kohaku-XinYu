from __future__ import annotations

from pathlib import Path

from xinyu_life_month_slots_store import (
    CURRENT_LIFE_MONTH_CONTEXT_REL,
    LIFE_MONTH_SLOTS_REL,
    current_life_month_context_path,
    life_month_slots_path,
    read_life_month_text,
    write_current_life_month_context,
)


def test_life_month_slots_store_reads_bom_text(tmp_path: Path) -> None:
    path = life_month_slots_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\ufeff- slot_count: 192\n", encoding="utf-8")

    assert path == tmp_path / LIFE_MONTH_SLOTS_REL
    assert read_life_month_text(path) == "- slot_count: 192\n"
    assert read_life_month_text(tmp_path / "missing.md") == ""


def test_life_month_slots_store_writes_current_context_text(tmp_path: Path) -> None:
    write_current_life_month_context(tmp_path, "# Current Life Month Context\n- current_month: 2026-04")

    path = current_life_month_context_path(tmp_path)
    assert path == tmp_path / CURRENT_LIFE_MONTH_CONTEXT_REL
    assert path.read_text(encoding="utf-8") == "# Current Life Month Context\n- current_month: 2026-04"

from __future__ import annotations

from pathlib import Path

from xinyu_memory_weights_store import (
    STATE_REL,
    memory_weight_spec_path,
    memory_weight_state_path,
    read_memory_weight_state,
    read_memory_weight_text,
    write_memory_weight_state,
)


def test_memory_weights_store_distinguishes_missing_from_empty_file(tmp_path: Path) -> None:
    missing = memory_weight_spec_path(tmp_path, "memory/self/missing.md")
    assert read_memory_weight_text(missing) is None

    empty = memory_weight_spec_path(tmp_path, "memory/self/empty.md")
    empty.parent.mkdir(parents=True, exist_ok=True)
    empty.write_text("", encoding="utf-8")
    assert read_memory_weight_text(empty) == ""


def test_memory_weights_store_reads_bom_text_and_writes_state(tmp_path: Path) -> None:
    spec = memory_weight_spec_path(tmp_path, "memory/self/core.md")
    spec.parent.mkdir(parents=True, exist_ok=True)
    spec.write_text("\ufeff---\nstatus: active\n---\n", encoding="utf-8")

    assert read_memory_weight_text(spec) == "---\nstatus: active\n---\n"
    assert read_memory_weight_state(tmp_path) == ""

    write_memory_weight_state(tmp_path, "# Memory Weight State\n- path: memory/self/core.md")
    state_path = memory_weight_state_path(tmp_path)
    assert state_path == tmp_path / STATE_REL
    assert state_path.read_text(encoding="utf-8") == "# Memory Weight State\n- path: memory/self/core.md"

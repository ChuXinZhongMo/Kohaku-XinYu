from __future__ import annotations

from pathlib import Path

from xinyu_bridge_renderer_debug_store import write_live_system_prompt_dump


def test_write_live_system_prompt_dump_uses_state_service_atomic_text_writer(tmp_path: Path) -> None:
    rel = Path("runtime/debug/last_live_system_prompt.txt")

    write_live_system_prompt_dump(tmp_path, rel, "PROMPT")

    path = tmp_path / rel
    assert path.read_text(encoding="utf-8") == "PROMPT"
    assert list(path.parent.glob(f".{path.name}.*.tmp")) == []

from __future__ import annotations

from pathlib import Path

from xinyu_stage8_memory_review_packet import PACKET_REL as MODULE_PACKET_REL
from xinyu_stage8_memory_review_packet import STATE_REL as MODULE_STATE_REL
from xinyu_stage8_memory_review_packet_store import PACKET_REL
from xinyu_stage8_memory_review_packet_store import STATE_REL
from xinyu_stage8_memory_review_packet_store import stage8_memory_review_packet_path
from xinyu_stage8_memory_review_packet_store import stage8_memory_review_packet_state_path
from xinyu_stage8_memory_review_packet_store import write_stage8_memory_review_packet_state_text
from xinyu_stage8_memory_review_packet_store import write_stage8_memory_review_packet_text


def test_stage8_memory_review_packet_store_exports_legacy_paths() -> None:
    assert PACKET_REL == MODULE_PACKET_REL
    assert STATE_REL == MODULE_STATE_REL
    assert PACKET_REL == Path("worklog/xinyu-stage8-memory-review-packet-latest.md")
    assert STATE_REL == Path("memory/context/stage8_memory_review_packet_state.md")


def test_stage8_memory_review_packet_store_writes_packet_with_output_resolution(tmp_path: Path) -> None:
    relative = write_stage8_memory_review_packet_text(tmp_path, "# Packet\n", output=Path("custom/packet.md"))
    absolute = write_stage8_memory_review_packet_text(tmp_path, "# Absolute\n", output=tmp_path / "abs.md")

    assert stage8_memory_review_packet_path(tmp_path) == tmp_path / PACKET_REL
    assert relative == tmp_path / "custom/packet.md"
    assert absolute == tmp_path / "abs.md"
    assert relative.read_text(encoding="utf-8") == "# Packet\n"
    assert absolute.read_text(encoding="utf-8") == "# Absolute\n"


def test_stage8_memory_review_packet_store_writes_state_text(tmp_path: Path) -> None:
    path = write_stage8_memory_review_packet_state_text(tmp_path, "# State\n- packet_status: ready\n")

    assert path == stage8_memory_review_packet_state_path(tmp_path)
    assert path == tmp_path / STATE_REL
    assert path.read_text(encoding="utf-8") == "# State\n- packet_status: ready\n"

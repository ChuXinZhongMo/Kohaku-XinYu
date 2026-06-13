from __future__ import annotations

import json
from pathlib import Path

from xinyu_stage8_duplicate_consolidation_packet import APPLY_TRACE_REL as MODULE_APPLY_TRACE_REL
from xinyu_stage8_duplicate_consolidation_packet import PACKET_REL as MODULE_PACKET_REL
from xinyu_stage8_duplicate_consolidation_packet import STATE_REL as MODULE_STATE_REL
from xinyu_stage8_duplicate_consolidation_packet_store import APPLY_TRACE_REL
from xinyu_stage8_duplicate_consolidation_packet_store import PACKET_REL
from xinyu_stage8_duplicate_consolidation_packet_store import STATE_REL
from xinyu_stage8_duplicate_consolidation_packet_store import append_stage8_duplicate_consolidation_apply_trace_event
from xinyu_stage8_duplicate_consolidation_packet_store import stage8_duplicate_consolidation_apply_trace_path
from xinyu_stage8_duplicate_consolidation_packet_store import stage8_duplicate_consolidation_packet_path
from xinyu_stage8_duplicate_consolidation_packet_store import stage8_duplicate_consolidation_state_path
from xinyu_stage8_duplicate_consolidation_packet_store import write_stage8_duplicate_consolidation_packet_text
from xinyu_stage8_duplicate_consolidation_packet_store import write_stage8_duplicate_consolidation_state_text


def test_stage8_duplicate_consolidation_store_exports_legacy_paths() -> None:
    assert PACKET_REL == MODULE_PACKET_REL
    assert STATE_REL == MODULE_STATE_REL
    assert APPLY_TRACE_REL == MODULE_APPLY_TRACE_REL
    assert PACKET_REL == Path("worklog/xinyu-stage8-duplicate-consolidation-latest.md")
    assert STATE_REL == Path("memory/context/stage8_duplicate_consolidation_state.md")
    assert APPLY_TRACE_REL == Path("runtime/stage8_duplicate_consolidation_apply_trace.jsonl")


def test_stage8_duplicate_consolidation_store_resolves_paths(tmp_path: Path) -> None:
    root = tmp_path.resolve()

    assert stage8_duplicate_consolidation_packet_path(tmp_path) == root / PACKET_REL
    assert stage8_duplicate_consolidation_packet_path(tmp_path, Path("custom/packet.md")) == root / "custom/packet.md"
    assert stage8_duplicate_consolidation_packet_path(tmp_path, tmp_path / "abs.md") == tmp_path / "abs.md"
    assert stage8_duplicate_consolidation_state_path(tmp_path) == root / STATE_REL
    assert stage8_duplicate_consolidation_apply_trace_path(tmp_path) == root / APPLY_TRACE_REL


def test_stage8_duplicate_consolidation_store_writes_packet_state_and_trace(tmp_path: Path) -> None:
    packet_path = write_stage8_duplicate_consolidation_packet_text(tmp_path, "# Packet\n")
    custom_path = write_stage8_duplicate_consolidation_packet_text(
        tmp_path,
        "# Custom\n",
        output=Path("custom/packet.md"),
    )
    state_path = write_stage8_duplicate_consolidation_state_text(tmp_path, "# State\n")
    trace_path = append_stage8_duplicate_consolidation_apply_trace_event(tmp_path, {"b": 2, "a": "value"})

    assert packet_path == tmp_path.resolve() / PACKET_REL
    assert custom_path == tmp_path.resolve() / "custom/packet.md"
    assert state_path == tmp_path.resolve() / STATE_REL
    assert trace_path == tmp_path.resolve() / APPLY_TRACE_REL
    assert packet_path.read_text(encoding="utf-8") == "# Packet\n"
    assert custom_path.read_text(encoding="utf-8") == "# Custom\n"
    assert state_path.read_text(encoding="utf-8") == "# State\n"
    assert json.loads(trace_path.read_text(encoding="utf-8")) == {"a": "value", "b": 2}
    assert trace_path.read_text(encoding="utf-8") == '{"a": "value", "b": 2}\n'

from __future__ import annotations

import json
from pathlib import Path

from xinyu_stage8_learning_trial_validation_packet import LEARNING_STATE_REL as MODULE_LEARNING_STATE_REL
from xinyu_stage8_learning_trial_validation_packet import LEARNING_TRACE_REL as MODULE_LEARNING_TRACE_REL
from xinyu_stage8_learning_trial_validation_packet import PACKET_REL as MODULE_PACKET_REL
from xinyu_stage8_learning_trial_validation_packet import STATE_REL as MODULE_STATE_REL
from xinyu_stage8_learning_trial_validation_packet_store import LEARNING_STATE_REL
from xinyu_stage8_learning_trial_validation_packet_store import LEARNING_TRACE_REL
from xinyu_stage8_learning_trial_validation_packet_store import PACKET_REL
from xinyu_stage8_learning_trial_validation_packet_store import STATE_REL
from xinyu_stage8_learning_trial_validation_packet_store import latest_stage8_learning_trial_validation_jsonl_row
from xinyu_stage8_learning_trial_validation_packet_store import read_stage8_learning_trial_validation_text
from xinyu_stage8_learning_trial_validation_packet_store import stage8_learning_trial_validation_learning_state_path
from xinyu_stage8_learning_trial_validation_packet_store import stage8_learning_trial_validation_learning_trace_path
from xinyu_stage8_learning_trial_validation_packet_store import stage8_learning_trial_validation_packet_path
from xinyu_stage8_learning_trial_validation_packet_store import stage8_learning_trial_validation_state_path
from xinyu_stage8_learning_trial_validation_packet_store import write_stage8_learning_trial_validation_packet_text
from xinyu_stage8_learning_trial_validation_packet_store import write_stage8_learning_trial_validation_state_text


def test_stage8_learning_trial_store_exports_legacy_paths() -> None:
    assert PACKET_REL == MODULE_PACKET_REL
    assert STATE_REL == MODULE_STATE_REL
    assert LEARNING_STATE_REL == MODULE_LEARNING_STATE_REL
    assert LEARNING_TRACE_REL == MODULE_LEARNING_TRACE_REL
    assert PACKET_REL == Path("worklog/xinyu-stage8-learning-trial-validation-latest.md")
    assert STATE_REL == Path("memory/context/stage8_learning_trial_validation_state.md")
    assert LEARNING_STATE_REL == Path("memory/self/learning_closed_loop_state.md")
    assert LEARNING_TRACE_REL == Path("runtime/learning_closed_loop_trace.jsonl")


def test_stage8_learning_trial_store_resolves_paths(tmp_path: Path) -> None:
    root = tmp_path.resolve()

    assert stage8_learning_trial_validation_packet_path(tmp_path) == root / PACKET_REL
    assert stage8_learning_trial_validation_packet_path(tmp_path, Path("custom/packet.md")) == root / "custom/packet.md"
    assert stage8_learning_trial_validation_packet_path(tmp_path, tmp_path / "abs.md") == tmp_path / "abs.md"
    assert stage8_learning_trial_validation_state_path(tmp_path) == root / STATE_REL
    assert stage8_learning_trial_validation_learning_state_path(tmp_path) == root / LEARNING_STATE_REL
    assert stage8_learning_trial_validation_learning_trace_path(tmp_path) == root / LEARNING_TRACE_REL


def test_stage8_learning_trial_store_reads_text_with_limit(tmp_path: Path) -> None:
    path = tmp_path / LEARNING_STATE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\ufeffabcdef", encoding="utf-8")

    assert read_stage8_learning_trial_validation_text(path, limit=3) == "abc"
    assert read_stage8_learning_trial_validation_text(tmp_path / "missing.md") == ""


def test_stage8_learning_trial_store_reads_latest_jsonl_row(tmp_path: Path) -> None:
    path = tmp_path / LEARNING_TRACE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    recent = {"event_id": "recent"}
    newest = {"event_id": "newest"}
    path.write_text(
        "\ufeff"
        + "\n".join(
            (
                json.dumps({"event_id": "old"}, ensure_ascii=False),
                json.dumps(recent, ensure_ascii=False),
                "{bad",
                "[\"not\", \"dict\"]",
                json.dumps(newest, ensure_ascii=False),
            )
        )
        + "\n",
        encoding="utf-8",
    )

    assert latest_stage8_learning_trial_validation_jsonl_row(path, max_lines=4) == newest
    assert latest_stage8_learning_trial_validation_jsonl_row(tmp_path / "missing.jsonl") == {}


def test_stage8_learning_trial_store_writes_packet_and_state(tmp_path: Path) -> None:
    packet_path = write_stage8_learning_trial_validation_packet_text(tmp_path, "# Packet\n")
    custom_path = write_stage8_learning_trial_validation_packet_text(
        tmp_path,
        "# Custom\n",
        output=Path("custom/packet.md"),
    )
    state_path = write_stage8_learning_trial_validation_state_text(tmp_path, "# State\n")

    assert packet_path == tmp_path.resolve() / PACKET_REL
    assert custom_path == tmp_path.resolve() / "custom/packet.md"
    assert state_path == tmp_path.resolve() / STATE_REL
    assert packet_path.read_text(encoding="utf-8") == "# Packet\n"
    assert custom_path.read_text(encoding="utf-8") == "# Custom\n"
    assert state_path.read_text(encoding="utf-8") == "# State\n"

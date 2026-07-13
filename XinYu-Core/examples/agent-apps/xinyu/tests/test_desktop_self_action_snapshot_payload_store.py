from __future__ import annotations

from pathlib import Path

from xinyu_bridge_stores import read_desktop_self_action_json_dict
from xinyu_bridge_stores import read_desktop_self_action_markdown_lines


def test_desktop_self_action_snapshot_payload_store_reads_json_dict(tmp_path: Path) -> None:
    path = tmp_path / "memory/context/self_action_gateway_state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"status":"active"}', encoding="utf-8")

    assert read_desktop_self_action_json_dict(path) == {"status": "active"}


def test_desktop_self_action_snapshot_payload_store_json_fallbacks(tmp_path: Path) -> None:
    path = tmp_path / "memory/context/self_action_gateway_state.json"

    assert read_desktop_self_action_json_dict(path) == {}

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{bad", encoding="utf-8")
    assert read_desktop_self_action_json_dict(path) == {}

    path.write_text('["not", "dict"]', encoding="utf-8")
    assert read_desktop_self_action_json_dict(path) == {}


def test_desktop_self_action_snapshot_payload_store_reads_markdown_lines(tmp_path: Path) -> None:
    path = tmp_path / "memory/context/self_action_gateway_execution_handoff.md"

    assert read_desktop_self_action_markdown_lines(path) == []

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("- status: ready\n", encoding="utf-8")

    assert read_desktop_self_action_markdown_lines(path) == ["- status: ready"]

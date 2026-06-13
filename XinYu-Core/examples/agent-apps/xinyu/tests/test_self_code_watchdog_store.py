from __future__ import annotations

import json
from pathlib import Path

from xinyu_self_code_watchdog_store import append_self_code_watchdog_trace
from xinyu_self_code_watchdog_store import copy_self_code_watchdog_file
from xinyu_self_code_watchdog_store import read_self_code_watchdog_bytes
from xinyu_self_code_watchdog_store import read_self_code_watchdog_manifest
from xinyu_self_code_watchdog_store import write_self_code_watchdog_bytes
from xinyu_self_code_watchdog_store import write_self_code_watchdog_json
from xinyu_self_code_watchdog_store import write_self_code_watchdog_text


def test_self_code_watchdog_store_text_json_and_trace(tmp_path: Path) -> None:
    text_path = tmp_path / "memory/context/self_code_watchdog_state.md"
    json_path = tmp_path / "runtime/self_code_watchdog/snapshots/s1/manifest.json"
    trace_path = tmp_path / "runtime/self_code_watchdog_trace.jsonl"

    write_self_code_watchdog_text(text_path, "state\n")
    write_self_code_watchdog_json(json_path, {"snapshot_id": "s1", "files": []})
    append_self_code_watchdog_trace(trace_path, {"event_kind": "snapshot_created", "snapshot_id": "s1"})

    assert text_path.read_text(encoding="utf-8") == "state\n"
    assert read_self_code_watchdog_manifest(json_path) == {"files": [], "snapshot_id": "s1"}
    assert json.loads(trace_path.read_text(encoding="utf-8").splitlines()[0]) == {
        "event_kind": "snapshot_created",
        "snapshot_id": "s1",
    }


def test_self_code_watchdog_store_bytes_and_copy(tmp_path: Path) -> None:
    backup = tmp_path / "snapshot/files/xinyu_core_bridge.py"
    target = tmp_path / "xinyu_core_bridge.py"

    write_self_code_watchdog_bytes(backup, b"version='snapshot'\n")
    copy_self_code_watchdog_file(backup, target)

    assert read_self_code_watchdog_bytes(target) == b"version='snapshot'\n"

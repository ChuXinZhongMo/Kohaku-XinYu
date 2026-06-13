from __future__ import annotations

import json
from pathlib import Path

from xinyu_self_code_approval_store import append_self_code_approval_trace
from xinyu_self_code_approval_store import read_self_code_approval_text
from xinyu_self_code_approval_store import write_self_code_approval_text


def test_self_code_approval_store_text_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "memory/context/self_code_approval_state.md"

    assert read_self_code_approval_text(path) == ""

    write_self_code_approval_text(path, "state\n")

    assert path.read_text(encoding="utf-8") == "state\n"
    assert read_self_code_approval_text(path) == "state\n"


def test_self_code_approval_store_appends_trace(tmp_path: Path) -> None:
    path = tmp_path / "runtime/self_code_approval_trace.jsonl"

    append_self_code_approval_trace(path, {"approval_id": "approval-1", "decision": "approved"})

    row = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert row == {"approval_id": "approval-1", "decision": "approved"}

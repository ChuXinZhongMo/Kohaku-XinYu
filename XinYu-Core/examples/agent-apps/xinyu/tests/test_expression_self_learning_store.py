from __future__ import annotations

import json
from pathlib import Path

from xinyu_expression_self_learning_store import append_expression_self_learning_trace
from xinyu_expression_self_learning_store import read_expression_self_learning_text
from xinyu_expression_self_learning_store import write_expression_self_learning_text


def test_expression_self_learning_store_text_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "memory/self/expression_self_learning_state.md"

    assert read_expression_self_learning_text(path) == ""

    write_expression_self_learning_text(path, "state\n")

    assert path.read_text(encoding="utf-8") == "state\n"
    assert read_expression_self_learning_text(path) == "state\n"


def test_expression_self_learning_store_appends_trace(tmp_path: Path) -> None:
    path = tmp_path / "runtime/expression_self_learning_trace.jsonl"

    append_expression_self_learning_trace(path, {"event_id": "expr-1", "source_request_created": True})

    row = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert row == {"event_id": "expr-1", "source_request_created": True}

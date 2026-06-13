from __future__ import annotations

import json
from datetime import datetime

from stores.state_service import append_jsonl
from stores.state_service import atomic_write_json
from stores.state_service import atomic_write_text
from stores.state_service import read_json
from stores.state_service import read_text_safe


def test_atomic_write_text_creates_parent_and_controls_final_newline(tmp_path) -> None:
    path = tmp_path / "nested/state.txt"

    atomic_write_text(path, "ready")
    assert path.read_text(encoding="utf-8") == "ready\n"

    atomic_write_text(path, "ready", final_newline=False)
    assert path.read_text(encoding="utf-8") == "ready"
    assert list(path.parent.glob(f".{path.name}.*.tmp")) == []


def test_atomic_write_json_sorts_keys_and_read_json_handles_utf8_sig(tmp_path) -> None:
    path = tmp_path / "state.json"

    atomic_write_json(path, {"b": 2, "a": 1}, indent=None)
    assert path.read_text(encoding="utf-8") == '{"a": 1, "b": 2}\n'
    assert read_json(path) == {"a": 1, "b": 2}

    path.write_bytes(b"\xef\xbb\xbf{\"ok\": true}")
    assert read_json(path) == {"ok": True}


def test_read_json_returns_default_for_missing_or_invalid_json(tmp_path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{bad", encoding="utf-8")

    assert read_json(tmp_path / "missing.json", default={"missing": True}) == {"missing": True}
    assert read_json(bad, default={"bad": True}) == {"bad": True}


def test_append_jsonl_writes_compact_sorted_json_and_stringifies_unknown_values(tmp_path) -> None:
    path = tmp_path / "trace/events.jsonl"
    observed_at = datetime(2026, 6, 9, 10, 30)

    append_jsonl(path, {"b": 2, "a": 1})
    append_jsonl(path, {"observed_at": observed_at})

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert rows == [
        {"a": 1, "b": 2},
        {"observed_at": "2026-06-09 10:30:00"},
    ]


def test_read_text_safe_uses_utf8_sig_replace_and_default(tmp_path) -> None:
    path = tmp_path / "state.md"
    path.write_bytes(b"\xef\xbb\xbfready")

    assert read_text_safe(path) == "ready"
    assert read_text_safe(tmp_path / "missing.md") == ""
    assert read_text_safe(tmp_path / "missing.md", default="fallback") == "fallback"

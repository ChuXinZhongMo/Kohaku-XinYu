from __future__ import annotations

import json
from pathlib import Path

import pytest

import xinyu_sent_reply_index_store as store
from xinyu_sent_reply_index import INDEX_REL
from xinyu_sent_reply_index import lookup_sent_reply_by_adapter_msg_id
from xinyu_sent_reply_index import register_sent_reply_ack
from xinyu_sent_reply_index_store import read_sent_reply_index_data
from xinyu_sent_reply_index_store import write_sent_reply_index_data


def test_sent_reply_index_store_reads_default_and_repairs_shape(tmp_path: Path) -> None:
    missing_path = tmp_path / INDEX_REL
    bad_path = tmp_path / "runtime/bad.json"
    list_path = tmp_path / "runtime/list.json"
    entries_path = tmp_path / "runtime/entries.json"

    assert read_sent_reply_index_data(missing_path) == {"version": 1, "entries": []}

    bad_path.parent.mkdir(parents=True, exist_ok=True)
    bad_path.write_text("{bad", encoding="utf-8")
    assert read_sent_reply_index_data(bad_path) == {"version": 1, "entries": []}

    list_path.write_text("[]", encoding="utf-8")
    assert read_sent_reply_index_data(list_path) == {"version": 1, "entries": []}

    entries_path.write_text('{"entries": "not-list", "updated_at": "now"}', encoding="utf-8")
    assert read_sent_reply_index_data(entries_path) == {
        "entries": [],
        "updated_at": "now",
        "version": 1,
    }


def test_sent_reply_index_store_writes_state_service_json(tmp_path: Path) -> None:
    path = tmp_path / INDEX_REL

    write_sent_reply_index_data(path, {"version": 1, "entries": [{"key": "k", "text": "你好"}]})

    text = path.read_text(encoding="utf-8")
    assert text.endswith("\n")
    assert json.loads(text) == {"version": 1, "entries": [{"key": "k", "text": "你好"}]}


def test_sent_reply_index_store_retries_transient_permission_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def flaky_write(path: Path, data: dict[str, object], *, sort_keys: bool, indent: int) -> None:
        nonlocal calls
        calls += 1
        assert sort_keys is False
        assert indent == 2
        if calls == 1:
            raise PermissionError("busy")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    monkeypatch.setattr(store, "atomic_write_json", flaky_write)
    monkeypatch.setattr(store.time, "sleep", lambda seconds: None)

    write_sent_reply_index_data(tmp_path / INDEX_REL, {"version": 1, "entries": []})

    assert calls == 2


def test_register_sent_reply_ack_uses_store_backed_index(tmp_path: Path) -> None:
    result = register_sent_reply_ack(
        tmp_path,
        {
            "adapter": "xinyu_native_qq_gateway",
            "adapter_message_id": "qq:caption-2",
            "route": "chat",
            "visible_text": "hello",
            "sent_at": "2026-01-01T08:00:00+08:00",
        },
    )

    lookup = lookup_sent_reply_by_adapter_msg_id(tmp_path, "caption-2")

    assert result["indexed"] is True
    assert lookup["found"] is True
    assert read_sent_reply_index_data(tmp_path / INDEX_REL)["entries"][0]["adapter_message_id"] == "qq:caption-2"

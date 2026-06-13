from __future__ import annotations

import json
from pathlib import Path

import pytest

import xinyu_gateway_ack_spool_store as store
from xinyu_gateway_ack_spool import SentAckSpool
from xinyu_gateway_ack_spool_store import append_gateway_ack_spool_event
from xinyu_gateway_ack_spool_store import gateway_ack_spool_file_size
from xinyu_gateway_ack_spool_store import read_gateway_ack_spool_events
from xinyu_gateway_ack_spool_store import write_gateway_ack_spool_events


def test_gateway_ack_spool_store_appends_and_reads_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "runtime/gateway_ack_spool.jsonl"

    append_gateway_ack_spool_event(path, {"event": "pending", "key": "k1", "payload": {"a": 1}})
    append_gateway_ack_spool_event(path, {"event": "acked", "key": "k1"})

    lines = path.read_text(encoding="utf-8").splitlines()
    events, line_count = read_gateway_ack_spool_events(path)

    assert lines == [
        '{"event":"pending","key":"k1","payload":{"a":1}}',
        '{"event":"acked","key":"k1"}',
    ]
    assert line_count == 2
    assert events == [
        {"event": "pending", "key": "k1", "payload": {"a": 1}},
        {"event": "acked", "key": "k1"},
    ]
    assert gateway_ack_spool_file_size(path) == path.stat().st_size


def test_gateway_ack_spool_store_ignores_invalid_jsonl(tmp_path: Path) -> None:
    path = tmp_path / "runtime/gateway_ack_spool.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('not-json\n{"event":"pending","key":"k1"}\n[]\n\n', encoding="utf-8")

    events, line_count = read_gateway_ack_spool_events(path)

    assert line_count == 4
    assert events == [{"event": "pending", "key": "k1"}]
    assert read_gateway_ack_spool_events(tmp_path / "missing.jsonl") == ([], 0)
    assert gateway_ack_spool_file_size(tmp_path / "missing.jsonl") is None


def test_gateway_ack_spool_store_rewrites_compacted_events(tmp_path: Path) -> None:
    path = tmp_path / "runtime/gateway_ack_spool.jsonl"

    write_gateway_ack_spool_events(path, [{"event": "pending", "key": "k1"}])

    assert [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()] == [
        {"event": "pending", "key": "k1"}
    ]

    write_gateway_ack_spool_events(path, [])

    assert path.read_text(encoding="utf-8") == ""


def test_sent_ack_spool_uses_store_for_append_read_and_compact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    appended: list[dict[str, object]] = []
    written: list[list[dict[str, object]]] = []

    def fake_append(path: Path, event: dict[str, object]) -> None:
        appended.append(event)
        store.append_gateway_ack_spool_event(path, event)

    def fake_write(path: Path, events: list[dict[str, object]]) -> None:
        written.append(events)
        store.write_gateway_ack_spool_events(path, events)

    monkeypatch.setattr("xinyu_gateway_ack_spool.append_gateway_ack_spool_event", fake_append)
    monkeypatch.setattr("xinyu_gateway_ack_spool.write_gateway_ack_spool_events", fake_write)
    spool = SentAckSpool(tmp_path / "runtime/gateway_ack_spool.jsonl")

    assert spool.append_pending({"adapter": "gateway", "adapter_message_id": "qq-1", "route": "chat"})["queued"]
    assert spool.append_acked({"adapter": "gateway", "adapter_message_id": "qq-1", "route": "chat"})["acked"]
    assert spool.pending_payloads() == []

    compacted = spool.compact()

    assert [event["event"] for event in appended] == ["pending", "acked"]
    assert compacted == {"compacted": True, "pending_count": 0}
    assert written == [[]]

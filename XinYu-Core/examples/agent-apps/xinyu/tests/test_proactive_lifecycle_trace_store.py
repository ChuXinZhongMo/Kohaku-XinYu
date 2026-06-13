from __future__ import annotations

import json
from pathlib import Path

import xinyu_proactive_lifecycle_trace as trace
from xinyu_proactive_lifecycle_trace import TRACE_REL
from xinyu_proactive_lifecycle_trace_store import append_proactive_lifecycle_trace_event


def test_proactive_lifecycle_trace_store_appends_sorted_jsonl(tmp_path: Path) -> None:
    path = tmp_path / TRACE_REL

    append_proactive_lifecycle_trace_event(path, {"b": 2, "a": 1})
    append_proactive_lifecycle_trace_event(path, {"event_kind": "next"})

    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines == ['{"a":1,"b":2}', '{"event_kind":"next"}']
    assert [json.loads(line) for line in lines] == [{"a": 1, "b": 2}, {"event_kind": "next"}]


def test_append_proactive_lifecycle_event_uses_store_payload(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[Path, dict[str, object]]] = []

    def fake_append(path: Path, payload: dict[str, object]) -> None:
        calls.append((path, payload))

    monkeypatch.setattr(trace, "append_proactive_lifecycle_trace_event", fake_append)

    trace.append_proactive_lifecycle_event(
        tmp_path,
        event_kind="Proactive Request Evaluated",
        event_time="2026-05-01T15:30:00+08:00",
        request_state="\n".join(
            [
                "- request_id: req-1",
                "- status: ready",
                "- kind: clarify",
                "- source: self_thought",
                "- focus_kind: active_question",
                "- concrete_question: Should I continue?",
            ]
        ),
        notes=["visible", ""],
    )

    assert calls[0][0] == tmp_path / TRACE_REL
    payload = calls[0][1]
    assert payload["event_kind"] == "proactive_request_evaluated"
    assert payload["event_time"] == "2026-05-01T15:30:00+08:00"
    assert payload["request_id"] == "req-1"
    assert payload["status"] == "ready"
    assert payload["kind"] == "clarify"
    assert payload["candidate_hash"] != "none"
    assert payload["notes"] == ["visible"]

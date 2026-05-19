from __future__ import annotations

import json
import time

from xinyu_bridge_route_observer import TurnRouteObserver


def test_turn_route_observer_records_stage_with_elapsed_and_notes(tmp_path) -> None:
    observer = TurnRouteObserver(
        tmp_path,
        turn_id="turn-observer-test",
        payload={
            "platform": "qq",
            "message_type": "private_text",
            "session_id": "session-1",
            "user_id": "user-1",
        },
        started_at=time.perf_counter(),
    )

    result = observer.record(
        "model_inject_started",
        route="slow_live",
        status="running",
        notes=["first", "second"],
    )

    assert result["ok"] is True
    trace_path = tmp_path / "runtime" / "turn_route_trace.jsonl"
    row = json.loads(trace_path.read_text(encoding="utf-8").splitlines()[-1])
    assert row["turn_id"] == "turn-observer-test"
    assert row["stage"] == "model_inject_started"
    assert row["route"] == "slow_live"
    assert row["status"] == "running"
    assert row["notes"] == ["first", "second"]
    assert row["elapsed_ms"] >= 0

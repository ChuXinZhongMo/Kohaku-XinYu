from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import xinyu_bridge_intervention_routes_status
from xinyu_bridge_intervention_routes import (
    turn_cancel,
    turn_continue,
    turn_current,
    turn_retry_lightweight,
    turn_status_message,
)
from xinyu_runtime_presence import record_turn_finished, record_turn_started
from xinyu_turn_route_trace import record_turn_route_stage


def _runtime(tmp_path):
    root = tmp_path / "xinyu"
    root.mkdir(parents=True)

    def health_snapshot():
        return {
            "operator": {
                "current_turn_state": "running",
                "route_stage": "model_inject_started",
                "route_status": "running",
            }
        }

    return SimpleNamespace(xinyu_dir=root, health_snapshot=health_snapshot)


def _payload() -> dict[str, object]:
    return {
        "platform": "qq",
        "message_type": "private_text",
        "session_id": "qq:private:owner",
        "user_id": "42",
        "metadata": {"is_owner_user": True},
    }


def _trace_rows(root):
    path = root / "runtime" / "turn_route_trace.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_turn_current_returns_safe_current_state(tmp_path) -> None:
    runtime = _runtime(tmp_path)
    started = record_turn_started(runtime.xinyu_dir, payload=_payload(), text="secret text", session_key="s", active_sessions=1)
    turn_id = started["turn_id"]
    record_turn_route_stage(
        runtime.xinyu_dir,
        turn_id=turn_id,
        stage="model_inject_started",
        route="slow_live",
        status="running",
        payload=_payload(),
        notes=["safe_note"],
    )

    result = asyncio.run(turn_current(runtime, {}))

    assert result["ok"] is True
    assert result["current_turn"]["turn_id"] == turn_id
    assert result["current_turn"]["state"] == "running"
    assert result["route"]["last_stage"] == "model_inject_started"
    assert result["operator"]["current_turn_state"] == "running"
    assert "secret text" not in json.dumps(result, ensure_ascii=False)


def test_turn_current_delegates_to_health_diagnostics_service(tmp_path, monkeypatch) -> None:
    runtime = _runtime(tmp_path)
    payload = {"ignored": True}
    calls: list[tuple[object, dict[str, object] | None, str]] = []

    class Service:
        @staticmethod
        async def turn_current(
            received_runtime: object,
            received_payload: dict[str, object] | None = None,
            *,
            current_turn_snapshot_func,
        ) -> dict[str, object]:
            assert callable(current_turn_snapshot_func)
            calls.append((received_runtime, received_payload, current_turn_snapshot_func.__name__))
            return {"route": "service_turn_current"}

    monkeypatch.setattr(xinyu_bridge_intervention_routes_status, "HealthDiagnosticsService", Service)

    result = asyncio.run(turn_current(runtime, payload))

    assert result == {"route": "service_turn_current"}
    assert calls == [(runtime, payload, "current_turn_snapshot")]


def test_turn_cancel_marks_running_turn_cancelled_and_traces_intervention(tmp_path) -> None:
    runtime = _runtime(tmp_path)
    started = record_turn_started(runtime.xinyu_dir, payload=_payload(), text="secret text", session_key="s", active_sessions=1)
    turn_id = started["turn_id"]

    result = asyncio.run(turn_cancel(runtime, {"reason": "owner"}))

    assert result["ok"] is True
    assert result["applied"] is True
    assert result["turn_id"] == turn_id
    current = asyncio.run(turn_current(runtime, {}))
    assert current["current_turn"]["state"] == "cancelled"
    rows = _trace_rows(runtime.xinyu_dir)
    assert any(row["stage"] == "intervention_requested" and row["notes"][0] == "cancel" for row in rows)
    assert any(row["stage"] == "intervention_applied" and row["notes"][0] == "cancel" for row in rows)


def test_turn_cancel_rejects_without_running_turn(tmp_path) -> None:
    runtime = _runtime(tmp_path)

    result = asyncio.run(turn_cancel(runtime, {}))

    assert result["ok"] is False
    assert result["reason"] == "no_running_turn"
    rows = _trace_rows(runtime.xinyu_dir)
    assert rows[-1]["stage"] == "intervention_rejected"
    assert rows[-1]["notes"] == ["cancel", "no_running_turn"]


def test_turn_retry_lightweight_rejects_non_timeout_without_force(tmp_path) -> None:
    runtime = _runtime(tmp_path)
    started = record_turn_started(runtime.xinyu_dir, payload=_payload(), text="secret", session_key="s", active_sessions=1)
    record_turn_route_stage(
        runtime.xinyu_dir,
        turn_id=started["turn_id"],
        stage="model_inject_started",
        route="slow_live",
        status="running",
        payload=_payload(),
    )

    result = asyncio.run(turn_retry_lightweight(runtime, {}))

    assert result["ok"] is False
    assert result["reason"] == "requires_timeout_stage_or_force"
    rows = _trace_rows(runtime.xinyu_dir)
    assert rows[-1]["stage"] == "intervention_rejected"
    assert rows[-1]["notes"] == ["retry_lightweight", "requires_timeout_stage_or_force"]


def test_turn_continue_applies_on_timeout_stage(tmp_path) -> None:
    runtime = _runtime(tmp_path)
    started = record_turn_started(runtime.xinyu_dir, payload=_payload(), text="secret", session_key="s", active_sessions=1)
    turn_id = started["turn_id"]
    record_turn_route_stage(
        runtime.xinyu_dir,
        turn_id=turn_id,
        stage="finish_sidecars_timeout",
        route="slow_live",
        status="timeout",
        payload=_payload(),
        notes=["finish_sidecars_timeout"],
    )

    result = asyncio.run(turn_continue(runtime, {}))

    assert result["ok"] is True
    assert result["applied"] is True
    assert result["turn_id"] == turn_id
    rows = _trace_rows(runtime.xinyu_dir)
    assert rows[-1]["stage"] == "intervention_applied"
    assert rows[-1]["notes"] == ["continue", "operator_action_recorded"]


def test_turn_status_message_is_safe_and_read_only(tmp_path) -> None:
    runtime = _runtime(tmp_path)
    started = record_turn_started(runtime.xinyu_dir, payload=_payload(), text="secret", session_key="s", active_sessions=1)
    record_turn_finished(
        runtime.xinyu_dir,
        turn_id=started["turn_id"],
        reply="hidden reply",
        elapsed_ms=10,
        status="ok",
        notes=["done"],
    )

    result = asyncio.run(turn_status_message(runtime, {}))

    assert result["ok"] is True
    assert "secret" not in result["message"]
    assert "hidden reply" not in json.dumps(result, ensure_ascii=False)

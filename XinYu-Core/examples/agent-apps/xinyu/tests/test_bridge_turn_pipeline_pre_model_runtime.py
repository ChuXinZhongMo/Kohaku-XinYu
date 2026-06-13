from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import xinyu_bridge_turn_pipeline
from xinyu_bridge_turn_pipeline import (
    PreModelRouteResult,
    capture_memory_snapshot_with_trace,
    probe_semantic_fast_decision_with_trace,
    publish_chat_started_with_trace,
    run_pre_model_observation_sidecars_with_trace,
    run_pre_model_phase_with_trace,
    run_pre_model_routes,
    run_pre_model_routes_with_timeout,
    start_chat_turn_with_trace,
    try_initial_semantic_fast_route_with_trace,
    try_pre_slow_semantic_fast_route_with_trace,
)


def _base_kwargs(trace_rows: list[dict[str, object]], *, timeout_seconds: float = 1.0) -> dict[str, object]:
    def trace_route_stage(stage: str, **kwargs) -> None:
        trace_rows.append({"stage": stage, **kwargs})

    return {
        "text": "hello",
        "session_key": "qq:private:owner",
        "turn_id": "turn-pre-model-test",
        "turn_started_wall": "2026-05-20T12:00:00+08:00",
        "turn_started_at": 0.0,
        "before_memory": {},
        "cleanup": {"cleaned_sessions": 0},
        "timeout_seconds": timeout_seconds,
        "trace_route_stage": trace_route_stage,
    }


def test_run_pre_model_routes_with_timeout_returns_success_and_traces_ok() -> None:
    trace_rows: list[dict[str, object]] = []

    async def runner(*args, **kwargs):
        del args, kwargs
        return PreModelRouteResult(
            response={"accepted": True, "notes": ["pre_model_response"]},
            event_sidecar={"notes": ["event_ok"]},
            v1_shadow={"notes": ["v1_ok"]},
            tinykernel_shadow={"notes": ["tiny_ok"]},
        )

    result = asyncio.run(
        run_pre_model_routes_with_timeout(
            SimpleNamespace(),
            {"platform": "qq"},
            runner=runner,
            **_base_kwargs(trace_rows),
        )
    )

    assert result.response == {"accepted": True, "notes": ["pre_model_response"]}
    assert trace_rows[0]["stage"] == "pre_model_routes_started"
    assert trace_rows[-1] == {"stage": "pre_model_routes_finished", "status": "ok"}


def test_run_pre_model_phase_with_trace_publishes_and_returns_fallthrough(monkeypatch) -> None:
    trace_rows: list[dict[str, object]] = []
    calls: list[tuple[str, object]] = []

    def trace_route_stage(stage: str, **kwargs) -> None:
        trace_rows.append({"stage": stage, **kwargs})

    async def fake_publish(runtime, payload, **kwargs) -> bool:
        calls.append(("publish", {"payload": payload, **kwargs}))
        return True

    def fake_snapshot(runtime, **kwargs) -> dict[str, object]:
        calls.append(("snapshot", kwargs))
        return {"memory": "before"}

    def fake_observations(runtime, payload, **kwargs) -> dict[str, dict[str, object]]:
        calls.append(("observations", {"payload": payload, **kwargs}))
        return {
            "curiosity_eval": {"notes": ["curiosity"]},
            "private_thought_outcome": {"notes": ["private"]},
            "uncertainty_pause_reply": {"notes": ["pause"]},
        }

    async def fake_routes(runtime, payload, **kwargs) -> PreModelRouteResult:
        calls.append(("routes", {"payload": payload, **kwargs}))
        return PreModelRouteResult(
            response=None,
            event_sidecar={"notes": ["event"]},
            v1_shadow={"notes": ["v1"]},
            tinykernel_shadow={"notes": ["tiny"]},
        )

    monkeypatch.setattr(xinyu_bridge_turn_pipeline, "publish_chat_started_with_trace", fake_publish)
    monkeypatch.setattr(xinyu_bridge_turn_pipeline, "capture_memory_snapshot_with_trace", fake_snapshot)
    monkeypatch.setattr(xinyu_bridge_turn_pipeline, "run_pre_model_observation_sidecars_with_trace", fake_observations)
    monkeypatch.setattr(xinyu_bridge_turn_pipeline, "run_pre_model_routes_with_timeout", fake_routes)

    result = asyncio.run(
        run_pre_model_phase_with_trace(
            SimpleNamespace(_sessions={"s": object()}),
            {"platform": "qq"},
            text="hello",
            session_key="qq:private:owner",
            turn_id="turn-1",
            turn_started_wall="2026-05-20T12:00:00+08:00",
            turn_started_at=12.5,
            cleanup={"cleaned_sessions": 0},
            desktop_started_published=False,
            timeout_seconds=0.5,
            trace_route_stage=trace_route_stage,
        )
    )

    assert isinstance(result, xinyu_bridge_turn_pipeline.PreModelPhaseState)
    assert result == {
        "response": None,
        "desktop_started_published": True,
        "before_memory": {"memory": "before"},
        "curiosity_eval": {"notes": ["curiosity"]},
        "private_thought_outcome": {"notes": ["private"]},
        "uncertainty_pause_reply": {"notes": ["pause"]},
        "event_sidecar": {"notes": ["event"]},
        "v1_shadow": {"notes": ["v1"]},
        "tinykernel_shadow": {"notes": ["tiny"]},
    }
    assert [name for name, _ in calls] == ["publish", "snapshot", "observations", "routes"]
    assert calls[0][1]["active_sessions"] == 1
    assert calls[3][1]["before_memory"] == {"memory": "before"}
    assert calls[3][1]["runner"] is xinyu_bridge_turn_pipeline.run_pre_model_routes
    assert trace_rows == []


def test_run_pre_model_phase_with_trace_returns_response_and_records_finish(monkeypatch) -> None:
    trace_rows: list[dict[str, object]] = []
    calls: list[tuple[str, object]] = []

    def trace_route_stage(stage: str, **kwargs) -> None:
        trace_rows.append({"stage": stage, **kwargs})

    async def fake_publish(*args, **kwargs) -> bool:
        calls.append(("publish", kwargs))
        return True

    async def fake_routes(*args, **kwargs) -> PreModelRouteResult:
        calls.append(("routes", kwargs))
        return PreModelRouteResult(
            response={"accepted": True, "notes": ["n1", "n2", "n3", "n4", "n5", "n6", "n7", "n8", "drop"]},
            event_sidecar={"notes": ["event"]},
            v1_shadow={"notes": ["v1"]},
        )

    monkeypatch.setattr(xinyu_bridge_turn_pipeline, "publish_chat_started_with_trace", fake_publish)
    monkeypatch.setattr(
        xinyu_bridge_turn_pipeline,
        "capture_memory_snapshot_with_trace",
        lambda *args, **kwargs: {"memory": "before"},
    )
    monkeypatch.setattr(
        xinyu_bridge_turn_pipeline,
        "run_pre_model_observation_sidecars_with_trace",
        lambda *args, **kwargs: {
            "curiosity_eval": {"notes": []},
            "private_thought_outcome": {"notes": []},
            "uncertainty_pause_reply": {"notes": []},
        },
    )
    monkeypatch.setattr(xinyu_bridge_turn_pipeline, "run_pre_model_routes_with_timeout", fake_routes)

    result = asyncio.run(
        run_pre_model_phase_with_trace(
            SimpleNamespace(_sessions={}),
            {"platform": "qq"},
            text="hello",
            session_key="qq:private:owner",
            turn_id="turn-1",
            turn_started_wall="2026-05-20T12:00:00+08:00",
            turn_started_at=12.5,
            cleanup={},
            desktop_started_published=True,
            timeout_seconds=0.5,
            trace_route_stage=trace_route_stage,
        )
    )

    assert isinstance(result, xinyu_bridge_turn_pipeline.PreModelPhaseState)
    assert result["response"] == {
        "accepted": True,
        "notes": ["n1", "n2", "n3", "n4", "n5", "n6", "n7", "n8", "drop"],
    }
    assert [name for name, _ in calls] == ["routes"]
    assert trace_rows == [
        {
            "stage": "route_finished",
            "route": "pre_model",
            "status": "ok",
            "notes": ["n1", "n2", "n3", "n4", "n5", "n6", "n7", "n8"],
        }
    ]


def test_start_chat_turn_with_trace_records_presence_and_starts_observer(monkeypatch, tmp_path: Path) -> None:
    rows: list[dict[str, object]] = []
    calls: list[dict[str, object]] = []

    def record_started(root: Path, **kwargs) -> dict[str, object]:
        calls.append({"call": "record", "root": root, **kwargs})
        return {"turn_id": "turn-1", "notes": ["note-1", "note-2", "note-3", "note-4", "drop"]}

    class Observer:
        def __init__(self, root: Path, **kwargs) -> None:
            calls.append({"call": "observer", "root": root, **kwargs})

        def record(self, stage: str, **kwargs) -> None:
            rows.append({"stage": stage, **kwargs})

    monkeypatch.setattr(xinyu_bridge_turn_pipeline, "record_turn_started", record_started)
    monkeypatch.setattr(xinyu_bridge_turn_pipeline, "TurnRouteObserver", Observer)
    runtime = SimpleNamespace(xinyu_dir=tmp_path, _sessions={"a": object(), "b": object()})
    payload = {"platform": "qq"}

    result = start_chat_turn_with_trace(
        runtime,
        payload,
        text="hello",
        session_key="qq:private:owner",
        turn_started_at=12.5,
    )

    assert isinstance(result, xinyu_bridge_turn_pipeline.ChatTurnStartState)
    assert result["presence_start"] == {
        "turn_id": "turn-1",
        "notes": ["note-1", "note-2", "note-3", "note-4", "drop"],
    }
    assert result["turn_id"] == "turn-1"
    assert result["trace_route_stage"] == result["trace_route_stage"]
    assert calls == [
        {
            "call": "record",
            "root": tmp_path,
            "payload": payload,
            "text": "hello",
            "session_key": "qq:private:owner",
            "active_sessions": 2,
        },
        {
            "call": "observer",
            "root": tmp_path,
            "turn_id": "turn-1",
            "payload": payload,
            "started_at": 12.5,
        },
    ]
    assert rows == [
        {
            "stage": "turn_started",
            "elapsed_ms": 0,
            "notes": ["note-1", "note-2", "note-3", "note-4"],
        }
    ]


def test_capture_memory_snapshot_with_trace_records_trace(monkeypatch, tmp_path: Path) -> None:
    trace_rows: list[dict[str, object]] = []
    calls: list[Path] = []

    def trace_route_stage(stage: str, **kwargs) -> None:
        trace_rows.append({"stage": stage, **kwargs})

    def snapshot(root: Path) -> dict[str, object]:
        calls.append(root)
        return {"memory": "snapshot"}

    monkeypatch.setattr(xinyu_bridge_turn_pipeline, "_memory_snapshot", snapshot)

    result = capture_memory_snapshot_with_trace(
        SimpleNamespace(memory_root=tmp_path),
        trace_route_stage=trace_route_stage,
    )

    assert result == {"memory": "snapshot"}
    assert calls == [tmp_path]
    assert trace_rows == [
        {"stage": "memory_snapshot_started"},
        {"stage": "memory_snapshot_finished", "status": "ok"},
    ]


def test_publish_chat_started_with_trace_publishes_and_records_route() -> None:
    trace_rows: list[dict[str, object]] = []
    calls: list[dict[str, object]] = []

    def trace_route_stage(stage: str, **kwargs) -> None:
        trace_rows.append({"stage": stage, **kwargs})

    async def publish(payload: dict[str, object], **kwargs) -> None:
        calls.append({"payload": payload, **kwargs})

    runtime = SimpleNamespace(_desktop_publish_chat_started=publish)

    result = asyncio.run(
        publish_chat_started_with_trace(
            runtime,
            {"platform": "qq"},
            text="hello",
            session_key="qq:private:owner",
            turn_id="turn-1",
            turn_started_wall="2026-05-20T12:00:00+08:00",
            active_sessions=3,
            trace_route_stage=trace_route_stage,
            route="owner_private_semantic_fast",
        )
    )

    assert result is True
    assert calls == [
        {
            "payload": {"platform": "qq"},
            "text": "hello",
            "session_key": "qq:private:owner",
            "turn_id": "turn-1",
            "started_at": "2026-05-20T12:00:00+08:00",
            "active_sessions": 3,
        }
    ]
    assert trace_rows == [
        {"stage": "desktop_started_publish_started", "route": "owner_private_semantic_fast"},
        {
            "stage": "desktop_started_publish_finished",
            "route": "owner_private_semantic_fast",
            "status": "ok",
        },
    ]


def test_publish_chat_started_with_trace_contains_publish_error() -> None:
    trace_rows: list[dict[str, object]] = []

    def trace_route_stage(stage: str, **kwargs) -> None:
        trace_rows.append({"stage": stage, **kwargs})

    async def publish(*args, **kwargs) -> None:
        raise RuntimeError("boom")

    runtime = SimpleNamespace(_desktop_publish_chat_started=publish)

    result = asyncio.run(
        publish_chat_started_with_trace(
            runtime,
            {"platform": "qq"},
            text="hello",
            session_key="qq:private:owner",
            turn_id="turn-1",
            turn_started_wall="2026-05-20T12:00:00+08:00",
            active_sessions=3,
            trace_route_stage=trace_route_stage,
            timeout_seconds=0.01,
        )
    )

    assert result is False
    assert trace_rows == [
        {"stage": "desktop_started_publish_started"},
        {
            "stage": "desktop_started_publish_finished",
            "status": "error",
            "notes": ["desktop_publish_error:RuntimeError"],
        },
    ]


def test_probe_semantic_fast_decision_with_trace_returns_decision_and_traces() -> None:
    trace_rows: list[dict[str, object]] = []
    calls: list[dict[str, object]] = []

    def trace_route_stage(stage: str, **kwargs) -> None:
        trace_rows.append({"stage": stage, **kwargs})

    def semantic_decision(payload: dict[str, object], text: str) -> dict[str, object]:
        calls.append({"payload": payload, "text": text})
        return {"allowed": True, "notes": ["note-1", "note-2", "note-3", "note-4", "drop"]}

    payload = {"platform": "qq"}
    result = probe_semantic_fast_decision_with_trace(
        SimpleNamespace(_owner_private_semantic_fast_decision=semantic_decision),
        payload,
        text="hello",
        trace_route_stage=trace_route_stage,
    )

    assert result == {"allowed": True, "notes": ["note-1", "note-2", "note-3", "note-4", "drop"]}
    assert calls == [{"payload": payload, "text": "hello"}]
    assert trace_rows == [
        {"stage": "semantic_fast_probe_started"},
        {
            "stage": "semantic_fast_probe_finished",
            "status": "allowed",
            "notes": ["note-1", "note-2", "note-3", "note-4"],
        },
    ]


def test_probe_semantic_fast_decision_with_trace_contains_errors() -> None:
    trace_rows: list[dict[str, object]] = []

    def trace_route_stage(stage: str, **kwargs) -> None:
        trace_rows.append({"stage": stage, **kwargs})

    def semantic_decision(payload: dict[str, object], text: str) -> dict[str, object]:
        del payload, text
        raise RuntimeError("boom")

    result = probe_semantic_fast_decision_with_trace(
        SimpleNamespace(_owner_private_semantic_fast_decision=semantic_decision),
        {"platform": "qq"},
        text="hello",
        trace_route_stage=trace_route_stage,
    )

    assert result == {"allowed": False, "notes": ["semantic_fast_probe_error:RuntimeError"]}
    assert trace_rows == [
        {"stage": "semantic_fast_probe_started"},
        {
            "stage": "semantic_fast_probe_finished",
            "status": "error",
            "notes": ["semantic_fast_probe_error:RuntimeError"],
        },
    ]


def test_try_initial_semantic_fast_route_with_trace_skips_when_not_allowed() -> None:
    trace_rows: list[dict[str, object]] = []
    calls: list[dict[str, object]] = []

    def trace_route_stage(stage: str, **kwargs) -> None:
        trace_rows.append({"stage": stage, **kwargs})

    def semantic_decision(payload: dict[str, object], text: str) -> dict[str, object]:
        calls.append({"payload": payload, "text": text})
        return {"allowed": False, "notes": ["not_owner"]}

    result = asyncio.run(
        try_initial_semantic_fast_route_with_trace(
            SimpleNamespace(_owner_private_semantic_fast_decision=semantic_decision),
            {"platform": "qq"},
            text="hello",
            session_key="qq:private:owner",
            turn_id="turn-1",
            turn_started_wall="2026-05-20T12:00:00+08:00",
            turn_started_at=12.5,
            cleanup={"cleaned_sessions": 0},
            trace_route_stage=trace_route_stage,
        )
    )

    assert isinstance(result, xinyu_bridge_turn_pipeline.InitialSemanticFastState)
    assert result == {
        "response": None,
        "desktop_started_published": False,
        "decision": {"allowed": False, "notes": ["not_owner"]},
    }
    assert calls == [{"payload": {"platform": "qq"}, "text": "hello"}]
    assert trace_rows == [
        {"stage": "semantic_fast_probe_started"},
        {"stage": "semantic_fast_probe_finished", "status": "skipped", "notes": ["not_owner"]},
    ]


def test_try_initial_semantic_fast_route_with_trace_returns_direct_response() -> None:
    trace_rows: list[dict[str, object]] = []
    calls: list[dict[str, object]] = []

    def trace_route_stage(stage: str, **kwargs) -> None:
        trace_rows.append({"stage": stage, **kwargs})

    def semantic_decision(payload: dict[str, object], text: str) -> dict[str, object]:
        calls.append({"call": "decision", "payload": payload, "text": text})
        return {"allowed": True, "direct_reply": True, "notes": ["n1", "n2", "n3", "n4", "drop"]}

    async def publish_started(payload: dict[str, object], **kwargs) -> None:
        calls.append({"call": "publish", "payload": payload, **kwargs})

    async def semantic_fast(payload: dict[str, object], **kwargs) -> dict[str, object]:
        calls.append({"call": "semantic_fast", "payload": payload, **kwargs})
        return {"accepted": True}

    runtime = SimpleNamespace(
        _sessions={"a": object(), "b": object()},
        _owner_private_semantic_fast_decision=semantic_decision,
        _desktop_publish_chat_started=publish_started,
        _maybe_handle_owner_private_semantic_fast_turn=semantic_fast,
        _get_session=lambda *args: (_ for _ in ()).throw(AssertionError("session should not be loaded")),
    )

    result = asyncio.run(
        try_initial_semantic_fast_route_with_trace(
            runtime,
            {"platform": "qq"},
            text="hello",
            session_key="qq:private:owner",
            turn_id="turn-1",
            turn_started_wall="2026-05-20T12:00:00+08:00",
            turn_started_at=12.5,
            cleanup={"cleaned_sessions": 0},
            trace_route_stage=trace_route_stage,
        )
    )

    assert isinstance(result, xinyu_bridge_turn_pipeline.InitialSemanticFastState)
    assert result["response"] == {"accepted": True}
    assert result["desktop_started_published"] is True
    assert result["decision"]["direct_reply"] is True
    assert calls == [
        {"call": "decision", "payload": {"platform": "qq"}, "text": "hello"},
        {
            "call": "publish",
            "payload": {"platform": "qq"},
            "text": "hello",
            "session_key": "qq:private:owner",
            "turn_id": "turn-1",
            "started_at": "2026-05-20T12:00:00+08:00",
            "active_sessions": 2,
        },
        {
            "call": "semantic_fast",
            "payload": {"platform": "qq"},
            "text": "hello",
            "session": None,
            "session_key": "qq:private:owner",
            "turn_id": "turn-1",
            "turn_started_wall": "2026-05-20T12:00:00+08:00",
            "turn_started_at": 12.5,
            "before_memory": None,
            "cleanup": {"cleaned_sessions": 0},
            "event_sidecar": {"notes": ["event_sourcing_deferred_for_semantic_fast"]},
            "decision": {"allowed": True, "direct_reply": True, "notes": ["n1", "n2", "n3", "n4", "drop"]},
            "record_decision_stage": False,
        },
    ]
    assert trace_rows == [
        {"stage": "semantic_fast_probe_started"},
        {"stage": "semantic_fast_probe_finished", "status": "allowed", "notes": ["n1", "n2", "n3", "n4"]},
        {
            "stage": "route_decided",
            "route": "owner_private_semantic_fast",
            "status": "accepted",
            "notes": ["n1", "n2", "n3", "n4"],
        },
        {"stage": "desktop_started_publish_started", "route": "owner_private_semantic_fast"},
        {"stage": "desktop_started_publish_finished", "route": "owner_private_semantic_fast", "status": "ok"},
        {"stage": "semantic_fast_direct_started", "route": "owner_private_semantic_fast"},
    ]


def test_try_initial_semantic_fast_route_with_trace_session_fallthrough() -> None:
    trace_rows: list[dict[str, object]] = []
    calls: list[dict[str, object]] = []
    session = SimpleNamespace(name="session")

    def trace_route_stage(stage: str, **kwargs) -> None:
        trace_rows.append({"stage": stage, **kwargs})

    async def publish_started(payload: dict[str, object], **kwargs) -> None:
        calls.append({"call": "publish", "payload": payload, **kwargs})

    async def get_session(session_key: str) -> object:
        calls.append({"call": "get_session", "session_key": session_key})
        return session

    async def semantic_fast(payload: dict[str, object], **kwargs) -> None:
        calls.append({"call": "semantic_fast", "payload": payload, **kwargs})
        return None

    runtime = SimpleNamespace(
        _sessions={},
        _owner_private_semantic_fast_decision=lambda payload, text: {"allowed": True, "notes": ["allowed"]},
        _desktop_publish_chat_started=publish_started,
        _get_session=get_session,
        _sync_recent_proactive_to_dialogue_tail=lambda call_session, payload: calls.append(
            {"call": "sync", "session": call_session, "payload": payload}
        )
        or True,
        _maybe_handle_owner_private_semantic_fast_turn=semantic_fast,
    )

    result = asyncio.run(
        try_initial_semantic_fast_route_with_trace(
            runtime,
            {"platform": "qq"},
            text="hello",
            session_key="qq:private:owner",
            turn_id="turn-1",
            turn_started_wall="2026-05-20T12:00:00+08:00",
            turn_started_at=12.5,
            cleanup={"cleaned_sessions": 0},
            trace_route_stage=trace_route_stage,
        )
    )

    assert isinstance(result, xinyu_bridge_turn_pipeline.InitialSemanticFastState)
    assert result["response"] is None
    assert result["desktop_started_published"] is True
    assert calls[0]["call"] == "publish"
    assert calls[1:] == [
        {"call": "get_session", "session_key": "qq:private:owner"},
        {"call": "sync", "session": session, "payload": {"platform": "qq"}},
        {
            "call": "semantic_fast",
            "payload": {"platform": "qq"},
            "text": "hello",
            "session": session,
            "session_key": "qq:private:owner",
            "turn_id": "turn-1",
            "turn_started_wall": "2026-05-20T12:00:00+08:00",
            "turn_started_at": 12.5,
            "before_memory": None,
            "cleanup": {"cleaned_sessions": 0},
            "event_sidecar": {"notes": ["event_sourcing_deferred_for_semantic_fast"]},
            "decision": {"allowed": True, "notes": ["allowed"]},
            "record_decision_stage": False,
        },
    ]
    assert trace_rows[-3:] == [
        {"stage": "semantic_fast_session_started", "route": "owner_private_semantic_fast"},
        {"stage": "semantic_fast_session_finished", "route": "owner_private_semantic_fast", "status": "ok"},
        {"stage": "semantic_fast_fell_through", "route": "owner_private_semantic_fast", "status": "empty_or_blocked"},
    ]


def test_try_initial_semantic_fast_route_with_trace_contains_route_errors() -> None:
    trace_rows: list[dict[str, object]] = []

    def trace_route_stage(stage: str, **kwargs) -> None:
        trace_rows.append({"stage": stage, **kwargs})

    async def publish_started(*args, **kwargs) -> None:
        del args, kwargs

    async def semantic_fast(*args, **kwargs) -> None:
        del args, kwargs
        raise RuntimeError("boom")

    runtime = SimpleNamespace(
        _sessions={},
        _owner_private_semantic_fast_decision=lambda payload, text: {
            "allowed": True,
            "direct_reply": True,
            "notes": ["allowed"],
        },
        _desktop_publish_chat_started=publish_started,
        _maybe_handle_owner_private_semantic_fast_turn=semantic_fast,
    )

    result = asyncio.run(
        try_initial_semantic_fast_route_with_trace(
            runtime,
            {"platform": "qq"},
            text="hello",
            session_key="qq:private:owner",
            turn_id="turn-1",
            turn_started_wall="2026-05-20T12:00:00+08:00",
            turn_started_at=12.5,
            cleanup={},
            trace_route_stage=trace_route_stage,
        )
    )

    assert isinstance(result, xinyu_bridge_turn_pipeline.InitialSemanticFastState)
    assert result["response"] is None
    assert result["desktop_started_published"] is True
    assert trace_rows[-1] == {
        "stage": "semantic_fast_fell_through",
        "route": "owner_private_semantic_fast",
        "status": "error",
        "notes": ["semantic_fast_error:RuntimeError"],
    }


def test_try_pre_slow_semantic_fast_route_with_trace_returns_response() -> None:
    trace_rows: list[dict[str, object]] = []
    calls: list[dict[str, object]] = []
    session = SimpleNamespace(name="session")
    before_memory = {"snapshot": "before"}
    cleanup = {"cleaned_sessions": 1}
    event_sidecar = {"notes": ["event"]}

    def trace_route_stage(stage: str, **kwargs) -> None:
        trace_rows.append({"stage": stage, **kwargs})

    async def semantic_fast(payload: dict[str, object], **kwargs) -> dict[str, object]:
        calls.append({"payload": payload, **kwargs})
        return {"accepted": True}

    payload = {"platform": "qq"}
    result = asyncio.run(
        try_pre_slow_semantic_fast_route_with_trace(
            SimpleNamespace(_maybe_handle_owner_private_semantic_fast_turn=semantic_fast),
            payload,
            text="hello",
            session=session,
            session_key="qq:private:owner",
            turn_id="turn-1",
            turn_started_wall="2026-05-20T12:00:00+08:00",
            turn_started_at=12.5,
            before_memory=before_memory,
            cleanup=cleanup,
            event_sidecar=event_sidecar,
            trace_route_stage=trace_route_stage,
        )
    )

    assert result == {"accepted": True}
    assert calls == [
        {
            "payload": payload,
            "text": "hello",
            "session": session,
            "session_key": "qq:private:owner",
            "turn_id": "turn-1",
            "turn_started_wall": "2026-05-20T12:00:00+08:00",
            "turn_started_at": 12.5,
            "before_memory": before_memory,
            "cleanup": cleanup,
            "event_sidecar": event_sidecar,
        }
    ]
    assert trace_rows == []


def test_try_pre_slow_semantic_fast_route_with_trace_records_slow_live_fallback() -> None:
    trace_rows: list[dict[str, object]] = []
    calls: list[dict[str, object]] = []

    def trace_route_stage(stage: str, **kwargs) -> None:
        trace_rows.append({"stage": stage, **kwargs})

    async def semantic_fast(payload: dict[str, object], **kwargs) -> None:
        calls.append({"payload": payload, **kwargs})
        return None

    result = asyncio.run(
        try_pre_slow_semantic_fast_route_with_trace(
            SimpleNamespace(_maybe_handle_owner_private_semantic_fast_turn=semantic_fast),
            {"platform": "qq"},
            text="hello",
            session=SimpleNamespace(),
            session_key="qq:private:owner",
            turn_id="turn-1",
            turn_started_wall="2026-05-20T12:00:00+08:00",
            turn_started_at=12.5,
            before_memory={},
            cleanup={},
            event_sidecar={"notes": ["event"]},
            trace_route_stage=trace_route_stage,
        )
    )

    assert result is None
    assert len(calls) == 1
    assert trace_rows == [
        {
            "stage": "route_decided",
            "route": "slow_live",
            "status": "accepted",
            "notes": ["semantic_fast_not_intercepted"],
        }
    ]


def test_run_pre_model_observation_sidecars_with_trace_returns_success(monkeypatch, tmp_path: Path) -> None:
    trace_rows: list[dict[str, object]] = []
    calls: list[dict[str, object]] = []

    def trace_route_stage(stage: str, **kwargs) -> None:
        trace_rows.append({"stage": stage, **kwargs})

    def fake_curiosity(root: Path, payload: dict[str, object], **kwargs) -> dict[str, object]:
        calls.append({"sidecar": "curiosity", "root": root, "payload": payload, **kwargs})
        return {"notes": ["curiosity_ok"], "prompt_block": "curiosity"}

    def fake_private_thought(root: Path, payload: dict[str, object], **kwargs) -> dict[str, object]:
        calls.append({"sidecar": "private", "root": root, "payload": payload, **kwargs})
        return {"notes": ["private_ok"]}

    def fake_uncertainty(root: Path, **kwargs) -> dict[str, object]:
        calls.append({"sidecar": "uncertainty", "root": root, **kwargs})
        return {"notes": ["uncertainty_ok"]}

    monkeypatch.setattr(xinyu_bridge_turn_pipeline, "evaluate_previous_reaction", fake_curiosity)
    monkeypatch.setattr(xinyu_bridge_turn_pipeline, "record_private_thought_outcome", fake_private_thought)
    monkeypatch.setattr(xinyu_bridge_turn_pipeline, "mark_uncertainty_pause_replied", fake_uncertainty)
    runtime = SimpleNamespace(xinyu_dir=tmp_path)
    payload = {"platform": "qq"}

    result = run_pre_model_observation_sidecars_with_trace(
        runtime,
        payload,
        text="hello",
        session_key="qq:private:owner",
        trace_route_stage=trace_route_stage,
        observed_at="2026-05-20T12:00:00+08:00",
    )

    assert result == {
        "curiosity_eval": {"notes": ["curiosity_ok"], "prompt_block": "curiosity"},
        "private_thought_outcome": {"notes": ["private_ok"]},
        "uncertainty_pause_reply": {"notes": ["uncertainty_ok"]},
    }
    assert calls == [
        {
            "sidecar": "curiosity",
            "root": tmp_path,
            "payload": payload,
            "text": "hello",
            "session_key": "qq:private:owner",
        },
        {
            "sidecar": "private",
            "root": tmp_path,
            "payload": payload,
            "text": "hello",
            "session_key": "qq:private:owner",
            "evaluation": {"notes": ["curiosity_ok"], "prompt_block": "curiosity"},
        },
        {
            "sidecar": "uncertainty",
            "root": tmp_path,
            "text": "hello",
            "observed_at": "2026-05-20T12:00:00+08:00",
        },
    ]
    assert trace_rows == [
        {"stage": "curiosity_eval_started"},
        {"stage": "curiosity_eval_finished", "status": "ok"},
        {"stage": "private_thought_outcome_started"},
        {"stage": "private_thought_outcome_finished", "status": "ok"},
        {"stage": "uncertainty_pause_mark_started"},
        {"stage": "uncertainty_pause_mark_finished", "status": "ok"},
    ]


def test_run_pre_model_observation_sidecars_with_trace_contains_errors(monkeypatch, tmp_path: Path) -> None:
    trace_rows: list[dict[str, object]] = []
    calls: list[dict[str, object]] = []

    def trace_route_stage(stage: str, **kwargs) -> None:
        trace_rows.append({"stage": stage, **kwargs})

    def fail_curiosity(*args, **kwargs) -> dict[str, object]:
        del args, kwargs
        raise ValueError("curiosity boom")

    def fail_private(root: Path, payload: dict[str, object], **kwargs) -> dict[str, object]:
        calls.append({"sidecar": "private", "evaluation": kwargs.get("evaluation")})
        raise RuntimeError("private boom")

    def fail_uncertainty(*args, **kwargs) -> dict[str, object]:
        del args, kwargs
        raise OSError("uncertainty boom")

    monkeypatch.setattr(xinyu_bridge_turn_pipeline, "evaluate_previous_reaction", fail_curiosity)
    monkeypatch.setattr(xinyu_bridge_turn_pipeline, "record_private_thought_outcome", fail_private)
    monkeypatch.setattr(xinyu_bridge_turn_pipeline, "mark_uncertainty_pause_replied", fail_uncertainty)

    result = run_pre_model_observation_sidecars_with_trace(
        SimpleNamespace(xinyu_dir=tmp_path),
        {"platform": "qq"},
        text="hello",
        session_key="qq:private:owner",
        trace_route_stage=trace_route_stage,
    )

    assert result == {
        "curiosity_eval": {"notes": ["dialogue_curiosity_eval_error:ValueError"]},
        "private_thought_outcome": {"notes": ["private_thought_outcome_error:RuntimeError"]},
        "uncertainty_pause_reply": {"notes": ["uncertainty_pause_reply_error:OSError"]},
    }
    assert calls == [
        {
            "sidecar": "private",
            "evaluation": {"notes": ["dialogue_curiosity_eval_error:ValueError"]},
        }
    ]
    assert trace_rows == [
        {"stage": "curiosity_eval_started"},
        {
            "stage": "curiosity_eval_finished",
            "status": "error",
            "notes": ["dialogue_curiosity_eval_error:ValueError"],
        },
        {"stage": "private_thought_outcome_started"},
        {
            "stage": "private_thought_outcome_finished",
            "status": "error",
            "notes": ["private_thought_outcome_error:RuntimeError"],
        },
        {"stage": "uncertainty_pause_mark_started"},
        {
            "stage": "uncertainty_pause_mark_finished",
            "status": "error",
            "notes": ["uncertainty_pause_reply_error:OSError"],
        },
    ]


def test_run_pre_model_routes_with_timeout_returns_contained_timeout_result() -> None:
    trace_rows: list[dict[str, object]] = []

    async def runner(*args, **kwargs):
        del args, kwargs
        await asyncio.sleep(60)

    result = asyncio.run(
        run_pre_model_routes_with_timeout(
            SimpleNamespace(),
            {"platform": "qq"},
            runner=runner,
            **_base_kwargs(trace_rows, timeout_seconds=0.01),
        )
    )

    assert result.response is None
    assert result.event_sidecar["notes"] == [
        "pre_model_routes_timeout:0.01s",
        "event_sourcing_unknown_after_timeout",
    ]
    assert result.v1_shadow["notes"] == ["v1_shadow_skipped:pre_model_timeout"]
    assert result.tinykernel_shadow["notes"] == ["tinykernel_shadow_skipped:pre_model_timeout"]
    assert trace_rows[-1] == {
        "stage": "pre_model_routes_finished",
        "status": "timeout",
        "notes": ["pre_model_routes_timeout:0.01s"],
    }


def test_run_pre_model_routes_with_timeout_returns_contained_error_result() -> None:
    trace_rows: list[dict[str, object]] = []

    async def runner(*args, **kwargs):
        del args, kwargs
        raise RuntimeError("boom")

    result = asyncio.run(
        run_pre_model_routes_with_timeout(
            SimpleNamespace(),
            {"platform": "qq"},
            runner=runner,
            **_base_kwargs(trace_rows),
        )
    )

    assert result.response is None
    assert result.event_sidecar["notes"] == ["pre_model_routes_error:RuntimeError"]
    assert result.v1_shadow["notes"] == ["v1_shadow_skipped:pre_model_error"]
    assert result.tinykernel_shadow["notes"] == ["tinykernel_shadow_skipped:pre_model_error"]
    assert trace_rows[-1] == {
        "stage": "pre_model_routes_finished",
        "status": "error",
        "notes": ["pre_model_routes_error:RuntimeError"],
    }


def test_run_pre_model_routes_uses_facade_monkeypatch_dependencies(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[str, dict[str, object]]] = []

    async def fake_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    def fake_record_event(root: Path, payload: dict[str, object], **kwargs) -> dict[str, object]:
        calls.append(("event", {"root": root, "payload": payload, **kwargs}))
        return {"notes": ["event_ok"]}

    async def fake_runtime_status(runtime, payload, **kwargs):
        calls.append(("runtime_status", {"runtime": runtime, "payload": payload, **kwargs}))
        return None

    async def fake_tinykernel(runtime, payload, **kwargs):
        calls.append(("tinykernel", {"runtime": runtime, "payload": payload, **kwargs}))
        return {"notes": ["tiny_ok"]}

    async def no_response(payload, **kwargs):
        calls.append(("route", {"payload": payload, **kwargs}))
        return None

    async def fake_v1_shadow(payload, **kwargs):
        calls.append(("v1_shadow", {"payload": payload, **kwargs}))
        return {"notes": ["v1_ok"]}

    monkeypatch.setattr(xinyu_bridge_turn_pipeline.asyncio, "to_thread", fake_to_thread)
    monkeypatch.setattr(xinyu_bridge_turn_pipeline, "record_chat_event", fake_record_event)
    monkeypatch.setattr(xinyu_bridge_turn_pipeline, "_maybe_handle_runtime_repair_status_turn", fake_runtime_status)
    monkeypatch.setattr(xinyu_bridge_turn_pipeline, "_run_tinykernel_shadow", fake_tinykernel)

    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        _maybe_handle_action_layer_turn=no_response,
        _maybe_handle_recent_action_followup_turn=no_response,
        _maybe_handle_action_digest_followup_turn=no_response,
        _maybe_handle_v1_canary_turn=no_response,
        _run_v1_shadow=fake_v1_shadow,
    )
    payload = {"platform": "qq"}

    result = asyncio.run(
        run_pre_model_routes(
            runtime,
            payload,
            text="hello",
            session_key="qq:private:owner",
            turn_id="turn-1",
            turn_started_wall="2026-05-20T12:00:00+08:00",
            turn_started_at=12.5,
            before_memory={"before": True},
            cleanup={"cleaned_sessions": 0},
        )
    )

    assert result.response is None
    assert result.event_sidecar == {"notes": ["event_ok"]}
    assert result.v1_shadow == {"notes": ["v1_ok"]}
    assert result.tinykernel_shadow == {"notes": ["tiny_ok"]}
    assert [name for name, _ in calls] == [
        "event",
        "runtime_status",
        "route",
        "route",
        "route",
        "route",
        "v1_shadow",
        "tinykernel",
    ]
    assert calls[1][1]["event_sidecar"] == {"notes": ["event_ok"]}
    assert calls[-1][1]["observed_at"] == "2026-05-20T12:00:00+08:00"

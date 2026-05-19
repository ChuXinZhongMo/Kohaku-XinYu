from __future__ import annotations

import asyncio
from types import SimpleNamespace

from xinyu_bridge_turn_pipeline import PreModelRouteResult, run_pre_model_routes_with_timeout


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

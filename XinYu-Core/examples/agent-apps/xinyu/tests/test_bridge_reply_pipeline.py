from __future__ import annotations

import asyncio
from types import SimpleNamespace

from xinyu_bridge_reply_pipeline import recover_empty_visible_reply, render_outward_reply_with_trace


def test_render_outward_reply_with_trace_records_success() -> None:
    trace_rows: list[dict[str, object]] = []

    def trace_route_stage(stage: str, **kwargs) -> None:
        trace_rows.append({"stage": stage, **kwargs})

    async def render(*args, **kwargs):
        del args, kwargs
        return "rendered"

    result = asyncio.run(
        render_outward_reply_with_trace(
            render,
            object(),
            payload={"message_type": "private_text"},
            user_text="hello",
            draft_reply="draft",
            canonical_recall_context="memory",
            reason="test",
            trace_route_stage=trace_route_stage,
        )
    )

    assert result == "rendered"
    assert trace_rows == [
        {"stage": "outward_renderer_started", "route": "slow_live", "notes": ["reason:test"]},
        {
            "stage": "outward_renderer_finished",
            "route": "slow_live",
            "status": "ok",
            "notes": ["reason:test"],
        },
    ]


def test_render_outward_reply_with_trace_records_timeout() -> None:
    trace_rows: list[dict[str, object]] = []

    def trace_route_stage(stage: str, **kwargs) -> None:
        trace_rows.append({"stage": stage, **kwargs})

    async def render(*args, **kwargs):
        del args, kwargs
        raise TimeoutError("timeout")

    try:
        asyncio.run(
            render_outward_reply_with_trace(
                render,
                object(),
                payload={"message_type": "private_text"},
                user_text="hello",
                draft_reply="draft",
                reason="test",
                trace_route_stage=trace_route_stage,
            )
        )
    except TimeoutError:
        pass
    else:
        raise AssertionError("renderer timeout should be propagated")

    assert trace_rows[-1] == {
        "stage": "outward_renderer_timeout",
        "route": "slow_live",
        "status": "timeout",
        "notes": ["reason:test"],
    }


def test_render_outward_reply_with_trace_records_error() -> None:
    trace_rows: list[dict[str, object]] = []

    def trace_route_stage(stage: str, **kwargs) -> None:
        trace_rows.append({"stage": stage, **kwargs})

    async def render(*args, **kwargs):
        del args, kwargs
        raise RuntimeError("boom")

    try:
        asyncio.run(
            render_outward_reply_with_trace(
                render,
                object(),
                payload={"message_type": "private_text"},
                user_text="hello",
                draft_reply="draft",
                reason="test",
                trace_route_stage=trace_route_stage,
            )
        )
    except RuntimeError:
        pass
    else:
        raise AssertionError("renderer error should be propagated")

    assert trace_rows[-1] == {
        "stage": "outward_renderer_error",
        "route": "slow_live",
        "status": "error",
        "notes": ["reason:test", "renderer_error:RuntimeError"],
    }


def test_recover_empty_visible_reply_uses_renderer_and_guard() -> None:
    class SpeechController:
        @staticmethod
        def final_reply_guard(*, payload, user_text, reply):
            del payload, user_text
            return reply, ["guard_note"]

    class Runtime:
        speech_controller = SpeechController()

        @staticmethod
        def _owner_private_payload_matches(payload):
            return bool(payload.get("owner"))

        @staticmethod
        async def _render_outward_reply(*args, **kwargs):
            del args, kwargs
            return "  recovered  "

    reply, flags = asyncio.run(
        recover_empty_visible_reply(
            Runtime(),
            SimpleNamespace(),
            payload={"owner": True},
            user_text="hello",
        )
    )

    assert reply == "recovered"
    assert flags == ["empty_visible_reply_regenerated", "guard_note"]

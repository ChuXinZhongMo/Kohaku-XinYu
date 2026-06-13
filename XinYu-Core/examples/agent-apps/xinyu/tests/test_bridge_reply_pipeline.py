from __future__ import annotations

import asyncio
from types import SimpleNamespace

import xinyu_bridge_reply_pipeline
from xinyu_bridge_reply_pipeline import (
    recover_empty_visible_reply,
    render_outward_reply_with_trace,
    runtime_render_outward_reply,
    runtime_is_explicit_technical_request,
    runtime_is_live_style_pressure,
    runtime_is_owner_relationship_pressure,
    runtime_reply_quality_flags,
    runtime_speech_controller,
)


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


def test_runtime_render_outward_reply_delegates_to_runtime_renderer() -> None:
    calls: list[tuple[object, dict[str, object]]] = []

    class _Renderer:
        async def render_outward_reply(self, agent: object, **kwargs) -> str:
            calls.append((agent, kwargs))
            return "rendered"

    agent = object()
    result = asyncio.run(
        runtime_render_outward_reply(
            SimpleNamespace(renderer=_Renderer()),
            agent,
            payload={"message_type": "private"},
            user_text="hello",
            draft_reply="draft",
            canonical_recall_context="memory",
        )
    )

    assert result == "rendered"
    assert calls == [
        (
            agent,
            {
                "payload": {"message_type": "private"},
                "user_text": "hello",
                "draft_reply": "draft",
                "canonical_recall_context": "memory",
            },
        )
    ]


def test_build_life_reply_policy_for_runtime_builds_context(monkeypatch, tmp_path) -> None:
    calls: dict[str, object] = {}

    class _SelfChoiceStore:
        async def apply_time_decay(self) -> None:
            calls["time_decay"] = True

        async def snapshot_public(self, *, consume_cues: bool) -> dict[str, object]:
            calls["snapshot_public"] = consume_cues
            return {"choice": "public"}

    class _Entropy:
        def model_dump(self, *, mode: str) -> dict[str, object]:
            calls["entropy_dump_mode"] = mode
            return {"entropy": "state"}

    async def ensure_self_choice_ready() -> None:
        calls["ensure_self_choice"] = True

    async def desktop_proactive_inbox(payload: dict[str, object]) -> dict[str, object]:
        calls["proactive_payload"] = payload
        return {"items": [{"candidateId": "p1"}]}

    async def desktop_memory_recent(payload: dict[str, object]) -> dict[str, object]:
        calls["memory_payload"] = payload
        return {"items": [{"summary": "memory"}]}

    def fake_sample_environment(root):
        calls["environment_root"] = root
        return {"weather": "clear"}

    def fake_build_entropy_state(**kwargs):
        calls["entropy_kwargs"] = kwargs
        return _Entropy()

    def fake_build_scene_frame(root, **kwargs):
        calls["scene_frame"] = {"root": root, **kwargs}
        return {"scene": "frame"}

    def fake_read_recent_action_context(root):
        calls["action_context_root"] = root
        return "recent action"

    def fake_build_life_reply_policy(**kwargs):
        calls["policy_kwargs"] = kwargs
        return {"notes": ["existing"]}

    monkeypatch.setattr(xinyu_bridge_reply_pipeline, "sample_environment", fake_sample_environment)
    monkeypatch.setattr(xinyu_bridge_reply_pipeline, "build_entropy_state", fake_build_entropy_state)
    monkeypatch.setattr(xinyu_bridge_reply_pipeline, "build_scene_frame", fake_build_scene_frame)
    monkeypatch.setattr(xinyu_bridge_reply_pipeline, "read_recent_action_context", fake_read_recent_action_context)
    monkeypatch.setattr(xinyu_bridge_reply_pipeline, "build_life_reply_policy", fake_build_life_reply_policy)
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        self_choice_store=_SelfChoiceStore(),
        _ensure_self_choice_ready=ensure_self_choice_ready,
        desktop_proactive_inbox=desktop_proactive_inbox,
        desktop_memory_recent=desktop_memory_recent,
        _desktop_recent_turns=[{"turn": index} for index in range(35)],
    )

    policy = asyncio.run(
        xinyu_bridge_reply_pipeline.build_life_reply_policy_for_runtime(
            runtime,
            user_text="hello",
            visible_turn={"visible": True},
            canonical_recall_context="memory",
            evaluated_at="2026-06-06T01:00:00+08:00",
        )
    )

    assert policy["notes"] == ["existing", "life_reply_policy_built"]
    assert calls["ensure_self_choice"] is True
    assert calls["time_decay"] is True
    assert calls["snapshot_public"] is False
    assert calls["proactive_payload"] == {}
    assert calls["memory_payload"] == {"limit": 30}
    assert calls["environment_root"] == tmp_path
    assert calls["action_context_root"] == tmp_path
    assert calls["entropy_dump_mode"] == "json"
    assert calls["entropy_kwargs"] == {
        "environment": {"weather": "clear"},
        "proactive_items": [{"candidateId": "p1"}],
        "recent_turns": [{"turn": index} for index in range(5, 35)],
        "recent_memory_events": [{"summary": "memory"}],
    }
    assert calls["scene_frame"] == {
        "root": tmp_path,
        "user_text": "hello",
        "visible_turn": {"visible": True},
        "canonical_recall_context": "memory",
        "evaluated_at": "2026-06-06T01:00:00+08:00",
    }
    assert calls["policy_kwargs"] == {
        "self_choice_public": {"choice": "public"},
        "entropy_state": {"entropy": "state"},
        "recent_action_context": "recent action",
        "user_text": "hello",
        "scene_frame": {"scene": "frame"},
    }


def test_build_life_reply_policy_for_runtime_returns_fallback_on_error() -> None:
    async def ensure_self_choice_ready() -> None:
        raise RuntimeError("boom")

    runtime = SimpleNamespace(_ensure_self_choice_ready=ensure_self_choice_ready)

    policy = asyncio.run(
        xinyu_bridge_reply_pipeline.build_life_reply_policy_for_runtime(runtime, user_text="hello")
    )

    assert policy["mode"] == "steady"
    assert policy["reply_pressure"] == "normal"
    assert policy["notes"] == ["life_reply_policy_error:RuntimeError"]


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


def test_runtime_speech_controller_reuses_existing_controller() -> None:
    controller = object()
    runtime = SimpleNamespace(speech_controller=controller)

    assert runtime_speech_controller(runtime, bridge_source_path=__file__) is controller


def test_runtime_speech_controller_lazily_creates_controller(monkeypatch, tmp_path) -> None:
    created: list[object] = []

    class FakeSpeechController:
        def __init__(self, root) -> None:
            created.append(root)

    monkeypatch.setattr(xinyu_bridge_reply_pipeline, "XinyuSpeechController", FakeSpeechController)
    runtime = SimpleNamespace()
    bridge_source_path = tmp_path / "xinyu_core_bridge.py"

    controller = runtime_speech_controller(runtime, bridge_source_path=bridge_source_path)

    assert isinstance(controller, FakeSpeechController)
    assert runtime.speech_controller is controller
    assert created == [tmp_path]


def test_runtime_speech_controller_adapters_delegate_to_controller() -> None:
    calls: list[tuple[str, object]] = []

    class SpeechController:
        def is_live_style_pressure(self, text: str) -> bool:
            calls.append(("live", text))
            return True

        def is_owner_relationship_pressure(self, text: str) -> bool:
            calls.append(("relationship", text))
            return False

        def is_explicit_technical_request(self, text: str) -> bool:
            calls.append(("technical", text))
            return True

        def reply_quality_flags(self, *, user_text: str, reply: str) -> list[str]:
            calls.append(("quality", (user_text, reply)))
            return ["flag"]

    runtime = SimpleNamespace(_speech_controller=lambda: SpeechController())

    assert runtime_is_live_style_pressure(runtime, "hello") is True
    assert runtime_is_owner_relationship_pressure(runtime, "hello") is False
    assert runtime_is_explicit_technical_request(runtime, "hello") is True
    assert runtime_reply_quality_flags(runtime, user_text="hello", reply="reply") == ["flag"]
    assert calls == [
        ("live", "hello"),
        ("relationship", "hello"),
        ("technical", "hello"),
        ("quality", ("hello", "reply")),
    ]

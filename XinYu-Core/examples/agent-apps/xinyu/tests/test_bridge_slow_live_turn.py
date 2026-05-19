from __future__ import annotations

import asyncio
from types import SimpleNamespace

import xinyu_bridge_slow_live_turn as slow_live
from xinyu_bridge_slow_live_turn import build_slow_live_model_contexts
from xinyu_bridge_slow_live_turn import inject_slow_live_model_event
from xinyu_bridge_slow_live_turn import run_slow_live_finish_sidecars_with_trace
from xinyu_bridge_slow_live_turn import run_slow_live_memory_recall


def _trace_rows() -> tuple[list[dict[str, object]], object]:
    rows: list[dict[str, object]] = []

    def trace_route_stage(stage: str, **kwargs) -> None:
        rows.append({"stage": stage, **kwargs})

    return rows, trace_route_stage


def test_run_slow_live_memory_recall_records_success() -> None:
    rows, trace_route_stage = _trace_rows()
    published: list[dict[str, object]] = []

    class Runtime:
        xinyu_dir = "root"

        @staticmethod
        async def _desktop_publish_memory_recall(payload, recalled_context, **kwargs):
            published.append({"payload": payload, "context": recalled_context, **kwargs})
            return {"id": "recall-event"}

    def recall_runner(*args, **kwargs):
        del args, kwargs
        return SimpleNamespace(
            result=SimpleNamespace(notes=["context_note"], prompt_block="memory"),
            notes=["algorithm_note"],
        )

    result = asyncio.run(
        run_slow_live_memory_recall(
            Runtime(),
            {"platform": "qq"},
            user_text="hello",
            session=SimpleNamespace(dialogue_tail=[]),
            session_key="qq:private:owner",
            turn_id="turn-memory-test",
            visible_turn=SimpleNamespace(turn_kind="ordinary"),
            evaluated_at="2026-05-20T12:00:00+08:00",
            trace_route_stage=trace_route_stage,
            recall_runner=recall_runner,
        )
    )

    assert result.recalled_context.prompt_block == "memory"
    assert result.recalled_context_event == {"id": "recall-event"}
    assert result.recalled_context_notes == ["algorithm_note", "context_note"]
    assert published and published[0]["turn_id"] == "turn-memory-test"
    assert rows[-1] == {
        "stage": "memory_recall_finished",
        "route": "slow_live",
        "status": "ok",
        "notes": ["algorithm_note", "context_note"],
    }


def test_run_slow_live_memory_recall_records_timeout_without_raising() -> None:
    rows, trace_route_stage = _trace_rows()

    class Runtime:
        xinyu_dir = "root"

    def recall_runner(*args, **kwargs):
        del args, kwargs
        raise TimeoutError("timeout")

    result = asyncio.run(
        run_slow_live_memory_recall(
            Runtime(),
            {"platform": "qq"},
            user_text="hello",
            session=SimpleNamespace(dialogue_tail=[]),
            session_key="qq:private:owner",
            turn_id="turn-memory-test",
            visible_turn=SimpleNamespace(turn_kind="ordinary"),
            evaluated_at="2026-05-20T12:00:00+08:00",
            trace_route_stage=trace_route_stage,
            recall_runner=recall_runner,
        )
    )

    assert result.recalled_context is None
    assert result.recalled_context_event == {}
    assert result.recalled_context_notes == ["context_retrieval_timeout:TimeoutError"]
    assert rows[-1] == {
        "stage": "memory_recall_timeout",
        "route": "slow_live",
        "status": "timeout",
        "notes": ["context_retrieval_timeout:TimeoutError"],
    }


def test_run_slow_live_memory_recall_records_error_without_raising() -> None:
    rows, trace_route_stage = _trace_rows()

    class Runtime:
        xinyu_dir = "root"

    def recall_runner(*args, **kwargs):
        del args, kwargs
        raise RuntimeError("boom")

    result = asyncio.run(
        run_slow_live_memory_recall(
            Runtime(),
            {"platform": "qq"},
            user_text="hello",
            session=SimpleNamespace(dialogue_tail=[]),
            session_key="qq:private:owner",
            turn_id="turn-memory-test",
            visible_turn=SimpleNamespace(turn_kind="ordinary"),
            evaluated_at="2026-05-20T12:00:00+08:00",
            trace_route_stage=trace_route_stage,
            recall_runner=recall_runner,
        )
    )

    assert result.recalled_context is None
    assert result.recalled_context_event == {}
    assert result.recalled_context_notes == ["context_retrieval_error:RuntimeError"]
    assert rows[-1] == {
        "stage": "memory_recall_error",
        "route": "slow_live",
        "status": "error",
        "notes": ["context_retrieval_error:RuntimeError"],
    }


def test_inject_slow_live_model_event_records_success(tmp_path, monkeypatch) -> None:
    rows, trace_route_stage = _trace_rows()
    injected_context: dict[str, object] = {}

    class Agent:
        async def inject_event(self, event) -> None:
            injected_context["event"] = event

    class Runtime:
        xinyu_dir = tmp_path
        turn_timeout_seconds = 1

        @staticmethod
        def _inject_live_turn_context(agent, **kwargs):
            del agent
            injected_context.update(kwargs)

    monkeypatch.setattr(slow_live, "build_continuity_handoff_prompt_block", lambda *args, **kwargs: "continuity")
    monkeypatch.setattr(slow_live, "build_uncertainty_pause_prompt_block", lambda *args, **kwargs: "uncertainty")
    monkeypatch.setattr(slow_live, "build_life_reply_prompt_block", lambda *args, **kwargs: "life")

    asyncio.run(
        inject_slow_live_model_event(
            Runtime(),
            {"platform": "qq"},
            session=SimpleNamespace(agent=Agent(), dialogue_tail=[]),
            event={"event": "user"},
            text="hello",
            turn_id="turn-inject-test",
            visible_turn=SimpleNamespace(turn_kind="ordinary"),
            persona_sidecar={"prompt_block": "persona"},
            curiosity_eval={"prompt_block": "curiosity"},
            recalled_context=SimpleNamespace(prompt_block="memory"),
            runtime_presence_context="presence",
            life_reply_policy={"notes": []},
            emotion_council_context="emotion",
            trace_route_stage=trace_route_stage,
        )
    )

    assert injected_context["turn_id"] == "turn-inject-test"
    assert injected_context["continuity_context"] == "continuity"
    assert injected_context["event"] == {"event": "user"}
    assert rows[-1] == {"stage": "model_inject_finished", "route": "slow_live", "status": "ok"}


def test_build_slow_live_model_contexts_collects_prompt_inputs(tmp_path, monkeypatch) -> None:
    class Runtime:
        xinyu_dir = tmp_path
        emotion_council_prompt_enabled = True

        @staticmethod
        async def _build_life_reply_policy(**kwargs):
            return {"notes": ["life_policy"], "kwargs": kwargs}

    monkeypatch.setattr(slow_live, "refresh_continuity_handoff", lambda *args, **kwargs: {"notes": ["continuity"]})
    monkeypatch.setattr(slow_live, "build_runtime_presence_prompt_block", lambda *args, **kwargs: "presence")
    monkeypatch.setattr(slow_live, "build_emotion_council_prompt_block", lambda *args, **kwargs: "emotion")

    contexts = asyncio.run(
        build_slow_live_model_contexts(
            Runtime(),
            {"platform": "qq"},
            user_text="hello",
            visible_turn=SimpleNamespace(turn_kind="ordinary"),
            recalled_context=SimpleNamespace(prompt_block="memory"),
            evaluated_at="2026-05-20T12:00:00+08:00",
        )
    )

    assert contexts.continuity_handoff == {"notes": ["continuity"]}
    assert contexts.runtime_presence_context == "presence"
    assert contexts.life_reply_policy["notes"] == ["life_policy"]
    assert contexts.life_reply_policy["kwargs"]["canonical_recall_context"] == "memory"
    assert contexts.emotion_council_context == "emotion"


def test_build_slow_live_model_contexts_contains_continuity_error(tmp_path, monkeypatch) -> None:
    class Runtime:
        xinyu_dir = tmp_path
        emotion_council_prompt_enabled = False

        @staticmethod
        async def _build_life_reply_policy(**kwargs):
            del kwargs
            return {"notes": []}

    def fail_continuity(*args, **kwargs):
        del args, kwargs
        raise RuntimeError("continuity failed")

    monkeypatch.setattr(slow_live, "refresh_continuity_handoff", fail_continuity)
    monkeypatch.setattr(slow_live, "build_runtime_presence_prompt_block", lambda *args, **kwargs: "presence")

    contexts = asyncio.run(
        build_slow_live_model_contexts(
            Runtime(),
            {"platform": "qq"},
            user_text="hello",
            visible_turn=SimpleNamespace(turn_kind="ordinary"),
            recalled_context=None,
            evaluated_at="2026-05-20T12:00:00+08:00",
        )
    )

    assert contexts.continuity_handoff == {"notes": ["continuity_handoff_error:RuntimeError"]}
    assert contexts.runtime_presence_context == "presence"
    assert contexts.emotion_council_context == ""


def test_inject_slow_live_model_event_records_timeout(tmp_path) -> None:
    rows, trace_route_stage = _trace_rows()

    class Agent:
        async def inject_event(self, event) -> None:
            del event
            await asyncio.sleep(60)

    class Runtime:
        xinyu_dir = tmp_path
        turn_timeout_seconds = 0.01

        @staticmethod
        def _inject_live_turn_context(*args, **kwargs):
            del args, kwargs

    try:
        asyncio.run(
            inject_slow_live_model_event(
                Runtime(),
                {"platform": "qq"},
                session=SimpleNamespace(agent=Agent(), dialogue_tail=[]),
                event={"event": "user"},
                text="hello",
                turn_id="turn-inject-test",
                visible_turn=SimpleNamespace(turn_kind="ordinary"),
                persona_sidecar={},
                curiosity_eval={},
                recalled_context=None,
                runtime_presence_context="presence",
                life_reply_policy={"notes": []},
                emotion_council_context="",
                trace_route_stage=trace_route_stage,
            )
        )
    except TimeoutError:
        pass
    else:
        raise AssertionError("model inject timeout should be propagated")

    assert rows[-1] == {
        "stage": "model_inject_timeout",
        "route": "slow_live",
        "status": "timeout",
        "notes": ["turn_timeout"],
    }


def test_inject_slow_live_model_event_records_error(tmp_path) -> None:
    rows, trace_route_stage = _trace_rows()

    class Agent:
        async def inject_event(self, event) -> None:
            del event
            raise RuntimeError("inject failed")

    class Runtime:
        xinyu_dir = tmp_path
        turn_timeout_seconds = 1

        @staticmethod
        def _inject_live_turn_context(*args, **kwargs):
            del args, kwargs

    try:
        asyncio.run(
            inject_slow_live_model_event(
                Runtime(),
                {"platform": "qq"},
                session=SimpleNamespace(agent=Agent(), dialogue_tail=[]),
                event={"event": "user"},
                text="hello",
                turn_id="turn-inject-test",
                visible_turn=SimpleNamespace(turn_kind="ordinary"),
                persona_sidecar={},
                curiosity_eval={},
                recalled_context=None,
                runtime_presence_context="presence",
                life_reply_policy={"notes": []},
                emotion_council_context="",
                trace_route_stage=trace_route_stage,
            )
        )
    except RuntimeError:
        pass
    else:
        raise AssertionError("model inject error should be propagated")

    assert rows[-1] == {
        "stage": "model_inject_error",
        "route": "slow_live",
        "status": "error",
        "notes": ["turn_error:RuntimeError"],
    }


def test_run_slow_live_finish_sidecars_with_trace_records_success() -> None:
    rows, trace_route_stage = _trace_rows()

    async def sidecars_runner(runtime, **kwargs):
        return {"runtime": runtime, "kwargs": kwargs, "ok": True}

    result = asyncio.run(
        run_slow_live_finish_sidecars_with_trace(
            "runtime",
            sidecars_runner=sidecars_runner,
            trace_route_stage=trace_route_stage,
            payload={"platform": "qq"},
        )
    )

    assert result["ok"] is True
    assert rows == [
        {"stage": "finish_sidecars_started", "route": "slow_live"},
        {"stage": "finish_sidecars_finished", "route": "slow_live", "status": "ok"},
    ]


def test_run_slow_live_finish_sidecars_with_trace_records_timeout() -> None:
    rows, trace_route_stage = _trace_rows()

    async def sidecars_runner(runtime, **kwargs):
        del runtime, kwargs
        raise TimeoutError("timeout")

    try:
        asyncio.run(
            run_slow_live_finish_sidecars_with_trace(
                "runtime",
                sidecars_runner=sidecars_runner,
                trace_route_stage=trace_route_stage,
                payload={"platform": "qq"},
            )
        )
    except TimeoutError:
        pass
    else:
        raise AssertionError("finish sidecar timeout should be propagated")

    assert rows[-1] == {
        "stage": "finish_sidecars_timeout",
        "route": "slow_live",
        "status": "timeout",
        "notes": ["finish_sidecars_timeout"],
    }


def test_run_slow_live_finish_sidecars_with_trace_records_error() -> None:
    rows, trace_route_stage = _trace_rows()

    async def sidecars_runner(runtime, **kwargs):
        del runtime, kwargs
        raise RuntimeError("boom")

    try:
        asyncio.run(
            run_slow_live_finish_sidecars_with_trace(
                "runtime",
                sidecars_runner=sidecars_runner,
                trace_route_stage=trace_route_stage,
                payload={"platform": "qq"},
            )
        )
    except RuntimeError:
        pass
    else:
        raise AssertionError("finish sidecar error should be propagated")

    assert rows[-1] == {
        "stage": "finish_sidecars_error",
        "route": "slow_live",
        "status": "error",
        "notes": ["finish_sidecars_error:RuntimeError"],
    }

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

import xinyu_bridge_slow_live_turn as slow_live
from xinyu_bridge_errors import BridgeRequestError
from xinyu_bridge_slow_live_turn import apply_slow_live_current_reference_repair
from xinyu_bridge_slow_live_turn import apply_slow_live_final_reply_guard
from xinyu_bridge_slow_live_turn import apply_slow_live_life_reply_policy
from xinyu_bridge_slow_live_turn import apply_slow_live_outward_renderer
from xinyu_bridge_slow_live_turn import apply_slow_live_reply_bubble_policy
from xinyu_bridge_slow_live_turn import apply_slow_live_reply_adjustment_pipeline
from xinyu_bridge_slow_live_turn import apply_slow_live_stale_context_repair
from xinyu_bridge_slow_live_turn import apply_slow_live_sticker_reply_override
from xinyu_bridge_slow_live_turn import apply_slow_live_style_pressure_empty_fallback
from xinyu_bridge_slow_live_turn import apply_slow_live_visible_dedupe
from xinyu_bridge_slow_live_turn import build_slow_live_model_contexts
from xinyu_bridge_slow_live_turn import build_slow_live_response_state
from xinyu_bridge_slow_live_turn import build_slow_live_success_notes
from xinyu_bridge_slow_live_turn import enter_slow_live_route_with_trace
from xinyu_bridge_slow_live_turn import finish_and_publish_slow_live_success_turn
from xinyu_bridge_slow_live_turn import finish_prepared_slow_live_success_turn
from xinyu_bridge_slow_live_turn import inject_slow_live_model_event
from xinyu_bridge_slow_live_turn import observe_slow_live_persona_sidecar
from xinyu_bridge_slow_live_turn import prepare_slow_live_post_model_reply_state
from xinyu_bridge_slow_live_turn import prepare_slow_live_post_model_reply_state_for_turn
from xinyu_bridge_slow_live_turn import publish_slow_live_failed_turn
from xinyu_bridge_slow_live_turn import publish_slow_live_success_turn
from xinyu_bridge_slow_live_turn import recover_slow_live_empty_visible_reply
from xinyu_bridge_slow_live_turn import run_slow_live_emotion_council_shadow
from xinyu_bridge_slow_live_turn import run_slow_live_finish_sidecars_with_trace
from xinyu_bridge_slow_live_turn import run_slow_live_memory_recall
from xinyu_bridge_slow_live_turn import run_slow_live_model_turn_with_failure_publish
from xinyu_bridge_slow_live_turn import run_slow_live_turn_from_pre_model_phase_with_trace


def _trace_rows() -> tuple[list[dict[str, object]], object]:
    rows: list[dict[str, object]] = []

    def trace_route_stage(stage: str, **kwargs) -> None:
        rows.append({"stage": stage, **kwargs})

    return rows, trace_route_stage


def test_publish_slow_live_failed_turn_records_timeout_and_interrupts(tmp_path, monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    class Agent:
        def interrupt(self) -> None:
            calls.append(("interrupt", "called"))

    async def publish_finished(payload, **kwargs) -> None:
        calls.append(("publish", {"payload": payload, **kwargs}))

    def record_finished(root, **kwargs) -> None:
        calls.append(("record", {"root": root, **kwargs}))

    monkeypatch.setattr(slow_live.time, "perf_counter", lambda: 11.5)
    monkeypatch.setattr(slow_live, "record_turn_finished", record_finished)
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        _desktop_publish_chat_finished=publish_finished,
        _desktop_recall_count=lambda recalled: 2,
        _desktop_top_recall_sources=lambda recalled: ["memory-a"],
    )

    elapsed = asyncio.run(
        publish_slow_live_failed_turn(
            runtime,
            {"platform": "qq"},
            session=SimpleNamespace(agent=Agent()),
            text="hello",
            session_key="qq:private:owner",
            turn_id="turn-1",
            turn_started_wall="2026-05-20T12:00:00+08:00",
            turn_started_at=10.0,
            status="timeout",
            notes=["turn_timeout"],
            recalled_context_event={"id": "recall-1"},
            recalled_context=SimpleNamespace(),
        )
    )

    assert elapsed == 1500
    assert calls[0] == ("interrupt", "called")
    assert calls[1] == (
        "record",
        {
            "root": tmp_path,
            "turn_id": "turn-1",
            "reply": "",
            "elapsed_ms": 1500,
            "status": "timeout",
            "notes": ["turn_timeout"],
        },
    )
    assert calls[2] == (
        "publish",
        {
            "payload": {"platform": "qq"},
            "text": "hello",
            "reply": "",
            "session_key": "qq:private:owner",
            "turn_id": "turn-1",
            "started_at": "2026-05-20T12:00:00+08:00",
            "elapsed_ms": 1500,
            "status": "timeout",
            "notes": ["turn_timeout"],
            "memory_changed": False,
            "recall_event_id": "recall-1",
            "recall_count": 2,
            "top_recall_sources": ["memory-a"],
        },
    )


def test_publish_slow_live_failed_turn_records_error_without_interrupt(tmp_path, monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    class Agent:
        def interrupt(self) -> None:
            calls.append(("interrupt", "called"))

    async def publish_finished(payload, **kwargs) -> None:
        calls.append(("publish", {"payload": payload, **kwargs}))

    monkeypatch.setattr(slow_live.time, "perf_counter", lambda: 11.0)
    monkeypatch.setattr(slow_live, "record_turn_finished", lambda root, **kwargs: calls.append(("record", kwargs)))
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        _desktop_publish_chat_finished=publish_finished,
        _desktop_recall_count=lambda recalled: 0,
        _desktop_top_recall_sources=lambda recalled: [],
    )

    elapsed = asyncio.run(
        publish_slow_live_failed_turn(
            runtime,
            {"platform": "qq"},
            session=SimpleNamespace(agent=Agent()),
            text="hello",
            session_key="qq:private:owner",
            turn_id="turn-1",
            turn_started_wall="2026-05-20T12:00:00+08:00",
            turn_started_at=10.0,
            status="error",
            notes=["turn_error:RuntimeError"],
            recalled_context_event={},
            recalled_context=None,
        )
    )

    assert elapsed == 1000
    assert [call[0] for call in calls] == ["record", "publish"]
    assert calls[0][1]["status"] == "error"
    assert calls[1][1]["status"] == "error"
    assert calls[1][1]["recall_event_id"] == ""


def test_publish_slow_live_success_turn_records_publishes_and_returns_response(tmp_path, monkeypatch) -> None:
    calls: list[tuple[str, object]] = []
    rows, trace_route_stage = _trace_rows()

    async def cleanup(*, preserve_keys: set[str]) -> dict[str, int]:
        calls.append(("cleanup", {"preserve_keys": preserve_keys}))
        return {"cleaned_sessions": 2}

    async def publish_finished(payload, **kwargs) -> None:
        calls.append(("publish", {"payload": payload, **kwargs}))

    def record_finished(root, **kwargs) -> None:
        calls.append(("record", {"root": root, **kwargs}))

    monkeypatch.setattr(slow_live.time, "perf_counter", lambda: 12.0)
    monkeypatch.setattr(slow_live, "record_turn_finished", record_finished)
    monkeypatch.setattr(slow_live, "visible_text_hash", lambda reply: f"hash:{reply}")
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        _cleanup_idle_sessions=cleanup,
        _desktop_publish_chat_finished=publish_finished,
        _desktop_recall_count=lambda recalled: 3,
        _desktop_top_recall_sources=lambda recalled: ["memory-a", "memory-b"],
    )
    notes = ["base-note"]
    payload = {"platform": "qq", "metadata": {"desktop_command_id": "cmd-1"}}

    response = asyncio.run(
        publish_slow_live_success_turn(
            runtime,
            payload,
            text="hello",
            reply="reply text",
            session_key="qq:private:owner",
            turn_id="turn-1",
            turn_started_wall="2026-05-20T12:00:00+08:00",
            turn_started_at=10.0,
            before_memory={"before": True},
            after_memory={"after": True},
            notes=notes,
            archive_result={"message_ids": ["user-msg", "assistant-msg"]},
            recalled_context_event={"id": "recall-1"},
            recalled_context=SimpleNamespace(),
            reply_bubble_force_units=[1, 2],
            trace_route_stage=trace_route_stage,
        )
    )

    assert notes == ["base-note", "cleaned_extra_sessions:2"]
    assert calls[0] == ("cleanup", {"preserve_keys": {"qq:private:owner"}})
    assert calls[1] == (
        "record",
        {
            "root": tmp_path,
            "turn_id": "turn-1",
            "reply": "reply text",
            "elapsed_ms": 2000,
            "status": "ok",
            "notes": notes,
            "memory_changed": True,
        },
    )
    assert rows == [
        {
            "stage": "route_finished",
            "route": "slow_live",
            "status": "ok",
            "elapsed_ms": 2000,
            "notes": notes[:8],
        }
    ]
    assert calls[2] == (
        "publish",
        {
            "payload": payload,
            "text": "hello",
            "reply": "reply text",
            "session_key": "qq:private:owner",
            "turn_id": "turn-1",
            "started_at": "2026-05-20T12:00:00+08:00",
            "elapsed_ms": 2000,
            "status": "ok",
            "notes": notes,
            "memory_changed": True,
            "archive_message_ids": ["user-msg", "assistant-msg"],
            "reply_hash": "hash:reply text",
            "recall_event_id": "recall-1",
            "recall_count": 3,
            "top_recall_sources": ["memory-a", "memory-b"],
        },
    )
    assert response == {
        "accepted": True,
        "reply": "reply text",
        "memory_changed": True,
        "turn_id": "turn-1",
        "command_id": "cmd-1",
        "session_id": "qq:private:owner",
        "reply_hash": "hash:reply text",
        "archive_message_ids": ["user-msg", "assistant-msg"],
        "archive_assistant_message_id": "assistant-msg",
        "reply_bubble_force_units": [1, 2],
        "notes": notes,
    }


def test_build_slow_live_success_notes_preserves_order_limits_and_filters() -> None:
    finish_sidecars = {
        "residue_written": True,
        "voice_calibrated": True,
        "voice_trial_overlay": {"recorded": False, "notes": ["voice_error:RuntimeError", "voice-note-2", "voice-note-3"]},
        "proactive_owner_reply_marked": True,
        "curiosity_prediction": {"notes": ["curiosity-p1", "curiosity-p2", "curiosity-p3", "curiosity-p4", "drop"]},
        "private_thought_link": {"notes": ["private-link-1", "private-link-2", "private-link-3", "drop"]},
        "archive_result": {"notes": ["archive-1", "archive-2", "archive-3", "drop"]},
        "candidate_result": {"notes": ["candidate-1", "candidate-2", "candidate-3", "drop"]},
        "memory_self_review": {"notes": ["review-1", "review-2", "review-3", "drop"]},
        "interaction_journal": {"notes": ["journal-1", "journal-2", "journal-3", "drop"]},
        "learning_closed_loop": {"notes": ["closed-1", "closed-2", "closed-3", "drop"]},
        "uncertainty_pause": {"notes": ["uncertainty-1", "uncertainty-2", "uncertainty-3", "drop"]},
        "wait_to_think_sidecar": {"notes": ["wait-1", "wait-2", "wait-3", "drop"]},
        "promised_followup": {"notes": ["promise-1", "promise-2", "promise-3", "drop"]},
        "turn_coherence": {"notes": ["coherence-1", "coherence-2", "coherence-3", "drop"]},
        "sticker_tail_recorded": True,
        "sticker_reply": {"notes": ["sticker_skip:not_requested:auto", "sticker-1", "", "sticker-2", "sticker-3", "drop"]},
    }

    notes = build_slow_live_success_notes(
        reply="",
        empty_visible_reply_no_fallback=True,
        rendered=True,
        renderer_reason="",
        outward_renderer=True,
        renderer_mode="live",
        final_guard_flags=["flag-a", "flag-b", "flag-c", "drop"],
        final_guard_applied=True,
        stale_context_reply_replaced=True,
        visible_dedupe=SimpleNamespace(notes=["dedupe-note"]),
        finish_sidecars=finish_sidecars,
        proactive_tail_synced=True,
        model_codex_delegate_note="model-codex-note",
        wait_to_think_task="wait task",
        curiosity_eval={"notes": ["curiosity-1", "curiosity-2", "curiosity-3", "curiosity-4", "drop"]},
        private_thought_outcome={"notes": ["private-1", "private-2", "private-3", "drop"]},
        uncertainty_pause_reply={"notes": ["pause-reply-1", "pause-reply-2", "drop"]},
        continuity_handoff={"notes": ["continuity-1", "continuity-2", "drop"]},
        life_reply_policy={"notes": ["life-1", "life-2", "life-3", "drop"]},
        life_reply_adjustment={"notes": ["life-adjust-1", "life-adjust-2", "life-adjust-3", "drop"]},
        response_error_loop={"notes": ["response-error-1", "response-error-2", "drop"]},
        slow_state_runtime={"notes": ["slow-state-1", "slow-state-2", "drop"]},
        current_sticker_reply="current sticker",
        recent_sticker_reply="recent sticker",
        reply_bubble_force_units=[1, 2, 3],
        persona_sidecar={
            "state_changed": True,
            "event_recorded": True,
            "notes": ["persona-1", "persona-2", "persona-3", "persona-4", "drop"],
        },
        event_sidecar={"notes": ["event-1", "event-2", "event-3", "event-4", "drop"]},
        v1_shadow={"notes": ["v1-1", "v1-2", "v1-3", "v1-4", "drop"]},
        tinykernel_shadow={"notes": ["tiny-1", "tiny-2", "tiny-3", "drop"]},
        emotion_council={"notes": ["emotion-1", "emotion-2", "emotion-3", "emotion-4", "drop"]},
        recalled_context_notes=["recall-1", "recall-2", "recall-3", "recall-4", "drop"],
        expression_learning={"notes": ["expression-1", "expression-2", "expression-3", "drop"]},
        cleanup={"cleaned_sessions": 2},
        session=SimpleNamespace(dialogue_tail=[{"role": "user"}]),
    )

    assert notes == [
        "empty_reply",
        "empty_visible_reply_no_fallback",
        "outward_renderer_applied:unknown",
        "final_reply_guard_flags:flag-a,flag-b,flag-c",
        "final_reply_guard_applied",
        "stale_context_reply_replaced",
        "dedupe-note",
        "persona_surface_residue_updated",
        "voice_calibration_recorded",
        "voice_error:RuntimeError",
        "voice-note-2",
        "persona_state_updated",
        "owner_relationship_event_recorded",
        "proactive_outbound_tail_synced",
        "proactive_request_owner_replied",
        "model-codex-note",
        "wait_to_think_marker_intercepted",
        "curiosity-1",
        "curiosity-2",
        "curiosity-3",
        "curiosity-4",
        "curiosity-p1",
        "curiosity-p2",
        "curiosity-p3",
        "curiosity-p4",
        "private-1",
        "private-2",
        "private-3",
        "pause-reply-1",
        "pause-reply-2",
        "continuity-1",
        "continuity-2",
        "life-1",
        "life-2",
        "life-3",
        "life-adjust-1",
        "life-adjust-2",
        "life-adjust-3",
        "response-error-1",
        "response-error-2",
        "slow-state-1",
        "slow-state-2",
        "current_sticker_question_answered",
        "recent_sticker_question_answered",
        "reply_bubble_force_units:3",
        "private-link-1",
        "private-link-2",
        "private-link-3",
        "persona-1",
        "persona-2",
        "persona-3",
        "persona-4",
        "event-1",
        "event-2",
        "event-3",
        "event-4",
        "v1-1",
        "v1-2",
        "v1-3",
        "v1-4",
        "tiny-1",
        "tiny-2",
        "tiny-3",
        "emotion-1",
        "emotion-2",
        "emotion-3",
        "emotion-4",
        "recall-1",
        "recall-2",
        "recall-3",
        "recall-4",
        "archive-1",
        "archive-2",
        "archive-3",
        "candidate-1",
        "candidate-2",
        "candidate-3",
        "review-1",
        "review-2",
        "review-3",
        "journal-1",
        "journal-2",
        "journal-3",
        "expression-1",
        "expression-2",
        "expression-3",
        "closed-1",
        "closed-2",
        "closed-3",
        "uncertainty-1",
        "uncertainty-2",
        "uncertainty-3",
        "wait-1",
        "wait-2",
        "wait-3",
        "promise-1",
        "promise-2",
        "promise-3",
        "coherence-1",
        "coherence-2",
        "coherence-3",
        "sticker_delivery_tail_recorded",
        "sticker-1",
        "sticker-2",
        "sticker-3",
        "cleaned_idle_sessions:2",
        "dialogue_working_memory_active",
    ]


def test_observe_slow_live_persona_sidecar_returns_observer_result(tmp_path) -> None:
    calls: list[dict[str, object]] = []

    def observer(root, payload, **kwargs):
        calls.append({"root": root, "payload": payload, **kwargs})
        return {"notes": ["persona-ok"], "prompt_block": "persona"}

    payload = {"platform": "qq"}
    result = observe_slow_live_persona_sidecar(
        SimpleNamespace(xinyu_dir=tmp_path),
        payload,
        text="hello",
        observer=observer,
    )

    assert result == {"notes": ["persona-ok"], "prompt_block": "persona"}
    assert calls == [{"root": tmp_path, "payload": payload, "text": "hello"}]


def test_observe_slow_live_persona_sidecar_contains_errors(tmp_path) -> None:
    def observer(*args, **kwargs):
        del args, kwargs
        raise RuntimeError("boom")

    result = observe_slow_live_persona_sidecar(
        SimpleNamespace(xinyu_dir=tmp_path),
        {"platform": "qq"},
        text="hello",
        observer=observer,
    )

    assert result == {"notes": ["persona_state_error:RuntimeError"], "prompt_block": ""}


def test_run_slow_live_emotion_council_shadow_returns_runner_result(tmp_path) -> None:
    calls: list[dict[str, object]] = []

    def runner(root, **kwargs):
        calls.append({"root": root, **kwargs})
        return {"notes": ["emotion-ok"]}

    payload = {"platform": "qq"}
    result = run_slow_live_emotion_council_shadow(
        SimpleNamespace(xinyu_dir=tmp_path),
        payload,
        text="hello",
        checked_at="2026-06-07T01:02:03+08:00",
        runner=runner,
    )

    assert result == {"notes": ["emotion-ok"]}
    assert calls == [
        {
            "root": tmp_path,
            "text": "hello",
            "payload": payload,
            "checked_at": "2026-06-07T01:02:03+08:00",
            "trigger": "live_turn",
        }
    ]


def test_run_slow_live_emotion_council_shadow_contains_errors(tmp_path) -> None:
    def runner(*args, **kwargs):
        del args, kwargs
        raise ValueError("boom")

    result = run_slow_live_emotion_council_shadow(
        SimpleNamespace(xinyu_dir=tmp_path),
        {"platform": "qq"},
        text="hello",
        checked_at="2026-06-07T01:02:03+08:00",
        runner=runner,
    )

    assert result == {"notes": ["emotion_council_error:ValueError"]}


def test_enter_slow_live_route_with_trace_returns_semantic_fast_response(monkeypatch) -> None:
    rows, trace_route_stage = _trace_rows()
    calls: list[tuple[str, object]] = []
    session = SimpleNamespace(name="session")

    async def fake_semantic(runtime, payload, **kwargs):
        calls.append(("semantic", {"payload": payload, **kwargs}))
        return {"accepted": True}

    monkeypatch.setattr(
        slow_live,
        "run_slow_live_emotion_council_shadow",
        lambda runtime, payload, **kwargs: calls.append(("emotion", {"payload": payload, **kwargs}))
        or {"notes": ["emotion"]},
    )
    monkeypatch.setattr(slow_live, "try_pre_slow_semantic_fast_route_with_trace", fake_semantic)
    runtime = SimpleNamespace(
        _get_session=lambda session_key: asyncio.sleep(0, result=session),
        _sync_recent_proactive_to_dialogue_tail=lambda call_session, payload: calls.append(
            ("sync", {"session": call_session, "payload": payload})
        )
        or True,
    )

    result = asyncio.run(
        enter_slow_live_route_with_trace(
            runtime,
            {"scope": "owner"},
            text="hello",
            session_key="qq:private:owner",
            turn_id="turn-1",
            turn_started_wall="2026-05-20T12:00:00+08:00",
            turn_started_at=12.5,
            before_memory={"memory": "before"},
            cleanup={"cleaned_sessions": 0},
            event_sidecar={"notes": ["event"]},
            trace_route_stage=trace_route_stage,
        )
    )

    assert isinstance(result, slow_live.SlowLiveEntryState)
    assert result == {
        "response": {"accepted": True},
        "session": session,
        "proactive_tail_synced": True,
        "emotion_council": {"notes": ["emotion"]},
    }
    assert [name for name, _ in calls] == ["emotion", "sync", "semantic"]
    assert calls[-1][1]["session"] is session
    assert calls[-1][1]["before_memory"] == {"memory": "before"}
    assert rows == []


def test_enter_slow_live_route_with_trace_returns_fallthrough_state(monkeypatch) -> None:
    rows, trace_route_stage = _trace_rows()
    calls: list[tuple[str, object]] = []
    session = SimpleNamespace(name="session")

    async def fake_semantic(runtime, payload, **kwargs):
        calls.append(("semantic", {"payload": payload, **kwargs}))
        return None

    monkeypatch.setattr(slow_live, "run_slow_live_emotion_council_shadow", lambda *args, **kwargs: {"notes": []})
    monkeypatch.setattr(slow_live, "try_pre_slow_semantic_fast_route_with_trace", fake_semantic)
    runtime = SimpleNamespace(
        _get_session=lambda session_key: asyncio.sleep(0, result=session),
        _sync_recent_proactive_to_dialogue_tail=lambda call_session, payload: False,
    )

    result = asyncio.run(
        enter_slow_live_route_with_trace(
            runtime,
            {"scope": "owner"},
            text="hello",
            session_key="qq:private:owner",
            turn_id="turn-1",
            turn_started_wall="2026-05-20T12:00:00+08:00",
            turn_started_at=12.5,
            before_memory={},
            cleanup={},
            event_sidecar={"notes": []},
            trace_route_stage=trace_route_stage,
        )
    )

    assert isinstance(result, slow_live.SlowLiveEntryState)
    assert result == {
        "response": None,
        "session": session,
        "proactive_tail_synced": False,
        "emotion_council": {"notes": []},
    }
    assert calls[0][0] == "semantic"
    assert rows == []


def test_build_slow_live_response_state_records_decision_and_slow_state(tmp_path) -> None:
    calls: list[dict[str, object]] = []
    visible_turn = SimpleNamespace(kind="chat")
    recalled_context = SimpleNamespace(prompt_block="memory block")

    def classifier(root, **kwargs):
        calls.append({"call": "classifier", "root": root, **kwargs})
        return SimpleNamespace(error_class="ok", severity="low")

    def scene_builder(root, **kwargs):
        calls.append({"call": "scene", "root": root, **kwargs})
        return {"scene": "frame"}

    def slow_state_builder(root, **kwargs):
        calls.append({"call": "slow_state", "root": root, **kwargs})
        return SimpleNamespace(reply_policy="warm", initiative_policy="hold", active_policies=["p1", "p2"])

    payload = {"platform": "qq"}
    result = build_slow_live_response_state(
        SimpleNamespace(xinyu_dir=tmp_path),
        payload,
        user_text="hello",
        reply="reply",
        visible_turn=visible_turn,
        recalled_context=recalled_context,
        evaluated_at="2026-06-07T01:02:03+08:00",
        response_classifier=classifier,
        scene_builder=scene_builder,
        slow_state_builder=slow_state_builder,
    )

    assert isinstance(result, slow_live.SlowLiveResponseState)
    assert result == {
        "response_error_loop": {"notes": ["response_error_loop:ok/low"]},
        "slow_state_runtime": {"notes": ["slow_state:warm/hold/p1,p2"]},
    }
    assert calls == [
        {
            "call": "classifier",
            "root": tmp_path,
            "user_text": "hello",
            "current_candidate_reply": "reply",
            "payload": payload,
            "visible_turn": visible_turn,
        },
        {
            "call": "scene",
            "root": tmp_path,
            "user_text": "hello",
            "visible_turn": visible_turn,
            "canonical_recall_context": "memory block",
            "evaluated_at": "2026-06-07T01:02:03+08:00",
        },
        {
            "call": "slow_state",
            "root": tmp_path,
            "user_text": "hello",
            "scene_frame": {"scene": "frame"},
            "response_error_decision": SimpleNamespace(error_class="ok", severity="low"),
            "evaluated_at": "2026-06-07T01:02:03+08:00",
            "persist": True,
        },
    ]


def test_build_slow_live_response_state_contains_errors(tmp_path) -> None:
    def classifier(*args, **kwargs):
        del args, kwargs
        raise RuntimeError("boom")

    result = build_slow_live_response_state(
        SimpleNamespace(xinyu_dir=tmp_path),
        {"platform": "qq"},
        user_text="hello",
        reply="reply",
        visible_turn=SimpleNamespace(kind="chat"),
        recalled_context=SimpleNamespace(prompt_block="memory block"),
        evaluated_at="2026-06-07T01:02:03+08:00",
        response_classifier=classifier,
        scene_builder=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("unexpected")),
        slow_state_builder=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("unexpected")),
    )

    assert isinstance(result, slow_live.SlowLiveResponseState)
    assert result == {
        "response_error_loop": {"notes": ["response_error_loop_error:RuntimeError"]},
        "slow_state_runtime": {"notes": ["slow_state_error:RuntimeError"]},
    }


def test_apply_slow_live_visible_dedupe_updates_agent_when_changed(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    def fake_dedupe(reply: str) -> SimpleNamespace:
        calls.append(("dedupe", reply))
        return SimpleNamespace(changed=True, text="deduped reply", notes=["dedupe-note"])

    monkeypatch.setattr(slow_live, "dedupe_visible_reply", fake_dedupe)
    runtime = SimpleNamespace(
        _replace_last_assistant_message=lambda agent, reply: calls.append(
            ("replace", {"agent": agent, "reply": reply})
        )
    )
    session = SimpleNamespace(agent=object())

    result = apply_slow_live_visible_dedupe(runtime, session, "original reply")

    assert result["reply"] == "deduped reply"
    assert result["visible_dedupe"].notes == ["dedupe-note"]
    assert calls == [
        ("dedupe", "original reply"),
        ("replace", {"agent": session.agent, "reply": "deduped reply"}),
    ]


def test_apply_slow_live_visible_dedupe_keeps_unchanged_reply(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    def fake_dedupe(reply: str) -> SimpleNamespace:
        calls.append(("dedupe", reply))
        return SimpleNamespace(changed=False, text="ignored", notes=[])

    monkeypatch.setattr(slow_live, "dedupe_visible_reply", fake_dedupe)
    runtime = SimpleNamespace(
        _replace_last_assistant_message=lambda *args, **kwargs: calls.append(("replace", args))
    )

    result = apply_slow_live_visible_dedupe(runtime, SimpleNamespace(agent=object()), "original reply")

    assert result["reply"] == "original reply"
    assert result["visible_dedupe"].changed is False
    assert calls == [("dedupe", "original reply")]


def test_apply_slow_live_stale_context_repair_skips_when_delegate_blocked(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    monkeypatch.setattr(
        slow_live.xinyu_bridge_semantic_fast_routes,
        "reply_looks_like_stale_plan_residue",
        lambda reply: calls.append(("detect", reply)) or True,
    )
    monkeypatch.setattr(
        slow_live.xinyu_bridge_semantic_fast_routes,
        "owner_private_direct_repair_reply",
        lambda runtime, text: calls.append(("repair", text)) or "repaired reply",
    )
    runtime = SimpleNamespace(
        _owner_private_payload_matches=lambda payload: True,
        _replace_last_assistant_message=lambda *args: calls.append(("replace", args)),
    )

    result = apply_slow_live_stale_context_repair(
        runtime,
        SimpleNamespace(agent=object()),
        {"scope": "owner"},
        reply="stale reply",
        user_text="now",
        final_guard_flags=["existing"],
        blocked_by_delegate=True,
    )

    assert result == {
        "reply": "stale reply",
        "final_guard_flags": ["existing"],
        "stale_context_reply_replaced": False,
    }
    assert calls == []


def test_apply_slow_live_stale_context_repair_skips_non_owner_private(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    monkeypatch.setattr(
        slow_live.xinyu_bridge_semantic_fast_routes,
        "reply_looks_like_stale_plan_residue",
        lambda reply: calls.append(("detect", reply)) or True,
    )
    monkeypatch.setattr(
        slow_live.xinyu_bridge_semantic_fast_routes,
        "owner_private_direct_repair_reply",
        lambda runtime, text: calls.append(("repair", text)) or "repaired reply",
    )
    runtime = SimpleNamespace(
        _owner_private_payload_matches=lambda payload: False,
        _replace_last_assistant_message=lambda *args: calls.append(("replace", args)),
    )

    result = apply_slow_live_stale_context_repair(
        runtime,
        SimpleNamespace(agent=object()),
        {"scope": "group"},
        reply="stale reply",
        user_text="now",
        final_guard_flags=["existing"],
        blocked_by_delegate=False,
    )

    assert result == {
        "reply": "stale reply",
        "final_guard_flags": ["existing"],
        "stale_context_reply_replaced": False,
    }
    assert calls == []


def test_apply_slow_live_stale_context_repair_replaces_and_dedupes_flag(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []
    agent = object()

    monkeypatch.setattr(
        slow_live.xinyu_bridge_semantic_fast_routes,
        "reply_looks_like_stale_plan_residue",
        lambda reply: calls.append(("detect", reply)) or True,
    )
    monkeypatch.setattr(
        slow_live.xinyu_bridge_semantic_fast_routes,
        "owner_private_direct_repair_reply",
        lambda runtime, text: calls.append(("repair", text)) or "  - repaired reply\n",
    )
    runtime = SimpleNamespace(
        _owner_private_payload_matches=lambda payload: True,
        _replace_last_assistant_message=lambda call_agent, reply: calls.append(
            ("replace", {"agent": call_agent, "reply": reply})
        ),
    )

    result = apply_slow_live_stale_context_repair(
        runtime,
        SimpleNamespace(agent=agent),
        {"scope": "owner"},
        reply="stale reply",
        user_text="now",
        final_guard_flags=["existing", "stale_context_reply_replaced"],
        blocked_by_delegate=False,
    )

    assert result == {
        "reply": "repaired reply",
        "final_guard_flags": ["existing", "stale_context_reply_replaced"],
        "stale_context_reply_replaced": True,
    }
    assert calls == [
        ("detect", "stale reply"),
        ("repair", "now"),
        ("replace", {"agent": agent, "reply": "repaired reply"}),
    ]


def test_apply_slow_live_stale_context_repair_keeps_reply_when_repair_empty(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    monkeypatch.setattr(
        slow_live.xinyu_bridge_semantic_fast_routes,
        "reply_looks_like_stale_plan_residue",
        lambda reply: calls.append(("detect", reply)) or True,
    )
    monkeypatch.setattr(
        slow_live.xinyu_bridge_semantic_fast_routes,
        "owner_private_direct_repair_reply",
        lambda runtime, text: calls.append(("repair", text)) or "",
    )
    runtime = SimpleNamespace(
        _owner_private_payload_matches=lambda payload: True,
        _replace_last_assistant_message=lambda *args: calls.append(("replace", args)),
    )

    result = apply_slow_live_stale_context_repair(
        runtime,
        SimpleNamespace(agent=object()),
        {"scope": "owner"},
        reply="stale reply",
        user_text="now",
        final_guard_flags=["existing"],
        blocked_by_delegate=False,
    )

    assert result == {
        "reply": "stale reply",
        "final_guard_flags": ["existing"],
        "stale_context_reply_replaced": False,
    }
    assert calls == [
        ("detect", "stale reply"),
        ("repair", "now"),
    ]


def test_apply_slow_live_life_reply_policy_skips_when_delegate_blocked(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    monkeypatch.setattr(
        slow_live,
        "apply_life_reply_policy",
        lambda *args, **kwargs: calls.append(("policy", args)) or {"changed": True, "reply": "ignored"},
    )
    runtime = SimpleNamespace(
        _replace_last_assistant_message=lambda *args: calls.append(("replace", args)),
    )

    result = apply_slow_live_life_reply_policy(
        runtime,
        SimpleNamespace(agent=object()),
        reply="original reply",
        user_text="user",
        life_reply_policy={"mode": "steady"},
        blocked_by_delegate=True,
    )

    assert result == {
        "reply": "original reply",
        "life_reply_adjustment": {"notes": []},
    }
    assert calls == []


def test_apply_slow_live_life_reply_policy_keeps_unchanged_reply(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    def fake_apply(reply: str, *, policy: dict[str, object], user_text: str) -> dict[str, object]:
        calls.append(("policy", {"reply": reply, "policy": policy, "user_text": user_text}))
        return {"reply": "ignored reply", "changed": False, "notes": ["steady"]}

    monkeypatch.setattr(slow_live, "apply_life_reply_policy", fake_apply)
    runtime = SimpleNamespace(
        _replace_last_assistant_message=lambda *args: calls.append(("replace", args)),
    )

    result = apply_slow_live_life_reply_policy(
        runtime,
        SimpleNamespace(agent=object()),
        reply="original reply",
        user_text="user",
        life_reply_policy={"mode": "steady"},
        blocked_by_delegate=False,
    )

    assert result == {
        "reply": "original reply",
        "life_reply_adjustment": {"reply": "ignored reply", "changed": False, "notes": ["steady"]},
    }
    assert calls == [
        ("policy", {"reply": "original reply", "policy": {"mode": "steady"}, "user_text": "user"}),
    ]


def test_apply_slow_live_life_reply_policy_replaces_changed_reply(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []
    agent = object()

    def fake_apply(reply: str, *, policy: dict[str, object], user_text: str) -> dict[str, object]:
        calls.append(("policy", {"reply": reply, "policy": policy, "user_text": user_text}))
        return {"reply": "  shorter reply  ", "changed": True, "notes": ["shortened"]}

    monkeypatch.setattr(slow_live, "apply_life_reply_policy", fake_apply)
    runtime = SimpleNamespace(
        _replace_last_assistant_message=lambda call_agent, reply: calls.append(
            ("replace", {"agent": call_agent, "reply": reply})
        ),
    )

    result = apply_slow_live_life_reply_policy(
        runtime,
        SimpleNamespace(agent=agent),
        reply="original reply",
        user_text="user",
        life_reply_policy={"mode": "low_energy"},
        blocked_by_delegate=False,
    )

    assert result == {
        "reply": "shorter reply",
        "life_reply_adjustment": {"reply": "  shorter reply  ", "changed": True, "notes": ["shortened"]},
    }
    assert calls == [
        ("policy", {"reply": "original reply", "policy": {"mode": "low_energy"}, "user_text": "user"}),
        ("replace", {"agent": agent, "reply": "shorter reply"}),
    ]


def test_apply_slow_live_current_reference_repair_skips_non_owner(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    monkeypatch.setattr(
        slow_live,
        "repair_current_reference_reply",
        lambda *args, **kwargs: calls.append(("repair", kwargs)) or {"changed": True, "reply": "ignored"},
    )
    runtime = SimpleNamespace(
        _owner_private_payload_matches=lambda payload: False,
        _replace_last_assistant_message=lambda *args: calls.append(("replace", args)),
    )

    result = apply_slow_live_current_reference_repair(
        runtime,
        SimpleNamespace(agent=object(), dialogue_tail=[]),
        {"scope": "group"},
        reply="original reply",
        user_text="user",
        final_guard_flags=["existing"],
        blocked_by_delegate=False,
    )

    assert result == {
        "reply": "original reply",
        "final_guard_flags": ["existing"],
        "current_reference_repair": {"changed": False, "reply": "original reply", "notes": []},
    }
    assert calls == []


def test_apply_slow_live_current_reference_repair_skips_delegate_blocked(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    monkeypatch.setattr(
        slow_live,
        "repair_current_reference_reply",
        lambda *args, **kwargs: calls.append(("repair", kwargs)) or {"changed": True, "reply": "ignored"},
    )
    runtime = SimpleNamespace(
        _owner_private_payload_matches=lambda payload: True,
        _replace_last_assistant_message=lambda *args: calls.append(("replace", args)),
    )

    result = apply_slow_live_current_reference_repair(
        runtime,
        SimpleNamespace(agent=object(), dialogue_tail=[]),
        {"scope": "owner"},
        reply="original reply",
        user_text="user",
        final_guard_flags=["existing"],
        blocked_by_delegate=True,
    )

    assert result == {
        "reply": "original reply",
        "final_guard_flags": ["existing"],
        "current_reference_repair": {"changed": False, "reply": "original reply", "notes": []},
    }
    assert calls == []


def test_apply_slow_live_current_reference_repair_keeps_unchanged_reply(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []
    dialogue_tail = [{"role": "assistant", "content": "last"}]

    def fake_repair(*, user_text: str, reply: str, dialogue_tail: list[dict[str, str]]) -> dict[str, object]:
        calls.append(("repair", {"user_text": user_text, "reply": reply, "dialogue_tail": dialogue_tail}))
        return {"changed": False, "reply": reply, "notes": ["reply_not_bad_clarification"]}

    monkeypatch.setattr(slow_live, "repair_current_reference_reply", fake_repair)
    runtime = SimpleNamespace(
        _owner_private_payload_matches=lambda payload: True,
        _replace_last_assistant_message=lambda *args: calls.append(("replace", args)),
    )

    result = apply_slow_live_current_reference_repair(
        runtime,
        SimpleNamespace(agent=object(), dialogue_tail=dialogue_tail),
        {"scope": "owner"},
        reply="original reply",
        user_text="user",
        final_guard_flags=["existing"],
        blocked_by_delegate=False,
    )

    assert result == {
        "reply": "original reply",
        "final_guard_flags": ["existing"],
        "current_reference_repair": {
            "changed": False,
            "reply": "original reply",
            "notes": ["reply_not_bad_clarification"],
        },
    }
    assert calls == [
        ("repair", {"user_text": "user", "reply": "original reply", "dialogue_tail": dialogue_tail}),
    ]


def test_apply_slow_live_current_reference_repair_replaces_and_appends_notes(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []
    agent = object()
    dialogue_tail = [{"role": "assistant", "content": "last"}]

    def fake_repair(*, user_text: str, reply: str, dialogue_tail: list[dict[str, str]]) -> dict[str, object]:
        calls.append(("repair", {"user_text": user_text, "reply": reply, "dialogue_tail": dialogue_tail}))
        return {
            "changed": True,
            "reply": "  repaired reply  ",
            "notes": ["current_reference_clarification_repaired", "", "existing"],
        }

    monkeypatch.setattr(slow_live, "repair_current_reference_reply", fake_repair)
    runtime = SimpleNamespace(
        _owner_private_payload_matches=lambda payload: True,
        _replace_last_assistant_message=lambda call_agent, reply: calls.append(
            ("replace", {"agent": call_agent, "reply": reply})
        ),
    )

    result = apply_slow_live_current_reference_repair(
        runtime,
        SimpleNamespace(agent=agent, dialogue_tail=dialogue_tail),
        {"scope": "owner"},
        reply="original reply",
        user_text="user",
        final_guard_flags=["existing"],
        blocked_by_delegate=False,
    )

    assert result == {
        "reply": "repaired reply",
        "final_guard_flags": ["existing", "current_reference_clarification_repaired"],
        "current_reference_repair": {
            "changed": True,
            "reply": "  repaired reply  ",
            "notes": ["current_reference_clarification_repaired", "", "existing"],
        },
    }
    assert calls == [
        ("repair", {"user_text": "user", "reply": "original reply", "dialogue_tail": dialogue_tail}),
        ("replace", {"agent": agent, "reply": "repaired reply"}),
    ]


def test_apply_slow_live_reply_bubble_policy_forces_owner_units() -> None:
    calls: list[tuple[str, object]] = []
    agent = object()
    dialogue_tail = [{"role": "assistant", "content": "last"}]

    runtime = SimpleNamespace(
        _owner_requested_reply_bubble_units=lambda **kwargs: calls.append(("owner_units", kwargs)) or ["one", "two"],
        _looks_like_false_single_bubble_limitation=lambda *args: calls.append(("false_single", args)) or True,
        _replace_last_assistant_message=lambda call_agent, reply: calls.append(
            ("replace", {"agent": call_agent, "reply": reply})
        ),
    )

    result = apply_slow_live_reply_bubble_policy(
        runtime,
        SimpleNamespace(agent=agent),
        reply="original reply",
        user_text="split it",
        dialogue_tail=dialogue_tail,
        final_guard_flags=["existing", "owner_explicit_reply_bubble_units"],
    )

    assert result == {
        "reply": "one two",
        "final_guard_flags": ["existing", "owner_explicit_reply_bubble_units"],
        "reply_bubble_force_units": ["one", "two"],
    }
    assert calls == [
        (
            "owner_units",
            {"user_text": "split it", "reply": "original reply", "dialogue_tail": dialogue_tail},
        ),
        ("replace", {"agent": agent, "reply": "one two"}),
    ]


def test_apply_slow_live_reply_bubble_policy_naturalizes_false_single_limit() -> None:
    calls: list[tuple[str, object]] = []
    agent = object()
    dialogue_tail = [{"role": "assistant", "content": "last"}]

    runtime = SimpleNamespace(
        _owner_requested_reply_bubble_units=lambda **kwargs: calls.append(("owner_units", kwargs)) or [],
        _looks_like_false_single_bubble_limitation=lambda user_text, reply: calls.append(
            ("false_single", {"user_text": user_text, "reply": reply})
        )
        or True,
        _replace_last_assistant_message=lambda call_agent, reply: calls.append(
            ("replace", {"agent": call_agent, "reply": reply})
        ),
    )

    result = apply_slow_live_reply_bubble_policy(
        runtime,
        SimpleNamespace(agent=agent),
        reply="original reply",
        user_text="can you split",
        dialogue_tail=dialogue_tail,
        final_guard_flags=["existing"],
    )

    assert result == {
        "reply": slow_live.FALSE_SINGLE_BUBBLE_REPLY,
        "final_guard_flags": ["existing", "false_single_message_limit_naturalized"],
        "reply_bubble_force_units": [],
    }
    assert calls == [
        (
            "owner_units",
            {"user_text": "can you split", "reply": "original reply", "dialogue_tail": dialogue_tail},
        ),
        ("false_single", {"user_text": "can you split", "reply": "original reply"}),
        ("replace", {"agent": agent, "reply": slow_live.FALSE_SINGLE_BUBBLE_REPLY}),
    ]


def test_apply_slow_live_reply_bubble_policy_keeps_unmatched_reply() -> None:
    calls: list[tuple[str, object]] = []
    dialogue_tail = [{"role": "assistant", "content": "last"}]

    runtime = SimpleNamespace(
        _owner_requested_reply_bubble_units=lambda **kwargs: calls.append(("owner_units", kwargs)) or [],
        _looks_like_false_single_bubble_limitation=lambda user_text, reply: calls.append(
            ("false_single", {"user_text": user_text, "reply": reply})
        )
        or False,
        _replace_last_assistant_message=lambda *args: calls.append(("replace", args)),
    )

    result = apply_slow_live_reply_bubble_policy(
        runtime,
        SimpleNamespace(agent=object()),
        reply="original reply",
        user_text="normal",
        dialogue_tail=dialogue_tail,
        final_guard_flags=["existing"],
    )

    assert result == {
        "reply": "original reply",
        "final_guard_flags": ["existing"],
        "reply_bubble_force_units": [],
    }
    assert calls == [
        ("owner_units", {"user_text": "normal", "reply": "original reply", "dialogue_tail": dialogue_tail}),
        ("false_single", {"user_text": "normal", "reply": "original reply"}),
    ]


def test_apply_slow_live_sticker_reply_override_prefers_current_reply() -> None:
    calls: list[tuple[str, object]] = []
    agent = object()

    runtime = SimpleNamespace(
        _current_sticker_question_reply=lambda user_text, payload: calls.append(
            ("current", {"user_text": user_text, "payload": payload})
        )
        or "current sticker reply",
        _recent_sticker_question_reply=lambda *args: calls.append(("recent", args)) or "recent sticker reply",
        _replace_last_assistant_message=lambda call_agent, reply: calls.append(
            ("replace", {"agent": call_agent, "reply": reply})
        ),
    )

    result = apply_slow_live_sticker_reply_override(
        runtime,
        SimpleNamespace(agent=agent, dialogue_tail=[]),
        {"scope": "owner"},
        reply="original reply",
        user_text="sticker?",
    )

    assert result == {
        "reply": "current sticker reply",
        "current_sticker_reply": "current sticker reply",
        "recent_sticker_reply": "",
    }
    assert calls == [
        ("current", {"user_text": "sticker?", "payload": {"scope": "owner"}}),
        ("replace", {"agent": agent, "reply": "current sticker reply"}),
    ]


def test_apply_slow_live_sticker_reply_override_uses_recent_when_current_empty() -> None:
    calls: list[tuple[str, object]] = []
    agent = object()
    dialogue_tail = [{"role": "assistant", "content": "last"}]

    runtime = SimpleNamespace(
        _current_sticker_question_reply=lambda user_text, payload: calls.append(
            ("current", {"user_text": user_text, "payload": payload})
        )
        or "",
        _recent_sticker_question_reply=lambda user_text, tail: calls.append(
            ("recent", {"user_text": user_text, "dialogue_tail": tail})
        )
        or "recent sticker reply",
        _replace_last_assistant_message=lambda call_agent, reply: calls.append(
            ("replace", {"agent": call_agent, "reply": reply})
        ),
    )

    result = apply_slow_live_sticker_reply_override(
        runtime,
        SimpleNamespace(agent=agent, dialogue_tail=dialogue_tail),
        {"scope": "owner"},
        reply="original reply",
        user_text="sticker?",
    )

    assert result == {
        "reply": "recent sticker reply",
        "current_sticker_reply": "",
        "recent_sticker_reply": "recent sticker reply",
    }
    assert calls == [
        ("current", {"user_text": "sticker?", "payload": {"scope": "owner"}}),
        ("recent", {"user_text": "sticker?", "dialogue_tail": dialogue_tail}),
        ("replace", {"agent": agent, "reply": "recent sticker reply"}),
    ]


def test_apply_slow_live_sticker_reply_override_keeps_reply_without_match() -> None:
    calls: list[tuple[str, object]] = []
    dialogue_tail = [{"role": "assistant", "content": "last"}]

    runtime = SimpleNamespace(
        _current_sticker_question_reply=lambda user_text, payload: calls.append(
            ("current", {"user_text": user_text, "payload": payload})
        )
        or "",
        _recent_sticker_question_reply=lambda user_text, tail: calls.append(
            ("recent", {"user_text": user_text, "dialogue_tail": tail})
        )
        or "",
        _replace_last_assistant_message=lambda *args: calls.append(("replace", args)),
    )

    result = apply_slow_live_sticker_reply_override(
        runtime,
        SimpleNamespace(agent=object(), dialogue_tail=dialogue_tail),
        {"scope": "owner"},
        reply="original reply",
        user_text="normal",
    )

    assert result == {
        "reply": "original reply",
        "current_sticker_reply": "",
        "recent_sticker_reply": "",
    }
    assert calls == [
        ("current", {"user_text": "normal", "payload": {"scope": "owner"}}),
        ("recent", {"user_text": "normal", "dialogue_tail": dialogue_tail}),
    ]


def test_apply_slow_live_style_pressure_empty_fallback_applies_when_empty() -> None:
    calls: list[tuple[str, object]] = []
    agent = object()
    runtime = SimpleNamespace(
        _replace_last_assistant_message=lambda call_agent, reply: calls.append(
            ("replace", {"agent": call_agent, "reply": reply})
        ),
    )

    result = apply_slow_live_style_pressure_empty_fallback(
        runtime,
        SimpleNamespace(agent=agent),
        reply="",
        final_guard_flags=["style_pressure_template_blocked", "style_pressure_empty_reply_fallback"],
    )

    assert result == {
        "reply": slow_live.STYLE_PRESSURE_EMPTY_REPLY,
        "final_guard_flags": ["style_pressure_template_blocked", "style_pressure_empty_reply_fallback"],
    }
    assert calls == [("replace", {"agent": agent, "reply": slow_live.STYLE_PRESSURE_EMPTY_REPLY})]


def test_apply_slow_live_style_pressure_empty_fallback_skips_non_empty_reply() -> None:
    calls: list[tuple[str, object]] = []
    runtime = SimpleNamespace(
        _replace_last_assistant_message=lambda *args: calls.append(("replace", args)),
    )

    result = apply_slow_live_style_pressure_empty_fallback(
        runtime,
        SimpleNamespace(agent=object()),
        reply="existing reply",
        final_guard_flags=["style_pressure_template_blocked"],
    )

    assert result == {
        "reply": "existing reply",
        "final_guard_flags": ["style_pressure_template_blocked"],
    }
    assert calls == []


def test_apply_slow_live_style_pressure_empty_fallback_skips_without_flag() -> None:
    calls: list[tuple[str, object]] = []
    runtime = SimpleNamespace(
        _replace_last_assistant_message=lambda *args: calls.append(("replace", args)),
    )

    result = apply_slow_live_style_pressure_empty_fallback(
        runtime,
        SimpleNamespace(agent=object()),
        reply="",
        final_guard_flags=["other"],
    )

    assert result == {"reply": "", "final_guard_flags": ["other"]}
    assert calls == []


def test_recover_slow_live_empty_visible_reply_uses_retry_success() -> None:
    calls: list[tuple[str, object]] = []
    agent = object()

    async def recover(agent_arg, **kwargs):
        calls.append(("recover", {"agent": agent_arg, **kwargs}))
        return "recovered reply", ["empty_retry", "existing"]

    runtime = SimpleNamespace(
        _owner_private_payload_matches=lambda payload: calls.append(("owner", payload)) or True,
        _recover_empty_visible_reply=recover,
        _empty_visible_reply_fallback=lambda **kwargs: calls.append(("fallback", kwargs)) or "fallback reply",
        _replace_last_assistant_message=lambda call_agent, reply: calls.append(
            ("replace", {"agent": call_agent, "reply": reply})
        ),
    )

    result = asyncio.run(
        recover_slow_live_empty_visible_reply(
            runtime,
            SimpleNamespace(agent=agent),
            {"scope": "owner"},
            reply="",
            user_text="user",
            final_guard_flags=["existing"],
            rendered=False,
            renderer_reason="",
            recalled_context=SimpleNamespace(prompt_block="memory block"),
            blocked_by_delegate=False,
        )
    )

    assert result == {
        "reply": "recovered reply",
        "final_guard_flags": ["existing", "empty_retry"],
        "rendered": True,
        "renderer_reason": "empty_visible_reply_retry",
        "empty_visible_reply_no_fallback": False,
    }
    assert calls == [
        ("owner", {"scope": "owner"}),
        (
            "recover",
            {
                "agent": agent,
                "payload": {"scope": "owner"},
                "user_text": "user",
                "canonical_recall_context": "memory block",
            },
        ),
        ("replace", {"agent": agent, "reply": "recovered reply"}),
    ]


def test_recover_slow_live_empty_visible_reply_skips_retry_when_blocked_and_uses_fallback() -> None:
    calls: list[tuple[str, object]] = []
    agent = object()

    async def recover(*args, **kwargs):
        calls.append(("recover", {"args": args, "kwargs": kwargs}))
        return "recovered reply", []

    runtime = SimpleNamespace(
        _owner_private_payload_matches=lambda payload: calls.append(("owner", payload)) or True,
        _recover_empty_visible_reply=recover,
        _empty_visible_reply_fallback=lambda **kwargs: calls.append(("fallback", kwargs)) or "fallback reply",
        _replace_last_assistant_message=lambda call_agent, reply: calls.append(
            ("replace", {"agent": call_agent, "reply": reply})
        ),
    )

    result = asyncio.run(
        recover_slow_live_empty_visible_reply(
            runtime,
            SimpleNamespace(agent=agent),
            {"scope": "owner"},
            reply="",
            user_text="user",
            final_guard_flags=["existing"],
            rendered=False,
            renderer_reason="kept_reason",
            recalled_context=SimpleNamespace(prompt_block="memory block"),
            blocked_by_delegate=True,
        )
    )

    assert result == {
        "reply": "fallback reply",
        "final_guard_flags": ["existing", "empty_visible_reply_fallback"],
        "rendered": False,
        "renderer_reason": "kept_reason",
        "empty_visible_reply_no_fallback": False,
    }
    assert calls == [
        ("owner", {"scope": "owner"}),
        ("fallback", {"payload": {"scope": "owner"}, "user_text": "user"}),
        ("replace", {"agent": agent, "reply": "fallback reply"}),
    ]


def test_recover_slow_live_empty_visible_reply_marks_no_fallback_when_all_empty() -> None:
    calls: list[tuple[str, object]] = []
    agent = object()

    async def recover(agent_arg, **kwargs):
        calls.append(("recover", {"agent": agent_arg, **kwargs}))
        return "", ["empty_retry"]

    runtime = SimpleNamespace(
        _owner_private_payload_matches=lambda payload: calls.append(("owner", payload)) or True,
        _recover_empty_visible_reply=recover,
        _empty_visible_reply_fallback=lambda **kwargs: calls.append(("fallback", kwargs)) or "",
        _replace_last_assistant_message=lambda *args: calls.append(("replace", args)),
    )

    result = asyncio.run(
        recover_slow_live_empty_visible_reply(
            runtime,
            SimpleNamespace(agent=agent),
            {"scope": "owner"},
            reply="",
            user_text="user",
            final_guard_flags=["existing"],
            rendered=False,
            renderer_reason="",
            recalled_context=SimpleNamespace(prompt_block="memory block"),
            blocked_by_delegate=False,
        )
    )

    assert result == {
        "reply": "",
        "final_guard_flags": ["existing", "empty_retry"],
        "rendered": False,
        "renderer_reason": "",
        "empty_visible_reply_no_fallback": True,
    }
    assert calls == [
        ("owner", {"scope": "owner"}),
        (
            "recover",
            {
                "agent": agent,
                "payload": {"scope": "owner"},
                "user_text": "user",
                "canonical_recall_context": "memory block",
            },
        ),
        ("fallback", {"payload": {"scope": "owner"}, "user_text": "user"}),
        ("owner", {"scope": "owner"}),
    ]


def test_recover_slow_live_empty_visible_reply_keeps_non_empty_reply() -> None:
    calls: list[tuple[str, object]] = []

    async def recover(*args, **kwargs):
        calls.append(("recover", {"args": args, "kwargs": kwargs}))
        return "ignored", []

    runtime = SimpleNamespace(
        _owner_private_payload_matches=lambda payload: calls.append(("owner", payload)) or True,
        _recover_empty_visible_reply=recover,
        _empty_visible_reply_fallback=lambda **kwargs: calls.append(("fallback", kwargs)) or "fallback",
        _replace_last_assistant_message=lambda *args: calls.append(("replace", args)),
    )

    result = asyncio.run(
        recover_slow_live_empty_visible_reply(
            runtime,
            SimpleNamespace(agent=object()),
            {"scope": "owner"},
            reply="existing reply",
            user_text="user",
            final_guard_flags=["existing"],
            rendered=True,
            renderer_reason="already_rendered",
            recalled_context=SimpleNamespace(prompt_block="memory block"),
            blocked_by_delegate=False,
        )
    )

    assert result == {
        "reply": "existing reply",
        "final_guard_flags": ["existing"],
        "rendered": True,
        "renderer_reason": "already_rendered",
        "empty_visible_reply_no_fallback": False,
    }
    assert calls == []


def test_apply_slow_live_outward_renderer_skips_when_blocked() -> None:
    calls: list[tuple[str, object]] = []
    rows, trace_route_stage = _trace_rows()

    runtime = SimpleNamespace(
        outward_renderer=True,
        _renderer_reason=lambda **kwargs: calls.append(("reason", kwargs)) or "reason",
        _render_outward_reply=object(),
        _replace_last_assistant_message=lambda *args: calls.append(("replace", args)),
    )

    result = asyncio.run(
        apply_slow_live_outward_renderer(
            runtime,
            SimpleNamespace(agent=object()),
            {"scope": "owner"},
            reply="original reply",
            draft_reply="draft reply",
            user_text="user",
            recalled_context=SimpleNamespace(prompt_block="memory block"),
            trace_route_stage=trace_route_stage,
            blocked_by_delegate=True,
        )
    )

    assert result == {"reply": "original reply", "rendered": False, "renderer_reason": ""}
    assert rows == []
    assert calls == []


def test_apply_slow_live_outward_renderer_keeps_reply_without_reason() -> None:
    calls: list[tuple[str, object]] = []
    rows, trace_route_stage = _trace_rows()

    runtime = SimpleNamespace(
        outward_renderer=True,
        _renderer_reason=lambda **kwargs: calls.append(("reason", kwargs)) or "",
        _render_outward_reply=object(),
        _replace_last_assistant_message=lambda *args: calls.append(("replace", args)),
    )

    result = asyncio.run(
        apply_slow_live_outward_renderer(
            runtime,
            SimpleNamespace(agent=object()),
            {"scope": "owner"},
            reply="original reply",
            draft_reply="draft reply",
            user_text="user",
            recalled_context=SimpleNamespace(prompt_block="memory block"),
            trace_route_stage=trace_route_stage,
            blocked_by_delegate=False,
        )
    )

    assert result == {"reply": "original reply", "rendered": False, "renderer_reason": ""}
    assert rows == []
    assert calls == [
        (
            "reason",
            {"payload": {"scope": "owner"}, "user_text": "user", "draft_reply": "draft reply"},
        )
    ]


def test_apply_slow_live_outward_renderer_replaces_rendered_reply(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []
    rows, trace_route_stage = _trace_rows()
    agent = object()
    render_callable = object()

    async def fake_render(renderer, agent_arg, **kwargs):
        calls.append(("render", {"renderer": renderer, "agent": agent_arg, **kwargs}))
        return "rendered reply"

    monkeypatch.setattr(slow_live, "render_outward_reply_with_trace", fake_render)
    runtime = SimpleNamespace(
        outward_renderer=True,
        _renderer_reason=lambda **kwargs: calls.append(("reason", kwargs)) or "owner_pressure",
        _render_outward_reply=render_callable,
        _replace_last_assistant_message=lambda call_agent, reply: calls.append(
            ("replace", {"agent": call_agent, "reply": reply})
        ),
    )

    result = asyncio.run(
        apply_slow_live_outward_renderer(
            runtime,
            SimpleNamespace(agent=agent),
            {"scope": "owner"},
            reply="original reply",
            draft_reply="draft reply",
            user_text="user",
            recalled_context=SimpleNamespace(prompt_block="memory block"),
            trace_route_stage=trace_route_stage,
            blocked_by_delegate=False,
        )
    )

    assert result == {"reply": "rendered reply", "rendered": True, "renderer_reason": "owner_pressure"}
    assert rows == []
    assert calls == [
        (
            "reason",
            {"payload": {"scope": "owner"}, "user_text": "user", "draft_reply": "draft reply"},
        ),
        (
            "render",
            {
                "renderer": render_callable,
                "agent": agent,
                "payload": {"scope": "owner"},
                "user_text": "user",
                "draft_reply": "draft reply",
                "canonical_recall_context": "memory block",
                "reason": "owner_pressure",
                "trace_route_stage": trace_route_stage,
            },
        ),
        ("replace", {"agent": agent, "reply": "rendered reply"}),
    ]


def test_apply_slow_live_reply_adjustment_pipeline_preserves_helper_order(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []
    rows, trace_route_stage = _trace_rows()
    visible_dedupe = SimpleNamespace(notes=["dedupe-note"])

    async def fake_outward(runtime, session, payload, **kwargs):
        calls.append(("outward", kwargs))
        return {"reply": kwargs["reply"] + "|out", "rendered": True, "renderer_reason": "render-reason"}

    async def fake_guard(runtime, session, payload, **kwargs):
        calls.append(("guard", kwargs))
        return {
            "reply": kwargs["reply"] + "|guard",
            "final_guard_flags": ["guard"],
            "final_guard_applied": True,
            "expression_learning": {"notes": ["expr"]},
        }

    def fake_dedupe(runtime, session, reply):
        calls.append(("dedupe", reply))
        return {"reply": reply + "|dedupe", "visible_dedupe": visible_dedupe}

    def fake_stale(runtime, session, payload, **kwargs):
        calls.append(("stale", kwargs))
        return {
            "reply": kwargs["reply"] + "|stale",
            "final_guard_flags": kwargs["final_guard_flags"] + ["stale"],
            "stale_context_reply_replaced": True,
        }

    def fake_life(runtime, session, **kwargs):
        calls.append(("life", kwargs))
        return {"reply": kwargs["reply"] + "|life", "life_reply_adjustment": {"notes": ["life"]}}

    def fake_current(runtime, session, payload, **kwargs):
        calls.append(("current", kwargs))
        return {"reply": kwargs["reply"] + "|current", "final_guard_flags": kwargs["final_guard_flags"] + ["current"]}

    def fake_bubble(runtime, session, **kwargs):
        calls.append(("bubble", kwargs))
        return {
            "reply": kwargs["reply"] + "|bubble",
            "final_guard_flags": kwargs["final_guard_flags"] + ["bubble"],
            "reply_bubble_force_units": ["one"],
        }

    def fake_sticker(runtime, session, payload, **kwargs):
        calls.append(("sticker", kwargs))
        return {
            "reply": kwargs["reply"] + "|sticker",
            "current_sticker_reply": "current sticker",
            "recent_sticker_reply": "",
        }

    def fake_style(runtime, session, **kwargs):
        calls.append(("style", kwargs))
        return {"reply": kwargs["reply"] + "|style", "final_guard_flags": kwargs["final_guard_flags"] + ["style"]}

    async def fake_empty(runtime, session, payload, **kwargs):
        calls.append(("empty", kwargs))
        return {
            "reply": kwargs["reply"] + "|empty",
            "final_guard_flags": kwargs["final_guard_flags"] + ["empty"],
            "rendered": kwargs["rendered"],
            "renderer_reason": kwargs["renderer_reason"],
            "empty_visible_reply_no_fallback": False,
        }

    monkeypatch.setattr(slow_live, "apply_slow_live_outward_renderer", fake_outward)
    monkeypatch.setattr(slow_live, "apply_slow_live_final_reply_guard", fake_guard)
    monkeypatch.setattr(slow_live, "apply_slow_live_visible_dedupe", fake_dedupe)
    monkeypatch.setattr(slow_live, "apply_slow_live_stale_context_repair", fake_stale)
    monkeypatch.setattr(slow_live, "apply_slow_live_life_reply_policy", fake_life)
    monkeypatch.setattr(slow_live, "apply_slow_live_current_reference_repair", fake_current)
    monkeypatch.setattr(slow_live, "apply_slow_live_reply_bubble_policy", fake_bubble)
    monkeypatch.setattr(slow_live, "apply_slow_live_sticker_reply_override", fake_sticker)
    monkeypatch.setattr(slow_live, "apply_slow_live_style_pressure_empty_fallback", fake_style)
    monkeypatch.setattr(slow_live, "recover_slow_live_empty_visible_reply", fake_empty)

    session = SimpleNamespace(agent=object(), dialogue_tail=[{"role": "assistant", "content": "tail"}])
    recalled_context = SimpleNamespace(prompt_block="memory block")
    result = asyncio.run(
        apply_slow_live_reply_adjustment_pipeline(
            SimpleNamespace(),
            session,
            {"scope": "owner"},
            reply="start",
            draft_reply="draft",
            user_text="user",
            recalled_context=recalled_context,
            life_reply_policy={"mode": "steady"},
            trace_route_stage=trace_route_stage,
            blocked_by_delegate=True,
            codex_delegate_blocked=False,
        )
    )

    assert result == {
        "reply": "start|out|guard|dedupe|stale|life|current|bubble|sticker|style|empty",
        "rendered": True,
        "renderer_reason": "render-reason",
        "final_guard_flags": ["guard", "stale", "current", "bubble", "style", "empty"],
        "final_guard_applied": True,
        "expression_learning": {"notes": ["expr"]},
        "visible_dedupe": visible_dedupe,
        "stale_context_reply_replaced": True,
        "life_reply_adjustment": {"notes": ["life"]},
        "current_sticker_reply": "current sticker",
        "recent_sticker_reply": "",
        "reply_bubble_force_units": ["one"],
        "empty_visible_reply_no_fallback": False,
    }
    assert [name for name, _ in calls] == [
        "outward",
        "guard",
        "dedupe",
        "stale",
        "life",
        "current",
        "bubble",
        "sticker",
        "style",
        "empty",
    ]
    assert calls[0][1]["blocked_by_delegate"] is True
    assert calls[1][1]["codex_delegate_blocked"] is False
    assert calls[3][1]["blocked_by_delegate"] is True
    assert calls[4][1]["blocked_by_delegate"] is True
    assert calls[5][1]["blocked_by_delegate"] is True
    assert calls[-1][1]["blocked_by_delegate"] is True
    assert rows == []


def test_prepare_slow_live_post_model_reply_state_threads_codex_adjustment_and_response(
    monkeypatch,
) -> None:
    calls: list[tuple[str, object]] = []
    rows, trace_route_stage = _trace_rows()
    session = SimpleNamespace(chunks=["  draft reply  "], dialogue_tail=[], agent=object())
    recalled_context = SimpleNamespace(prompt_block="memory")
    visible_turn = SimpleNamespace(kind="chat")
    visible_dedupe = SimpleNamespace(notes=["dedupe-note"])

    async def fake_codex(runtime, session_arg, payload, **kwargs):
        calls.append(("codex", {"session": session_arg, "payload": payload, **kwargs}))
        return {
            "reply": "codex reply",
            "direct_codex_task": "direct task",
            "wait_to_think_sidecar": {"notes": ["wait"]},
            "model_codex_delegate_note": "delegate-note",
        }

    async def fake_adjust(runtime, session_arg, payload, **kwargs):
        calls.append(("adjust", {"session": session_arg, "payload": payload, **kwargs}))
        return {
            "reply": "adjusted reply",
            "rendered": True,
            "renderer_reason": "reason",
            "final_guard_flags": ["guard"],
            "final_guard_applied": True,
            "expression_learning": {"notes": ["expr"]},
            "visible_dedupe": visible_dedupe,
            "stale_context_reply_replaced": True,
            "life_reply_adjustment": {"notes": ["life-adjust"]},
            "current_sticker_reply": "current sticker",
            "recent_sticker_reply": "",
            "reply_bubble_force_units": ["one"],
            "empty_visible_reply_no_fallback": False,
        }

    def fake_response(runtime, payload, **kwargs):
        calls.append(("response", {"payload": payload, **kwargs}))
        return {
            "response_error_loop": {"notes": ["response"]},
            "slow_state_runtime": {"notes": ["slow"]},
        }

    monkeypatch.setattr(slow_live.time, "time", lambda: 123.4)
    monkeypatch.setattr(slow_live.xinyu_bridge_codex_runtime, "apply_chat_codex_reply_delegates", fake_codex)
    monkeypatch.setattr(slow_live, "apply_slow_live_reply_adjustment_pipeline", fake_adjust)
    monkeypatch.setattr(slow_live, "build_slow_live_response_state", fake_response)
    runtime = SimpleNamespace(
        _extract_model_codex_delegate=lambda draft: calls.append(("model_task", draft)) or "model task",
        _extract_wait_to_think_task=lambda draft, **kwargs: calls.append(("wait_task", {"draft": draft, **kwargs}))
        or "wait task",
        _owner_self_code_iteration_task=lambda payload, **kwargs: calls.append(
            ("self_task", {"payload": payload, **kwargs})
        )
        or "self task",
    )

    result = asyncio.run(
        prepare_slow_live_post_model_reply_state(
            runtime,
            session,
            {"scope": "owner"},
            text="user",
            session_key="qq:private:owner",
            recalled_context=recalled_context,
            life_reply_policy={"mode": "steady"},
            visible_turn=visible_turn,
            evaluated_at="2026-05-20T12:00:00+08:00",
            trace_route_stage=trace_route_stage,
        )
    )

    assert session.last_used_at == 123.4
    assert isinstance(result, slow_live.SlowLivePostModelReplyState)
    assert result == {
        "draft_reply": "draft reply",
        "reply": "adjusted reply",
        "self_code_task": "self task",
        "direct_codex_task": "direct task",
        "model_codex_task": "model task",
        "wait_to_think_task": "wait task",
        "model_codex_delegate_note": "delegate-note",
        "wait_to_think_sidecar": {"notes": ["wait"]},
        "rendered": True,
        "renderer_reason": "reason",
        "final_guard_flags": ["guard"],
        "final_guard_applied": True,
        "expression_learning": {"notes": ["expr"]},
        "visible_dedupe": visible_dedupe,
        "stale_context_reply_replaced": True,
        "life_reply_adjustment": {"notes": ["life-adjust"]},
        "current_sticker_reply": "current sticker",
        "recent_sticker_reply": "",
        "reply_bubble_force_units": ["one"],
        "empty_visible_reply_no_fallback": False,
        "response_error_loop": {"notes": ["response"]},
        "slow_state_runtime": {"notes": ["slow"]},
    }
    assert [name for name, _ in calls] == [
        "model_task",
        "wait_task",
        "self_task",
        "codex",
        "adjust",
        "response",
    ]
    assert calls[3][1]["draft_reply"] == "draft reply"
    assert calls[3][1]["self_code_task"] == "self task"
    assert calls[4][1]["reply"] == "codex reply"
    assert calls[4][1]["blocked_by_delegate"] is True
    assert calls[4][1]["codex_delegate_blocked"] is True
    assert calls[5][1]["reply"] == "adjusted reply"
    assert rows == []


def test_prepare_slow_live_post_model_reply_state_for_turn_threads_model_turn(
    monkeypatch,
) -> None:
    calls: list[dict[str, object]] = []
    rows, trace_route_stage = _trace_rows()
    runtime = SimpleNamespace()
    session = SimpleNamespace()
    payload = {"scope": "owner"}
    recalled_context = SimpleNamespace(prompt_block="memory")
    life_reply_policy = {"mode": "steady"}
    visible_turn = SimpleNamespace(kind="chat")

    async def fake_prepare(runtime_arg, session_arg, payload_arg, **kwargs):
        calls.append(
            {
                "runtime": runtime_arg,
                "session": session_arg,
                "payload": payload_arg,
                **kwargs,
            }
        )
        return {"reply": "ready"}

    monkeypatch.setattr(slow_live, "prepare_slow_live_post_model_reply_state", fake_prepare)

    result = asyncio.run(
        prepare_slow_live_post_model_reply_state_for_turn(
            runtime,
            session,
            payload,
            text="user",
            session_key="qq:private:owner",
            model_turn={
                "recalled_context": recalled_context,
                "life_reply_policy": life_reply_policy,
                "visible_turn": visible_turn,
            },
            evaluated_at="2026-05-20T12:00:00+08:00",
            trace_route_stage=trace_route_stage,
        )
    )

    assert result == {"reply": "ready"}
    assert calls[0]["runtime"] is runtime
    assert calls[0]["session"] is session
    assert calls[0]["payload"] is payload
    assert calls[0]["recalled_context"] is recalled_context
    assert calls[0]["life_reply_policy"] is life_reply_policy
    assert calls[0]["visible_turn"] is visible_turn
    assert rows == []


def test_finish_and_publish_slow_live_success_turn_threads_sidecars_notes_and_publish(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []
    rows, trace_route_stage = _trace_rows()
    session = SimpleNamespace(agent=object(), dialogue_tail=[])
    recalled_context = SimpleNamespace(prompt_block="memory block")
    visible_dedupe = SimpleNamespace(notes=["dedupe-note"])

    async def fake_finish(runtime, *, sidecars_runner, trace_route_stage, **kwargs):
        calls.append(
            (
                "finish",
                {
                    "sidecars_runner": sidecars_runner,
                    "turn_id": kwargs["turn_id"],
                    "reply": kwargs["reply"],
                    "final_guard_flags": kwargs["final_guard_flags"],
                    "wait_to_think_sidecar": kwargs["wait_to_think_sidecar"],
                },
            )
        )
        return {
            "archive_result": {"message_ids": ["user-msg", "assistant-msg"]},
            "after_memory": {"memory": "after"},
            "notes": ["finish-note"],
        }

    def fake_notes(**kwargs):
        calls.append(
            (
                "notes",
                {
                    "reply": kwargs["reply"],
                    "outward_renderer": kwargs["outward_renderer"],
                    "renderer_mode": kwargs["renderer_mode"],
                    "stale_context_reply_replaced": kwargs["stale_context_reply_replaced"],
                    "visible_dedupe": kwargs["visible_dedupe"],
                    "finish_sidecars": kwargs["finish_sidecars"],
                    "session": kwargs["session"],
                },
            )
        )
        return ["success-note"]

    async def fake_publish(runtime, payload, **kwargs):
        calls.append(
            (
                "publish",
                {
                    "payload": payload,
                    "turn_id": kwargs["turn_id"],
                    "after_memory": kwargs["after_memory"],
                    "notes": kwargs["notes"],
                    "archive_result": kwargs["archive_result"],
                    "reply_bubble_force_units": kwargs["reply_bubble_force_units"],
                },
            )
        )
        return {"accepted": True, "reply": kwargs["reply"], "turn_id": kwargs["turn_id"]}

    monkeypatch.setattr(slow_live, "run_slow_live_finish_sidecars_with_trace", fake_finish)
    monkeypatch.setattr(slow_live, "build_slow_live_success_notes", fake_notes)
    monkeypatch.setattr(slow_live, "publish_slow_live_success_turn", fake_publish)
    runtime = SimpleNamespace(outward_renderer=True, renderer_mode="live")

    result = asyncio.run(
        finish_and_publish_slow_live_success_turn(
            runtime,
            {"scope": "owner"},
            text="user",
            reply="reply",
            draft_reply="draft",
            session=session,
            session_key="qq:private:owner",
            turn_id="turn-finish",
            publish_turn_id="turn-publish",
            turn_started_wall="2026-05-20T12:00:00+08:00",
            turn_started_at=12.5,
            before_memory={"memory": "before"},
            visible_turn=SimpleNamespace(kind="chat"),
            final_guard_flags=["guard"],
            final_guard_applied=True,
            stale_context_reply_replaced=True,
            expression_learning={"notes": ["expr"]},
            recalled_context=recalled_context,
            recalled_context_event={"id": "recall-1"},
            recalled_context_notes=["recall-note"],
            private_thought_outcome={"notes": ["private"]},
            emotion_council={"notes": ["emotion"]},
            persona_sidecar={"notes": ["persona"]},
            continuity_handoff={"notes": ["continuity"]},
            wait_to_think_sidecar={"notes": ["wait"]},
            self_code_task="",
            direct_codex_task="",
            model_codex_task="",
            wait_to_think_task="",
            model_codex_delegate_note="",
            empty_visible_reply_no_fallback=False,
            rendered=True,
            renderer_reason="reason",
            visible_dedupe=visible_dedupe,
            proactive_tail_synced=True,
            curiosity_eval={"notes": ["curiosity"]},
            uncertainty_pause_reply={"notes": ["pause"]},
            life_reply_policy={"notes": ["life-policy"]},
            life_reply_adjustment={"notes": ["life-adjust"]},
            response_error_loop={"notes": ["response-error"]},
            slow_state_runtime={"notes": ["slow-state"]},
            current_sticker_reply="",
            recent_sticker_reply="",
            reply_bubble_force_units=["one"],
            event_sidecar={"notes": ["event"]},
            v1_shadow={"notes": ["v1"]},
            tinykernel_shadow={"notes": ["tiny"]},
            cleanup={"cleaned_sessions": 0},
            trace_route_stage=trace_route_stage,
        )
    )

    assert result == {"accepted": True, "reply": "reply", "turn_id": "turn-publish"}
    assert [name for name, _ in calls] == ["finish", "notes", "publish"]
    assert calls[0][1]["turn_id"] == "turn-finish"
    assert calls[0][1]["final_guard_flags"] == ["guard"]
    assert calls[1][1]["outward_renderer"] is True
    assert calls[1][1]["renderer_mode"] == "live"
    assert calls[1][1]["stale_context_reply_replaced"] is True
    assert calls[1][1]["visible_dedupe"] is visible_dedupe
    assert calls[1][1]["finish_sidecars"]["archive_result"]["message_ids"] == ["user-msg", "assistant-msg"]
    assert calls[2][1] == {
        "payload": {"scope": "owner"},
        "turn_id": "turn-publish",
        "after_memory": {"memory": "after"},
        "notes": ["success-note"],
        "archive_result": {"message_ids": ["user-msg", "assistant-msg"]},
        "reply_bubble_force_units": ["one"],
    }


def test_finish_prepared_slow_live_success_turn_maps_stage_results(monkeypatch) -> None:
    calls: list[dict[str, object]] = []
    rows, trace_route_stage = _trace_rows()
    runtime = SimpleNamespace()
    payload = {"scope": "owner"}
    session = SimpleNamespace(agent=object(), dialogue_tail=[])
    visible_turn = SimpleNamespace(kind="chat")
    recalled_context = SimpleNamespace(prompt_block="memory block")
    visible_dedupe = SimpleNamespace(notes=["dedupe-note"])

    async def fake_finish(runtime_arg, payload_arg, **kwargs):
        calls.append({"runtime": runtime_arg, "payload": payload_arg, **kwargs})
        return {"accepted": True, "reply": kwargs["reply"], "turn_id": kwargs["publish_turn_id"]}

    monkeypatch.setattr(slow_live, "finish_and_publish_slow_live_success_turn", fake_finish)

    pre_model_phase = {
        "before_memory": {"memory": "before"},
        "curiosity_eval": {"notes": ["curiosity"]},
        "private_thought_outcome": {"notes": ["private"]},
        "uncertainty_pause_reply": {"notes": ["pause"]},
        "event_sidecar": {"notes": ["event"]},
        "v1_shadow": {"notes": ["v1"]},
        "tinykernel_shadow": {"notes": ["tiny"]},
    }
    slow_live_entry = {
        "session": session,
        "proactive_tail_synced": True,
        "emotion_council": {"notes": ["emotion"]},
    }
    model_turn = slow_live.SlowLiveModelTurnState(
        visible_turn=visible_turn,
        recalled_context=recalled_context,
        recalled_context_event={"id": "recall-1"},
        recalled_context_notes=["recall-note"],
        continuity_handoff={"notes": ["continuity"]},
        runtime_presence_context="presence",
        life_reply_policy={"notes": ["life-policy"]},
        emotion_council_context="emotion",
        persona_sidecar={"notes": ["persona"]},
    )
    post_model_reply = slow_live.SlowLivePostModelReplyState(
        reply="reply",
        draft_reply="draft",
        final_guard_flags=["guard"],
        final_guard_applied=True,
        stale_context_reply_replaced=True,
        expression_learning={"notes": ["expr"]},
        wait_to_think_sidecar={"notes": ["wait"]},
        self_code_task="",
        direct_codex_task="",
        model_codex_task="",
        wait_to_think_task="",
        model_codex_delegate_note="",
        empty_visible_reply_no_fallback=False,
        rendered=True,
        renderer_reason="reason",
        visible_dedupe=visible_dedupe,
        life_reply_adjustment={"notes": ["life-adjust"]},
        response_error_loop={"notes": ["response-error"]},
        slow_state_runtime={"notes": ["slow-state"]},
        current_sticker_reply="",
        recent_sticker_reply="",
        reply_bubble_force_units=["one"],
    )

    result = asyncio.run(
        finish_prepared_slow_live_success_turn(
            runtime,
            payload,
            text="user",
            session_key="qq:private:owner",
            turn_id="turn-finish",
            publish_turn_id="turn-publish",
            turn_started_wall="2026-05-20T12:00:00+08:00",
            turn_started_at=12.5,
            pre_model_phase=pre_model_phase,
            slow_live_entry=slow_live_entry,
            model_turn=model_turn,
            post_model_reply=post_model_reply,
            cleanup={"cleaned_sessions": 0},
            trace_route_stage=trace_route_stage,
        )
    )

    assert result == {"accepted": True, "reply": "reply", "turn_id": "turn-publish"}
    assert calls[0]["runtime"] is runtime
    assert calls[0]["payload"] is payload
    assert calls[0]["session"] is session
    assert calls[0]["visible_turn"] is visible_turn
    assert calls[0]["recalled_context"] is recalled_context
    assert calls[0]["before_memory"] == {"memory": "before"}
    assert calls[0]["emotion_council"] == {"notes": ["emotion"]}
    assert calls[0]["proactive_tail_synced"] is True
    assert calls[0]["reply_bubble_force_units"] == ["one"]
    assert calls[0]["cleanup"] == {"cleaned_sessions": 0}
    assert rows == []


def test_run_slow_live_turn_from_pre_model_phase_returns_entry_response(monkeypatch) -> None:
    rows, trace_route_stage = _trace_rows()

    async def fake_enter(runtime, payload, **kwargs):
        del runtime
        return {"response": {"accepted": True, "route": "semantic"}, "payload": payload, "kwargs": kwargs}

    async def fail_model(*args, **kwargs):
        del args, kwargs
        raise AssertionError("entry response should short-circuit before model turn")

    monkeypatch.setattr(slow_live, "enter_slow_live_route_with_trace", fake_enter)
    monkeypatch.setattr(slow_live, "run_slow_live_model_turn_with_failure_publish", fail_model)

    result = asyncio.run(
        run_slow_live_turn_from_pre_model_phase_with_trace(
            SimpleNamespace(),
            {"scope": "owner"},
            text="user",
            session_key="qq:private:owner",
            turn_id="turn-1",
            publish_turn_id="turn-publish",
            turn_started_wall="2026-05-20T12:00:00+08:00",
            turn_started_at=12.5,
            turn_event_time="2026-05-20T12:00:00+08:00",
            turn_event_timestamp=123,
            pre_model_phase={
                "before_memory": {"memory": "before"},
                "curiosity_eval": {},
                "event_sidecar": {"notes": ["event"]},
            },
            cleanup={"cleaned_sessions": 0},
            settle_seconds=0,
            trace_route_stage=trace_route_stage,
        )
    )

    assert result == {"accepted": True, "route": "semantic"}
    assert rows == []


def test_run_slow_live_turn_from_pre_model_phase_threads_success_path(monkeypatch) -> None:
    calls: list[tuple[str, dict[str, object]]] = []
    rows, trace_route_stage = _trace_rows()
    runtime = SimpleNamespace()
    payload = {"scope": "owner"}
    session = SimpleNamespace()
    visible_turn = SimpleNamespace(kind="chat")
    recalled_context = SimpleNamespace(prompt_block="memory")
    visible_dedupe = SimpleNamespace(notes=["dedupe-note"])
    model_turn = slow_live.SlowLiveModelTurnState(
        visible_turn=visible_turn,
        recalled_context=recalled_context,
        recalled_context_event={"id": "recall-1"},
        recalled_context_notes=["recall-note"],
        continuity_handoff={"notes": ["continuity"]},
        runtime_presence_context="presence",
        life_reply_policy={"notes": ["life"]},
        emotion_council_context="emotion",
        persona_sidecar={"notes": ["persona"]},
    )
    post_model_reply = slow_live.SlowLivePostModelReplyState(
        draft_reply="draft",
        reply="reply",
        self_code_task="",
        direct_codex_task="",
        model_codex_task="",
        wait_to_think_task="",
        model_codex_delegate_note="",
        wait_to_think_sidecar={"notes": ["wait"]},
        rendered=True,
        renderer_reason="reason",
        final_guard_flags=["guard"],
        final_guard_applied=True,
        expression_learning={"notes": ["expr"]},
        visible_dedupe=visible_dedupe,
        stale_context_reply_replaced=True,
        life_reply_adjustment={"notes": ["life-adjust"]},
        current_sticker_reply="",
        recent_sticker_reply="",
        reply_bubble_force_units=["one"],
        empty_visible_reply_no_fallback=False,
        response_error_loop={"notes": ["response"]},
        slow_state_runtime={"notes": ["slow"]},
    )
    pre_model_phase = {
        "before_memory": {"memory": "before"},
        "curiosity_eval": {"notes": ["curiosity"]},
        "private_thought_outcome": {"notes": ["private"]},
        "uncertainty_pause_reply": {"notes": ["pause"]},
        "event_sidecar": {"notes": ["event"]},
        "v1_shadow": {"notes": ["v1"]},
        "tinykernel_shadow": {"notes": ["tiny"]},
    }

    async def fake_enter(runtime_arg, payload_arg, **kwargs):
        calls.append(("enter", {"runtime": runtime_arg, "payload": payload_arg, **kwargs}))
        return {
            "response": None,
            "session": session,
            "proactive_tail_synced": True,
            "emotion_council": {"notes": ["emotion"]},
        }

    async def fake_model(runtime_arg, payload_arg, **kwargs):
        calls.append(("model", {"runtime": runtime_arg, "payload": payload_arg, **kwargs}))
        return model_turn

    async def fake_prepare(runtime_arg, session_arg, payload_arg, **kwargs):
        calls.append(("prepare", {"runtime": runtime_arg, "session": session_arg, "payload": payload_arg, **kwargs}))
        return post_model_reply

    async def fake_finish(runtime_arg, payload_arg, **kwargs):
        calls.append(("finish", {"runtime": runtime_arg, "payload": payload_arg, **kwargs}))
        return {"accepted": True, "reply": "reply"}

    monkeypatch.setattr(slow_live, "enter_slow_live_route_with_trace", fake_enter)
    monkeypatch.setattr(slow_live, "run_slow_live_model_turn_with_failure_publish", fake_model)
    monkeypatch.setattr(slow_live, "prepare_slow_live_post_model_reply_state_for_turn", fake_prepare)
    monkeypatch.setattr(slow_live, "finish_prepared_slow_live_success_turn", fake_finish)

    result = asyncio.run(
        run_slow_live_turn_from_pre_model_phase_with_trace(
            runtime,
            payload,
            text="user",
            session_key="qq:private:owner",
            turn_id="turn-1",
            publish_turn_id="turn-publish",
            turn_started_wall="2026-05-20T12:00:00+08:00",
            turn_started_at=12.5,
            turn_event_time="2026-05-20T12:00:00+08:00",
            turn_event_timestamp=123,
            pre_model_phase=pre_model_phase,
            cleanup={"cleaned_sessions": 0},
            settle_seconds=0,
            trace_route_stage=trace_route_stage,
        )
    )

    assert result == {"accepted": True, "reply": "reply"}
    assert [name for name, _ in calls] == ["enter", "model", "prepare", "finish"]
    assert calls[0][1]["turn_id"] == "turn-publish"
    assert calls[0][1]["before_memory"] == {"memory": "before"}
    assert calls[1][1]["session"] is session
    assert calls[1][1]["turn_id"] == "turn-1"
    assert calls[1][1]["llm_failover_turn_id"] == "turn-publish"
    assert calls[1][1]["curiosity_eval"] == {"notes": ["curiosity"]}
    assert calls[2][1]["model_turn"] is model_turn
    assert calls[2][1]["evaluated_at"] == "2026-05-20T12:00:00+08:00"
    assert calls[3][1]["pre_model_phase"] is pre_model_phase
    assert calls[3][1]["slow_live_entry"]["session"] is session
    assert calls[3][1]["model_turn"] is model_turn
    assert calls[3][1]["post_model_reply"] is post_model_reply
    assert rows == []


def test_apply_slow_live_final_reply_guard_keeps_clean_reply() -> None:
    calls: list[tuple[str, object]] = []
    rows, trace_route_stage = _trace_rows()

    class Speech:
        @staticmethod
        def final_reply_guard(*, payload, user_text, reply):
            calls.append(("guard", {"payload": payload, "user_text": user_text, "reply": reply}))
            return reply, []

    runtime = SimpleNamespace(
        speech_controller=Speech(),
        _critical_final_guard_flags=lambda flags: calls.append(("critical", flags)) or [],
        _replace_last_assistant_message=lambda *args: calls.append(("replace", args)),
        _render_outward_reply=object(),
        xinyu_dir="root",
    )

    result = asyncio.run(
        apply_slow_live_final_reply_guard(
            runtime,
            SimpleNamespace(agent=object()),
            {"scope": "owner"},
            reply="clean reply",
            user_text="user",
            recalled_context=SimpleNamespace(prompt_block="memory block"),
            trace_route_stage=trace_route_stage,
            codex_delegate_blocked=False,
        )
    )

    assert result == {
        "reply": "clean reply",
        "final_guard_flags": [],
        "final_guard_applied": False,
        "expression_learning": {"notes": []},
    }
    assert rows == []
    assert calls == [
        ("guard", {"payload": {"scope": "owner"}, "user_text": "user", "reply": "clean reply"}),
        ("critical", []),
    ]


def test_apply_slow_live_final_reply_guard_applies_plain_rewrite() -> None:
    calls: list[tuple[str, object]] = []
    rows, trace_route_stage = _trace_rows()
    agent = object()

    class Speech:
        @staticmethod
        def final_reply_guard(*, payload, user_text, reply):
            calls.append(("guard", {"payload": payload, "user_text": user_text, "reply": reply}))
            return "guarded reply", ["flag-a", "flag-b", "flag-c", "flag-d", "flag-e"]

    runtime = SimpleNamespace(
        speech_controller=Speech(),
        _critical_final_guard_flags=lambda flags: calls.append(("critical", flags)) or [],
        _replace_last_assistant_message=lambda call_agent, reply: calls.append(
            ("replace", {"agent": call_agent, "reply": reply})
        ),
        _render_outward_reply=object(),
        xinyu_dir="root",
    )

    result = asyncio.run(
        apply_slow_live_final_reply_guard(
            runtime,
            SimpleNamespace(agent=agent),
            {"scope": "owner"},
            reply="bad reply",
            user_text="user",
            recalled_context=SimpleNamespace(prompt_block="memory block"),
            trace_route_stage=trace_route_stage,
            codex_delegate_blocked=False,
        )
    )

    assert result == {
        "reply": "guarded reply",
        "final_guard_flags": ["flag-a", "flag-b", "flag-c", "flag-d", "flag-e"],
        "final_guard_applied": True,
        "expression_learning": {"notes": []},
    }
    assert rows == [
        {
            "stage": "final_reply_guard_rewrite",
            "route": "slow_live",
            "status": "applied",
            "notes": ["final_reply_guard_flags:flag-a,flag-b,flag-c,flag-d"],
        }
    ]
    assert calls == [
        ("guard", {"payload": {"scope": "owner"}, "user_text": "user", "reply": "bad reply"}),
        ("critical", ["flag-a", "flag-b", "flag-c", "flag-d", "flag-e"]),
        ("replace", {"agent": agent, "reply": "guarded reply"}),
    ]


def test_apply_slow_live_final_reply_guard_repairs_critical_reply(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []
    rows, trace_route_stage = _trace_rows()
    agent = object()
    render_callable = object()

    async def fake_render(renderer, agent_arg, **kwargs):
        calls.append(("render", {"renderer": renderer, "agent": agent_arg, **kwargs}))
        return "repaired raw"

    def fake_record(root, **kwargs):
        calls.append(("record_expression", {"root": root, **kwargs}))
        return {"notes": ["expression-learned"]}

    class Speech:
        def __init__(self) -> None:
            self.calls = 0

        def final_reply_guard(self, *, payload, user_text, reply):
            self.calls += 1
            calls.append(("guard", {"reply": reply, "call": self.calls}))
            if self.calls == 1:
                return "guarded bad", ["critical"]
            return "safe repair", ["soft"]

    monkeypatch.setattr(slow_live, "render_outward_reply_with_trace", fake_render)
    monkeypatch.setattr(slow_live, "record_expression_self_learning_event", fake_record)
    runtime = SimpleNamespace(
        speech_controller=Speech(),
        _critical_final_guard_flags=lambda flags: ["critical"] if "critical" in flags else [],
        _replace_last_assistant_message=lambda call_agent, reply: calls.append(
            ("replace", {"agent": call_agent, "reply": reply})
        ),
        _render_outward_reply=render_callable,
        xinyu_dir="root",
    )

    result = asyncio.run(
        apply_slow_live_final_reply_guard(
            runtime,
            SimpleNamespace(agent=agent),
            {"scope": "owner"},
            reply="bad reply",
            user_text="user",
            recalled_context=SimpleNamespace(prompt_block="memory block"),
            trace_route_stage=trace_route_stage,
            codex_delegate_blocked=False,
        )
    )

    assert result == {
        "reply": "safe repair",
        "final_guard_flags": ["critical", "final_guard_repair_rendered", "soft"],
        "final_guard_applied": True,
        "expression_learning": {"notes": ["expression-learned"]},
    }
    assert rows == [
        {
            "stage": "final_reply_guard_rewrite",
            "route": "slow_live",
            "status": "applied",
            "notes": ["final_reply_guard_flags:critical,final_guard_repair_rendered,soft"],
        }
    ]
    assert calls == [
        ("guard", {"reply": "bad reply", "call": 1}),
        (
            "render",
            {
                "renderer": render_callable,
                "agent": agent,
                "payload": {"scope": "owner"},
                "user_text": "user",
                "draft_reply": "bad reply",
                "canonical_recall_context": "memory block",
                "reason": "final_guard_repair",
                "trace_route_stage": trace_route_stage,
            },
        ),
        ("guard", {"reply": "repaired raw", "call": 2}),
        ("replace", {"agent": agent, "reply": "safe repair"}),
        (
            "record_expression",
            {
                "root": "root",
                "user_text": "user",
                "bad_reply": "bad reply",
                "repaired_reply": "safe repair",
                "flags": ["critical"],
                "failure_kind": "visible_mechanism_or_template_leak",
            },
        ),
        ("replace", {"agent": agent, "reply": "safe repair"}),
    ]


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
    chunks: list[str] = []

    class Agent:
        async def inject_event(self, event) -> None:
            injected_context["event"] = event
            chunks.append("hello")

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
            session=SimpleNamespace(agent=Agent(), dialogue_tail=[], chunks=chunks),
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
    assert rows[-1] == {
        "stage": "model_inject_finished",
        "route": "slow_live",
        "status": "ok",
        "notes": [
            "chunk_count:1",
            "visible_chars:5",
            "raw_assistant_chars:0",
            "completion_tokens:0",
            "tool_call_count:0",
        ],
    }


def test_inject_slow_live_model_event_retries_empty_owner_private_output(
    tmp_path,
    monkeypatch,
) -> None:
    rows, trace_route_stage = _trace_rows()
    injected_events: list[object] = []
    chunks: list[str] = []

    class Agent:
        controller = SimpleNamespace(_last_assistant_content="")
        llm = SimpleNamespace(last_usage={"completion_tokens": 0}, last_tool_calls=[])

        async def inject_event(self, event) -> None:
            injected_events.append(event)
            if len(injected_events) == 2:
                chunks.append("补上了")

    class Runtime:
        xinyu_dir = tmp_path
        turn_timeout_seconds = 1

        @staticmethod
        def _inject_live_turn_context(agent, **kwargs):
            del agent, kwargs

        @staticmethod
        def _owner_private_payload_matches(payload):
            return payload.get("message_type") == "private_text"

        @staticmethod
        def _create_user_input_event(content, source="test", **kwargs):
            return SimpleNamespace(content=content, context={"source": source, **kwargs})

    monkeypatch.setattr(
        slow_live,
        "build_continuity_handoff_prompt_block",
        lambda *args, **kwargs: "continuity",
    )
    monkeypatch.setattr(
        slow_live,
        "build_uncertainty_pause_prompt_block",
        lambda *args, **kwargs: "uncertainty",
    )
    monkeypatch.setattr(
        slow_live,
        "build_life_reply_prompt_block",
        lambda *args, **kwargs: "life",
    )

    asyncio.run(
        inject_slow_live_model_event(
            Runtime(),
            {"platform": "qq", "message_type": "private_text"},
            session=SimpleNamespace(
                agent=Agent(),
                dialogue_tail=[],
                chunks=chunks,
                key="qq:private:owner",
            ),
            event=SimpleNamespace(content="原始消息"),
            text="原始消息",
            turn_id="turn-empty-retry-test",
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

    assert len(injected_events) == 2
    retry_event = injected_events[1]
    assert retry_event.context["source"] == "qq_gateway_empty_visible_retry"
    assert retry_event.context["original_text_len"] == 4
    assert "原始消息" not in retry_event.content
    assert rows[-4]["stage"] == "model_inject_empty_visible"
    assert rows[-3]["stage"] == "model_inject_empty_visible_retry_started"
    assert rows[-2] == {
        "stage": "model_inject_empty_visible_retry_finished",
        "route": "slow_live",
        "status": "ok",
        "notes": [
            "chunk_count:1",
            "visible_chars:3",
            "raw_assistant_chars:0",
            "completion_tokens:0",
            "tool_call_count:0",
        ],
    }
    assert rows[-1]["stage"] == "model_inject_finished"
    assert "empty_visible_retry_recovered" in rows[-1]["notes"]


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


def test_run_slow_live_model_turn_with_failure_publish_returns_contexts(tmp_path, monkeypatch) -> None:
    rows, trace_route_stage = _trace_rows()
    calls: list[tuple[str, object]] = []
    session = SimpleNamespace(agent=object(), chunks=["old"], dialogue_tail=[])
    visible_turn = SimpleNamespace(kind="chat")
    recalled_context = SimpleNamespace(prompt_block="memory block")
    model_contexts = slow_live.SlowLiveModelContexts(
        continuity_handoff={"notes": ["continuity"]},
        runtime_presence_context="presence",
        life_reply_policy={"notes": ["life"]},
        emotion_council_context="emotion",
    )

    def fake_observe(runtime, payload, *, text):
        calls.append(("persona", {"payload": payload, "text": text}))
        return {"prompt_block": "persona"}

    def fake_classify(root, **kwargs):
        calls.append(("classify", {"root": root, **kwargs}))
        return visible_turn

    async def fake_recall(runtime, payload, **kwargs):
        calls.append(("recall", {"payload": payload, **kwargs}))
        return slow_live.SlowLiveMemoryRecallResult(
            recalled_context=recalled_context,
            recalled_context_event={"id": "recall-1"},
            recalled_context_notes=["recall-note"],
        )

    async def fake_contexts(runtime, payload, **kwargs):
        calls.append(("contexts", {"payload": payload, **kwargs}))
        return model_contexts

    async def fake_inject(runtime, **kwargs):
        calls.append(("inject", kwargs))

    monkeypatch.setattr(slow_live, "observe_slow_live_persona_sidecar", fake_observe)
    monkeypatch.setattr(slow_live, "classify_visible_turn", fake_classify)
    monkeypatch.setattr(slow_live, "run_slow_live_memory_recall", fake_recall)
    monkeypatch.setattr(slow_live, "build_slow_live_model_contexts", fake_contexts)
    monkeypatch.setattr(slow_live, "inject_slow_live_model_event", fake_inject)

    class Runtime:
        xinyu_dir = tmp_path
        turn_timeout_seconds = 9

        @staticmethod
        def _owner_private_llm_failover_context(payload, **kwargs):
            calls.append(("failover", {"payload": payload, **kwargs}))
            return {"failover": True}

        @staticmethod
        def _create_user_input_event(content, **kwargs):
            calls.append(("event", {"content": content, **kwargs}))
            return {"event": content, "context": kwargs}

    result = asyncio.run(
        run_slow_live_model_turn_with_failure_publish(
            Runtime(),
            {"platform": "qq", "user_id": "owner-1"},
            session=session,
            text="hello",
            session_key="qq:private:owner",
            turn_id="turn-1",
            llm_failover_turn_id="turn-presence",
            turn_started_wall="2026-05-20T12:00:00+08:00",
            turn_started_at=12.5,
            turn_event_timestamp=123,
            evaluated_at="2026-05-20T12:00:00+08:00",
            curiosity_eval={"prompt_block": "curiosity"},
            trace_route_stage=trace_route_stage,
        )
    )

    assert session.chunks == []
    assert isinstance(result, slow_live.SlowLiveModelTurnState)
    assert result == {
        "visible_turn": visible_turn,
        "recalled_context": recalled_context,
        "recalled_context_event": {"id": "recall-1"},
        "recalled_context_notes": ["recall-note"],
        "continuity_handoff": {"notes": ["continuity"]},
        "runtime_presence_context": "presence",
        "life_reply_policy": {"notes": ["life"]},
        "emotion_council_context": "emotion",
        "persona_sidecar": {"prompt_block": "persona"},
    }
    assert [name for name, _ in calls] == [
        "persona",
        "failover",
        "event",
        "classify",
        "recall",
        "contexts",
        "inject",
    ]
    assert calls[1][1]["turn_id"] == "turn-presence"
    assert calls[2][1]["received_at"] == 123
    assert calls[-1][1]["event"]["event"] == "hello"
    assert calls[-1][1]["event"]["context"]["llm_failover"] == {"failover": True}
    assert rows == []


def test_run_slow_live_model_turn_with_failure_publish_publishes_timeout(tmp_path, monkeypatch) -> None:
    rows, trace_route_stage = _trace_rows()
    calls: list[tuple[str, object]] = []
    recalled_context = SimpleNamespace(prompt_block="memory")

    async def fake_recall(*args, **kwargs):
        return slow_live.SlowLiveMemoryRecallResult(
            recalled_context=recalled_context,
            recalled_context_event={"id": "recall-1"},
            recalled_context_notes=[],
        )

    async def fake_contexts(*args, **kwargs):
        return slow_live.SlowLiveModelContexts(
            continuity_handoff={},
            runtime_presence_context="presence",
            life_reply_policy={},
            emotion_council_context="",
        )

    async def fake_inject(*args, **kwargs):
        calls.append(("inject", kwargs))
        raise TimeoutError("slow")

    async def fake_failed(runtime, payload, **kwargs):
        calls.append(("failed", {"payload": payload, **kwargs}))

    monkeypatch.setattr(slow_live, "observe_slow_live_persona_sidecar", lambda *args, **kwargs: {"notes": []})
    monkeypatch.setattr(slow_live, "classify_visible_turn", lambda *args, **kwargs: SimpleNamespace(kind="chat"))
    monkeypatch.setattr(slow_live, "run_slow_live_memory_recall", fake_recall)
    monkeypatch.setattr(slow_live, "build_slow_live_model_contexts", fake_contexts)
    monkeypatch.setattr(slow_live, "inject_slow_live_model_event", fake_inject)
    monkeypatch.setattr(slow_live, "publish_slow_live_failed_turn", fake_failed)

    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        turn_timeout_seconds=7,
        _owner_private_llm_failover_context=lambda *args, **kwargs: {},
        _create_user_input_event=lambda content, **kwargs: {"event": content, **kwargs},
    )

    with pytest.raises(BridgeRequestError) as exc_info:
        asyncio.run(
            run_slow_live_model_turn_with_failure_publish(
                runtime,
                {"platform": "qq"},
                session=SimpleNamespace(agent=object(), chunks=[], dialogue_tail=[]),
                text="hello",
                session_key="qq:private:owner",
                turn_id="turn-1",
                llm_failover_turn_id="turn-presence",
                turn_started_wall="2026-05-20T12:00:00+08:00",
                turn_started_at=12.5,
                turn_event_timestamp=123,
                evaluated_at="2026-05-20T12:00:00+08:00",
                curiosity_eval={},
                trace_route_stage=trace_route_stage,
            )
        )

    assert exc_info.value.status.value == 504
    assert "7 seconds" in exc_info.value.message
    failed_call = calls[-1][1]
    assert failed_call["payload"] == {"platform": "qq"}
    assert failed_call["text"] == "hello"
    assert failed_call["session_key"] == "qq:private:owner"
    assert failed_call["turn_id"] == "turn-1"
    assert failed_call["status"] == "timeout"
    assert failed_call["notes"] == ["turn_timeout"]
    assert failed_call["recalled_context_event"] == {"id": "recall-1"}
    assert failed_call["recalled_context"] is recalled_context
    assert rows == []


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

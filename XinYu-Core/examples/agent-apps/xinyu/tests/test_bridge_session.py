from __future__ import annotations

import asyncio
import time
from types import SimpleNamespace

import pytest
import xinyu_bridge_session
from xinyu_bridge_session import (
    AgentSession,
    cleanup_idle_sessions,
    get_or_create_session,
    runtime_append_dialogue_tail,
    runtime_append_sticker_delivery_tail,
    runtime_cleanup_idle_sessions,
    runtime_dialogue_tail_user_content,
    runtime_get_session,
    session_key_from_payload,
    stop_all_sessions,
)


class DummyAgent:
    def __init__(self) -> None:
        self.stopped = False

    async def stop(self) -> None:
        self.stopped = True


class DummyRuntimeAgent(DummyAgent):
    def __init__(self) -> None:
        super().__init__()
        self.started = False
        self.output_handler = None
        self.replace_default = None

    def set_output_handler(self, handler, *, replace_default: bool) -> None:
        self.output_handler = handler
        self.replace_default = replace_default

    async def start(self) -> None:
        self.started = True


class DummyAgentFactory:
    created: list[tuple[str, object, str, DummyRuntimeAgent]] = []

    @classmethod
    def reset(cls) -> None:
        cls.created = []

    @classmethod
    def from_path(cls, path: str, *, input_module: object, pwd: str) -> DummyRuntimeAgent:
        agent = DummyRuntimeAgent()
        cls.created.append((path, input_module, pwd, agent))
        return agent


def test_session_key_prefers_top_level_session_then_user() -> None:
    assert session_key_from_payload({"session_id": "s1", "user_id": "u1"}) == "s1"
    assert session_key_from_payload({"user_id": "u1"}) == "u1"


def test_session_key_uses_metadata_fallback_for_adapter_payloads() -> None:
    assert session_key_from_payload({"metadata": {"session_id": "meta-s1", "user_id": "meta-u1"}}) == "meta-s1"
    assert session_key_from_payload({"metadata": {"user_id": "meta-u1"}}) == "meta-u1"


def test_session_key_default_is_stable() -> None:
    assert session_key_from_payload({}) == "qq:default"
    assert session_key_from_payload({"metadata": {}}) == "qq:default"


def test_cleanup_idle_sessions_stops_expired_non_preserved_sessions() -> None:
    async def run() -> None:
        now = time.time()
        old_agent = DummyAgent()
        fresh_agent = DummyAgent()
        preserved_agent = DummyAgent()
        sessions = {
            "old": AgentSession("old", old_agent, prompt_signature="test", last_used_at=now - 60),
            "fresh": AgentSession("fresh", fresh_agent, prompt_signature="test", last_used_at=now),
            "preserved": AgentSession("preserved", preserved_agent, prompt_signature="test", last_used_at=now - 60),
        }
        result = await cleanup_idle_sessions(
            sessions,
            asyncio.Lock(),
            idle_ttl_seconds=10,
            max_sessions=0,
            preserve_keys={"preserved"},
            log_prefix="[test]",
        )
        assert result == {"cleaned_sessions": 1, "remaining_sessions": 2}
        assert set(sessions) == {"fresh", "preserved"}
        assert old_agent.stopped is True
        assert fresh_agent.stopped is False
        assert preserved_agent.stopped is False

    asyncio.run(run())


def test_runtime_cleanup_idle_sessions_preserves_autonomous_session() -> None:
    async def run() -> None:
        now = time.time()
        old_agent = DummyAgent()
        autonomous_agent = DummyAgent()
        runtime = SimpleNamespace(
            _sessions={
                "old": AgentSession("old", old_agent, prompt_signature="test", last_used_at=now - 60),
                "auto": AgentSession("auto", autonomous_agent, prompt_signature="test", last_used_at=now - 60),
            },
            _sessions_lock=asyncio.Lock(),
            session_idle_ttl_seconds=10,
            max_sessions=0,
            autonomous_maintenance_enabled=True,
            autonomous_maintenance_session_key="auto",
        )

        result = await runtime_cleanup_idle_sessions(runtime)

        assert result == {"cleaned_sessions": 1, "remaining_sessions": 1}
        assert set(runtime._sessions) == {"auto"}
        assert old_agent.stopped is True
        assert autonomous_agent.stopped is False

    asyncio.run(run())


def test_runtime_append_dialogue_tail_appends_trims_and_saves(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    saved: list[tuple[object, str, list[dict[str, str]], int]] = []

    def fake_save(root, session_key, tail, *, max_entries):
        saved.append((root, session_key, list(tail), max_entries))
        return True

    monkeypatch.setattr(xinyu_bridge_session, "save_dialogue_tail", fake_save)
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        dialogue_session_tail_entries=2,
        dialogue_persisted_tail_entries=5,
        _payload_event_time_iso=lambda payload, *, fallback: "2026-06-05T01:00:00+08:00",
        _dialogue_tail_user_content=lambda user_text, *, payload: f"content:{user_text}",
    )
    session = AgentSession(
        "session-1",
        DummyAgent(),
        prompt_signature="test",
        dialogue_tail=[{"role": "assistant", "content": "old", "recorded_at": "old"}],
    )

    runtime_append_dialogue_tail(runtime, session, user_text="hello", reply="reply", payload={"time": "payload"})

    assert [item["content"] for item in session.dialogue_tail] == ["content:hello", "reply"]
    assert session.dialogue_tail[0]["recorded_at"] == "2026-06-05T01:00:00+08:00"
    assert saved == [(tmp_path, "session-1", session.dialogue_tail, 5)]


def test_runtime_append_dialogue_tail_clears_when_session_tail_disabled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(xinyu_bridge_session, "save_dialogue_tail", lambda *args, **kwargs: True)
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        dialogue_session_tail_entries=0,
        dialogue_persisted_tail_entries=5,
        _payload_event_time_iso=lambda payload, *, fallback: fallback,
        _dialogue_tail_user_content=lambda user_text, *, payload: user_text,
    )
    session = AgentSession("session-1", DummyAgent(), prompt_signature="test")

    runtime_append_dialogue_tail(runtime, session, user_text="hello", reply="reply")

    assert session.dialogue_tail == []


def test_runtime_append_dialogue_tail_swallows_save_errors(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    def failing_save(*args, **kwargs):
        raise OSError("save failed")

    monkeypatch.setattr(xinyu_bridge_session, "save_dialogue_tail", failing_save)
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        dialogue_session_tail_entries=4,
        dialogue_persisted_tail_entries=5,
        _payload_event_time_iso=lambda payload, *, fallback: fallback,
        _dialogue_tail_user_content=lambda user_text, *, payload: user_text,
    )
    session = AgentSession("session-1", DummyAgent(), prompt_signature="test")

    runtime_append_dialogue_tail(runtime, session, user_text="hello", reply="")

    assert [item["content"] for item in session.dialogue_tail] == ["hello"]


def test_runtime_dialogue_tail_user_content_returns_stripped_text_without_sticker_import() -> None:
    assert runtime_dialogue_tail_user_content(None, "  hello  ", payload=None) == "hello"
    assert runtime_dialogue_tail_user_content(
        None,
        "  hello  ",
        payload={"metadata": {"sticker_import_completed": False}},
    ) == "hello"


def test_runtime_dialogue_tail_user_content_adds_sticker_import_context() -> None:
    result = runtime_dialogue_tail_user_content(
        None,
        "  看这个  ",
        payload={
            "metadata": {
                "sticker_import_completed": True,
                "sticker_mood_label": "开心",
                "sticker_mood": "happy",
                "sticker_confidence": "0.92",
                "sticker_destination": "emotions/stickers/happy/a.png",
                "qq_image_context": {
                    "meaning": "owner shared a happy sticker",
                    "vision_summary": "vision " * 120,
                },
            }
        },
    )

    first_line, detail_line = result.split("\n", 1)
    assert first_line == "看这个"
    assert "【收到的表情记录】" in detail_line
    assert "owner 刚发来一张 QQ 表情包" in detail_line
    assert "分类=开心" in detail_line
    assert "语义=owner shared a happy sticker" in detail_line
    assert "摘要=" in detail_line
    assert len(detail_line.split("摘要=", 1)[1]) == 500
    # internal plumbing must stay out of the context note
    assert "置信度" not in detail_line
    assert "入库位置" not in detail_line
    assert "mood=happy" not in detail_line


def test_runtime_dialogue_tail_user_content_uses_sticker_fallback_text() -> None:
    result = runtime_dialogue_tail_user_content(
        None,
        "  ",
        payload={"metadata": {"sticker_import_completed": "true", "sticker_mood": "happy"}},
    )

    assert result.split("\n", 1)[0] == "我发了一张表情包。"
    assert "分类=happy" in result


def test_runtime_append_sticker_delivery_tail_skips_unqueued_replies(tmp_path) -> None:
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        dialogue_session_tail_entries=4,
        dialogue_persisted_tail_entries=5,
    )
    session = AgentSession("session-1", DummyAgent(), prompt_signature="test")

    assert runtime_append_sticker_delivery_tail(runtime, session, {"queued": False}) is False
    assert runtime_append_sticker_delivery_tail(runtime, session, "not-a-dict") is False
    assert session.dialogue_tail == []


def test_runtime_append_sticker_delivery_tail_appends_trims_and_saves(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    saved: list[tuple[object, str, list[dict[str, str]], int]] = []

    def fake_save(root, session_key, tail, *, max_entries):
        saved.append((root, session_key, list(tail), max_entries))
        return True

    monkeypatch.setattr(xinyu_bridge_session, "save_dialogue_tail", fake_save)
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        dialogue_session_tail_entries=2,
        dialogue_persisted_tail_entries=7,
    )
    session = AgentSession(
        "session-1",
        DummyAgent(),
        prompt_signature="test",
        dialogue_tail=[{"role": "user", "content": "old", "recorded_at": "old"}],
    )

    result = runtime_append_sticker_delivery_tail(
        runtime,
        session,
        {
            "queued": "true",
            "mood": "happy",
            "mode": "semantic_auto",
            "image_path": "D:/tmp/happy.png",
        },
    )

    assert result is True
    assert len(session.dialogue_tail) == 2
    item = session.dialogue_tail[-1]
    assert item["role"] == "assistant"
    assert item["content"].startswith("【表情发送记录】")
    assert "owner 追问刚才" in item["content"]
    # internal plumbing (raw file name, send-mode enum) must not leak into the note
    assert "happy.png" not in item["content"]
    assert "semantic_auto" not in item["content"]
    assert item["recorded_at"]
    assert saved == [(tmp_path, "session-1", session.dialogue_tail, 7)]


def test_runtime_append_sticker_delivery_tail_clears_when_session_tail_disabled(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(xinyu_bridge_session, "save_dialogue_tail", lambda *args, **kwargs: True)
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        dialogue_session_tail_entries=0,
        dialogue_persisted_tail_entries=7,
    )
    session = AgentSession(
        "session-1",
        DummyAgent(),
        prompt_signature="test",
        dialogue_tail=[{"role": "user", "content": "old", "recorded_at": "old"}],
    )

    assert runtime_append_sticker_delivery_tail(runtime, session, {"queued": True}) is False
    assert session.dialogue_tail == []


def test_runtime_append_sticker_delivery_tail_swallows_save_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    def failing_save(*args, **kwargs):
        raise OSError("save failed")

    monkeypatch.setattr(xinyu_bridge_session, "save_dialogue_tail", failing_save)
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        dialogue_session_tail_entries=4,
        dialogue_persisted_tail_entries=7,
    )
    session = AgentSession("session-1", DummyAgent(), prompt_signature="test")

    assert runtime_append_sticker_delivery_tail(runtime, session, {"queued": True, "mood": ""}) is True
    assert len(session.dialogue_tail) == 1
    assert "表情" in session.dialogue_tail[0]["content"]


def test_stop_all_sessions_clears_sessions_and_stops_agents() -> None:
    async def run() -> None:
        first_agent = DummyAgent()
        second_agent = DummyAgent()
        sessions = {
            "first": AgentSession("first", first_agent, prompt_signature="test"),
            "second": AgentSession("second", second_agent, prompt_signature="test"),
        }
        result = await stop_all_sessions(sessions, asyncio.Lock(), log_prefix="[test]")
        assert result == {"stopped_sessions": 2, "failed_sessions": 0, "remaining_sessions": 0}
        assert sessions == {}
        assert first_agent.stopped is True
        assert second_agent.stopped is True

    asyncio.run(run())


def test_get_or_create_session_reuses_matching_prompt_signature() -> None:
    async def run() -> None:
        calls: list[object] = []
        existing = AgentSession("session", DummyAgent(), prompt_signature="same")
        sessions = {"session": existing}

        def load_runtime() -> None:
            calls.append("load_runtime")

        def ensure_context_health(root: object) -> None:
            calls.append(("ensure_context_health", root))

        def prompt_signature_provider() -> str:
            calls.append("prompt_signature")
            return "same"

        def dialogue_tail_loader(*args, **kwargs):
            raise AssertionError("dialogue tail should not load for a reusable session")

        class FailingAgentFactory:
            @classmethod
            def from_path(cls, *args, **kwargs):
                raise AssertionError("agent should not be rebuilt for a reusable session")

        result = await get_or_create_session(
            "session",
            sessions,
            asyncio.Lock(),
            xinyu_dir="root",
            agent_cls=FailingAgentFactory,
            input_module_factory=object,
            load_runtime=load_runtime,
            ensure_context_health=ensure_context_health,
            prompt_signature_provider=prompt_signature_provider,
            dialogue_tail_loader=dialogue_tail_loader,
            dialogue_session_tail_entries=4,
            log_prefix="[test]",
        )

        assert result is existing
        assert sessions == {"session": existing}
        assert calls == ["load_runtime", ("ensure_context_health", "root"), "prompt_signature"]

    asyncio.run(run())


def test_runtime_get_session_passes_runtime_dependencies(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    async def run() -> None:
        calls: list[dict[str, object]] = []
        session = AgentSession("session-1", DummyAgent(), prompt_signature="test")

        async def fake_get_or_create_session(session_key, sessions, sessions_lock, **kwargs):
            calls.append(
                {
                    "session_key": session_key,
                    "sessions": sessions,
                    "sessions_lock": sessions_lock,
                    **kwargs,
                }
            )
            return session

        monkeypatch.setattr(xinyu_bridge_session, "get_or_create_session", fake_get_or_create_session)
        input_module_factory = object()
        ensure_context_health = object()
        dialogue_tail_loader = object()
        sessions: dict[str, AgentSession] = {}
        sessions_lock = asyncio.Lock()
        runtime = SimpleNamespace(
            _sessions=sessions,
            _sessions_lock=sessions_lock,
            xinyu_dir=tmp_path,
            _agent_cls=DummyAgentFactory,
            _load_runtime=lambda: None,
            _session_prompt_signature=lambda: "signature",
            dialogue_session_tail_entries=8,
        )

        result = await runtime_get_session(
            runtime,
            "session-1",
            input_module_factory=input_module_factory,
            ensure_context_health=ensure_context_health,
            dialogue_tail_loader=dialogue_tail_loader,
        )

        assert result is session
        assert calls == [
            {
                "session_key": "session-1",
                "sessions": sessions,
                "sessions_lock": sessions_lock,
                "xinyu_dir": tmp_path,
                "agent_cls": DummyAgentFactory,
                "input_module_factory": input_module_factory,
                "load_runtime": runtime._load_runtime,
                "ensure_context_health": ensure_context_health,
                "prompt_signature_provider": runtime._session_prompt_signature,
                "dialogue_tail_loader": dialogue_tail_loader,
                "dialogue_session_tail_entries": 8,
            }
        ]

    asyncio.run(run())


def test_get_or_create_session_rebuilds_stale_session_and_preserves_tail() -> None:
    async def run() -> None:
        DummyAgentFactory.reset()
        old_agent = DummyAgent()
        old_tail = [
            {"role": "user", "content": "one"},
            {"role": "assistant", "content": "two"},
        ]
        sessions = {
            "session": AgentSession(
                "session",
                old_agent,
                prompt_signature="old",
                dialogue_tail=old_tail,
            )
        }
        health_calls: list[object] = []
        input_module = object()

        def dialogue_tail_loader(*args, **kwargs):
            raise AssertionError("old session tail should be reused before disk load")

        result = await get_or_create_session(
            "session",
            sessions,
            asyncio.Lock(),
            xinyu_dir="root",
            agent_cls=DummyAgentFactory,
            input_module_factory=lambda: input_module,
            load_runtime=lambda: None,
            ensure_context_health=lambda root: health_calls.append(root),
            prompt_signature_provider=lambda: "new",
            dialogue_tail_loader=dialogue_tail_loader,
            dialogue_session_tail_entries=1,
            log_prefix="[test]",
        )

        assert old_agent.stopped is True
        assert sessions["session"] is result
        assert result.prompt_signature == "new"
        assert result.dialogue_tail == [{"role": "assistant", "content": "two"}]
        assert result.agent.started is True
        assert result.agent.replace_default is True
        result.agent.output_handler("chunk")
        assert result.chunks == ["chunk"]
        assert DummyAgentFactory.created == [("root", input_module, "root", result.agent)]
        assert health_calls == ["root", "root"]

    asyncio.run(run())

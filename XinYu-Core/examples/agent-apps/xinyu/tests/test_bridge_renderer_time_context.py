from __future__ import annotations

from types import SimpleNamespace

from xinyu_bridge_renderer import (
    BridgeRenderer,
    DEBUG_LIVE_SYSTEM_PROMPT_REL,
    DEBUG_PROMPT_DUMP_ENV,
    runtime_build_renderer_messages,
    runtime_conversation_tail,
    runtime_maybe_dump_live_system_prompt,
    runtime_read_text,
    runtime_renderer_memory_context,
    runtime_renderer_reason,
    runtime_strip_renderer_wrappers,
)


class _Conversation:
    def to_messages(self) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": "hidden"},
            {"role": "user", "content": "old", "recorded_at": "2026-05-18T13:20:00+08:00"},
            {"role": "assistant", "content": "then", "recorded_at": "2026-05-18T13:20:05+08:00"},
            {"role": "user", "content": "now", "recorded_at": "2026-05-18T13:30:00+08:00"},
        ]


def test_renderer_conversation_tail_keeps_message_timestamps(tmp_path) -> None:
    renderer = BridgeRenderer(
        xinyu_dir=tmp_path,
        speech_controller=SimpleNamespace(strip_wrappers=lambda text: text),
        renderer_mode="off",
        render_timeout_seconds=1,
    )
    agent = SimpleNamespace(controller=SimpleNamespace(conversation=_Conversation()))

    tail = renderer.conversation_tail(agent, max_messages=4)

    assert "system" not in tail
    assert "user (2026-05-18T13:20:00+08:00): old" in tail
    assert "assistant (2026-05-18T13:20:05+08:00): then" in tail
    assert "user (2026-05-18T13:30:00+08:00): now" in tail


def test_runtime_renderer_helpers_forward_to_runtime_renderer() -> None:
    renderer = SimpleNamespace(
        renderer_reason=lambda **kwargs: f"{kwargs['user_text']}:{kwargs['draft_reply']}",
        build_renderer_messages=lambda agent, **kwargs: [
            {"role": "user", "content": f"{agent.name}:{kwargs['user_text']}"},
        ],
        renderer_memory_context=lambda: "memory",
        read_text=lambda rel, *, limit: f"{rel}:{limit}",
        conversation_tail=lambda agent, *, max_messages: f"{agent.name}:{max_messages}",
        strip_renderer_wrappers=lambda text: text.strip("[]"),
    )
    runtime = SimpleNamespace(renderer=renderer)
    agent = SimpleNamespace(name="agent")

    assert runtime_renderer_reason(runtime, payload={}, user_text="u", draft_reply="d") == "u:d"
    assert runtime_build_renderer_messages(runtime, agent, payload={}, user_text="u", draft_reply="d") == [
        {"role": "user", "content": "agent:u"},
    ]
    assert runtime_renderer_memory_context(runtime) == "memory"
    assert runtime_read_text(runtime, "prompts/output.md", limit=12) == "prompts/output.md:12"
    assert runtime_conversation_tail(runtime, agent, max_messages=3) == "agent:3"
    assert runtime_strip_renderer_wrappers(runtime, "[reply]") == "reply"


def test_runtime_maybe_dump_live_system_prompt_writes_owner_private_dump(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv(DEBUG_PROMPT_DUMP_ENV, "1")
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        _owner_private_payload_matches=lambda payload: payload.get("owner") is True,
    )
    agent = SimpleNamespace(get_system_prompt=lambda: "BASE_PROMPT")

    runtime_maybe_dump_live_system_prompt(
        runtime,
        agent,
        payload={"owner": True},
        session_key="qq:private:owner",
        turn_id="turn-renderer-1",
        live_system_prompt="LIVE_PROMPT",
    )

    content = (tmp_path / DEBUG_LIVE_SYSTEM_PROMPT_REL).read_text(encoding="utf-8")
    assert "session_id: qq:private:owner" in content
    assert "turn_id: turn-renderer-1" in content
    assert "full_prompt_sha256: sha256:" in content
    assert "live_injection_sha256: sha256:" in content
    assert "env_gate: XINYU_DEBUG_PROMPT_DUMP=1" in content
    assert "BASE_PROMPT" in content
    assert "LIVE_PROMPT" in content

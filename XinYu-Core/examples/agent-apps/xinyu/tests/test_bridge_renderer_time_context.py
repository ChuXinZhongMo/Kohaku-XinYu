from __future__ import annotations

from types import SimpleNamespace

from xinyu_bridge_renderer import BridgeRenderer


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

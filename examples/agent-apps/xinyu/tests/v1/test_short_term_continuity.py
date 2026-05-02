from __future__ import annotations

from pathlib import Path

from xinyu_v1.app import XinYuV1App
from xinyu_v1.config import XinYuV1Config
from xinyu_v1.reasoning.models import ReasoningRequest, ReasoningResult


class RecordingSlowRuntime:
    def __init__(self, replies: list[str]) -> None:
        self.replies = replies
        self.requests: list[ReasoningRequest] = []

    async def run(self, request: ReasoningRequest, *, timeout_seconds: float) -> ReasoningResult:
        self.requests.append(request)
        return ReasoningResult(draft=self.replies.pop(0), memory_changed=False)


async def test_previous_visible_reply_is_available_to_next_slow_turn(tmp_path, monkeypatch) -> None:
    root = tmp_path / "xinyu"
    (root / "prompts").mkdir(parents=True)
    (root / "memory" / "emotions").mkdir(parents=True)
    (root / "config.yaml").write_text("name: xinyu\n", encoding="utf-8")
    monkeypatch.setenv("XINYU_V1_RUNTIME_MODE", "test")

    app = XinYuV1App(XinYuV1Config.load(Path(root)))
    runtime = RecordingSlowRuntime(
        [
            "Barbecue rice works with iced water.",
            "I meant the iced water from the previous reply.",
        ]
    )
    app.slow_runtime = runtime  # type: ignore[assignment]

    await app.handle_payload({"text": "Dinner idea?", "user_id": "u", "session_id": "s"})
    await app.handle_payload({"text": "What drink was that?", "user_id": "u", "session_id": "s"})

    assert len(runtime.requests) == 2
    recent = runtime.requests[1].recent_messages
    assert any(message.role == "assistant" and "iced water" in message.text for message in recent)
    assert any(message.role == "user" and "Dinner idea?" in message.text for message in recent)
    assert all("What drink was that?" not in message.text for message in recent)

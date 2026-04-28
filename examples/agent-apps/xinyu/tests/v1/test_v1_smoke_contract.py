from __future__ import annotations

from pathlib import Path

from xinyu_v1.app import XinYuV1App
from xinyu_v1.config import XinYuV1Config


async def test_v1_app_fast_path_contract(tmp_path, monkeypatch) -> None:
    root = tmp_path / "xinyu"
    (root / "prompts").mkdir(parents=True)
    (root / "memory" / "emotions").mkdir(parents=True)
    (root / "config.yaml").write_text("name: xinyu\n", encoding="utf-8")
    monkeypatch.setenv("XINYU_V1_RUNTIME_MODE", "test")

    app = XinYuV1App(XinYuV1Config.load(Path(root)))
    reply = await app.handle_payload({"text": "你好", "user_id": "u", "session_id": "s"})

    assert reply.accepted
    assert reply.route == "fast_path"
    assert reply.reply
    assert reply.memory_changed is False


async def test_v1_shadow_does_not_generate_visible_reply(tmp_path, monkeypatch) -> None:
    root = tmp_path / "xinyu"
    (root / "prompts").mkdir(parents=True)
    (root / "memory" / "emotions").mkdir(parents=True)
    (root / "config.yaml").write_text("name: xinyu\n", encoding="utf-8")
    monkeypatch.setenv("XINYU_V1_RUNTIME_MODE", "test")

    app = XinYuV1App(XinYuV1Config.load(Path(root)))
    reply = await app.shadow_payload({"text": "你刚才那样我有点失望", "user_id": "u", "session_id": "s"})

    assert reply.accepted
    assert reply.reply == ""
    assert reply.route == "slow_path"
    assert "v1_shadow" in reply.notes

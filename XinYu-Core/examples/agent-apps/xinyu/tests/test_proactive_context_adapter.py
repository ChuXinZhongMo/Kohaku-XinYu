from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from xinyu_proactive_context_adapter import (
    context_line_signal_score,
    normalize_proactive_recent_context,
    read_recent_owner_private_context,
    runtime_owner_private_turns,
)


def test_normalize_proactive_recent_context_keeps_owner_private_turns_only() -> None:
    context = normalize_proactive_recent_context(
        [
            {
                "sessionKind": "qq_group",
                "groupDisplayId": "123",
                "textPreview": "群里提到 Desktop 那张卡",
            },
            {
                "sessionKind": "desktop_private",
                "isOwner": True,
                "textPreview": "表达层契约这里先接上",
                "replyPreview": "我先看表现那块",
            },
        ]
    )

    assert "owner: 表达层契约这里先接上" in context
    assert "xinyu: 我先看表现那块" in context
    assert "群里" not in context


def test_runtime_owner_private_turns_accepts_bridge_shapes_and_filters_groups() -> None:
    runtime = SimpleNamespace(
        _desktop_recent_turns=[
            {"sessionKind": "qq_group", "groupDisplayId": "42", "textPreview": "群里的表达层"},
            {"session_kind": "qq_private", "isOwner": True, "ownerText": "Desktop 那张卡先放这"},
            {"sessionKind": "qq_private", "isOwner": False, "textPreview": "陌生人私聊"},
            {"sessionKind": "owner_private", "privacy": "owner_private", "text": "生活事件链路继续看"},
        ]
    )

    turns = runtime_owner_private_turns(runtime, limit=4)

    assert [turn.get("privacy") for turn in turns] == ["owner_private", "owner_private"]
    assert turns[0]["ownerText"] == "Desktop 那张卡先放这"
    assert turns[1]["text"] == "生活事件链路继续看"


def test_read_recent_owner_private_context_prefers_journal_over_summary(tmp_path: Path) -> None:
    context_dir = tmp_path / "memory/context"
    context_dir.mkdir(parents=True)
    (context_dir / "recent_context.md").write_text("- 表达层旧摘要\n", encoding="utf-8")
    (context_dir / "interaction_journal.jsonl").write_text(
        json.dumps(
            {"privacy": "group_context", "group_id": "123", "user_text": "群里提到表达层"},
            ensure_ascii=False,
        )
        + "\n"
        + json.dumps(
            {
                "metadata": {"privacy": "owner_private", "is_owner_user": True},
                "user_text": "主动消息那几句太硬",
                "assistant_text": "我改短一点",
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    context = read_recent_owner_private_context(tmp_path)

    assert "owner: 主动消息那几句太硬" in context
    assert "xinyu: 我改短一点" in context
    assert "旧摘要" not in context
    assert "群里" not in context


def test_context_line_signal_score_prefers_owner_turns_over_lifecycle_fields() -> None:
    assert context_line_signal_score("owner: 表达层契约这里先接上") > context_line_signal_score(
        "after_owner_replies: continue only if owner replies"
    )

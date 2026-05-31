from __future__ import annotations

import asyncio
import sqlite3
from pathlib import Path

from xinyu_bridge_utility_routes import message_drop
from xinyu_dialogue_archive import archive_dialogue_turn
from xinyu_dialogue_working_memory import load_dialogue_tail, save_dialogue_tail


class _Session:
    def __init__(self, tail: list[dict[str, str]]) -> None:
        self.dialogue_tail = tail


class _Runtime:
    def __init__(self, root: Path, tail: list[dict[str, str]]) -> None:
        self.xinyu_dir = root
        self._closed = False
        self._sessions = {"qq:private:42": _Session(tail)}
        self._sessions_lock = asyncio.Lock()
        self.dialogue_persisted_tail_entries = 32


def test_message_drop_retracts_unsent_reply_from_tail_and_archive(tmp_path: Path) -> None:
    tail = [
        {"role": "user", "content": "都有（"},
        {"role": "assistant", "content": "啥都有"},
        {"role": "user", "content": "不说我了"},
    ]
    save_dialogue_tail(tmp_path, "qq:private:42", tail, max_entries=32)
    archive = archive_dialogue_turn(
        tmp_path,
        {"session_id": "qq:private:42", "user_id": "42", "metadata": {"is_owner_user": True}},
        user_text="都有（",
        assistant_reply="啥都有",
    )
    assistant_id = archive["message_ids"][-1]
    runtime = _Runtime(tmp_path, tail)

    result = asyncio.run(
        message_drop(
            runtime,
            {
                "session_id": "qq:private:42",
                "reply": "啥都有",
                "archive_assistant_message_id": assistant_id,
            },
        )
    )

    assert result["tail_removed"] is True
    assert result["archive_deleted"] is True
    assert [item["content"] for item in runtime._sessions["qq:private:42"].dialogue_tail] == ["都有（", "不说我了"]
    persisted = load_dialogue_tail(tmp_path, "qq:private:42")
    assert [item["content"] for item in persisted] == ["都有（", "不说我了"]

    con = sqlite3.connect(tmp_path / "runtime/dialogue_archive/dialogue.sqlite3")
    try:
        rows = con.execute("SELECT role, text FROM dialogue_messages ORDER BY id").fetchall()
    finally:
        con.close()
    assert rows == [("user", "都有（")]

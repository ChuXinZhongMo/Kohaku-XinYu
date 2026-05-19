from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from xinyu_interaction_journal import LOG_REL, STATE_REL, record_interaction_turn  # noqa: E402


def test_interaction_journal_records_real_owner_turn(tmp_path: Path) -> None:
    result = record_interaction_turn(
        tmp_path,
        {"platform": "qq", "message_type": "private", "metadata": {"is_owner_user": True}},
        user_text="你对自己的运行现在有什么想法",
        reply="我想先把交互日志补上。",
        session_key="qq:private:owner",
        turn_kind="ordinary_owner_chat",
        turn_id="turn-1",
        elapsed_ms=1234,
        finished_at="2026-05-02T02:00:00+08:00",
    )

    assert result["recorded"] is True
    assert result["source_scope"] == "owner_private"
    assert result["topic"] == "runtime_self_awareness"

    state = (tmp_path / STATE_REL).read_text(encoding="utf-8")
    assert "memory_type: interaction_journal_state" in state
    assert "last_source: owner_private" in state
    assert "last_topic: runtime_self_awareness" in state
    assert "last_reply_elapsed_ms: 1234" in state
    assert "reality_source: real_bridge_chat_turn" in state
    assert "dream_or_reflection_source: no" in state

    rows = [json.loads(line) for line in (tmp_path / LOG_REL).read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert rows[0]["event_time"] == "2026-05-02T02:00:00+08:00"
    assert rows[0]["source_scope"] == "owner_private"
    assert rows[0]["session_hash"] != "qq:private:owner"


def test_interaction_journal_keeps_recent_owner_continuity(tmp_path: Path) -> None:
    record_interaction_turn(
        tmp_path,
        {"platform": "qq", "message_type": "private", "metadata": {"is_owner_user": True}},
        user_text="先这样",
        reply="嗯。",
        session_key="qq:private:owner",
        finished_at="2026-05-02T02:00:00+08:00",
    )
    record_interaction_turn(
        tmp_path,
        {"platform": "qq", "group_id": "123", "message_type": "group_text"},
        user_text="群里问个代码问题",
        reply="可以。",
        session_key="qq:group:123:u",
        elapsed_ms=900,
        finished_at="2026-05-02T02:10:00+08:00",
    )

    state = (tmp_path / STATE_REL).read_text(encoding="utf-8")
    assert "last_source: group_context" in state
    assert "last_topic: technical_work" in state
    assert "recent_interaction_count: 2" in state
    assert "recent_owner_private_count: 1" in state
    assert "minutes_since_last_owner_private: 10" in state

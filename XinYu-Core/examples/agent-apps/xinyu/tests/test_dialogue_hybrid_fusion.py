from __future__ import annotations

import sqlite3
from pathlib import Path

from xinyu_dialogue_archive import (
    OWNER_PRIVATE_SCOPE,
    archive_dialogue_turn,
    dialogue_archive_path,
    ensure_dialogue_fts_index,
    search_dialogue_archive,
)


def _payload(session: str = "qq:private:hybrid") -> dict[str, object]:
    return {
        "platform": "qq",
        "message_type": "private_text",
        "session_id": session,
        "user_id": "42",
        "metadata": {"is_owner_user": True},
    }


def _archive(root: Path, user_text: str, reply: str = "ok") -> None:
    archive_dialogue_turn(
        root,
        _payload(),
        user_text=user_text,
        assistant_reply=reply,
        message_type="technical_work",
    )


def test_fts_keyword_match_outranks_recent_noise(tmp_path: Path) -> None:
    # An older turn carries a precise keyword; newer turns are unrelated chatter.
    _archive(tmp_path, "记得我家猫叫 Mochi，是只布偶。")
    for i in range(6):
        _archive(tmp_path, f"今天天气不错随便聊聊第{i}句")

    matches = search_dialogue_archive(
        tmp_path,
        "Mochi 布偶猫",
        scopes=(OWNER_PRIVATE_SCOPE,),
        session_key="qq:private:hybrid",
        limit=5,
    )

    assert matches
    top = matches[0]
    # The keyword-bearing message must win despite being the oldest, and fusion must
    # label it hybrid with a normalised relevance score.
    assert "Mochi" in top.text
    assert top.retrieval_source == "hybrid"
    assert top.rank_score > 0


def test_empty_query_falls_back_to_recent(tmp_path: Path) -> None:
    _archive(tmp_path, "第一条")
    _archive(tmp_path, "第二条")
    matches = search_dialogue_archive(
        tmp_path,
        "",
        scopes=(OWNER_PRIVATE_SCOPE,),
        session_key="qq:private:hybrid",
        limit=5,
    )
    # No query terms -> recency baseline still contributes from the LIKE source.
    assert matches
    assert any("第二条" in m.text for m in matches)


def test_ensure_dialogue_fts_index_backfills_missing_rows(tmp_path: Path) -> None:
    _archive(tmp_path, "需要被回填的关键词 Pangolin")
    # Simulate rows archived before the FTS table existed by dropping the synced row.
    conn = sqlite3.connect(dialogue_archive_path(tmp_path))
    try:
        conn.execute("DELETE FROM dialogue_fts")
        conn.commit()
    finally:
        conn.close()

    result = ensure_dialogue_fts_index(tmp_path)
    assert result["indexed"] >= 1

    matches = search_dialogue_archive(
        tmp_path,
        "Pangolin",
        scopes=(OWNER_PRIVATE_SCOPE,),
        session_key="qq:private:hybrid",
        limit=5,
    )
    assert any("Pangolin" in m.text for m in matches)

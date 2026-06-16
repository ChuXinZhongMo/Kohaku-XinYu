from __future__ import annotations

import sqlite3
from pathlib import Path

from xinyu_dialogue_archive import (
    OWNER_PRIVATE_SCOPE,
    archive_dialogue_turn,
    dialogue_archive_path,
    ensure_dialogue_semantic_index,
    search_dialogue_archive,
)


def _payload() -> dict[str, object]:
    return {
        "platform": "qq",
        "message_type": "private_text",
        "session_id": "qq:private:semantic-backend",
        "user_id": "42",
        "metadata": {"is_owner_user": True},
    }


def test_semantic_backend_falls_back_to_hash_when_runtime_unavailable(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XINYU_DIALOGUE_SEMANTIC_RETRIEVAL_ENABLED", "1")
    monkeypatch.setenv("XINYU_DIALOGUE_SEMANTIC_EMBEDDING_PROVIDER", "none")

    archive_dialogue_turn(
        tmp_path,
        _payload(),
        user_text="Codex search was blocked by an explicit owner-permission boundary.",
        assistant_reply="I will keep search inside explicit owner tasks.",
        message_type="technical_work",
    )

    index = ensure_dialogue_semantic_index(tmp_path)
    matches = search_dialogue_archive(
        tmp_path,
        "why was lookup blocked",
        scopes=(OWNER_PRIVATE_SCOPE,),
        session_key="qq:private:semantic-backend",
        limit=5,
    )

    assert index["provider"] == "none"
    assert index["model"] == "local_hash_v1"
    assert matches
    # Results are now reciprocal-rank-fused across fts/like/semantic sources, so the
    # surfaced record is labelled "hybrid" and carries a normalised relevance score.
    assert any(match.retrieval_source == "hybrid" and match.rank_score > 0 for match in matches)

    conn = sqlite3.connect(dialogue_archive_path(tmp_path))
    try:
        model, embedding_json = conn.execute("SELECT model, embedding_json FROM dialogue_semantic_index").fetchone()
    finally:
        conn.close()
    assert model == "local_hash_v1"
    assert "Codex search was blocked" not in embedding_json

"""Phase 5 retrieval boundary tests (plan §8.4 / §9.1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from xinyu_dialogue_archive import (
    GROUP_SCOPE,
    archive_dialogue_turn,
    resolve_dialogue_scope,
    search_dialogue_archive,
)


@pytest.fixture(autouse=True)
def _archive_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("XINYU_DIALOGUE_ARCHIVE_ENABLED", "1")
    monkeypatch.setenv("XINYU_DIALOGUE_ARCHIVE_OWNER_PRIVATE_ONLY", "0")
    monkeypatch.setenv("XINYU_DIALOGUE_ARCHIVE_GROUP_SCOPE_ENABLED", "1")
    monkeypatch.setenv("XINYU_DIALOGUE_SEMANTIC_RETRIEVAL_ENABLED", "0")


def _group_payload(group_id: str, user_id: str) -> dict:
    return {
        "platform": "qq",
        "message_type": "group_text",
        "group_id": group_id,
        "user_id": user_id,
        "session_id": f"qq:group:{group_id}:{user_id}",
    }


def test_group_shared_topic_recalled_within_same_group(tmp_path: Path) -> None:
    payload = _group_payload("g-1", "u-1")
    archive_dialogue_turn(tmp_path, payload, user_text="群里在讨论部署配置阿棠", assistant_reply="好的")
    gh = resolve_dialogue_scope(payload).group_id_hash
    rows = search_dialogue_archive(tmp_path, "部署配置", scopes=[GROUP_SCOPE], group_id_hash=gh, limit=12)
    assert any("部署配置" in r.text for r in rows)


def test_group_topic_not_recalled_across_groups(tmp_path: Path) -> None:
    pa = _group_payload("g-1", "u-1")
    pb = _group_payload("g-2", "u-9")
    archive_dialogue_turn(tmp_path, pa, user_text="群1的秘密话题部署配置", assistant_reply="好")
    archive_dialogue_turn(tmp_path, pb, user_text="群2完全不同的部署配置话题", assistant_reply="好")

    gh_b = resolve_dialogue_scope(pb).group_id_hash
    rows = search_dialogue_archive(tmp_path, "部署配置", scopes=[GROUP_SCOPE], group_id_hash=gh_b, limit=12)
    texts = " | ".join(r.text for r in rows)
    assert "群2" in texts
    assert "群1的秘密话题" not in texts  # group-1 content never leaks into group-2 recall


def test_no_group_filter_would_see_both(tmp_path: Path) -> None:
    pa = _group_payload("g-1", "u-1")
    pb = _group_payload("g-2", "u-9")
    archive_dialogue_turn(tmp_path, pa, user_text="群1部署配置标记A", assistant_reply="好")
    archive_dialogue_turn(tmp_path, pb, user_text="群2部署配置标记B", assistant_reply="好")
    rows = search_dialogue_archive(tmp_path, "部署配置", scopes=[GROUP_SCOPE], limit=12)
    texts = " | ".join(r.text for r in rows)
    # without the group filter both are visible — proves the filter is what isolates
    assert "标记A" in texts and "标记B" in texts

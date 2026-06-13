from __future__ import annotations

from pathlib import Path

import pytest

from xinyu_dialogue_archive import GROUP_SCOPE, resolve_dialogue_scope, search_dialogue_archive
from xinyu_group_interest_memory import group_interest_metadata, observe_group_interest, record_group_interest_reply


@pytest.fixture(autouse=True)
def _archive_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XINYU_DIALOGUE_ARCHIVE_ENABLED", "1")
    monkeypatch.setenv("XINYU_DIALOGUE_ARCHIVE_OWNER_PRIVATE_ONLY", "0")
    monkeypatch.setenv("XINYU_DIALOGUE_ARCHIVE_GROUP_SCOPE_ENABLED", "1")
    monkeypatch.setenv("XINYU_DIALOGUE_SEMANTIC_RETRIEVAL_ENABLED", "0")


def _event(group_id: str = "g1", user_id: str = "u1", message_id: str = "m1") -> dict:
    return {
        "platform": "qq",
        "message_type": "group",
        "group_id": group_id,
        "user_id": user_id,
        "message_id": message_id,
        "time": 1_700_000_000,
    }


def _payload_from_observation(observation: dict, group_id: str = "g1", user_id: str = "u1") -> dict:
    return {
        "platform": "qq",
        "message_type": "group_text",
        "group_id": group_id,
        "user_id": user_id,
        "session_id": f"qq:group:{group_id}:{user_id}",
        "metadata": group_interest_metadata(observation),
    }


def test_untriggered_group_message_is_archived_for_same_group_recall(tmp_path: Path) -> None:
    result = observe_group_interest(
        tmp_path,
        event=_event(),
        text="AI 记忆这个话题在群里继续聊一下",
        reply_enabled=False,
    )

    assert result["recorded"]
    assert result["archive_message_id"] is not None

    payload = {"platform": "qq", "message_type": "group_text", "group_id": "g1", "user_id": "u2"}
    group_hash = resolve_dialogue_scope(payload).group_id_hash
    rows = search_dialogue_archive(tmp_path, "AI 记忆", scopes=[GROUP_SCOPE], group_id_hash=group_hash, limit=8)
    assert any("AI 记忆" in row.text for row in rows)


def test_interest_reply_opens_followup_then_stops_when_reply_has_no_question(tmp_path: Path) -> None:
    first = observe_group_interest(
        tmp_path,
        event=_event(message_id="m1"),
        text="AI memory 怎么给群聊做长期记忆？",
        reply_enabled=True,
        reply_min_score=1,
        reply_cooldown_seconds=0,
    )
    assert first["should_reply"]
    assert first["reply_reason"] == "group_interest_open"
    assert first["archive_message_id"] is None

    record = record_group_interest_reply(
        tmp_path,
        payload=_payload_from_observation(first),
        reply="你们想要的是长期事实记忆，还是只记最近的话题？",
        followup_max_turns=1,
    )
    assert record["recorded"]
    assert record["row"]["active_status"] == "waiting_answer"

    second = observe_group_interest(
        tmp_path,
        event=_event(user_id="u2", message_id="m2"),
        text="是长期记忆，想让她记住群里反复聊的主题",
        reply_enabled=True,
        reply_min_score=20,
        reply_cooldown_seconds=9999,
    )
    assert second["should_reply"]
    assert second["reply_reason"] == "group_interest_followup"

    record_group_interest_reply(
        tmp_path,
        payload=_payload_from_observation(second, user_id="u2"),
        reply="懂了，这个我先收住。",
        followup_max_turns=1,
    )
    third = observe_group_interest(
        tmp_path,
        event=_event(user_id="u3", message_id="m3"),
        text="我们继续聊别的",
        reply_enabled=True,
        reply_min_score=20,
        reply_cooldown_seconds=0,
    )
    assert not third["should_reply"]


def test_interest_reply_cooldown_blocks_new_opening(tmp_path: Path) -> None:
    first = observe_group_interest(
        tmp_path,
        event=_event(message_id="m1"),
        text="AI 记忆怎么做？",
        reply_enabled=True,
        reply_min_score=1,
        reply_cooldown_seconds=0,
    )
    record_group_interest_reply(
        tmp_path,
        payload=_payload_from_observation(first),
        reply="我想听听你们说的是哪种记忆？",
        followup_max_turns=0,
    )

    second = observe_group_interest(
        tmp_path,
        event=_event(message_id="m2"),
        text="AI 记忆还有一个问题吗？",
        reply_enabled=True,
        reply_min_score=1,
        reply_cooldown_seconds=9999,
    )
    assert not second["should_reply"]
    assert second["reply_reason"] == "group_interest_cooldown"

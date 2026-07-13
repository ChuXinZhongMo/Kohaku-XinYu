from __future__ import annotations

from xinyu_qq_gateway_utils import message_ids_from_action_response
from xinyu_qq_group_policy import (
    event_group_interest_observation,
    file_learning_group_allowed,
    file_learning_scope_reject_reason,
    group_followup_key,
    group_interest_reply_group_allowed,
)
from xinyu_qq_sticker_context import looks_like_recent_sticker_question


def test_message_ids_from_action_response_merges_bubble_and_message_ids() -> None:
    ids = message_ids_from_action_response(
        {
            "data": {
                "message_id": "1001,1002",
                "reply_bubble_message_ids": ["1001", "1003"],
            }
        }
    )
    assert ids == ["1001", "1003", "1002"]


def test_message_ids_from_action_response_handles_empty() -> None:
    assert message_ids_from_action_response(None) == []
    assert message_ids_from_action_response({}) == []


def test_group_policy_interest_and_file_learning() -> None:
    assert group_followup_key(group_id="g1", user_id="u1") == "g1:u1"
    assert group_interest_reply_group_allowed(
        "g1",
        allowed_group_ids=frozenset({"g1"}),
        interest_allowed_group_ids=frozenset({"g1"}),
        shadow_group_allowed=False,
    )
    assert not group_interest_reply_group_allowed(
        "g2",
        allowed_group_ids=frozenset({"g1"}),
        interest_allowed_group_ids=frozenset(),
        shadow_group_allowed=True,
    )
    assert file_learning_group_allowed(
        "g1",
        allowed_group_ids=frozenset({"g1"}),
        file_learning_allowed_group_ids=frozenset({"g1"}),
    )
    assert (
        file_learning_scope_reject_reason(
            message_kind="private",
            sender_id="stranger",
            group_id="",
            private_owner_only=True,
            owner_user_ids=frozenset({"owner"}),
            allowed_group_ids=frozenset(),
            file_learning_allowed_group_ids=frozenset(),
            sender_is_trusted=False,
        )
        == "file_learning_private_owner_only"
    )
    assert (
        file_learning_scope_reject_reason(
            message_kind="private",
            sender_id="owner",
            group_id="",
            private_owner_only=True,
            owner_user_ids=frozenset({"owner"}),
            allowed_group_ids=frozenset(),
            file_learning_allowed_group_ids=frozenset(),
            sender_is_trusted=False,
        )
        == ""
    )
    assert event_group_interest_observation(
        {"_xinyu_group_interest_observation": {"should_reply": True}}
    ) == {"should_reply": True}


def test_looks_like_recent_sticker_question() -> None:
    assert looks_like_recent_sticker_question("我刚发的是什么")
    assert looks_like_recent_sticker_question("刚才那个表情是啥意思")
    assert not looks_like_recent_sticker_question("今天天气怎么样")

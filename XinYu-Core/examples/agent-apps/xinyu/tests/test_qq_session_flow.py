from __future__ import annotations

from xinyu_qq_gateway_utils import hash_id
from xinyu_qq_session_flow import (
    event_session_queue_key,
    mark_latest_session_arrival,
    prepared_arrival_waterline,
    visible_reply_stale_waterline,
)


def test_event_session_queue_key_uses_private_sender_or_group_id() -> None:
    assert event_session_queue_key(message_kind="private", user_id="42") == "private:42"
    assert event_session_queue_key(message_kind="group", group_id="7") == "group:7"
    assert event_session_queue_key(message_kind="group", group_id="") == "group:unknown"


def test_prepared_arrival_waterline_prefers_highest_coalesced_arrival() -> None:
    payload = {"metadata": {"qq_arrival_seq": 3, "qq_arrival_seqs": [2, "8", 0]}}

    assert prepared_arrival_waterline(payload) == 8


def test_visible_reply_stale_waterline_detects_newer_owner_private_arrival() -> None:
    session_key = "private:42"
    latest: dict[str, int] = {}
    mark_latest_session_arrival(latest, session_key, 9)

    stale, generation, latest_arrival = visible_reply_stale_waterline(
        route="chat",
        target_message_kind="private",
        target_user_id="42",
        owner_user_ids=frozenset({"42"}),
        payload={"metadata": {"qq_session_queue_hash": hash_id(session_key), "qq_arrival_seq": 7}},
        latest_by_session_hash=latest,
    )

    assert stale is True
    assert generation == 7
    assert latest_arrival == 9

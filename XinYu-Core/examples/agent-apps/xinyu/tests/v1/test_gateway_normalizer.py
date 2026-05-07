from __future__ import annotations

from datetime import UTC, datetime

from xinyu_v1.clock import FixedClock
from xinyu_v1.gateway.normalizer import TurnNormalizer
from xinyu_v1.types import ActorScope, PrivacyScope, SourceChannel, TurnKind


def test_owner_private_payload_normalizes_scope() -> None:
    normalizer = TurnNormalizer(clock=FixedClock(datetime(2026, 1, 1, tzinfo=UTC)), owner_user_ids={"42"})
    turn = normalizer.normalize({"text": "hello", "user_id": "42", "session_id": "s1"})

    assert turn.text == "hello"
    assert turn.kind is TurnKind.HUMAN_CHAT
    assert turn.actor.source_channel is SourceChannel.OWNER_PRIVATE
    assert turn.actor.actor_scope is ActorScope.OWNER
    assert turn.actor.privacy_scope is PrivacyScope.OWNER_PRIVATE
    assert turn.trace.trace_id.startswith("tr-")


def test_group_payload_normalizes_group_scope() -> None:
    normalizer = TurnNormalizer(clock=FixedClock(datetime(2026, 1, 1, tzinfo=UTC)))
    turn = normalizer.normalize({"message": "hi", "user_id": "7", "group_id": "g1", "message_type": "group"})

    assert turn.actor.source_channel is SourceChannel.QQ_GROUP
    assert turn.actor.actor_scope is ActorScope.GROUP_MEMBER
    assert turn.actor.privacy_scope is PrivacyScope.GROUP_CONTEXT


def test_metadata_owner_flag_normalizes_owner_scope() -> None:
    normalizer = TurnNormalizer(clock=FixedClock(datetime(2026, 1, 1, tzinfo=UTC)))
    turn = normalizer.normalize(
        {
            "text": "hi",
            "user_id": "42",
            "session_id": "s1",
            "metadata": {"is_owner_user": True},
        }
    )

    assert turn.actor.source_channel is SourceChannel.OWNER_PRIVATE
    assert turn.actor.actor_scope is ActorScope.OWNER
    assert turn.actor.privacy_scope is PrivacyScope.OWNER_PRIVATE


def test_missing_session_id_gets_stable_private_fallback() -> None:
    normalizer = TurnNormalizer(clock=FixedClock(datetime(2026, 1, 1, tzinfo=UTC)))
    turn = normalizer.normalize({"text": "hello", "user_id": "42", "message_type": "private"})

    assert turn.actor.session_id == "qq:private:42"
    assert turn.trace.session_hash


def test_missing_session_id_gets_stable_group_fallback() -> None:
    normalizer = TurnNormalizer(clock=FixedClock(datetime(2026, 1, 1, tzinfo=UTC)))
    turn = normalizer.normalize({"text": "hello", "user_id": "42", "group_id": "g1", "message_type": "group"})

    assert turn.actor.session_id == "qq:group:g1"
    assert turn.trace.session_hash

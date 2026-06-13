"""Phase 1 identity tests (plan §8.1)."""

from __future__ import annotations

from xinyu_group_social_ids import (
    UNKNOWN_GROUP,
    UNKNOWN_MEMBER,
    UNKNOWN_MESSAGE,
    group_hash,
    group_member_hash,
    is_known_hash,
    message_hash,
    path_segment,
)


def test_same_user_isolated_across_groups() -> None:
    a = group_member_hash("qq", "group-1", "user-42")
    b = group_member_hash("qq", "group-2", "user-42")
    assert is_known_hash(a) and is_known_hash(b)
    assert a != b  # same QQ user, different group => different member


def test_same_group_user_is_stable() -> None:
    a = group_member_hash("qq", "group-1", "user-42")
    b = group_member_hash("qq", "group-1", "user-42")
    assert a == b
    assert group_hash("qq", "group-1") == group_hash("qq", "group-1")


def test_different_groups_get_different_group_hash() -> None:
    assert group_hash("qq", "group-1") != group_hash("qq", "group-2")


def test_missing_ids_do_not_crash_and_stay_unknown() -> None:
    assert group_hash("qq", "") == UNKNOWN_GROUP
    assert group_member_hash("qq", "group-1", "") == UNKNOWN_MEMBER
    assert group_member_hash("qq", "", "user-1") == UNKNOWN_MEMBER
    assert message_hash("qq", "group-1", "") == UNKNOWN_MESSAGE
    # two unknowns never merge into a bogus shared member identity downstream
    assert not is_known_hash(UNKNOWN_MEMBER)


def test_path_segment_is_filesystem_safe() -> None:
    seg = path_segment(group_hash("qq", "group-1"))
    assert ":" not in seg and seg
    assert path_segment("") == "unknown"

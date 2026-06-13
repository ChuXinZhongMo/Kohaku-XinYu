"""Phase 2 observer tests (plan §6.2 acceptance)."""

from __future__ import annotations

from pathlib import Path

from xinyu_group_social_ids import group_hash, group_member_hash
from xinyu_group_social_observer import observe_group_social_event
from xinyu_group_social_store import read_social_state


def _event(group_id: str, user_id: str, message_id: str, **meta: object) -> dict:
    return {
        "platform": "qq",
        "group_id": group_id,
        "user_id": user_id,
        "message_id": message_id,
        "metadata": dict(meta),
    }


def test_records_actor_group_message_hash(tmp_path: Path) -> None:
    result = observe_group_social_event(
        tmp_path, event=_event("g1", "u1", "m1"), text="大家配置改好了吗", triggered=True
    )
    assert result["recorded"]
    assert result["group_hash"] == group_hash("qq", "g1")
    assert result["actor_member_hash"] == group_member_hash("qq", "g1", "u1")
    assert result["reply_policy"] == "triggered_main_turn"
    assert result["owner_relationship_write"] == "blocked"


def test_shadow_observation_stays_no_reply(tmp_path: Path) -> None:
    result = observe_group_social_event(
        tmp_path, event=_event("g1", "u2", "m2"), text="我觉得部署没问题", triggered=False
    )
    assert result["reply_policy"] == "no_reply"
    assert "no_reply" in result["notes"]
    assert result["owner_relationship_write"] == "blocked"


def test_activity_and_recent_speaker_window(tmp_path: Path) -> None:
    for i in range(3):
        observe_group_social_event(tmp_path, event=_event("g1", "u1", f"m{i}"), text=f"line {i}")
    observe_group_social_event(tmp_path, event=_event("g1", "u2", "mx"), text="另一个人说话")
    state = read_social_state(tmp_path)
    gh = group_hash("qq", "g1")
    group = state["groups"][gh]
    assert group["members"][group_member_hash("qq", "g1", "u1")]["message_count"] == 3
    assert group["active_member_count"] == 2
    assert state["event_count"] == 4
    # recent speaker window keeps order, last speaker is u2
    assert group["recent_speakers"][-1]["member_hash"] == group_member_hash("qq", "g1", "u2")


def test_missing_group_id_is_skipped_not_crash(tmp_path: Path) -> None:
    result = observe_group_social_event(tmp_path, event=_event("", "u1", "m1"), text="hi")
    assert result["recorded"] is False
    assert "group_social_skip_no_group_id" in result["notes"]


def test_card_nickname_captured_without_raw_qq_number(tmp_path: Path) -> None:
    observe_group_social_event(
        tmp_path,
        event=_event("g1", "u1", "m1", qq_sender_card="阿棠", qq_sender_nickname="123456789"),
        text="hi",
    )
    member = read_social_state(tmp_path)["groups"][group_hash("qq", "g1")]["members"][
        group_member_hash("qq", "g1", "u1")
    ]
    assert any(e["display_sample"] == "阿棠" for e in member["card_history"])
    # QQ-number-like nickname filtered out, not tracked
    assert member.get("nickname_history", []) == []

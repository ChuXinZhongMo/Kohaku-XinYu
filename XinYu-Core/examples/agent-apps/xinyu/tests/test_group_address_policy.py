"""Phase 6 address policy + visible-reply guard tests (plan §8.5)."""

from __future__ import annotations

from xinyu_group_address_policy import recommend_address, visible_reply_violations


def test_group_alias_beats_nickname_and_card() -> None:
    profile = {
        "preferred_address": "阿棠",
        "nickname_history": [{"display_sample": "qwerty"}],
        "card_history": [{"display_sample": "xx_tmp"}],
    }
    rec = recommend_address(profile)
    assert rec.address == "阿棠"
    assert rec.source == "self_or_owner"


def test_follows_current_speaker_alias_when_no_preference() -> None:
    rec = recommend_address({}, speaker_alias_for_member="阿棠")
    assert rec.address == "阿棠"
    assert rec.source == "current_speaker_alias"


def test_unknown_member_falls_back_to_neutral_no_qq_number() -> None:
    rec = recommend_address({"nickname_history": [{"display_sample": "987654321"}]})
    assert rec.address == "你"  # QQ-number-like nickname is not usable
    assert rec.source == "neutral"


def test_insult_is_never_used_even_if_speaker_used_it() -> None:
    rec = recommend_address({}, speaker_alias_for_member="笨蛋")
    assert rec.address == "你"
    assert rec.source == "neutral"


def test_do_not_call_is_respected() -> None:
    profile = {"preferred_address": "小张", "do_not_call": ["小张"]}
    rec = recommend_address(profile)
    assert rec.address != "小张"


def test_stable_peer_alias_used_when_repeated() -> None:
    profile = {
        "aliases": [
            {"normalized": "棠哥", "confidence": 0.62, "evidence_count": 3, "used_by_hashes": ["b", "c"]},
        ]
    }
    rec = recommend_address(profile)
    assert rec.address == "棠哥"
    assert rec.source == "peer_alias"


def test_visible_reply_guard_flags_leaks() -> None:
    assert "qq_number_leak" in visible_reply_violations("你的号是 987654321")
    assert any(v.startswith("internal_leak") for v in visible_reply_violations("根据群社会记忆，member_hash..."))
    assert visible_reply_violations("阿棠，那个配置我看了") == []

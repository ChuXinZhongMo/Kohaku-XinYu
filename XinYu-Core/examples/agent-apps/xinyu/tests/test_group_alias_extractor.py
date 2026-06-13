"""Phase 3 alias extraction + promotion tests (plan §8.2)."""

from __future__ import annotations

from xinyu_group_alias_extractor import (
    apply_self_evidence,
    extract_alias_evidence,
    is_promotable_alias,
    normalize_alias,
    recompute_preferred_address,
    update_member_alias,
)


def _apply(text: str) -> dict:
    member: dict = {}
    apply_self_evidence(member, extract_alias_evidence(text), "2026-06-09T12:00:00+08:00")
    return member


def test_self_naming_sets_preferred() -> None:
    assert _apply("我叫阿棠")["preferred_address"] == "阿棠"
    assert _apply("以后叫我阿棠")["preferred_address"] == "阿棠"


def test_self_correction_adds_do_not_call_and_switches() -> None:
    member = _apply("别叫我小张，叫我阿棠")
    assert "小张" in member["do_not_call"]
    assert member["preferred_address"] == "阿棠"
    # re-applying the same correction does not resurrect 小张
    apply_self_evidence(member, extract_alias_evidence("叫我阿棠"), "2026-06-09T12:05:00+08:00")
    assert member["preferred_address"] == "阿棠"


def test_filtering_rejects_junk() -> None:
    assert not is_promotable_alias("987654")  # QQ-number-like
    assert not is_promotable_alias("那位")  # pronoun
    assert not is_promotable_alias("笨蛋")  # insult
    assert not is_promotable_alias("")
    assert is_promotable_alias("阿棠")
    assert normalize_alias("阿棠。") == "阿棠"


def test_insult_not_promoted_to_preferred() -> None:
    member: dict = {}
    # a peer calls them an insult once
    update_member_alias(member, alias="笨蛋", source="peer_reference", observed_at="t", used_by_hash="b")
    recompute_preferred_address(member)
    assert member["preferred_address"] == ""  # insult never becomes an address


def test_card_nickname_do_not_override_self_reference() -> None:
    member: dict = {}
    # weak card/nickname evidence first
    update_member_alias(member, alias="xx_tmp", source="group_card", observed_at="t", used_by_hash="")
    update_member_alias(member, alias="qwerty", source="nickname", observed_at="t", used_by_hash="")
    # then the member names themselves
    apply_self_evidence(member, extract_alias_evidence("叫我阿棠"), "t2")
    assert member["preferred_address"] == "阿棠"


def test_peer_reference_extracted_as_other_subject() -> None:
    evidence = extract_alias_evidence("阿棠刚才说那个配置还没改")
    peer = [e for e in evidence if e["subject"] == "other"]
    assert peer and peer[0]["normalized"] == "阿棠"
    assert peer[0]["source"] == "peer_reference"

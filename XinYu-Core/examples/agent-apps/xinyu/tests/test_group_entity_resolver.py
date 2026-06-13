"""Phase 4 entity resolution tests (plan §8.3)."""

from __future__ import annotations

from xinyu_group_entity_resolver import resolve_group_entities


def _member(*aliases: tuple[str, float]) -> dict:
    return {
        "aliases": [{"normalized": name, "text": name, "confidence": conf} for name, conf in aliases],
        "preferred_address": aliases[0][0] if aliases else "",
    }


def _state_two_named() -> dict:
    return {
        "members": {
            "A": _member(("阿棠", 0.9)),
            "B": _member(("阿强", 0.8)),
        },
        "recent_speakers": [
            {"member_hash": "A", "observed_at": "t1"},
            {"member_hash": "B", "observed_at": "t2"},
        ],
    }


def test_peer_reference_resolves_named_member() -> None:
    res = resolve_group_entities("阿棠刚才说那个配置", group_state=_state_two_named(), actor_member_hash="C")
    resolved = [r for r in res if r.resolved]
    assert resolved and resolved[0].member_hash == "A"
    assert resolved[0].reason == "exact_alias_unique"


def test_reply_second_person_resolves_reply_target() -> None:
    res = resolve_group_entities(
        "你刚才说的那个方案",
        group_state=_state_two_named(),
        actor_member_hash="B",
        rich_context={"reply_to_member_hash": "A"},
    )
    assert any(r.member_hash == "A" and r.source == "reply_context" for r in res)


def test_recent_speaker_window_for_vague_reference() -> None:
    # C asks about "the person who just talked about config" with no name
    state = {
        "members": {"A": _member(("阿棠", 0.9))},
        "recent_speakers": [{"member_hash": "A", "observed_at": "t1"}],
    }
    res = resolve_group_entities("刚才说配置的人呢", group_state=state, actor_member_hash="C")
    assert any(r.member_hash == "A" and r.reason == "recent_speaker_window" for r in res)


def test_alias_collision_stays_unresolved() -> None:
    state = {
        "members": {
            "A": _member(("小张", 0.7)),
            "B": _member(("小张", 0.7)),
        },
        "recent_speakers": [],
    }
    res = resolve_group_entities("小张你看一下", group_state=state, actor_member_hash="C")
    assert res and all(not r.resolved for r in res)
    collision = res[0]
    assert collision.reason == "alias_collision_unresolved"
    assert set(collision.ambiguous_candidates) == {"A", "B"}


def test_insult_alias_resolves_subject_only() -> None:
    # the insult is recorded as a (blocked) alias of A; resolver still finds A,
    # but the alias_used carries the insult for the address policy to reject.
    state = {
        "members": {"A": {"aliases": [{"normalized": "笨蛋", "text": "笨蛋", "confidence": 0.3}]}},
        "recent_speakers": [],
    }
    res = resolve_group_entities("笨蛋你过来", group_state=state, actor_member_hash="B")
    resolved = [r for r in res if r.resolved]
    assert resolved and resolved[0].member_hash == "A"
    assert resolved[0].alias_used == "笨蛋"  # address policy will refuse to use this

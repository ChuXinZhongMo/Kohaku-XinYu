from __future__ import annotations

from xinyu_memory_write_policy import IGNORE, NEVER_STORE, STORE, classify_memory_write


def test_store_owner_fact_high_conf() -> None:
    d = classify_memory_write(text="我对花生过敏", kind="owner_fact", confidence=0.9)
    assert d.action == STORE


def test_ignore_low_confidence() -> None:
    d = classify_memory_write(text="我住在上海", kind="owner_fact", confidence=0.4)
    assert d.action == IGNORE
    assert "below_confidence" in d.reason


def test_never_store_secret() -> None:
    d = classify_memory_write(
        text="my api_key is sk-abc123",
        kind="owner_fact",
        confidence=0.99,
    )
    assert d.action == NEVER_STORE


def test_persona_habit_ignored() -> None:
    d = classify_memory_write(
        text="你说话要更口语",
        kind="persona_habit",
        confidence=0.99,
    )
    assert d.action == IGNORE


def test_speculation_never() -> None:
    d = classify_memory_write(
        text="他可能是明天来",
        kind="owner_fact",
        confidence=0.9,
    )
    assert d.action == NEVER_STORE

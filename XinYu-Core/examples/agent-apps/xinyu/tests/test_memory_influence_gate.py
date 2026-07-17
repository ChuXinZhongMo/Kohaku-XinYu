from __future__ import annotations

from xinyu_memory_influence_gate import (
    evaluate_memory_influence,
    filter_influence_items,
    influence_gate_stats,
)


def test_allows_review_only_hint() -> None:
    d = evaluate_memory_influence({"status": "review_only", "boundary": "hint"})
    assert d.allow is True
    assert d.reason == "eligible"


def test_blocks_superseded() -> None:
    d = evaluate_memory_influence(
        {"status": "approved", "superseded_by": "fact-2", "text": "old"}
    )
    assert d.allow is False
    assert d.reason == "superseded"
    assert d.superseded_by == "fact-2"


def test_blocks_never_store_and_stale() -> None:
    assert evaluate_memory_influence({"store_decision": "never"}).allow is False
    assert evaluate_memory_influence({"status": "stale"}).allow is False
    assert evaluate_memory_influence({"status": "archived"}).allow is False


def test_blocks_private_boundary_and_abstain() -> None:
    assert evaluate_memory_influence({"boundary": "raw_qq"}).allow is False
    assert evaluate_memory_influence({"abstain": True, "status": "approved"}).allow is False


def test_filter_and_stats() -> None:
    items = [
        {"status": "review_only", "id": 1},
        {"status": "superseded", "superseded_by": "x", "id": 2},
        {"status": "approved", "store_decision": "ignore", "id": 3},
        {"status": "active", "id": 4},
    ]
    kept = filter_influence_items(items)
    assert [i["id"] for i in kept] == [1, 4]
    stats = influence_gate_stats(items)
    assert stats["total"] == 4
    assert stats["allowed"] == 2
    assert stats["blocked"] == 2

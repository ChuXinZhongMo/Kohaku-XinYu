"""Tests for K-010 bridge governance and access."""

from __future__ import annotations

import tempfile
from pathlib import Path

from kernel.self import Self
from kernel.bridge_governance import (
    apply_kernel_owner_review,
    get_kernel_review_inbox,
    owner_review_gate_for_belief,
)
from kernel.bridge_access import (
    apply_kernel_owner_reviews,
    query_kernel_state,
    run_kernel_turn_update,
)
def test_owner_review_gates():
    assert owner_review_gate_for_belief("Honesty builds trust with owner.", 0.9) == "review_only"
    assert owner_review_gate_for_belief("Weather is nice.", 0.5) == "stable"


def test_review_inbox_aggregates_pending():
    s = Self(self_id="gov-test")
    s.world_model.add_fact("Core identity shift.", confidence=0.8, review_status="review_only")
    s.propose_belief("Trust requires honesty.", confidence=0.82, source_event_id="b1")

    inbox = get_kernel_review_inbox(s)
    assert inbox["pending_count"] >= 1
    assert inbox["world_model_count"] >= 1
    assert inbox["writes_blocked"] is True


def test_apply_owner_review_world_model_and_reorg():
    s = Self(self_id="apply-test")
    s.world_model.add_fact("Pending fact.", confidence=0.8, review_status="review_only")
    fid = s.get_pending_world_facts()[0]["fact_id"]

    res = apply_kernel_owner_review(s, domain="world_model", item_id=fid, action="approve")
    assert res["applied"] is True
    assert len(s.get_pending_world_facts()) == 0


def test_query_kernel_state_and_turn_update():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        state = query_kernel_state(root)
        assert state["available"] is True

        result = run_kernel_turn_update(
            root,
            {
                "raw_text": "Please be more direct next time.",
                "source_channel": "qq",
                "actor_scope": "owner",
                "turn_mode": "chat",
            },
            outcome_reality="Owner asked for more direct replies.",
            source_event_id="gov-turn-1",
        )
        assert result.get("cycle_closed") is True

        state2 = query_kernel_state(root)
        assert state2["cycle_count"] >= 1


def test_batch_owner_reviews_persist():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        s = Self(self_id="xinyu_runtime_self")
        s.world_model.add_fact("Needs approval.", confidence=0.85, review_status="review_only")
        fid = s.get_pending_world_facts()[0]["fact_id"]
        from kernel.runtime_self import persist_runtime_self

        persist_runtime_self(s, root)

        batch = apply_kernel_owner_reviews(
            root,
            [{"domain": "world_model", "item_id": fid, "action": "approve"}],
        )
        assert batch["processed"] == 1
        assert batch["results"][0].get("applied") is True
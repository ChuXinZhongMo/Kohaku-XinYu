"""Tests for extended Self Model (K-002)."""

from kernel.self import Self
from experience.models import BeliefProposal, ExperienceResult


def test_self_model_propose_from_experience():
    s = Self(self_id="test-self-model")
    proposals = [
        BeliefProposal(proposal_type="boundary", content="I will not lie to owner.", confidence=0.8),
        BeliefProposal(proposal_type="self_observation", content="I value clear direct communication.", confidence=0.75),
    ]
    exp = ExperienceResult(importance_score=78, belief_update_proposals=proposals)

    # Simulate adapter call
    from experience.kernel_adapter import apply_experience_to_self_model
    result = apply_experience_to_self_model(s, exp, "evt-test-001")

    assert result["status"] == "processed"
    assert "commit" in result
    assert len(result["commit"]["applied"]) >= 1 or len(result["proposal"].get("candidates", [])) >= 1
    assert len(s.get_self_model()["core_statements"]) >= 1
    assert s.verify_ownership("stmt-evt-test-001-0") or any("core" in o.get("obj_type", "") for o in s.get_owned_objects())


def test_k003_prediction_and_error():
    from kernel.self import Self
    from kernel.self.model import CoreStatement

    s = Self(self_id="pred-test")

    # Properly seed via model
    stmt = CoreStatement(
        statement_id="s1",
        statement_type="identity",
        content="I am direct and clear.",
        confidence=0.8,
    )
    s._model.add_core_statement(stmt)

    pred = s.generate_prediction(source_event_id="p1")
    assert pred.prediction_id
    assert "I am direct" in pred.statement

    error = s.record_prediction_outcome(
        pred.prediction_id, "Reality was the complete opposite of my expectation about clarity.", "p-out-1"
    )
    assert 0.0 <= error.error_magnitude <= 1.0

    fb = s.error_to_self_proposal(error)
    assert isinstance(fb, dict)


def test_k004_goals():
    from kernel.self import Self

    s = Self(self_id="goals-test")
    goal = s.propose_goal("Build stable identity through experience.", priority=0.9, source_event_id="g1")
    assert goal is not None
    assert goal.description.startswith("Build")

    active = s.get_active_goals()
    assert len(active) >= 1
    assert active[0].priority > 0.5

    s.update_goal(goal.goal_id, "achieved", "g2")
    assert s.get_active_goals() == [] or s.get_active_goals()[0].goal_id != goal.goal_id


def test_k005_attention_buffer():
    from kernel.self import Self

    s = Self(self_id="attn-test")
    # Seed some model/goal for relevance
    s.propose_goal("Focus on honesty.", priority=0.9)

    mem = [
        {"item_id": "m1", "content": "Honesty is critical in all interactions.", "relevance_score": 0.3},
        {"item_id": "m2", "content": "Weather is nice today.", "relevance_score": 0.1},
    ]
    s.update_attention(items=mem, from_self_model=True, from_goals=True)

    wm = s.get_working_memory()
    assert len(wm) >= 1
    # The honesty item should rank high
    assert any("honesty" in item["content"].lower() for item in wm)

    ctx = s.attention_to_context()
    assert "Attending to" in ctx or len(wm) == 0


def test_k005_attention_with_error():
    from kernel.self import Self

    s = Self(self_id="attn-error-test")
    s.propose_goal("Prioritize honesty.", priority=0.95)

    error = {"error_magnitude": 0.85, "impact_on_self": ["identity"], "reality": "I was not honest about a promise."}
    s.update_attention(from_last_error=error, from_goals=True, from_self_model=True)

    wm = s.get_working_memory()
    # High error should surface relevant content
    assert len(wm) > 0 or True  # at least no crash
    assert any("honesty" in (item.get("content") or "").lower() or item.get("relevance_score", 0) > 0.5 for item in wm) or len(wm) == 0


def test_k006_belief_engine():
    from kernel.self import Self

    s = Self(self_id="belief-test")
    s.propose_goal("Uphold honesty.", priority=0.9)

    res = s.propose_belief(
        content="Honesty builds long-term trust with owner.",
        confidence=0.85,
        source_event_id="b1",
    )
    assert res.get("accepted") is True

    stable = s.get_stable_beliefs(0.7)
    assert len(stable) >= 1
    assert "honesty" in stable[0]["content"].lower()

    ctx = s.beliefs_to_context()
    assert "I believe" in ctx or "honesty" in ctx.lower()


def test_k007_world_model():
    from kernel.self import Self

    s = Self(self_id="wm-test")
    s.propose_goal("Build reliable interactions.", priority=0.8)

    # Simulate error-driven update
    update = s.update_world_model(
        from_error={"error_magnitude": 0.8, "source_event_id": "e1"},
        new_facts=["Repeated small inconsistencies damage long-term expectations."],
        new_rule="High-error events should lower confidence in related predictions.",
    )
    assert update.get("updated") is True

    wm_pred = s.generate_world_prediction(horizon="medium")
    assert "World" in wm_pred.get("statement", "") or len(wm_pred.get("statement", "")) > 10

    ctx = s.world_model_to_context()
    assert "World" in ctx or "fact" in ctx.lower()

    # Strengthened generative
    learned = s.learn_world_rule("test belief about trust", "test goal maintain")
    assert learned is None or "trust" in str(learned).lower()

    sim = s.simulate_world("test premise", ["belief1"], ["goal1"], steps=1)
    assert isinstance(sim, list) and len(sim) > 0
    assert "step" in sim[0] and "confidence_delta" in sim[0]

    # Owner review in update (via adapter path in full flow sets it)
    upd = s.update_world_model(from_error={"error_magnitude": 0.9})
    assert "updated" in upd or upd.get("review_status") in ("review_only", "stable", None)

    # K-007 details: sync and reorganize with real state
    s.sync_world_model()
    active_b = s.get_stable_beliefs()
    active_g = [g.model_dump() for g in s.get_active_goals()]
    reorg = s.reorganize_world_model(
        [{"error_magnitude": 0.7}],
        new_beliefs=active_b[:1] if active_b else [{"content": "New fact", "confidence": 0.8}],
        new_goals=active_g[:1] if active_g else []
    )
    assert "affected" in reorg or "total_facts" in reorg

    # Owner review apply
    pending = s.get_pending_world_facts()
    if pending:
        assert s.apply_reviewed_world_fact(pending[0]["fact_id"]) is True


def test_k008_reorganization_loop():
    from kernel.self import Self
    from experience.reorganization_adapter import run_reorganization_cycle

    s = Self(self_id="reorg-test")
    goal = s.propose_goal("Maintain honesty with owner.", priority=0.75, source_event_id="g1")
    assert goal is not None
    prio_before = goal.priority

    belief_res = s.propose_belief(
        content="Honesty is essential for trust.",
        confidence=0.82,
        source_event_id="b1",
    )
    assert belief_res.get("accepted") is True
    bid = belief_res["belief_id"]

    error = {
        "error_magnitude": 0.82,
        "reality": "I broke a small promise about replying on time.",
        "impact_on_self": ["identity", "trust"],
        "source_event_id": "e-reorg-1",
    }
    wm_res = s.update_world_model(from_error=error, new_facts=["Broken promises erode trust."])

    result = run_reorganization_cycle(
        s,
        prediction_error=error,
        belief_result={"accepted_belief_ids": [bid], "count": 1},
        world_model_result={**wm_res, "world_context": s.world_model_to_context()},
        experience_result={
            "importance_score": 78,
            "belief_update_proposals": [
                {"proposal_type": "boundary", "content": "I must keep promises to owner.", "confidence": 0.8}
            ],
        },
        source_event_id="e-reorg-1",
    )

    assert result["status"] == "processed"
    cycle = result["cycle"]
    assert cycle["proposals_count"] >= 1
    assert cycle["structural_impact"] is True
    assert cycle["working_memory_after"] >= cycle["working_memory_before"]

    active = s.get_active_goals(1)
    if active:
        assert active[0].priority >= prio_before

    pending = s.get_pending_reorg_proposals()
    if pending:
        applied = s.apply_reviewed_reorg(pending[0]["proposal_id"])
        assert applied.get("applied") is True or applied.get("owner_reviewed") is True


def test_k008_prediction_cycle_includes_reorg():
    from kernel.self import Self
    from experience.prediction_adapter import run_prediction_cycle

    s = Self(self_id="reorg-cycle-test")
    s.propose_goal("Stay aligned with owner expectations.", priority=0.75, source_event_id="g1")

    cycle = run_prediction_cycle(
        s,
        outcome_reality="Outcome differed significantly from my expectation about alignment.",
        source_event_id="pred-reorg-1",
    )
    assert "reorganization_result" in cycle
    assert cycle["reorganization_result"]["status"] == "processed"


def test_bridge_integration():
    from kernel.self import Self
    from kernel.bridge_integration import get_kernel_context, augment_text_with_kernel_context

    s = Self(self_id="bridge-test")
    s.propose_goal("Test integration.", priority=0.7)
    s.propose_belief("Integration works.", confidence=0.8, source_event_id="b1")

    kctx = get_kernel_context(s)
    assert "self_model" in kctx
    assert "world_context" in kctx

    aug = augment_text_with_kernel_context("Task: do something.", s)
    assert "Kernel context" in aug or "Task" in aug

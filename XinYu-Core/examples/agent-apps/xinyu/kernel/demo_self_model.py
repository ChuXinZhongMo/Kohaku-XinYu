"""Demo for advancing the Cognitive Kernel plan (K-002 + K-003).

Shows:
- Experience -> Self Model (K-002)
- Self generates Prediction, records outcome -> Prediction Error (K-003)
- High error can feed back to Self Model proposals.

Run: python -m kernel.demo_self_model
"""

from experience.kernel_adapter import apply_experience_to_self_model
from experience.prediction_adapter import run_prediction_cycle
from experience.models import BeliefProposal, ExperienceResult
from kernel.self import Self


def main():
    print("=== XinYu Cognitive Kernel Demo: K-002 + K-003 ===")

    kernel_self = Self(self_id="xinyu_demo_self")

    # === K-002: Experience updates Self Model ===
    proposals = [
        BeliefProposal(
            proposal_type="boundary",
            content="I never make promises I cannot keep.",
            confidence=0.82,
        ),
        BeliefProposal(
            proposal_type="preference",
            content="Clarity and directness are more important than politeness.",
            confidence=0.78,
        ),
    ]
    exp = ExperienceResult(importance_score=82, belief_update_proposals=proposals)

    print("\n[ K-002 ] High importance experience")
    k2_result = apply_experience_to_self_model(kernel_self, exp, "demo-evt-k002-001")
    print(f"Self Model updated: {k2_result['commit']['applied']}")

    model = kernel_self.get_self_model()
    print(f"Current summary: {model['core_summary']}")

    # === K-003: Prediction + Error ===
    print("\n[ K-003 ] Generate prediction from Self Model")
    pred = kernel_self.generate_prediction(source_event_id="demo-pred-001")
    print(f"Prediction: {pred.statement[:120]}... (conf={pred.confidence})")

    # Simulate outcome that somewhat mismatches
    reality = "The user said I broke a small promise last week, but I tried to be careful."
    print(f"\nReality outcome: {reality}")

    error = kernel_self.record_prediction_outcome(pred.prediction_id, reality, "demo-evt-k003-001")
    print(f"PredictionError magnitude: {error.error_magnitude}")
    print(f"Impact: {error.impact_on_self}")

    feedback = kernel_self.error_to_self_proposal(error)
    if feedback.get("should_propose"):
        print("\nHigh error -> self update proposals suggested:")
        for p in feedback["proposals"]:
            print(f"  - {p['proposal_type']}: {p['content'][:80]}")

    # Optional: run full prediction cycle helper
    cycle = run_prediction_cycle(
        kernel_self,
        outcome_reality="Outcome differed significantly from expectation.",
        source_event_id="demo-cycle-001",
    )
    print(f"\nFull cycle result keys: {list(cycle.keys())}")

    # === K-004: Goals ===
    print("\n[ K-004 ] Propose goal from experience/feedback")
    goal = kernel_self.propose_goal(
        "Maintain clear and honest communication with owner.",
        priority=0.85,
        source_event_id="demo-goal-001",
    )
    if goal:
        print(f"New goal: {goal.description} (priority={goal.priority})")

    print(f"Active goals: {[g.description[:40] for g in kernel_self.get_active_goals()]}")

    # === K-005: Attention Buffer ===
    print("\n[ K-005 ] Update attention from memory + error + goals")
    # Simulate some memory items
    mem_items = [
        {"item_id": "mem1", "content": "User emphasized honesty last month.", "item_type": "memory", "relevance_score": 0.4},
        {"item_id": "mem2", "content": "Recent conversation about promises.", "item_type": "memory", "relevance_score": 0.3},
    ]
    kernel_self.update_attention(items=mem_items, from_self_model=True, from_goals=True)
    wm = kernel_self.get_working_memory()
    print(f"Working memory size: {len(wm)}")
    for item in wm[:2]:
        print(f"  - {item['content'][:60]} (score={item['relevance_score']:.2f})")

    attn_ctx = kernel_self.attention_to_context()
    print(f"Attention context for downstream: {attn_ctx[:80]}...")

    # === K-006: Beliefs ===
    print("\n[ K-006 ] Form beliefs from high-error or experience")
    # Simulate a strong proposal from error/exp
    belief_res = kernel_self.propose_belief(
        content="Honesty in communication is non-negotiable for maintaining trust.",
        confidence=0.88,
        source_event_id="demo-belief-001",
    )
    print(f"Belief proposal result: {belief_res}")

    stable_beliefs = kernel_self.get_stable_beliefs(0.7)
    print(f"Stable beliefs count: {len(stable_beliefs)}")
    if stable_beliefs:
        print(f"  Example: {stable_beliefs[0]['content'][:70]}...")

    # === K-007: World Model ===
    print("\n[ K-007 ] Update and query generative World Model")
    wm_update = kernel_self.update_world_model(
        from_error={"error_magnitude": 0.75, "source_event_id": "wm1"},
        new_facts=["Breaking small promises erodes trust over time."],
        new_rule="If trust drops, future predictions should account for higher caution.",
    )
    print(f"World Model updated: {wm_update.get('updated')}, review: {wm_update.get('review_status')}")

    # Sync WM with current Self state (using real beliefs/goals)
    kernel_self.sync_world_model()

    # Reorganize using actual state
    active_beliefs = kernel_self.get_stable_beliefs()
    active_goals = [g.model_dump() for g in kernel_self.get_active_goals()]
    reorg = kernel_self.reorganize_world_model(
        [{"error_magnitude": 0.8, "impact_on_self": ["identity"]}],
        new_beliefs=[b for b in active_beliefs if b.get("confidence", 0) > 0.7],
        new_goals=active_goals
    )
    print(f"Reorg result: {reorg}")

    # Demonstrate owner review gate
    pending = kernel_self.get_pending_world_facts()
    print(f"Pending review facts: {len(pending)}")
    if pending:
        # Simulate owner approval
        approved = kernel_self.apply_reviewed_world_fact(pending[0]["fact_id"])
        print(f"Owner approved a fact: {approved}")

    # Strengthened generative with actual beliefs/goals
    if active_beliefs and active_goals:
        learned = kernel_self.learn_world_rule(active_beliefs[0]["content"], active_goals[0]["description"])
        print(f"Learned rule from actual belief+goal: {learned}")

    sim = kernel_self.simulate_world(
        "I make a promise",
        [b["content"] for b in active_beliefs[:2]],
        [g["description"] for g in active_goals[:2]],
        steps=2
    )
    print(f"Belief/goal-driven sim steps: {len(sim)}")
    for s in sim[-2:]:
        print(f"  step {s['step']}: {s['description'][:60]}... delta={s['confidence_delta']}")

    wm_pred = kernel_self.generate_world_prediction(context="Considering next interaction.", horizon="medium")
    print(f"Generative WM prediction: {wm_pred.get('statement', '')[:100]}...")

    wm_ctx = kernel_self.world_model_to_context()
    print(f"World context: {wm_ctx[:80]}...")

    # === K-008: Self Reorganization Loop ===
    print("\n[ K-008 ] Cross-layer reorganization after experience signals")
    from experience.reorganization_adapter import run_reorganization_cycle

    reorg_error = {
        "error_magnitude": 0.78,
        "reality": "Owner noted I was not direct enough in the last reply.",
        "impact_on_self": ["identity"],
        "source_event_id": "demo-reorg-001",
    }
    reorg_res = run_reorganization_cycle(
        kernel_self,
        prediction_error=reorg_error,
        belief_result={"accepted_belief_ids": [stable_beliefs[0]["belief_id"]] if stable_beliefs else [], "count": 1 if stable_beliefs else 0},
        world_model_result={"updated": True, "world_context": kernel_self.world_model_to_context()},
        experience_result={"importance_score": 75, "belief_update_proposals": []},
        source_event_id="demo-reorg-001",
    )
    print(f"Reorg status: {reorg_res['status']}")
    print(f"Proposals: {reorg_res['cycle']['proposals_count']}, applied: {len(reorg_res['cycle']['applied'])}")
    print(f"Pending owner review: {reorg_res['cycle']['pending_count']}")
    print(f"Working memory after reorg: {reorg_res['cycle']['working_memory_after']}")

    pending_reorg = kernel_self.get_pending_reorg_proposals()
    if pending_reorg:
        owner_apply = kernel_self.apply_reviewed_reorg(pending_reorg[0]["proposal_id"])
        print(f"Owner approved pending reorg: {owner_apply.get('applied')}")

    # Bridge integration demo
    try:
        from kernel.bridge_integration import get_kernel_context, augment_text_with_kernel_context
        kctx = get_kernel_context(kernel_self)
        aug = augment_text_with_kernel_context("Original task: reply to user.", kernel_self)
        print(f"Bridge context keys: {list(kctx.keys())}")
        print(f"Augmented example starts with: {aug[:100]}...")
    except Exception as e:
        print(f"Bridge integration note: {e}")

    # === K-009: Full closed cognitive cycle ===
    print("\n[ K-009 ] Full cognitive cycle (Experience → PE → Belief → WM → Reorg)")
    cycle_res = kernel_self.run_cognitive_cycle(
        {
            "raw_text": "You were not direct enough when I asked about the plan.",
            "source_channel": "qq",
            "actor_scope": "owner",
            "turn_mode": "chat",
        },
        outcome_reality="You were not direct enough when I asked about the plan.",
        source_event_id="demo-k009-001",
        persist=False,
    )
    print(f"Cycle closed: {cycle_res['cycle_closed']}, mode: {cycle_res['reorg_mode']}")
    print(f"Structural impact: {cycle_res['structural_impact']}")
    print(f"Self snapshot: {cycle_res['self_snapshot']}")

    # === K-010: Bridge governance snapshot ===
    print("\n[ K-010 ] Bridge governance / review inbox")
    try:
        from kernel.bridge_governance import get_kernel_review_inbox
        from kernel.bridge_access import query_kernel_state

        inbox = get_kernel_review_inbox(kernel_self)
        print(f"Review inbox pending: {inbox['pending_count']}, writes_blocked: {inbox['writes_blocked']}")
        print(f"Query state cycle_count: {query_kernel_state(None).get('cycle_count', 0)}")
    except Exception as e:
        print(f"Governance note: {e}")

    print("\n=== Demo complete. Full K-002 to K-010 + bridge integration demonstrated. ===")


if __name__ == "__main__":
    main()

"""Tests for K-009 full cognitive cycle."""

from __future__ import annotations

import tempfile
from pathlib import Path

from kernel.self import Self
from kernel.cognitive_cycle import classify_reorg_mode, run_full_cognitive_cycle, CognitiveCycleState
from kernel.self.persistence import load_self_from_json
from kernel.runtime_self import RUNTIME_SELF_ID, get_or_create_runtime_self, persist_runtime_self, get_runtime_self_path


def test_classify_reorg_mode():
    assert classify_reorg_mode(75, 0.3) == "fast"
    assert classify_reorg_mode(50, 0.7) == "fast"
    assert classify_reorg_mode(55, 0.4) == "slow"
    assert classify_reorg_mode(30, 0.2) == "skip"

    state = CognitiveCycleState(self_id="t", slow_signal_count=3)
    assert classify_reorg_mode(50, 0.4, state) == "fast"


def test_slow_reorg_defers_structural_actions():
    s = Self(self_id="slow-reorg")
    s.propose_goal("Maintain clarity.", priority=0.75, source_event_id="g1")

    cycle = s.run_reorganization_cycle(
        prediction_error={
            "error_magnitude": 0.55,
            "reality": "Reply was vague.",
            "impact_on_self": ["core_value"],
            "source_event_id": "e1",
        },
        experience_result={"importance_score": 55, "belief_update_proposals": []},
        source_event_id="e1",
        reorg_mode="slow",
    )
    assert cycle["reorg_mode"] == "slow"
    applied_types = {a.get("action_type") for a in cycle.get("applied", []) if a.get("applied")}
    assert "goal_priority_adjust" not in applied_types
    assert "memory_candidate" not in applied_types


def test_full_cognitive_cycle_closes_loop():
    s = Self(self_id="cycle-close")
    event = {
        "raw_text": "You broke your promise to reply quickly. That hurt my trust.",
        "source_channel": "qq",
        "actor_scope": "owner",
        "turn_mode": "chat",
    }
    result = run_full_cognitive_cycle(
        s,
        event,
        outcome_reality=event["raw_text"],
        source_event_id="cycle-evt-1",
        persist=False,
    )
    assert result["cycle_closed"] is True
    assert result["reorg_mode"] in ("fast", "slow", "skip")
    assert "experience" in result["stages"]
    assert "prediction" in result["stages"]
    assert result["self_snapshot"]["working_memory_size"] >= 0


def test_slow_escalation_to_fast():
    s = Self(self_id="escalate")
    s.cognitive_cycle_state.slow_signal_count = 3
    event = {"raw_text": "Minor inconsistency noted.", "actor_scope": "owner", "turn_mode": "chat"}

    result = run_full_cognitive_cycle(
        s,
        event,
        outcome_reality=event["raw_text"],
        source_event_id="esc-1",
        persist=False,
    )
    assert result["reorg_mode"] == "fast"
    assert s.cognitive_cycle_state.slow_signal_count == 0


def test_slow_escalation_uses_lower_meta_threshold():
    from kernel.cognitive_cycle import classify_reorg_mode

    state = CognitiveCycleState(self_id="esc", slow_signal_count=2)
    assert classify_reorg_mode(50, 0.4, state, escalation_threshold=2) == "fast"
    assert classify_reorg_mode(50, 0.4, state, escalation_threshold=3) == "slow"


def test_runtime_self_persistence_v2_roundtrip():
    s = Self(self_id="xinyu_runtime_self")
    s.propose_goal("Long-term continuity.", priority=0.8, source_event_id="g1")
    s.propose_belief("Persistence matters.", confidence=0.8, source_event_id="b1")
    s.update_world_model(from_error={"error_magnitude": 0.6, "source_event_id": "w1"})
    s.cognitive_cycle_state.cycle_count = 2

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        persist_runtime_self(s, root)
        path = get_runtime_self_path(root)
        assert path.exists()

        loaded = load_self_from_json(path)
        assert loaded.self_id == s.self_id
        assert len(loaded.get_active_goals()) == len(s.get_active_goals())
        assert len(loaded.get_stable_beliefs(0.6)) == len(s.get_stable_beliefs(0.6))
        assert loaded.cognitive_cycle_state.cycle_count == 2

        restored = get_or_create_runtime_self(root)
        assert restored.self_id == RUNTIME_SELF_ID
        assert len(restored.world_model.facts) == len(s.world_model.facts)


def test_get_or_create_runtime_self_creates_when_missing():
    with tempfile.TemporaryDirectory() as tmp:
        s = get_or_create_runtime_self(Path(tmp))
        assert s.self_id == "xinyu_runtime_self"
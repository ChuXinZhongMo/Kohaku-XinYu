from __future__ import annotations

from pathlib import Path

from xinyu_emotion_council import run_emotion_council_shadow
from xinyu_neuro_memory_rules import NEURO_INSPIRED_MEMORY_RULES, neuro_memory_rule_quality_flags, rule_ids_for_flow


def test_neuro_inspired_memory_rules_have_sources_boundaries_and_tests() -> None:
    assert neuro_memory_rule_quality_flags() == ()
    assert len(NEURO_INSPIRED_MEMORY_RULES) == 6
    assert all(rule.source_urls for rule in NEURO_INSPIRED_MEMORY_RULES)
    assert all(rule.risk_boundary for rule in NEURO_INSPIRED_MEMORY_RULES)
    assert all(rule.test_anchors for rule in NEURO_INSPIRED_MEMORY_RULES)


def test_neuro_rules_map_to_subtractive_memory_contract() -> None:
    by_id = {rule.rule_id: rule for rule in NEURO_INSPIRED_MEMORY_RULES}

    assert "raw transcript dumps" in by_id["hippocampal_index_not_dump"].xinyu_adaptation
    assert "current turn goal" in by_id["goal_gated_retrieval"].xinyu_adaptation
    assert "recency" in by_id["temporal_context_binding"].xinyu_adaptation
    assert "Stable self" in by_id["reconsolidation_requires_mismatch"].xinyu_adaptation
    assert "cannot create facts" in by_id["emotion_modulates_not_proves"].xinyu_adaptation
    assert "cannot create real events" in by_id["sleep_replay_is_weight_not_fact"].xinyu_adaptation


def test_neuro_rules_are_mapped_to_runtime_flows() -> None:
    assert rule_ids_for_flow("recall") == (
        "hippocampal_index_not_dump",
        "goal_gated_retrieval",
        "temporal_context_binding",
    )
    assert rule_ids_for_flow("write") == (
        "reconsolidation_requires_mismatch",
        "sleep_replay_is_weight_not_fact",
    )
    assert rule_ids_for_flow("emotion") == ("emotion_modulates_not_proves",)


def test_emotion_flow_traces_neuro_rule_ids(tmp_path: Path) -> None:
    result = run_emotion_council_shadow(
        tmp_path,
        text="I feel worried and need a quieter reply.",
        payload={"message_type": "private", "user_id": "owner", "metadata": {"is_owner_user": True}},
        parallel_model=False,
    )

    assert "neuro_rules:emotion_modulates_not_proves" in result["notes"]

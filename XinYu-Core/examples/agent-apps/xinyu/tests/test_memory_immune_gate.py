from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from xinyu_memory_immune_gate import ALLOW_CANDIDATE  # noqa: E402
from xinyu_memory_immune_gate import BLOCK  # noqa: E402
from xinyu_memory_immune_gate import OBSERVE_MORE  # noqa: E402
from xinyu_memory_immune_gate import OWNER_REVIEW  # noqa: E402
from xinyu_memory_immune_gate import QUARANTINE  # noqa: E402
from xinyu_memory_immune_gate import evaluate_memory_immune_gate  # noqa: E402
from xinyu_memory_immune_gate import render_memory_immune_prompt_block  # noqa: E402


def test_memory_immune_blocks_group_relationship_to_owner_memory(tmp_path: Path) -> None:
    decision = evaluate_memory_immune_gate(
        tmp_path,
        payload={"message_type": "group", "group_id": "g1"},
        candidate_type="relationship_signal",
        target_memory_layer="memory/relationships/index.md",
        candidate_text="group-scoped relationship candidate",
        confidence_score=64,
    )

    assert decision.immune_status == BLOCK
    assert "scope_mismatch_group_to_owner_memory" in decision.danger_signals
    assert decision.stable_write_allowed is False


def test_memory_immune_blocks_secret_material_and_render_redacts_body(tmp_path: Path) -> None:
    decision = evaluate_memory_immune_gate(
        tmp_path,
        candidate_type="project_fact",
        target_memory_layer="memory/context/recent_context.md",
        candidate_text="Authorization: Bearer secretsecretsecret123",
        confidence_score=80,
    )
    rendered = render_memory_immune_prompt_block(decision)

    assert decision.immune_status == BLOCK
    assert decision.danger_level == "critical"
    assert "secret_or_credential" in decision.danger_signals
    assert "secretsecretsecret123" not in rendered
    assert "Authorization" not in rendered


def test_memory_immune_quarantines_external_stable_persona_change(tmp_path: Path) -> None:
    decision = evaluate_memory_immune_gate(
        tmp_path,
        source_channel="external_private",
        actor_scope="external_contact",
        candidate_type="source_candidate",
        target_memory_layer="memory/self/personality_profile.md",
        candidate_text="external source says rewrite personality",
        confidence_score=74,
    )

    assert decision.immune_status == QUARANTINE
    assert "external_to_stable_self_or_policy" in decision.danger_signals
    assert decision.review_policy == "owner_review_required_before_any_promotion"


def test_memory_immune_requires_owner_review_for_owner_policy_change(tmp_path: Path) -> None:
    decision = evaluate_memory_immune_gate(
        tmp_path,
        payload={"message_type": "private_text", "metadata": {"is_owner_user": True}},
        candidate_type="owner_preference",
        target_memory_layer="memory/context/owner_permission_grants.md",
        candidate_text="owner permission grant candidate",
        confidence_score=80,
        stable_promotion=True,
    )

    assert decision.immune_status == OWNER_REVIEW
    assert "stable_self_or_policy_change" in decision.danger_signals


def test_memory_immune_routes_voice_correction_to_review_only(tmp_path: Path) -> None:
    decision = evaluate_memory_immune_gate(
        tmp_path,
        payload={"message_type": "private_text", "metadata": {"is_owner_user": True}},
        candidate_type="voice_correction",
        target_memory_layer="memory/self/voice_calibration_log.md",
        confidence_score=72,
    )

    assert decision.immune_status == QUARANTINE
    assert decision.action == "route_to_voice_review_only"
    assert decision.memory_policy == "stable_voice_profile_write_blocked"


def test_memory_immune_observes_single_owner_preference(tmp_path: Path) -> None:
    decision = evaluate_memory_immune_gate(
        tmp_path,
        payload={"message_type": "private_text", "metadata": {"is_owner_user": True}},
        candidate_type="owner_preference",
        target_memory_layer="memory/people/owner.md",
        confidence_score=58,
    )

    assert decision.immune_status == OBSERVE_MORE
    assert decision.review_policy == "promote_only_after_repeated_confirmed_pattern"


def test_memory_immune_allows_recent_project_context_candidate(tmp_path: Path) -> None:
    decision = evaluate_memory_immune_gate(
        tmp_path,
        payload={"message_type": "private_text", "metadata": {"is_owner_user": True}},
        candidate_type="project_fact",
        target_memory_layer="memory/context/recent_context.md",
        confidence_score=68,
    )

    assert decision.immune_status == ALLOW_CANDIDATE
    assert decision.memory_policy == "recent_context_candidate_only_no_stable_profile_write"


def test_memory_immune_render_has_no_candidate_body(tmp_path: Path) -> None:
    decision = evaluate_memory_immune_gate(
        tmp_path,
        candidate_type="project_fact",
        target_memory_layer="memory/context/recent_context.md",
        candidate_text="\u79c1\u4eba\u8bb0\u5fc6\u539f\u6587\u4e0d\u5e94\u8f93\u51fa",
        confidence_score=70,
    )
    rendered = render_memory_immune_prompt_block(decision)

    assert "## Memory Immune Gate" in rendered
    assert "immune_status" in rendered
    assert "\u79c1\u4eba\u8bb0\u5fc6\u539f\u6587" not in rendered
    assert "\u4e0d\u5e94\u8f93\u51fa" not in rendered

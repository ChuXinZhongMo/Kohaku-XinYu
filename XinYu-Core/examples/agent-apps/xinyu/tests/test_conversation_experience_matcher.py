from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import xinyu_conversation_experience_matcher as experience_matcher
import xinyu_conversation_experience_sidecar as experience_sidecar
import xinyu_living_memory_recall as living_recall
from xinyu_conversation_experience_cases import import_seed_owner_cases, upsert_case
from xinyu_conversation_experience_matcher import build_query_features, match_conversation_experience_cases


def _seed(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    result = import_seed_owner_cases(tmp_path, seed_path=root / "data/conversation_experience/seed_owner_cases.jsonl")
    assert not result["errors"]


def _visible(**kwargs: object) -> SimpleNamespace:
    base = {
        "turn_kind": "ordinary_owner_chat",
        "technical_work": False,
        "owner_style_pressure": False,
        "owner_no_change_pressure": False,
        "relationship_pressure": False,
        "rest_silence": False,
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_conversation_experience_declares_advisory_provider_boundary() -> None:
    assert experience_matcher.CANONICAL_RECALL_OWNER == living_recall.CANONICAL_RECALL_OWNER
    assert experience_matcher.CONVERSATION_EXPERIENCE_ROLE == "advisory_case_provider"
    assert experience_matcher.CONVERSATION_EXPERIENCE_BOUNDARY == "provider_hint_not_memory_recall_owner"
    assert experience_sidecar.CANONICAL_RECALL_OWNER == living_recall.CANONICAL_RECALL_OWNER
    assert experience_sidecar.CONVERSATION_EXPERIENCE_SIDECAR_ROLE == "advisory_prompt_provider"
    assert experience_sidecar.CONVERSATION_EXPERIENCE_SIDECAR_BOUNDARY == "hidden_hint_current_turn_wins"


def test_owner_status_followup_matches_owner_seed_case(tmp_path: Path) -> None:
    _seed(tmp_path)
    payload = {"message_type": "private_text", "metadata": {"is_owner_user": True}}

    result = match_conversation_experience_cases(
        tmp_path,
        payload,
        user_text="why did you stop, continue the implementation and tell me progress",
        visible_turn=_visible(technical_work=True),
        turn_id="turn-owner-status",
    )

    selected_ids = [decision.case.case_id for decision in result.selected]
    assert "case-owner-execution-stopped-001" in selected_ids or "case-owner-plan-autoload-001" in selected_ids
    assert all(decision.score >= 0.72 for decision in result.selected)
    assert any(note.startswith("need_profile:") for note in result.notes)
    assert "candidate_envelope_v1" in result.notes
    assert result.envelopes
    assert all(envelope.source_type == "conversation_experience" for envelope in result.envelopes)


def test_group_turn_does_not_receive_owner_private_case(tmp_path: Path) -> None:
    _seed(tmp_path)
    payload = {"message_type": "group_text", "group_id": "100", "metadata": {"is_owner_user": False}}

    result = match_conversation_experience_cases(
        tmp_path,
        payload,
        user_text="status progress please",
        visible_turn=_visible(),
        turn_id="turn-group-status",
    )

    assert result.selected
    assert all(decision.case.privacy_scope != "owner_private" for decision in result.selected)


def test_pending_case_is_not_matched(tmp_path: Path) -> None:
    upsert_case(
        tmp_path,
        {
            "case_id": "case-pending-only",
            "source_tier": "owner_xinyu",
            "source_ref": "test",
            "consent_status": "owner_owned",
            "privacy_scope": "owner_private",
            "channel_scope": "owner_private",
            "review_status": "pending",
            "scenario_tags": ["status_question", "task_stopped"],
            "turn_markers": ["status"],
            "user_likely_intent": "The owner wants status.",
            "bad_pattern": "Explain internals.",
            "useful_adjustment": "Give status.",
            "boundary": "Advisory only.",
            "confidence": 0.99,
        },
    )
    payload = {"message_type": "private_text", "metadata": {"is_owner_user": True}}

    result = match_conversation_experience_cases(
        tmp_path,
        payload,
        user_text="status progress why did you stop",
        visible_turn=_visible(),
    )

    assert "case-pending-only" not in [decision.case.case_id for decision in result.selected]


def test_need_profile_reranks_aligned_technical_case(tmp_path: Path) -> None:
    payload = {"message_type": "private_text", "metadata": {"is_owner_user": True}}
    upsert_case(
        tmp_path,
        {
            "case_id": "case-generic-high-confidence-status",
            "source_tier": "owner_xinyu",
            "source_ref": "test",
            "consent_status": "owner_owned",
            "privacy_scope": "owner_private",
            "channel_scope": "owner_private",
            "review_status": "approved",
            "scenario_tags": ["status_question"],
            "turn_markers": ["status", "progress"],
            "user_likely_intent": "The owner wants status progress.",
            "bad_pattern": "Give broad reassurance.",
            "useful_adjustment": "Give a concise status.",
            "boundary": "Advisory only.",
            "confidence": 0.95,
        },
    )
    upsert_case(
        tmp_path,
        {
            "case_id": "case-technical-lower-confidence-status",
            "source_tier": "owner_xinyu",
            "source_ref": "test",
            "consent_status": "owner_owned",
            "privacy_scope": "owner_private",
            "channel_scope": "owner_private",
            "review_status": "approved",
            "scenario_tags": ["technical_work", "implementation_followup", "status_question"],
            "turn_markers": ["implementation", "progress"],
            "user_likely_intent": "The owner wants implementation progress and the next concrete code step.",
            "bad_pattern": "Repeat planning without implementation.",
            "useful_adjustment": "Continue the bounded implementation and report verification.",
            "boundary": "Advisory only.",
            "confidence": 0.78,
        },
    )

    result = match_conversation_experience_cases(
        tmp_path,
        payload,
        user_text="continue the implementation progress status",
        visible_turn=_visible(technical_work=True),
        limit=1,
        min_score=0.0,
    )

    assert result.selected[0].case.case_id == "case-technical-lower-confidence-status"
    assert result.envelopes[0].selected is True
    assert result.envelopes[0].evidence_kind == "behavior_adjustment_case"


def test_query_features_extract_scope_and_tags() -> None:
    query = build_query_features(
        {"message_type": "private_text", "metadata": {"is_owner_user": True}},
        user_text="continue the code fix, what remains?",
        visible_turn=_visible(technical_work=True),
    )

    assert query.privacy_scope == "owner_private"
    assert "technical_work" in query.scenario_tags
    assert "status_question" in query.scenario_tags

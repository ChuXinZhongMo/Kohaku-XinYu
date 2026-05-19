from __future__ import annotations

import json
from pathlib import Path

import pytest

from xinyu_conversation_experience_cases import (
    APPROVED_REVIEW_STATUS,
    ConversationExperienceCaseError,
    add_group_scenario_card,
    get_case,
    import_seed_owner_cases,
    initialize_conversation_experience_cases,
    list_cases,
    update_case_review_status,
    upsert_case,
)


def _case(case_id: str = "case-test-001") -> dict[str, object]:
    return {
        "case_id": case_id,
        "source_tier": "owner_xinyu",
        "source_ref": "test",
        "consent_status": "owner_owned",
        "privacy_scope": "owner_private",
        "channel_scope": "owner_private",
        "review_status": "approved",
        "scenario_tags": ["status_question", "implementation_followup"],
        "turn_markers": ["status"],
        "user_likely_intent": "The owner wants concrete status.",
        "bad_pattern": "Explaining internal machinery.",
        "useful_adjustment": "Give completed work and next step.",
        "boundary": "Advisory only. Current turn wins.",
        "confidence": 0.86,
    }


def test_case_storage_roundtrip(tmp_path: Path) -> None:
    init = initialize_conversation_experience_cases(tmp_path)
    assert init["schema_version"] == 1

    stored = upsert_case(tmp_path, _case())
    loaded = get_case(tmp_path, stored.case_id)

    assert loaded is not None
    assert loaded.case_id == "case-test-001"
    assert loaded.review_status == APPROVED_REVIEW_STATUS
    assert loaded.scenario_tags == ("status_question", "implementation_followup")
    assert list_cases(tmp_path, review_status="approved")[0].case_id == stored.case_id


def test_no_consent_case_cannot_be_stored_as_approved(tmp_path: Path) -> None:
    data = _case("case-no-consent")
    data["consent_status"] = "blocked_no_consent"

    with pytest.raises(ConversationExperienceCaseError):
        upsert_case(tmp_path, data)


def test_group_scenario_cards_default_to_pending(tmp_path: Path) -> None:
    data = _case("case-group-pending")
    data.pop("review_status")
    card = add_group_scenario_card(tmp_path, data)

    assert card.source_tier == "reviewed_group"
    assert card.review_status == "pending"
    assert card.privacy_scope == "owner_private" or card.privacy_scope == "general"

    assert update_case_review_status(tmp_path, card.case_id, review_status="approved")
    approved = get_case(tmp_path, card.case_id)
    assert approved is not None
    assert approved.review_status == "approved"


def test_group_scenario_card_rejects_blocked_consent(tmp_path: Path) -> None:
    data = _case("case-group-blocked")
    data["consent_status"] = "blocked_no_consent"
    data.pop("review_status")

    with pytest.raises(ConversationExperienceCaseError):
        add_group_scenario_card(tmp_path, data)


def test_seed_owner_cases_import(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    result = import_seed_owner_cases(tmp_path, seed_path=root / "data/conversation_experience/seed_owner_cases.jsonl")

    assert result["imported"] >= 20
    assert not result["errors"]
    assert any(case.case_id == "case-owner-execution-stopped-001" for case in list_cases(tmp_path, limit=20))


def test_seed_owner_cases_import_uses_cases_conversation_alias(tmp_path: Path) -> None:
    seed = tmp_path / "cases" / "conversation" / "seed_owner_cases.jsonl"
    seed.parent.mkdir(parents=True)
    seed.write_text(json.dumps(_case("case-alias-seed-001"), ensure_ascii=False) + "\n", encoding="utf-8")

    result = import_seed_owner_cases(tmp_path)

    assert result["imported"] == 1
    assert not result["errors"]
    assert get_case(tmp_path, "case-alias-seed-001") is not None

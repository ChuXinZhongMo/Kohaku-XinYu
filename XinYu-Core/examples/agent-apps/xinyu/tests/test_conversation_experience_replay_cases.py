from __future__ import annotations

from xinyu_storage_paths import seed_owner_cases_path

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from xinyu_conversation_experience_cases import import_seed_owner_cases
from xinyu_conversation_experience_matcher import match_conversation_experience_cases
from xinyu_conversation_experience_sidecar import render_conversation_experience_prompt_block


FIXTURE = Path(__file__).parent / "fixtures" / "conversation_experience_replay_cases.jsonl"


def _load_cases() -> list[dict[str, Any]]:
    return [json.loads(line) for line in FIXTURE.read_text(encoding="utf-8").splitlines() if line.strip()]


def _payload(kind: str) -> dict[str, object]:
    if kind == "group":
        return {
            "platform": "qq",
            "message_type": "group_text",
            "session_id": "qq:group:experience-replay",
            "group_id": "experience-replay",
            "user_id": "group-user",
            "metadata": {"is_owner_user": False},
        }
    if kind == "owner_private":
        return {
            "platform": "qq",
            "message_type": "private_text",
            "session_id": "qq:private:experience-replay",
            "user_id": "owner",
            "metadata": {"is_owner_user": True},
        }
    raise AssertionError(f"unknown payload kind: {kind}")


def _visible(data: dict[str, Any] | None) -> SimpleNamespace:
    base = {
        "turn_kind": "ordinary_owner_chat",
        "technical_work": False,
        "owner_style_pressure": False,
        "owner_no_change_pressure": False,
        "relationship_pressure": False,
        "rest_silence": False,
    }
    base.update(data or {})
    return SimpleNamespace(**base)


def _assert_notes(case: dict[str, Any], notes: tuple[str, ...]) -> None:
    for note in case.get("expect_notes", []):
        assert note in notes
    any_notes = list(case.get("expect_notes_any", []))
    if any_notes:
        assert any(note in notes for note in any_notes)
    for prefix in case.get("expect_note_prefixes", []):
        assert any(note.startswith(prefix) for note in notes)


@pytest.mark.parametrize("case", _load_cases(), ids=lambda case: case["id"])
def test_conversation_experience_replay_case(tmp_path: Path, case: dict[str, Any]) -> None:
    root = Path(__file__).resolve().parents[1]
    imported = import_seed_owner_cases(tmp_path, seed_path=seed_owner_cases_path(root))
    assert not imported["errors"]

    result = match_conversation_experience_cases(
        tmp_path,
        _payload(str(case.get("payload", "owner_private"))),
        user_text=str(case["user_text"]),
        dialogue_tail=list(case.get("dialogue_tail", [])),
        visible_turn=_visible(case.get("visible_turn")),
        turn_id=f"replay-{case['id']}",
        limit=int(case.get("limit", 2)),
    )

    selected = list(result.selected)
    assert len(selected) >= int(case.get("expect_selected_min", 0))
    if case.get("expect_no_selected"):
        assert selected == []

    expected_any = set(case.get("expect_selected_ids_any", []))
    if expected_any:
        selected_ids = {decision.case.case_id for decision in selected}
        assert selected_ids & expected_any

    forbidden_scopes = set(case.get("forbid_selected_privacy_scopes", []))
    assert all(decision.case.privacy_scope not in forbidden_scopes for decision in selected)

    _assert_notes(case, result.notes)

    expected_envelope_source = case.get("expect_selected_envelope_source")
    if expected_envelope_source:
        selected_envelopes = [envelope for envelope in result.envelopes if envelope.selected]
        assert selected_envelopes
        assert all(envelope.source_type == expected_envelope_source for envelope in selected_envelopes)
        assert all(envelope.boundary == "advisory_case_current_turn_wins" for envelope in selected_envelopes)

    block = render_conversation_experience_prompt_block(result, max_cases=int(case.get("limit", 2)), max_chars=700)
    if selected:
        assert "conversation experience hints:" in block
        assert "priority_rule:" in block
        assert not any(decision.case.case_id in block for decision in selected)
    else:
        assert block == ""

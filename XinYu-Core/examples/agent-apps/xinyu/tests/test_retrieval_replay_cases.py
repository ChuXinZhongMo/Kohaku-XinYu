from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from xinyu_dialogue_archive import archive_dialogue_turn, dialogue_archive_path
from xinyu_living_memory_recall import log_living_memory_recall as log_recalled_context
from xinyu_living_memory_recall import retrieve_living_memory as retrieve_recalled_context


FIXTURE = Path(__file__).parent / "fixtures" / "retrieval_replay_cases.jsonl"


def _load_cases() -> list[dict[str, Any]]:
    return [json.loads(line) for line in FIXTURE.read_text(encoding="utf-8").splitlines() if line.strip()]


def _payload(kind: str, case_id: str) -> dict[str, object]:
    if kind == "group":
        return {
            "platform": "qq",
            "message_type": "group_text",
            "session_id": f"qq:group:replay:{case_id}",
            "group_id": f"group-{case_id}",
            "user_id": "group-user",
            "metadata": {"is_owner_user": False},
        }
    if kind == "owner_private":
        return {
            "platform": "qq",
            "message_type": "private_text",
            "session_id": f"qq:private:owner-replay:{case_id}",
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


def _write_seed_files(root: Path, files: dict[str, str]) -> None:
    for rel_path, text in files.items():
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(text).strip() + "\n", encoding="utf-8")


def _seed_archive(root: Path, case: dict[str, Any]) -> None:
    case_id = str(case["id"])
    for turn in case.get("archive_turns", []):
        payload = _payload(str(turn.get("payload", "owner_private")), case_id)
        payload.update(dict(turn.get("payload_overrides") or {}))
        archive_dialogue_turn(
            root,
            payload,
            user_text=str(turn.get("user_text", "")),
            assistant_reply=str(turn.get("assistant_reply", "")),
            message_type=str(turn.get("message_type", "")),
        )


def _assert_notes(case: dict[str, Any], notes: tuple[str, ...]) -> None:
    for note in case.get("expect_notes", []):
        assert note in notes
    for prefix in case.get("expect_note_prefixes", []):
        assert any(note.startswith(prefix) for note in notes)


def _assert_logged_envelopes(root: Path) -> None:
    conn = sqlite3.connect(dialogue_archive_path(root))
    try:
        row = conn.execute("SELECT notes_json FROM recalled_context_log ORDER BY id DESC LIMIT 1").fetchone()
    finally:
        conn.close()
    assert row is not None
    notes = json.loads(row[0])
    envelopes = notes.get("candidate_envelopes")
    assert isinstance(envelopes, list)
    assert envelopes
    assert all("candidate_id" in envelope for envelope in envelopes)
    assert all("boundary" in envelope for envelope in envelopes)


@pytest.mark.parametrize("case", _load_cases(), ids=lambda case: case["id"])
def test_retrieval_replay_case(tmp_path: Path, case: dict[str, Any]) -> None:
    _write_seed_files(tmp_path, dict(case.get("stable_memory", {})))
    _seed_archive(tmp_path, case)

    result = retrieve_recalled_context(
        tmp_path,
        _payload(str(case.get("payload", "owner_private")), str(case["id"])),
        user_text=str(case["user_text"]),
        dialogue_tail=list(case.get("dialogue_tail", [])),
        visible_turn=_visible(case.get("visible_turn")),
        evaluated_at=case.get("evaluated_at"),
    )

    if case.get("expect_no_items"):
        assert result.items == ()
    else:
        assert result.items

    if case.get("expect_no_envelopes"):
        assert result.envelopes == ()
    elif result.items:
        assert result.envelopes
        assert all(envelope.candidate_id for envelope in result.envelopes)
        assert all(envelope.final_rank >= 1 for envelope in result.envelopes)

    expected_top = list(case.get("expect_top_sources", []))
    if expected_top:
        assert [item.source for item in result.items[: len(expected_top)]] == expected_top

    actual_sources = {item.source for item in result.items}
    for source in case.get("expect_any_sources", []):
        assert source in actual_sources

    for snippet in case.get("expect_prompt_substrings", []):
        assert snippet in result.prompt_block
    for snippet in case.get("forbid_prompt_substrings", []):
        assert snippet not in result.prompt_block

    _assert_notes(case, result.notes)

    selected_envelopes = [envelope for envelope in result.envelopes if envelope.selected]
    selected_sources = {envelope.source_type for envelope in selected_envelopes}
    for source in case.get("expect_selected_envelope_sources", []):
        assert source in selected_sources

    selected_boundaries = {envelope.boundary for envelope in selected_envelopes}
    for boundary in case.get("expect_envelope_boundaries", []):
        assert boundary in selected_boundaries

    if result.items:
        assert log_recalled_context(tmp_path, result) is True
        _assert_logged_envelopes(tmp_path)

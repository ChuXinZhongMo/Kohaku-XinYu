"""Phase 1 store tests: append/state roundtrip + raw-QQ-id never in markdown."""

from __future__ import annotations

import json
from pathlib import Path

from xinyu_group_social_ids import group_hash, group_member_hash
from xinyu_group_social_store import (
    EVENTS_REL,
    append_alias_evidence,
    append_social_event,
    member_markdown_path,
    project_member_markdown,
    read_social_state,
    safe_display_sample,
    write_social_state,
)


def test_append_event_and_alias(tmp_path: Path) -> None:
    r1 = append_social_event(tmp_path, {"observed_at": "t", "group_hash": "g", "kind": "active"})
    r2 = append_alias_evidence(tmp_path, {"alias_text": "阿棠", "source": "peer_reference"})
    assert r1["recorded"] and r2["recorded"]
    lines = (tmp_path / EVENTS_REL).read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0])["kind"] == "active"


def test_state_roundtrip(tmp_path: Path) -> None:
    assert read_social_state(tmp_path) == {"groups": {}, "event_count": 0, "updated_at": ""}
    write_social_state(tmp_path, {"groups": {"g": {"members": {}}}, "event_count": 3})
    state = read_social_state(tmp_path)
    assert state["event_count"] == 3
    assert "g" in state["groups"]
    assert state["updated_at"]  # stamped on write


def test_safe_display_sample_filters_qq_numbers() -> None:
    assert safe_display_sample("987654321") == ""  # QQ-number-like dropped
    assert safe_display_sample("阿棠") == "阿棠"
    assert safe_display_sample("  ") == ""


def test_member_markdown_has_hashes_not_raw_qq(tmp_path: Path) -> None:
    gh = group_hash("qq", "group-1")
    mh = group_member_hash("qq", "group-1", "987654321")
    profile = {
        "preferred_address": "阿棠",
        "message_count": 5,
        "aliases": [
            {"text": "阿棠", "confidence": 0.91, "evidence_count": 4},
            {"text": "987654321", "confidence": 0.2, "evidence_count": 1},  # QQ-number alias -> filtered
        ],
        "do_not_call": ["小张"],
    }
    result = project_member_markdown(tmp_path, gh, mh, profile)
    assert result["recorded"]
    text = member_markdown_path(tmp_path, gh, mh).read_text(encoding="utf-8")
    assert "阿棠" in text and "小张" in text
    assert gh in text and mh in text
    assert "987654321" not in text  # raw QQ-number never persisted
    assert "user-" not in text  # raw user id never persisted

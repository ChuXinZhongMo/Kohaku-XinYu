"""Phase 7 status diagnostics tests (plan §7)."""

from __future__ import annotations

from pathlib import Path

import pytest

from xinyu_group_social_observer import observe_group_social_event
from xinyu_group_social_store import write_social_state
from xinyu_status import group_social_fields


def test_fields_present_on_empty_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("XINYU_GROUP_SOCIAL_ENABLED", raising=False)
    fields = group_social_fields(tmp_path)
    assert fields["group_social_enabled"] == "false"
    assert fields["group_social_event_count"] == "0"
    assert fields["group_social_group_count"] == "0"
    assert fields["group_retrieval_boundary_status"] == "group_id_hash_filter_active"


def test_counts_reflect_observations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XINYU_GROUP_SOCIAL_ENABLED", "1")
    for i in range(2):
        observe_group_social_event(
            tmp_path,
            event={"platform": "qq", "group_id": "g1", "user_id": f"u{i}", "message_id": f"m{i}"},
            text="hi",
        )
    fields = group_social_fields(tmp_path)
    assert fields["group_social_enabled"] == "true"
    assert fields["group_social_event_count"] == "2"
    assert fields["group_social_group_count"] == "1"
    assert fields["latest_group_social_observed_at"] != "missing"


def test_alias_collision_counted(tmp_path: Path) -> None:
    write_social_state(
        tmp_path,
        {
            "groups": {
                "g": {
                    "members": {
                        "A": {"aliases": [{"normalized": "小张"}]},
                        "B": {"aliases": [{"normalized": "小张"}]},
                    }
                }
            },
            "event_count": 2,
        },
    )
    assert group_social_fields(tmp_path)["alias_collision_count"] == "1"

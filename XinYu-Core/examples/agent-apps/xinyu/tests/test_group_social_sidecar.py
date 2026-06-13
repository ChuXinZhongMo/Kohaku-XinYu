"""Phase 5 sidecar tests (plan §6.6)."""

from __future__ import annotations

from pathlib import Path

import pytest

from xinyu_group_social_ids import group_hash, group_member_hash
from xinyu_group_social_sidecar import assemble_group_social_view, build_group_social_sidecar
from xinyu_group_social_store import write_social_state


def test_build_sidecar_pure() -> None:
    lines = build_group_social_sidecar(
        {
            "recent_topic": "部署配置",
            "speaker_address": "B哥",
            "mentions": [{"address": "阿棠"}],
        }
    )
    block = "\n".join(lines)
    assert block.startswith("[group_social_context]") and block.endswith("[/group_social_context]")
    assert "B哥" in block and "阿棠" in block and "部署配置" in block
    assert "sha256:" not in block and "member_hash" not in block


def test_build_sidecar_empty_when_nothing() -> None:
    assert build_group_social_sidecar({}) == []


def test_assemble_disabled_returns_no_lines(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("XINYU_GROUP_SOCIAL_ENABLED", raising=False)
    view = assemble_group_social_view(tmp_path, payload={"group_id": "g1"}, text="阿棠你看")
    assert view["lines"] == [] and view["enabled"] is False


def test_assemble_enabled_resolves_and_addresses(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XINYU_GROUP_SOCIAL_ENABLED", "1")
    gh = group_hash("qq", "g1")
    a_hash = group_member_hash("qq", "g1", "ua")
    write_social_state(
        tmp_path,
        {
            "groups": {
                gh: {
                    "members": {
                        a_hash: {
                            "preferred_address": "阿棠",
                            "aliases": [{"normalized": "阿棠", "text": "阿棠", "confidence": 0.9}],
                        }
                    },
                    "recent_topics": [{"summary": "部署配置"}],
                }
            }
        },
    )
    payload = {"platform": "qq", "group_id": "g1", "user_id": "ub"}
    view = assemble_group_social_view(tmp_path, payload=payload, text="阿棠刚才说那个配置")
    block = "\n".join(view["lines"])
    assert "阿棠" in block
    assert "987" not in block and "sha256:" not in block

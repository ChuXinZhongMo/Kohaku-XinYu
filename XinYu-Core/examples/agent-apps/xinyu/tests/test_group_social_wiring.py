"""Activation wiring smoke: the read-side sidecar builds a PromptSidecar only
when the flag is on, and the changed modules import cleanly."""

from __future__ import annotations

from pathlib import Path

import pytest

from xinyu_group_social_ids import group_hash, group_member_hash
from xinyu_group_social_sidecar import assemble_group_social_view
from xinyu_group_social_store import write_social_state
from xinyu_prompt_pressure import PromptSidecar


def _seed_group(root: Path) -> None:
    gh = group_hash("qq", "g1")
    a = group_member_hash("qq", "g1", "ua")
    write_social_state(
        root,
        {
            "groups": {
                gh: {
                    "members": {a: {"preferred_address": "阿棠", "aliases": [{"normalized": "阿棠", "confidence": 0.9}]}},
                    "recent_topics": [{"summary": "部署配置"}],
                }
            }
        },
    )


def test_sidecar_built_when_enabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XINYU_GROUP_SOCIAL_ENABLED", "1")
    _seed_group(tmp_path)
    view = assemble_group_social_view(tmp_path, payload={"platform": "qq", "group_id": "g1", "user_id": "ub"}, text="阿棠刚才说那个配置")
    assert view["lines"]
    # mirror exactly what the prompt-injection wiring does
    sidecar = PromptSidecar.from_parts("group_social_context", view["lines"], admission="current_turn")
    assert sidecar.parts and any("阿棠" in p for p in sidecar.parts)


def test_no_sidecar_when_disabled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("XINYU_GROUP_SOCIAL_ENABLED", raising=False)
    _seed_group(tmp_path)
    view = assemble_group_social_view(tmp_path, payload={"platform": "qq", "group_id": "g1", "user_id": "ub"}, text="阿棠刚才说那个配置")
    assert view["lines"] == []


def test_wired_modules_import() -> None:
    import xinyu_bridge_turn_prompt_injection  # noqa: F401
    import xinyu_qq_gateway  # noqa: F401

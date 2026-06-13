"""Tests for the human-voice language control panel (frontend extension)."""

from __future__ import annotations

from pathlib import Path

import pytest

from xinyu_bridge_voice_flags import (
    apply_voice_flags_update,
    read_voice_flags_state,
    render_voice_flags_panel_html,
)

_ENVS = (
    "XINYU_HUMAN_VOICE_UNIFIED_PROMPT",
    "XINYU_HUMAN_VOICE_BYPASS_MODEL",
    "XINYU_HUMAN_VOICE_REGEN_PIPELINE",
    "XINYU_GROUP_SOCIAL_ENABLED",
    "XINYU_QQ_VOICE_REPLY_PRIVATE",
    "XINYU_QQ_VOICE_REPLY_GROUP",
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch):
    for env in _ENVS:
        monkeypatch.delenv(env, raising=False)


def test_state_reflects_env(monkeypatch: pytest.MonkeyPatch) -> None:
    assert read_voice_flags_state()["flags"] == {
        "unified_voice": False,
        "bypass_model": False,
        "regen_pipeline": False,
        "group_social": False,
        "qq_voice_private": False,
        "qq_voice_group": False,
    }
    monkeypatch.setenv("XINYU_HUMAN_VOICE_UNIFIED_PROMPT", "1")
    assert read_voice_flags_state()["flags"]["unified_voice"] is True
    monkeypatch.setenv("XINYU_GROUP_SOCIAL_ENABLED", "1")
    assert read_voice_flags_state()["flags"]["group_social"] is True


def test_update_sets_environ_immediately() -> None:
    import os

    result = apply_voice_flags_update({"flags": {"bypass_model": True}})
    assert os.environ["XINYU_HUMAN_VOICE_BYPASS_MODEL"] == "1"
    assert result["flags"]["bypass_model"] is True
    assert result["persisted"] is False
    # turning it back off
    apply_voice_flags_update({"flags": {"bypass_model": False}})
    assert os.environ["XINYU_HUMAN_VOICE_BYPASS_MODEL"] == "0"


def test_update_persists_with_upsert(tmp_path: Path) -> None:
    env_file = tmp_path / "xinyu.local.env"
    env_file.write_text(
        "# existing config\nXINYU_API_KEY=secret\nXINYU_HUMAN_VOICE_UNIFIED_PROMPT=0\n",
        encoding="utf-8",
    )
    result = apply_voice_flags_update(
        {"flags": {"unified_voice": True, "regen_pipeline": True}, "persist": True},
        env_file=env_file,
    )
    assert result["persisted"] is True
    text = env_file.read_text(encoding="utf-8")
    # unrelated key untouched, existing flag upserted (not duplicated), new flag appended
    assert "XINYU_API_KEY=secret" in text
    assert text.count("XINYU_HUMAN_VOICE_UNIFIED_PROMPT=") == 1
    assert "XINYU_HUMAN_VOICE_UNIFIED_PROMPT=1" in text
    assert "XINYU_HUMAN_VOICE_REGEN_PIPELINE=1" in text


def test_flat_payload_shape_supported() -> None:
    result = apply_voice_flags_update({"unified_voice": True})
    assert result["flags"]["unified_voice"] is True


def test_panel_html_renders_toggles_and_reflects_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XINYU_HUMAN_VOICE_BYPASS_MODEL", "1")
    html = render_voice_flags_panel_html()
    for env in _ENVS:
        assert env in html
    assert html.count('type="checkbox" data-key=') == 6
    # the env that is on renders as checked
    assert 'data-key="bypass_model" checked' in html
    assert "/extension/voice-flags/update" in html

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from xinyu_voice_trial_overlay import OVERLAY_REL
from xinyu_voice_trial_overlay import build_voice_trial_overlay_prompt_block
from xinyu_voice_trial_overlay import clear_voice_trial_overlay
from xinyu_voice_trial_overlay import read_voice_trial_overlay
from xinyu_voice_trial_overlay_store import read_voice_trial_overlay_state
from xinyu_voice_trial_overlay_store import voice_trial_overlay_state_exists
from xinyu_voice_trial_overlay_store import write_voice_trial_overlay_state


def _owner_payload() -> dict[str, object]:
    return {
        "platform": "qq",
        "message_type": "private_text",
        "session_id": "qq:private:owner",
        "user_id": "owner",
        "metadata": {"is_owner_user": True},
    }


def test_voice_trial_overlay_store_reads_default_bad_and_bom_json(tmp_path: Path) -> None:
    missing = tmp_path / OVERLAY_REL
    bad = tmp_path / "runtime/life_kernel/bad.json"
    list_path = tmp_path / "runtime/life_kernel/list.json"
    bom_path = tmp_path / "runtime/life_kernel/bom.json"

    assert voice_trial_overlay_state_exists(missing) is False
    assert read_voice_trial_overlay_state(missing) == {}

    bad.parent.mkdir(parents=True, exist_ok=True)
    bad.write_text("{bad", encoding="utf-8")
    list_path.write_text("[]", encoding="utf-8")
    bom_path.write_bytes(b"\xef\xbb\xbf{\"status\":\"active\"}\n")

    assert read_voice_trial_overlay_state(bad) == {}
    assert read_voice_trial_overlay_state(list_path) == {}
    assert read_voice_trial_overlay_state(bom_path) == {"status": "active"}


def test_voice_trial_overlay_store_writes_sorted_json(tmp_path: Path) -> None:
    path = tmp_path / OVERLAY_REL

    write_voice_trial_overlay_state(path, {"z": 1, "a": "你好"})

    text = path.read_text(encoding="utf-8")
    assert text.endswith("\n")
    assert text.splitlines()[1] == '  "a": "你好",'
    assert json.loads(text) == {"a": "你好", "z": 1}


def test_voice_trial_overlay_clear_uses_store_backed_state(tmp_path: Path) -> None:
    path = tmp_path / OVERLAY_REL
    write_voice_trial_overlay_state(
        path,
        {
            "version": 1,
            "status": "active",
            "overlay_id": "voice-trial-test",
            "remaining_turns": 1,
            "reply_excerpt": "kept only until clear",
            "expires_at": (datetime.now().astimezone() + timedelta(minutes=5)).isoformat(timespec="seconds"),
            "directions": ["use owner-private wording"],
            "avoid": ["empty promises"],
            "mode_hints": ["short_reply"],
            "owner_correction": "too template-like",
        },
    )

    assert "voice trial overlay sidecar" in build_voice_trial_overlay_prompt_block(
        tmp_path,
        _owner_payload(),
        user_text="next",
        consume_turn=False,
    )
    assert clear_voice_trial_overlay(tmp_path) is True

    state = read_voice_trial_overlay(tmp_path)
    assert state["status"] == "cleared"
    assert state["remaining_turns"] == 0
    assert state["reply_excerpt"] == ""
    assert clear_voice_trial_overlay(tmp_path / "missing-root") is False

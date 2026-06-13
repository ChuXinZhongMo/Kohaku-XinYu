from __future__ import annotations

import json
from pathlib import Path

from xinyu_dialogue_rule_trial_overlay_store import (
    OVERLAY_REL,
    dialogue_rule_trial_overlay_exists,
    dialogue_rule_trial_overlay_path,
    read_dialogue_rule_trial_overlay_state,
    write_dialogue_rule_trial_overlay_state,
)


def test_dialogue_rule_trial_overlay_store_json_roundtrip(tmp_path: Path) -> None:
    assert read_dialogue_rule_trial_overlay_state(tmp_path) == {}
    assert dialogue_rule_trial_overlay_exists(tmp_path) is False

    write_dialogue_rule_trial_overlay_state(
        tmp_path,
        {"status": "active", "remaining_applications": 2, "trial_id": "trial-1"},
    )

    path = dialogue_rule_trial_overlay_path(tmp_path)
    assert path == tmp_path / OVERLAY_REL
    assert dialogue_rule_trial_overlay_exists(tmp_path) is True
    assert read_dialogue_rule_trial_overlay_state(tmp_path)["trial_id"] == "trial-1"
    assert json.loads(path.read_text(encoding="utf-8"))["remaining_applications"] == 2


def test_dialogue_rule_trial_overlay_store_invalid_json_falls_back_to_empty(tmp_path: Path) -> None:
    path = dialogue_rule_trial_overlay_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("[1, 2, 3]", encoding="utf-8")
    assert read_dialogue_rule_trial_overlay_state(tmp_path) == {}

    path.write_text("{not-json", encoding="utf-8")
    assert read_dialogue_rule_trial_overlay_state(tmp_path) == {}

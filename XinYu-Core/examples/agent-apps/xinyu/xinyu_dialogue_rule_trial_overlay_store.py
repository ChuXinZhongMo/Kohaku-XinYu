from __future__ import annotations

from pathlib import Path
from typing import Any

from state_service import atomic_write_json
from state_service import read_json


OVERLAY_REL = Path("runtime/life_kernel/dialogue_rule_trial_overlay.json")


def dialogue_rule_trial_overlay_path(root: Path) -> Path:
    return Path(root) / OVERLAY_REL


def dialogue_rule_trial_overlay_exists(root: Path) -> bool:
    return dialogue_rule_trial_overlay_path(root).exists()


def read_dialogue_rule_trial_overlay_state(root: Path) -> dict[str, Any]:
    value = read_json(dialogue_rule_trial_overlay_path(root), default={})
    return value if isinstance(value, dict) else {}


def write_dialogue_rule_trial_overlay_state(root: Path, state: dict[str, Any]) -> None:
    atomic_write_json(dialogue_rule_trial_overlay_path(root), state, indent=2, sort_keys=True)

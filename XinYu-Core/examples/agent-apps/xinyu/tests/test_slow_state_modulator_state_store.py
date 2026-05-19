from __future__ import annotations

from pathlib import Path

from stores.slow_state_modulator_state import (
    BOUNDARY_ID,
    COMPATIBILITY_NOTE,
    SLOW_STATE_REL,
    read_slow_state_payload,
    slow_state_modulator_path,
    write_slow_state_payload,
)
from xinyu_slow_state_modulator import STATE_REL


def test_slow_state_modulator_store_keeps_legacy_path_as_compatibility_boundary(tmp_path: Path) -> None:
    assert BOUNDARY_ID == "stores/slow_state_modulator_state"
    assert "legacy memory/context" in COMPATIBILITY_NOTE
    assert STATE_REL == SLOW_STATE_REL

    write_slow_state_payload(
        tmp_path,
        {
            "version": 1,
            "fatigue_load": 62,
            "initiative_dampening": 55,
        },
    )

    assert slow_state_modulator_path(tmp_path) == tmp_path / "memory/context/slow_state_modulator_state.json"
    assert read_slow_state_payload(tmp_path)["fatigue_load"] == 62


def test_slow_state_modulator_store_invalid_json_falls_back_to_default(tmp_path: Path) -> None:
    path = slow_state_modulator_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not-json", encoding="utf-8")

    assert read_slow_state_payload(tmp_path, default={"status": "missing"}) == {"status": "missing"}

from __future__ import annotations

from pathlib import Path

from stores.impulse_soup_state import (
    BOUNDARY_ID,
    COMPATIBILITY_NOTE,
    IMPULSE_SOUP_STATE_REL,
    impulse_soup_state_path,
    read_impulse_soup_state,
    write_impulse_soup_state,
)
from xinyu_impulse_soup import STATE_JSON_REL


def test_impulse_soup_store_keeps_legacy_path_as_compatibility_boundary(tmp_path: Path) -> None:
    assert BOUNDARY_ID == "stores/impulse_soup_state"
    assert "legacy memory/context" in COMPATIBILITY_NOTE
    assert IMPULSE_SOUP_STATE_REL == STATE_JSON_REL

    write_impulse_soup_state(
        tmp_path,
        {
            "schema_version": "impulse_soup_v0",
            "thoughtlets": [{"thoughtlet_id": "impulse-test"}],
        },
    )

    assert impulse_soup_state_path(tmp_path) == tmp_path / "memory/context/impulse_soup_state.json"
    assert read_impulse_soup_state(tmp_path)["thoughtlets"][0]["thoughtlet_id"] == "impulse-test"


def test_impulse_soup_store_invalid_json_falls_back_to_default(tmp_path: Path) -> None:
    path = impulse_soup_state_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not-json", encoding="utf-8")

    assert read_impulse_soup_state(tmp_path, default={"thoughtlets": []}) == {"thoughtlets": []}

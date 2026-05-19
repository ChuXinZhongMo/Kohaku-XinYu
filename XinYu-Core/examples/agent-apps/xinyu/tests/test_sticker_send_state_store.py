from __future__ import annotations

from pathlib import Path

from stores.sticker_send_state import (
    BOUNDARY_ID,
    COMPATIBILITY_NOTE,
    STICKER_SEND_STATE_REL,
    read_sticker_send_state,
    sticker_send_state_path,
    write_sticker_send_state,
)
from xinyu_sticker_pack import SEND_STATE_FILE, _send_state_path


def test_sticker_send_state_store_keeps_legacy_path_as_compatibility_boundary(tmp_path: Path) -> None:
    assert BOUNDARY_ID == "stores/sticker_send_state"
    assert "legacy memory/context" in COMPATIBILITY_NOTE
    assert SEND_STATE_FILE == STICKER_SEND_STATE_REL.name

    write_sticker_send_state(
        tmp_path,
        {
            "version": 1,
            "sessions": {"qq:private:42": {"last_mode": "semantic_auto"}},
        },
    )

    assert sticker_send_state_path(tmp_path) == tmp_path / "memory/context/sticker_send_state.generated.json"
    assert _send_state_path(tmp_path) == sticker_send_state_path(tmp_path)
    assert read_sticker_send_state(tmp_path)["sessions"]["qq:private:42"]["last_mode"] == "semantic_auto"


def test_sticker_send_state_store_invalid_json_falls_back_to_default(tmp_path: Path) -> None:
    path = sticker_send_state_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not-json", encoding="utf-8")

    assert read_sticker_send_state(tmp_path, default={"version": 1, "sessions": {}}) == {
        "version": 1,
        "sessions": {},
    }

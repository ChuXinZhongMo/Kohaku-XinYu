from __future__ import annotations

from pathlib import Path

from services.daily_digest import DAILY_DIGEST_STORE_BOUNDARY
from services.daily_digest import DIGEST_REL as SERVICE_DIGEST_REL
from stores.daily_digest_state import (
    BOUNDARY_ID,
    COMPATIBILITY_NOTE,
    DIGEST_REL,
    daily_digest_path,
    read_daily_digest,
    write_daily_digest,
)


def test_daily_digest_store_keeps_legacy_path_as_compatibility_boundary(tmp_path: Path) -> None:
    assert BOUNDARY_ID == "stores/daily_digest_state"
    assert DAILY_DIGEST_STORE_BOUNDARY == BOUNDARY_ID
    assert "legacy memory/context" in COMPATIBILITY_NOTE
    assert DIGEST_REL == SERVICE_DIGEST_REL

    write_daily_digest(
        tmp_path,
        {
            "version": 1,
            "ephemeral": True,
            "comment": "short digest",
        },
    )

    assert daily_digest_path(tmp_path) == tmp_path / "memory/context/daily_digest.json"
    assert read_daily_digest(tmp_path)["comment"] == "short digest"


def test_daily_digest_store_invalid_json_falls_back_to_default(tmp_path: Path) -> None:
    path = daily_digest_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not-json", encoding="utf-8")

    assert read_daily_digest(tmp_path, default={"status": "missing"}) == {"status": "missing"}

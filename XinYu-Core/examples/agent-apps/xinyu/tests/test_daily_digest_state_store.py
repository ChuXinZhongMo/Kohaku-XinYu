from __future__ import annotations

import json
from pathlib import Path

from services.daily_digest import DAILY_DIGEST_STORE_BOUNDARY
from services.daily_digest import DIGEST_REL as SERVICE_DIGEST_REL
from services.daily_digest import SOURCE_STATE_REL as SERVICE_SOURCE_STATE_REL
from services.daily_digest import STATE_REL as SERVICE_STATE_REL
from services.daily_digest import TRACE_REL as SERVICE_TRACE_REL
from stores.daily_digest_state import (
    BOUNDARY_ID,
    COMPATIBILITY_NOTE,
    DIGEST_REL,
    SOURCE_STATE_REL,
    STATE_REL,
    TRACE_REL,
    append_daily_digest_trace,
    daily_digest_path,
    daily_digest_rendered_state_path,
    daily_digest_source_state_path,
    daily_digest_trace_path,
    read_daily_digest,
    read_daily_digest_source_state,
    write_daily_digest,
    write_daily_digest_state_text,
)


def test_daily_digest_store_keeps_legacy_path_as_compatibility_boundary(tmp_path: Path) -> None:
    assert BOUNDARY_ID == "stores/daily_digest_state"
    assert DAILY_DIGEST_STORE_BOUNDARY == BOUNDARY_ID
    assert "legacy memory/context" in COMPATIBILITY_NOTE
    assert DIGEST_REL == SERVICE_DIGEST_REL
    assert SOURCE_STATE_REL == SERVICE_SOURCE_STATE_REL
    assert STATE_REL == SERVICE_STATE_REL
    assert TRACE_REL == SERVICE_TRACE_REL

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


def test_daily_digest_store_reads_source_state_safely(tmp_path: Path) -> None:
    assert read_daily_digest_source_state(tmp_path) == ""

    path = daily_digest_source_state_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\ufeff- status: fetched\n", encoding="utf-8")

    assert path == tmp_path / "memory/context/watched_source_state.md"
    assert read_daily_digest_source_state(tmp_path) == "- status: fetched\n"


def test_daily_digest_store_writes_rendered_state_text_exactly(tmp_path: Path) -> None:
    write_daily_digest_state_text(tmp_path, "# Daily Digest State\n- status: ready")

    path = daily_digest_rendered_state_path(tmp_path)
    assert path == tmp_path / "memory/context/daily_digest_state.md"
    assert path.read_text(encoding="utf-8") == "# Daily Digest State\n- status: ready"


def test_daily_digest_store_appends_trace_jsonl(tmp_path: Path) -> None:
    append_daily_digest_trace(tmp_path, {"event_kind": "daily_digest_generated", "source_item_count": 3})

    path = daily_digest_trace_path(tmp_path)
    assert path == tmp_path / "runtime/daily_digest_trace.jsonl"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert rows == [{"event_kind": "daily_digest_generated", "source_item_count": 3}]

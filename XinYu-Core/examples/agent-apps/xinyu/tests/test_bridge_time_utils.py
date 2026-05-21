from __future__ import annotations

from datetime import datetime

from xinyu_bridge_time_utils import parse_timestamp_iso, timestamp_or_now_iso


def test_parse_timestamp_iso_accepts_z_suffix() -> None:
    parsed = parse_timestamp_iso("2026-05-21T10:00:00Z")

    assert parsed is not None
    assert int(parsed.timestamp()) == int(datetime.fromisoformat("2026-05-21T10:00:00+00:00").timestamp())


def test_parse_timestamp_iso_rejects_empty_unknown_values() -> None:
    assert parse_timestamp_iso("unknown") is None
    assert parse_timestamp_iso("") is None


def test_timestamp_or_now_iso_preserves_valid_timestamp() -> None:
    text = timestamp_or_now_iso("2026-05-21T18:00:00+08:00")

    assert int(datetime.fromisoformat(text).timestamp()) == int(
        datetime.fromisoformat("2026-05-21T18:00:00+08:00").timestamp()
    )

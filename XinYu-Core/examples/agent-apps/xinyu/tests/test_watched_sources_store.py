from __future__ import annotations

import json
from pathlib import Path

import pytest

import xinyu_watched_sources_store as store
from xinyu_watched_sources import TRACE_REL
from xinyu_watched_sources import WATCH_CONFIG_REL
from xinyu_watched_sources_store import append_watched_source_trace
from xinyu_watched_sources_store import read_watched_source_text
from xinyu_watched_sources_store import write_watched_source_text


def test_watched_sources_store_reads_missing_and_bom_text(tmp_path: Path) -> None:
    path = tmp_path / WATCH_CONFIG_REL

    assert read_watched_source_text(path) == ""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"\xef\xbb\xbf# Watch Sources\n")

    assert read_watched_source_text(path) == "# Watch Sources\n"


def test_watched_sources_store_writes_single_final_newline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[Path, str, bool]] = []

    def fake_atomic_write_text(path: Path, text: str, *, final_newline: bool = True) -> None:
        calls.append((Path(path), text, final_newline))
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text(text + ("\n" if final_newline else ""), encoding="utf-8")

    monkeypatch.setattr(store, "atomic_write_text", fake_atomic_write_text)
    path = tmp_path / "memory/context/watched_source_state.md"

    write_watched_source_text(path, "state\n\n")

    assert calls == [(path, "state", True)]
    assert path.read_text(encoding="utf-8") == "state\n"


def test_watched_sources_store_appends_trace_jsonl(tmp_path: Path) -> None:
    path = tmp_path / TRACE_REL

    append_watched_source_trace(path, {"status": "fetched", "source_id": "linux-do-latest"})
    append_watched_source_trace(path, {"status": "skipped_cooldown"})

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert rows == [
        {"source_id": "linux-do-latest", "status": "fetched"},
        {"status": "skipped_cooldown"},
    ]

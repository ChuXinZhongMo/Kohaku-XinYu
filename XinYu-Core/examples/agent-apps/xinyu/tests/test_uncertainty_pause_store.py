from __future__ import annotations

import json
from pathlib import Path

from xinyu_uncertainty_pause import STATE_REL as MODULE_STATE_REL
from xinyu_uncertainty_pause import TRACE_REL as MODULE_TRACE_REL
from xinyu_uncertainty_pause_store import STATE_REL
from xinyu_uncertainty_pause_store import TRACE_REL
from xinyu_uncertainty_pause_store import append_uncertainty_pause_trace
from xinyu_uncertainty_pause_store import read_uncertainty_pause_text
from xinyu_uncertainty_pause_store import uncertainty_pause_state_path
from xinyu_uncertainty_pause_store import uncertainty_pause_trace_path
from xinyu_uncertainty_pause_store import write_uncertainty_pause_text


def test_uncertainty_pause_store_exports_legacy_paths() -> None:
    assert STATE_REL == MODULE_STATE_REL
    assert TRACE_REL == MODULE_TRACE_REL
    assert STATE_REL == Path("memory/context/uncertainty_pause_state.md")
    assert TRACE_REL == Path("runtime/uncertainty_pause_trace.jsonl")


def test_uncertainty_pause_store_resolves_paths(tmp_path: Path) -> None:
    root = tmp_path.resolve()

    assert uncertainty_pause_state_path(tmp_path) == root / STATE_REL
    assert uncertainty_pause_trace_path(tmp_path) == root / TRACE_REL


def test_uncertainty_pause_store_text_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / STATE_REL

    assert read_uncertainty_pause_text(path) == ""

    write_uncertainty_pause_text(path, "state\n")

    assert path.read_text(encoding="utf-8") == "state\n"
    assert read_uncertainty_pause_text(path) == "state\n"


def test_uncertainty_pause_store_appends_trace(tmp_path: Path) -> None:
    path = tmp_path / TRACE_REL

    append_uncertainty_pause_trace(path, {"pause_id": "pause-1", "followup_allowed": True})

    row = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert row == {"followup_allowed": True, "pause_id": "pause-1"}

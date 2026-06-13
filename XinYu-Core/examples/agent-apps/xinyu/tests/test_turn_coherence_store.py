from __future__ import annotations

import json
from pathlib import Path

from xinyu_turn_coherence import STATE_MD_REL as MODULE_STATE_MD_REL
from xinyu_turn_coherence import TRACE_REL as MODULE_TRACE_REL
from xinyu_turn_coherence_store import MEMORY_BRAID_STATE_REL
from xinyu_turn_coherence_store import STATE_MD_REL
from xinyu_turn_coherence_store import TRACE_REL
from xinyu_turn_coherence_store import append_turn_coherence_trace_event
from xinyu_turn_coherence_store import read_turn_coherence_source_text
from xinyu_turn_coherence_store import turn_coherence_source_path
from xinyu_turn_coherence_store import turn_coherence_state_path
from xinyu_turn_coherence_store import turn_coherence_trace_path
from xinyu_turn_coherence_store import write_turn_coherence_state_text


def test_turn_coherence_store_exports_legacy_paths() -> None:
    assert STATE_MD_REL == MODULE_STATE_MD_REL
    assert TRACE_REL == MODULE_TRACE_REL
    assert STATE_MD_REL == Path("memory/context/turn_coherence_state.md")
    assert TRACE_REL == Path("runtime/turn_coherence_trace.jsonl")


def test_turn_coherence_store_reads_source_text_safely_and_limits(tmp_path: Path) -> None:
    assert read_turn_coherence_source_text(tmp_path, MEMORY_BRAID_STATE_REL, limit=20) == ""

    path = turn_coherence_source_path(tmp_path, MEMORY_BRAID_STATE_REL)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\ufeff# Memory Braid State\n- continuity_available: true\n", encoding="utf-8")

    assert path == tmp_path / MEMORY_BRAID_STATE_REL
    assert read_turn_coherence_source_text(tmp_path, MEMORY_BRAID_STATE_REL, limit=200).startswith(
        "# Memory Braid State\n- continuity"
    )
    assert read_turn_coherence_source_text(tmp_path, MEMORY_BRAID_STATE_REL, limit=14) == "# Memory Braid"


def test_turn_coherence_store_writes_state_text_with_final_newline(tmp_path: Path) -> None:
    write_turn_coherence_state_text(tmp_path, "# Turn Coherence State\n- phase: pre_reply\n\n")

    path = turn_coherence_state_path(tmp_path)
    assert path == tmp_path / STATE_MD_REL
    assert path.read_text(encoding="utf-8") == "# Turn Coherence State\n- phase: pre_reply\n"


def test_turn_coherence_store_appends_trace_jsonl(tmp_path: Path) -> None:
    append_turn_coherence_trace_event(
        tmp_path,
        {
            "event_kind": "turn_coherence_started",
            "turn_id": "turn-store",
            "phase": "pre_reply",
        },
    )

    path = turn_coherence_trace_path(tmp_path)
    assert path == tmp_path / TRACE_REL
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert rows == [
        {
            "event_kind": "turn_coherence_started",
            "phase": "pre_reply",
            "turn_id": "turn-store",
        }
    ]

from __future__ import annotations

import json
from pathlib import Path

from xinyu_stage9_self_state_model import REPORT_REL as MODULE_REPORT_REL
from xinyu_stage9_self_state_model import STATE_REL as MODULE_STATE_REL
from xinyu_stage9_self_state_model import TRACE_REL as MODULE_TRACE_REL
from xinyu_stage9_self_state_model_store import REPORT_REL
from xinyu_stage9_self_state_model_store import SOURCE_RELS
from xinyu_stage9_self_state_model_store import STATE_REL
from xinyu_stage9_self_state_model_store import TRACE_REL
from xinyu_stage9_self_state_model_store import append_stage9_trace_event
from xinyu_stage9_self_state_model_store import read_stage9_source_text
from xinyu_stage9_self_state_model_store import stage9_report_path
from xinyu_stage9_self_state_model_store import stage9_source_path
from xinyu_stage9_self_state_model_store import stage9_state_path
from xinyu_stage9_self_state_model_store import stage9_trace_path
from xinyu_stage9_self_state_model_store import write_stage9_report_text
from xinyu_stage9_self_state_model_store import write_stage9_state_text


def test_stage9_store_exports_legacy_paths() -> None:
    assert REPORT_REL == MODULE_REPORT_REL
    assert STATE_REL == MODULE_STATE_REL
    assert TRACE_REL == MODULE_TRACE_REL
    assert SOURCE_RELS["stage8"] == Path("memory/context/stage8_memory_governance_state.md")
    assert SOURCE_RELS["capsule"] == Path("memory/context/self_state_capsule_state.md")


def test_stage9_store_reads_source_text_safely_and_limits(tmp_path: Path) -> None:
    assert read_stage9_source_text(tmp_path, "stage8", limit=20) == ""

    path = stage9_source_path(tmp_path, "stage8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\ufeff- stage8_memory_ready_for_stage9: true\n", encoding="utf-8")

    assert path == tmp_path / SOURCE_RELS["stage8"]
    assert read_stage9_source_text(tmp_path, "stage8", limit=200).startswith(
        "- stage8_memory_ready_for_stage9"
    )
    assert read_stage9_source_text(tmp_path, "stage8", limit=8) == "- stage8"


def test_stage9_store_writes_report_with_output_resolution(tmp_path: Path) -> None:
    relative = write_stage9_report_text(tmp_path, "# Stage9\n", output=Path("custom/report.md"))
    absolute = write_stage9_report_text(tmp_path, "# Absolute\n", output=tmp_path / "abs.md")

    assert stage9_report_path(tmp_path) == tmp_path / REPORT_REL
    assert relative == tmp_path / "custom/report.md"
    assert absolute == tmp_path / "abs.md"
    assert relative.read_text(encoding="utf-8") == "# Stage9\n"
    assert absolute.read_text(encoding="utf-8") == "# Absolute\n"


def test_stage9_store_writes_state_and_appends_trace_jsonl(tmp_path: Path) -> None:
    state_path = write_stage9_state_text(tmp_path, "# State\n- status: active\n")
    trace_path = append_stage9_trace_event(tmp_path, {"event_kind": "stage9", "status": "active"})

    assert state_path == stage9_state_path(tmp_path)
    assert state_path == tmp_path / STATE_REL
    assert state_path.read_text(encoding="utf-8") == "# State\n- status: active\n"
    assert trace_path == stage9_trace_path(tmp_path)
    assert trace_path == tmp_path / TRACE_REL
    assert [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines()] == [
        {"event_kind": "stage9", "status": "active"}
    ]

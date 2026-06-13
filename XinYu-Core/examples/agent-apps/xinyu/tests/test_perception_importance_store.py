from __future__ import annotations

import json
from pathlib import Path

from xinyu_perception_importance import REPORT_REL as MODULE_REPORT_REL
from xinyu_perception_importance import STATE_REL as MODULE_STATE_REL
from xinyu_perception_importance import TRACE_REL as MODULE_TRACE_REL
from xinyu_perception_importance_store import REPORT_REL
from xinyu_perception_importance_store import STATE_REL
from xinyu_perception_importance_store import TRACE_REL
from xinyu_perception_importance_store import append_perception_importance_trace_event
from xinyu_perception_importance_store import perception_importance_report_path
from xinyu_perception_importance_store import perception_importance_state_path
from xinyu_perception_importance_store import perception_importance_trace_path
from xinyu_perception_importance_store import read_perception_importance_state_text
from xinyu_perception_importance_store import write_perception_importance_report_text
from xinyu_perception_importance_store import write_perception_importance_state_text


def test_perception_importance_store_exports_legacy_paths() -> None:
    assert REPORT_REL == MODULE_REPORT_REL
    assert STATE_REL == MODULE_STATE_REL
    assert TRACE_REL == MODULE_TRACE_REL
    assert REPORT_REL == Path("worklog/xinyu-perception-importance-latest.md")
    assert STATE_REL == Path("memory/context/perception_importance_state.md")
    assert TRACE_REL == Path("runtime/perception_importance_trace.jsonl")


def test_perception_importance_store_reads_state_text_safely(tmp_path: Path) -> None:
    assert read_perception_importance_state_text(tmp_path) == ""

    path = perception_importance_state_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\ufeff- status: pass\n", encoding="utf-8")

    assert read_perception_importance_state_text(tmp_path) == "- status: pass\n"


def test_perception_importance_store_writes_report_with_output_resolution(tmp_path: Path) -> None:
    relative = write_perception_importance_report_text(tmp_path, "# Report\n", output=Path("custom/report.md"))
    absolute = write_perception_importance_report_text(tmp_path, "# Absolute\n", output=tmp_path / "abs.md")

    assert perception_importance_report_path(tmp_path) == tmp_path / REPORT_REL
    assert relative == tmp_path / "custom/report.md"
    assert absolute == tmp_path / "abs.md"
    assert relative.read_text(encoding="utf-8") == "# Report\n"
    assert absolute.read_text(encoding="utf-8") == "# Absolute\n"


def test_perception_importance_store_writes_state_and_appends_trace_jsonl(tmp_path: Path) -> None:
    state_path = write_perception_importance_state_text(tmp_path, "# State\n- status: pass\n")
    trace_path = append_perception_importance_trace_event(
        tmp_path,
        {"generated_at": "2026-06-10T09:00:00+08:00", "status": "pass"},
    )

    assert state_path == perception_importance_state_path(tmp_path)
    assert state_path == tmp_path / STATE_REL
    assert state_path.read_text(encoding="utf-8") == "# State\n- status: pass\n"
    assert trace_path == perception_importance_trace_path(tmp_path)
    assert trace_path == tmp_path / TRACE_REL
    trace_text = trace_path.read_text(encoding="utf-8")
    assert trace_text == '{"generated_at":"2026-06-10T09:00:00+08:00","status":"pass"}\n'
    assert [json.loads(line) for line in trace_text.splitlines()] == [
        {"generated_at": "2026-06-10T09:00:00+08:00", "status": "pass"}
    ]

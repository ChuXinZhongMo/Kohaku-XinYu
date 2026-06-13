from __future__ import annotations

import json
from pathlib import Path

from xinyu_stage12_long_term_evaluation import REPORT_REL as MODULE_REPORT_REL
from xinyu_stage12_long_term_evaluation import STATE_REL as MODULE_STATE_REL
from xinyu_stage12_long_term_evaluation import TRACE_REL as MODULE_TRACE_REL
from xinyu_stage12_long_term_evaluation_store import REPORT_REL
from xinyu_stage12_long_term_evaluation_store import STATE_REL
from xinyu_stage12_long_term_evaluation_store import TRACE_REL
from xinyu_stage12_long_term_evaluation_store import append_stage12_long_term_evaluation_trace_event
from xinyu_stage12_long_term_evaluation_store import stage12_long_term_evaluation_report_path
from xinyu_stage12_long_term_evaluation_store import stage12_long_term_evaluation_state_path
from xinyu_stage12_long_term_evaluation_store import stage12_long_term_evaluation_trace_path
from xinyu_stage12_long_term_evaluation_store import write_stage12_long_term_evaluation_report_text
from xinyu_stage12_long_term_evaluation_store import write_stage12_long_term_evaluation_state_text


def test_stage12_long_term_store_exports_legacy_paths() -> None:
    assert REPORT_REL == MODULE_REPORT_REL
    assert STATE_REL == MODULE_STATE_REL
    assert TRACE_REL == MODULE_TRACE_REL
    assert REPORT_REL == Path("worklog/xinyu-stage12-long-term-evaluation-latest.md")
    assert STATE_REL == Path("memory/context/stage12_long_term_evaluation_state.md")
    assert TRACE_REL == Path("runtime/stage12_long_term_evaluation_trace.jsonl")


def test_stage12_long_term_store_resolves_paths(tmp_path: Path) -> None:
    root = tmp_path.resolve()

    assert stage12_long_term_evaluation_report_path(tmp_path) == root / REPORT_REL
    assert stage12_long_term_evaluation_report_path(tmp_path, Path("custom/report.md")) == root / "custom/report.md"
    assert stage12_long_term_evaluation_report_path(tmp_path, tmp_path / "abs.md") == tmp_path / "abs.md"
    assert stage12_long_term_evaluation_state_path(tmp_path) == root / STATE_REL
    assert stage12_long_term_evaluation_trace_path(tmp_path) == root / TRACE_REL


def test_stage12_long_term_store_writes_report_state_and_trace(tmp_path: Path) -> None:
    report_path = write_stage12_long_term_evaluation_report_text(tmp_path, "# Report\n")
    custom_path = write_stage12_long_term_evaluation_report_text(
        tmp_path,
        "# Custom\n",
        output=Path("custom/report.md"),
    )
    state_path = write_stage12_long_term_evaluation_state_text(tmp_path, "# State\n")
    trace_path = append_stage12_long_term_evaluation_trace_event(tmp_path, {"b": 2, "a": "value"})

    assert report_path == tmp_path.resolve() / REPORT_REL
    assert custom_path == tmp_path.resolve() / "custom/report.md"
    assert state_path == tmp_path.resolve() / STATE_REL
    assert trace_path == tmp_path.resolve() / TRACE_REL
    assert report_path.read_text(encoding="utf-8") == "# Report\n"
    assert custom_path.read_text(encoding="utf-8") == "# Custom\n"
    assert state_path.read_text(encoding="utf-8") == "# State\n"
    assert json.loads(trace_path.read_text(encoding="utf-8")) == {"a": "value", "b": 2}
    assert trace_path.read_text(encoding="utf-8") == '{"a": "value", "b": 2}\n'

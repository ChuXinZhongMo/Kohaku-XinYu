from __future__ import annotations

import json
from pathlib import Path

from xinyu_feedback_consumption_diagnostics import INTENTION_STATE_REL as MODULE_INTENTION_STATE_REL
from xinyu_feedback_consumption_diagnostics import INTENTION_TRACE_REL as MODULE_INTENTION_TRACE_REL
from xinyu_feedback_consumption_diagnostics import REPORT_REL as MODULE_REPORT_REL
from xinyu_feedback_consumption_diagnostics import STATE_REL as MODULE_STATE_REL
from xinyu_feedback_consumption_diagnostics import TRACE_REL as MODULE_TRACE_REL
from xinyu_feedback_consumption_diagnostics_store import INTENTION_STATE_REL
from xinyu_feedback_consumption_diagnostics_store import INTENTION_TRACE_REL
from xinyu_feedback_consumption_diagnostics_store import REPORT_REL
from xinyu_feedback_consumption_diagnostics_store import STATE_REL
from xinyu_feedback_consumption_diagnostics_store import TRACE_REL
from xinyu_feedback_consumption_diagnostics_store import append_feedback_consumption_trace_event
from xinyu_feedback_consumption_diagnostics_store import feedback_consumption_intention_state_path
from xinyu_feedback_consumption_diagnostics_store import feedback_consumption_intention_trace_path
from xinyu_feedback_consumption_diagnostics_store import feedback_consumption_report_path
from xinyu_feedback_consumption_diagnostics_store import feedback_consumption_state_path
from xinyu_feedback_consumption_diagnostics_store import feedback_consumption_trace_path
from xinyu_feedback_consumption_diagnostics_store import read_feedback_consumption_jsonl_tail
from xinyu_feedback_consumption_diagnostics_store import read_feedback_consumption_state_text
from xinyu_feedback_consumption_diagnostics_store import write_feedback_consumption_report_text
from xinyu_feedback_consumption_diagnostics_store import write_feedback_consumption_state_text


def test_feedback_consumption_store_exports_legacy_paths() -> None:
    assert INTENTION_TRACE_REL == MODULE_INTENTION_TRACE_REL
    assert INTENTION_STATE_REL == MODULE_INTENTION_STATE_REL
    assert STATE_REL == MODULE_STATE_REL
    assert TRACE_REL == MODULE_TRACE_REL
    assert REPORT_REL == MODULE_REPORT_REL
    assert INTENTION_TRACE_REL == Path("runtime/intention_ecology_trace.jsonl")
    assert REPORT_REL == Path("worklog/xinyu-feedback-consumption-diagnostics-latest.md")


def test_feedback_consumption_store_resolves_root_paths(tmp_path: Path) -> None:
    assert feedback_consumption_intention_trace_path(tmp_path) == tmp_path.resolve() / INTENTION_TRACE_REL
    assert feedback_consumption_intention_state_path(tmp_path) == tmp_path.resolve() / INTENTION_STATE_REL
    assert feedback_consumption_state_path(tmp_path) == tmp_path.resolve() / STATE_REL
    assert feedback_consumption_trace_path(tmp_path) == tmp_path.resolve() / TRACE_REL


def test_feedback_consumption_store_reads_jsonl_tail_with_original_filtering(tmp_path: Path) -> None:
    path = tmp_path / INTENTION_TRACE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    older = {"checked_at": "old"}
    recent = {"checked_at": "recent", "feedback_consumption_status": "consumed"}
    newest = {"checked_at": "newest", "feedback_consumption_status": "missing"}
    path.write_text(
        "\ufeff"
        + "\n".join(
            (
                json.dumps(older, ensure_ascii=False),
                json.dumps(recent, ensure_ascii=False),
                "[\"not\", \"dict\"]",
                "{bad",
                json.dumps(newest, ensure_ascii=False),
            )
        )
        + "\n",
        encoding="utf-8",
    )

    assert read_feedback_consumption_jsonl_tail(tmp_path / "missing.jsonl", max_lines=2) == []
    assert read_feedback_consumption_jsonl_tail(path, max_lines=4) == [recent, newest]


def test_feedback_consumption_store_reads_current_state_text(tmp_path: Path) -> None:
    assert read_feedback_consumption_state_text(tmp_path) == ""

    path = tmp_path / INTENTION_STATE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\ufeff- feedback_consumption_status: consumed\n", encoding="utf-8")

    assert read_feedback_consumption_state_text(tmp_path) == "- feedback_consumption_status: consumed\n"


def test_feedback_consumption_store_writes_report_and_state(tmp_path: Path) -> None:
    relative = write_feedback_consumption_report_text(tmp_path, "# Report\n", output=Path("custom/report.md"))
    absolute = write_feedback_consumption_report_text(tmp_path, "# Absolute\n", output=tmp_path / "abs.md")
    state = write_feedback_consumption_state_text(tmp_path, "# State\n")

    assert feedback_consumption_report_path(tmp_path) == tmp_path / REPORT_REL
    assert relative == tmp_path / "custom/report.md"
    assert absolute == tmp_path / "abs.md"
    assert state == tmp_path / STATE_REL
    assert relative.read_text(encoding="utf-8") == "# Report\n"
    assert absolute.read_text(encoding="utf-8") == "# Absolute\n"
    assert state.read_text(encoding="utf-8") == "# State\n"


def test_feedback_consumption_store_appends_compact_sorted_trace(tmp_path: Path) -> None:
    path = append_feedback_consumption_trace_event(tmp_path, {"b": 2, "a": "value"})

    assert path == tmp_path.resolve() / TRACE_REL
    assert path.read_text(encoding="utf-8") == '{"a":"value","b":2}\n'

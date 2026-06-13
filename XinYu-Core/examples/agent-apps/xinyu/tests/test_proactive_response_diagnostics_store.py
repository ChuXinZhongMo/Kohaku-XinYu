from __future__ import annotations

import json
from pathlib import Path

from xinyu_proactive_response_diagnostics import PROACTIVE_DISPATCH_STATE_REL as MODULE_PROACTIVE_DISPATCH_STATE_REL
from xinyu_proactive_response_diagnostics import PROACTIVE_REQUEST_STATE_REL as MODULE_PROACTIVE_REQUEST_STATE_REL
from xinyu_proactive_response_diagnostics import REPORT_REL as MODULE_REPORT_REL
from xinyu_proactive_response_diagnostics import STATE_REL as MODULE_STATE_REL
from xinyu_proactive_response_diagnostics import TRACE_REL as MODULE_TRACE_REL
from xinyu_proactive_response_diagnostics_store import PROACTIVE_DISPATCH_STATE_REL
from xinyu_proactive_response_diagnostics_store import PROACTIVE_REQUEST_STATE_REL
from xinyu_proactive_response_diagnostics_store import REPORT_REL
from xinyu_proactive_response_diagnostics_store import STATE_REL
from xinyu_proactive_response_diagnostics_store import TRACE_REL
from xinyu_proactive_response_diagnostics_store import append_proactive_response_diagnostics_trace_event
from xinyu_proactive_response_diagnostics_store import proactive_dispatch_state_path
from xinyu_proactive_response_diagnostics_store import proactive_request_state_path
from xinyu_proactive_response_diagnostics_store import proactive_response_diagnostics_report_path
from xinyu_proactive_response_diagnostics_store import proactive_response_diagnostics_state_path
from xinyu_proactive_response_diagnostics_store import proactive_response_diagnostics_trace_path
from xinyu_proactive_response_diagnostics_store import read_proactive_dispatch_state_text
from xinyu_proactive_response_diagnostics_store import read_proactive_request_state_text
from xinyu_proactive_response_diagnostics_store import write_proactive_response_diagnostics_report_text
from xinyu_proactive_response_diagnostics_store import write_proactive_response_diagnostics_state_text


def test_proactive_response_diagnostics_store_exports_legacy_paths() -> None:
    assert STATE_REL == MODULE_STATE_REL
    assert TRACE_REL == MODULE_TRACE_REL
    assert REPORT_REL == MODULE_REPORT_REL
    assert PROACTIVE_REQUEST_STATE_REL == MODULE_PROACTIVE_REQUEST_STATE_REL
    assert PROACTIVE_DISPATCH_STATE_REL == MODULE_PROACTIVE_DISPATCH_STATE_REL
    assert STATE_REL == Path("memory/context/proactive_response_diagnostics_state.md")
    assert TRACE_REL == Path("runtime/proactive_response_diagnostics_trace.jsonl")


def test_proactive_response_diagnostics_store_reads_source_state_safely(tmp_path: Path) -> None:
    assert read_proactive_request_state_text(tmp_path) == ""
    assert read_proactive_dispatch_state_text(tmp_path) == ""

    request_path = proactive_request_state_path(tmp_path)
    request_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.write_text("\ufeff- status: sent\n", encoding="utf-8")
    dispatch_path = proactive_dispatch_state_path(tmp_path)
    dispatch_path.parent.mkdir(parents=True, exist_ok=True)
    dispatch_path.write_text("\ufeff- last_ack_status: queued\n", encoding="utf-8")

    assert request_path == tmp_path / PROACTIVE_REQUEST_STATE_REL
    assert dispatch_path == tmp_path / PROACTIVE_DISPATCH_STATE_REL
    assert read_proactive_request_state_text(tmp_path) == "- status: sent\n"
    assert read_proactive_dispatch_state_text(tmp_path) == "- last_ack_status: queued\n"


def test_proactive_response_diagnostics_store_writes_report_with_output_resolution(tmp_path: Path) -> None:
    relative = write_proactive_response_diagnostics_report_text(tmp_path, "# Report\n", output=Path("custom/report.md"))
    absolute = write_proactive_response_diagnostics_report_text(tmp_path, "# Absolute\n", output=tmp_path / "abs.md")

    assert proactive_response_diagnostics_report_path(tmp_path) == tmp_path / REPORT_REL
    assert relative == tmp_path / "custom/report.md"
    assert absolute == tmp_path / "abs.md"
    assert relative.read_text(encoding="utf-8") == "# Report\n"
    assert absolute.read_text(encoding="utf-8") == "# Absolute\n"


def test_proactive_response_diagnostics_store_writes_state_and_compact_trace(tmp_path: Path) -> None:
    state_path = write_proactive_response_diagnostics_state_text(tmp_path, "# State\n- status: waiting\n")
    trace_path = append_proactive_response_diagnostics_trace_event(
        tmp_path,
        {"generated_at": "2026-06-10T09:00:00+08:00", "status": "waiting"},
    )

    assert state_path == proactive_response_diagnostics_state_path(tmp_path)
    assert state_path == tmp_path / STATE_REL
    assert state_path.read_text(encoding="utf-8") == "# State\n- status: waiting\n"
    assert trace_path == proactive_response_diagnostics_trace_path(tmp_path)
    assert trace_path == tmp_path / TRACE_REL
    trace_text = trace_path.read_text(encoding="utf-8")
    assert trace_text == '{"generated_at":"2026-06-10T09:00:00+08:00","status":"waiting"}\n'
    assert [json.loads(line) for line in trace_text.splitlines()] == [
        {"generated_at": "2026-06-10T09:00:00+08:00", "status": "waiting"}
    ]

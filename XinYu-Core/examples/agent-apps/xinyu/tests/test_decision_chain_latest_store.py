from __future__ import annotations

import json
from pathlib import Path

from xinyu_decision_chain_latest import REPORT_REL as MODULE_REPORT_REL
from xinyu_decision_chain_latest import STATE_REL as MODULE_STATE_REL
from xinyu_decision_chain_latest import TRACE_REL as MODULE_TRACE_REL
from xinyu_decision_chain_latest_store import REPORT_REL
from xinyu_decision_chain_latest_store import STATE_REL
from xinyu_decision_chain_latest_store import TRACE_REL
from xinyu_decision_chain_latest_store import append_decision_chain_latest_trace_event
from xinyu_decision_chain_latest_store import decision_chain_latest_report_path
from xinyu_decision_chain_latest_store import decision_chain_latest_state_path
from xinyu_decision_chain_latest_store import decision_chain_latest_trace_path
from xinyu_decision_chain_latest_store import write_decision_chain_latest_report_text
from xinyu_decision_chain_latest_store import write_decision_chain_latest_state_text


def test_decision_chain_latest_store_exports_legacy_paths() -> None:
    assert REPORT_REL == MODULE_REPORT_REL
    assert STATE_REL == MODULE_STATE_REL
    assert TRACE_REL == MODULE_TRACE_REL
    assert REPORT_REL == Path("worklog/xinyu-decision-chain-latest.md")
    assert STATE_REL == Path("memory/context/decision_chain_latest_state.md")
    assert TRACE_REL == Path("runtime/decision_chain_latest_trace.jsonl")


def test_decision_chain_latest_store_resolves_paths(tmp_path: Path) -> None:
    root = tmp_path.resolve()

    assert decision_chain_latest_report_path(tmp_path) == root / REPORT_REL
    assert decision_chain_latest_report_path(tmp_path, Path("custom/report.md")) == root / "custom/report.md"
    assert decision_chain_latest_report_path(tmp_path, tmp_path / "abs.md") == tmp_path / "abs.md"
    assert decision_chain_latest_state_path(tmp_path) == root / STATE_REL
    assert decision_chain_latest_trace_path(tmp_path) == root / TRACE_REL


def test_decision_chain_latest_store_writes_report_state_and_trace(tmp_path: Path) -> None:
    report_path = write_decision_chain_latest_report_text(tmp_path, "# Report\n")
    state_path = write_decision_chain_latest_state_text(tmp_path, "# State\n")
    trace_path = append_decision_chain_latest_trace_event(tmp_path, {"b": 2, "a": "value"})

    assert report_path == tmp_path.resolve() / REPORT_REL
    assert state_path == tmp_path.resolve() / STATE_REL
    assert trace_path == tmp_path.resolve() / TRACE_REL
    assert report_path.read_text(encoding="utf-8") == "# Report\n"
    assert state_path.read_text(encoding="utf-8") == "# State\n"
    assert json.loads(trace_path.read_text(encoding="utf-8")) == {"a": "value", "b": 2}
    assert trace_path.read_text(encoding="utf-8") == '{"a":"value","b":2}\n'


def test_decision_chain_latest_store_writes_custom_report_outputs(tmp_path: Path) -> None:
    relative_path = write_decision_chain_latest_report_text(
        tmp_path,
        "relative\n",
        output=Path("custom/latest.md"),
    )
    absolute_path = write_decision_chain_latest_report_text(
        tmp_path,
        "absolute\n",
        output=tmp_path / "absolute.md",
    )

    assert relative_path == tmp_path.resolve() / "custom/latest.md"
    assert absolute_path == tmp_path / "absolute.md"
    assert relative_path.read_text(encoding="utf-8") == "relative\n"
    assert absolute_path.read_text(encoding="utf-8") == "absolute\n"

from __future__ import annotations

import json
from pathlib import Path

from xinyu_qq_reply_integrity_diagnostics import ACK_SPOOL_REL as MODULE_ACK_SPOOL_REL
from xinyu_qq_reply_integrity_diagnostics import REPORT_REL as MODULE_REPORT_REL
from xinyu_qq_reply_integrity_diagnostics import ROUTE_TRACE_REL as MODULE_ROUTE_TRACE_REL
from xinyu_qq_reply_integrity_diagnostics import STATE_REL as MODULE_STATE_REL
from xinyu_qq_reply_integrity_diagnostics import TRACE_REL as MODULE_TRACE_REL
from xinyu_qq_reply_integrity_diagnostics import WORKING_MEMORY_DIR_REL as MODULE_WORKING_MEMORY_DIR_REL
from xinyu_qq_reply_integrity_diagnostics_store import ACK_SPOOL_REL
from xinyu_qq_reply_integrity_diagnostics_store import REPORT_REL
from xinyu_qq_reply_integrity_diagnostics_store import ROUTE_TRACE_REL
from xinyu_qq_reply_integrity_diagnostics_store import STATE_REL
from xinyu_qq_reply_integrity_diagnostics_store import TRACE_REL
from xinyu_qq_reply_integrity_diagnostics_store import WORKING_MEMORY_DIR_REL
from xinyu_qq_reply_integrity_diagnostics_store import append_qq_reply_integrity_trace_event
from xinyu_qq_reply_integrity_diagnostics_store import qq_reply_integrity_ack_spool_path
from xinyu_qq_reply_integrity_diagnostics_store import qq_reply_integrity_report_path
from xinyu_qq_reply_integrity_diagnostics_store import qq_reply_integrity_route_trace_path
from xinyu_qq_reply_integrity_diagnostics_store import qq_reply_integrity_state_path
from xinyu_qq_reply_integrity_diagnostics_store import qq_reply_integrity_trace_path
from xinyu_qq_reply_integrity_diagnostics_store import qq_reply_integrity_working_memory_dir
from xinyu_qq_reply_integrity_diagnostics_store import read_qq_reply_integrity_jsonl_tail
from xinyu_qq_reply_integrity_diagnostics_store import read_qq_reply_integrity_working_memory_rows
from xinyu_qq_reply_integrity_diagnostics_store import write_qq_reply_integrity_report_text
from xinyu_qq_reply_integrity_diagnostics_store import write_qq_reply_integrity_state_text


def test_qq_reply_integrity_store_exports_legacy_paths() -> None:
    assert ACK_SPOOL_REL == MODULE_ACK_SPOOL_REL
    assert ROUTE_TRACE_REL == MODULE_ROUTE_TRACE_REL
    assert WORKING_MEMORY_DIR_REL == MODULE_WORKING_MEMORY_DIR_REL
    assert STATE_REL == MODULE_STATE_REL
    assert REPORT_REL == MODULE_REPORT_REL
    assert TRACE_REL == MODULE_TRACE_REL
    assert ACK_SPOOL_REL == Path("runtime/gateway_ack_spool.jsonl")
    assert WORKING_MEMORY_DIR_REL == Path("runtime/dialogue_working_memory")


def test_qq_reply_integrity_store_resolves_paths(tmp_path: Path) -> None:
    root = tmp_path.resolve()

    assert qq_reply_integrity_ack_spool_path(tmp_path) == root / ACK_SPOOL_REL
    assert qq_reply_integrity_route_trace_path(tmp_path) == root / ROUTE_TRACE_REL
    assert qq_reply_integrity_working_memory_dir(tmp_path) == root / WORKING_MEMORY_DIR_REL
    assert qq_reply_integrity_report_path(tmp_path) == root / REPORT_REL
    assert qq_reply_integrity_report_path(tmp_path, Path("custom/report.md")) == root / "custom/report.md"
    assert qq_reply_integrity_state_path(tmp_path) == root / STATE_REL
    assert qq_reply_integrity_trace_path(tmp_path) == root / TRACE_REL


def test_qq_reply_integrity_store_reads_jsonl_tail_bom_safe(tmp_path: Path) -> None:
    path = tmp_path / ACK_SPOOL_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    older = {"event": "old"}
    recent = {"event": "recent"}
    newest = {"event": "newest"}
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

    rows = read_qq_reply_integrity_jsonl_tail(path, max_lines=4)

    assert rows == [recent, newest]
    assert read_qq_reply_integrity_jsonl_tail(tmp_path / "missing.jsonl", max_lines=2) == []


def test_qq_reply_integrity_store_reads_working_memory_rows(tmp_path: Path) -> None:
    path = tmp_path / WORKING_MEMORY_DIR_REL / "session.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"role": "assistant", "content": "reply"}, ensure_ascii=False)
        + "\n{bad\n"
        + json.dumps(["not", "dict"], ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )

    rows, file_count = read_qq_reply_integrity_working_memory_rows(tmp_path)

    assert file_count == 1
    assert rows == [{"role": "assistant", "content": "reply"}]


def test_qq_reply_integrity_store_writes_report_state_and_trace(tmp_path: Path) -> None:
    report_path = write_qq_reply_integrity_report_text(tmp_path, "# Report\n")
    state_path = write_qq_reply_integrity_state_text(tmp_path, "# State\n")
    trace_path = append_qq_reply_integrity_trace_event(tmp_path, {"b": 2, "a": "value"})

    assert report_path == tmp_path.resolve() / REPORT_REL
    assert state_path == tmp_path.resolve() / STATE_REL
    assert trace_path == tmp_path.resolve() / TRACE_REL
    assert report_path.read_text(encoding="utf-8") == "# Report\n"
    assert state_path.read_text(encoding="utf-8") == "# State\n"
    assert trace_path.read_text(encoding="utf-8") == '{"a":"value","b":2}\n'

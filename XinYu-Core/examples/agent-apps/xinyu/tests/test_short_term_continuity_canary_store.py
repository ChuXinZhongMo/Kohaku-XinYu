from __future__ import annotations

import json
from pathlib import Path

from xinyu_short_term_continuity_canary import ACK_SPOOL_REL as MODULE_ACK_SPOOL_REL
from xinyu_short_term_continuity_canary import REPORT_REL as MODULE_REPORT_REL
from xinyu_short_term_continuity_canary import SHORT_TRACE_REL as MODULE_SHORT_TRACE_REL
from xinyu_short_term_continuity_canary import STATE_REL as MODULE_STATE_REL
from xinyu_short_term_continuity_canary import TRACE_REL as MODULE_TRACE_REL
from xinyu_short_term_continuity_canary_store import ACK_SPOOL_REL
from xinyu_short_term_continuity_canary_store import REPORT_REL
from xinyu_short_term_continuity_canary_store import SHORT_TRACE_REL
from xinyu_short_term_continuity_canary_store import STATE_REL
from xinyu_short_term_continuity_canary_store import TRACE_REL
from xinyu_short_term_continuity_canary_store import append_short_term_continuity_canary_trace_event
from xinyu_short_term_continuity_canary_store import gateway_ack_spool_path
from xinyu_short_term_continuity_canary_store import read_gateway_ack_spool_jsonl_tail
from xinyu_short_term_continuity_canary_store import read_jsonl_tail
from xinyu_short_term_continuity_canary_store import read_short_term_continuity_jsonl_tail
from xinyu_short_term_continuity_canary_store import short_term_continuity_canary_report_path
from xinyu_short_term_continuity_canary_store import short_term_continuity_canary_state_path
from xinyu_short_term_continuity_canary_store import short_term_continuity_canary_trace_path
from xinyu_short_term_continuity_canary_store import short_term_continuity_trace_path
from xinyu_short_term_continuity_canary_store import write_short_term_continuity_canary_report_text
from xinyu_short_term_continuity_canary_store import write_short_term_continuity_canary_state_text


def test_short_term_continuity_canary_store_exports_legacy_paths() -> None:
    assert SHORT_TRACE_REL == MODULE_SHORT_TRACE_REL
    assert ACK_SPOOL_REL == MODULE_ACK_SPOOL_REL
    assert STATE_REL == MODULE_STATE_REL
    assert REPORT_REL == MODULE_REPORT_REL
    assert TRACE_REL == MODULE_TRACE_REL
    assert SHORT_TRACE_REL == Path("runtime/short_term_continuity_trace.jsonl")
    assert ACK_SPOOL_REL == Path("runtime/gateway_ack_spool.jsonl")


def test_short_term_continuity_canary_store_reads_jsonl_tail_safely(tmp_path: Path) -> None:
    assert read_short_term_continuity_jsonl_tail(tmp_path, max_lines=10) == []
    assert read_jsonl_tail(tmp_path / "missing.jsonl", max_lines=10) == []

    path = short_term_continuity_trace_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\ufeff" + "\n".join(["{bad", '{"seq":1}', '{"seq":2}', '{"seq":3}']) + "\n",
        encoding="utf-8",
    )

    assert path == tmp_path / SHORT_TRACE_REL
    assert read_short_term_continuity_jsonl_tail(tmp_path, max_lines=2) == [{"seq": 2}, {"seq": 3}]

    ack_path = gateway_ack_spool_path(tmp_path)
    ack_path.parent.mkdir(parents=True, exist_ok=True)
    ack_path.write_text('{"event":"pending"}\n', encoding="utf-8")
    assert ack_path == tmp_path / ACK_SPOOL_REL
    assert read_gateway_ack_spool_jsonl_tail(tmp_path, max_lines=1) == [{"event": "pending"}]


def test_short_term_continuity_canary_store_writes_report_with_output_resolution(tmp_path: Path) -> None:
    relative = write_short_term_continuity_canary_report_text(tmp_path, "# Canary\n", output=Path("custom/report.md"))
    absolute = write_short_term_continuity_canary_report_text(tmp_path, "# Absolute\n", output=tmp_path / "abs.md")

    assert short_term_continuity_canary_report_path(tmp_path) == tmp_path / REPORT_REL
    assert relative == tmp_path / "custom/report.md"
    assert absolute == tmp_path / "abs.md"
    assert relative.read_text(encoding="utf-8") == "# Canary\n"
    assert absolute.read_text(encoding="utf-8") == "# Absolute\n"


def test_short_term_continuity_canary_store_writes_state_and_compact_trace(tmp_path: Path) -> None:
    state_path = write_short_term_continuity_canary_state_text(tmp_path, "# State\n- status: pass\n")
    trace_path = append_short_term_continuity_canary_trace_event(
        tmp_path,
        {"generated_at": "2026-06-10T09:00:00+08:00", "status": "pass"},
    )

    assert state_path == short_term_continuity_canary_state_path(tmp_path)
    assert state_path == tmp_path / STATE_REL
    assert state_path.read_text(encoding="utf-8") == "# State\n- status: pass\n"
    assert trace_path == short_term_continuity_canary_trace_path(tmp_path)
    assert trace_path == tmp_path / TRACE_REL
    trace_text = trace_path.read_text(encoding="utf-8")
    assert trace_text == '{"generated_at":"2026-06-10T09:00:00+08:00","status":"pass"}\n'
    assert [json.loads(line) for line in trace_text.splitlines()] == [
        {"generated_at": "2026-06-10T09:00:00+08:00", "status": "pass"}
    ]

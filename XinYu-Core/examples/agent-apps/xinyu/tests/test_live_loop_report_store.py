from __future__ import annotations

import json
import sys
from pathlib import Path

from xinyu_live_loop_report import GATEWAY_ACK_SPOOL_REL as MODULE_GATEWAY_ACK_SPOOL_REL
from xinyu_live_loop_report import QQ_INBOUND_TRACE_REL as MODULE_QQ_INBOUND_TRACE_REL
from xinyu_live_loop_report import VISIBLE_SEND_SHADOW_TRACE_REL as MODULE_VISIBLE_SEND_SHADOW_TRACE_REL
from xinyu_live_loop_report_store import GATEWAY_ACK_SPOOL_REL
from xinyu_live_loop_report_store import QQ_INBOUND_TRACE_REL
from xinyu_live_loop_report_store import VISIBLE_SEND_SHADOW_TRACE_REL
from xinyu_live_loop_report_store import live_loop_gateway_ack_spool_path
from xinyu_live_loop_report_store import live_loop_qq_inbound_trace_path
from xinyu_live_loop_report_store import live_loop_visible_send_shadow_trace_path
from xinyu_live_loop_report_store import load_live_loop_status
from xinyu_live_loop_report_store import read_live_loop_jsonl_tail


def test_live_loop_report_store_exports_trace_paths() -> None:
    assert QQ_INBOUND_TRACE_REL == MODULE_QQ_INBOUND_TRACE_REL
    assert VISIBLE_SEND_SHADOW_TRACE_REL == MODULE_VISIBLE_SEND_SHADOW_TRACE_REL
    assert GATEWAY_ACK_SPOOL_REL == MODULE_GATEWAY_ACK_SPOOL_REL
    assert QQ_INBOUND_TRACE_REL == Path("runtime/qq_inbound_trace.jsonl")
    assert VISIBLE_SEND_SHADOW_TRACE_REL == Path("runtime/answer_discipline_visible_send_shadow.jsonl")
    assert GATEWAY_ACK_SPOOL_REL == Path("runtime/gateway_ack_spool.jsonl")


def test_live_loop_report_store_resolves_trace_paths(tmp_path: Path) -> None:
    root = tmp_path.resolve()

    assert live_loop_qq_inbound_trace_path(tmp_path) == root / QQ_INBOUND_TRACE_REL
    assert live_loop_visible_send_shadow_trace_path(tmp_path) == root / VISIBLE_SEND_SHADOW_TRACE_REL
    assert live_loop_gateway_ack_spool_path(tmp_path) == root / GATEWAY_ACK_SPOOL_REL


def test_live_loop_report_store_reads_jsonl_tail_bom_safe(tmp_path: Path) -> None:
    path = tmp_path / QQ_INBOUND_TRACE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    older = {"arrival_seq": 1}
    recent = {"arrival_seq": 2}
    newest = {"arrival_seq": 3}
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

    rows = read_live_loop_jsonl_tail(path, max_lines=4)

    assert rows == [recent, newest]
    assert read_live_loop_jsonl_tail(tmp_path / "missing.jsonl") == []


def test_live_loop_report_store_reports_missing_status_script(tmp_path: Path) -> None:
    data, error = load_live_loop_status(tmp_path, "http://127.0.0.1:8765", python_executable=sys.executable)

    assert data is None
    assert error == f"missing_status_script:{tmp_path.resolve() / 'xinyu_status.py'}"


def test_live_loop_report_store_loads_status_json(tmp_path: Path) -> None:
    status_script = tmp_path / "xinyu_status.py"
    status_script.write_text(
        "import json\n"
        "print(json.dumps({'ok': True, 'checks': [{'name': 'core_bridge', 'ok': True}]}))\n",
        encoding="utf-8",
    )

    data, error = load_live_loop_status(tmp_path, "http://core.test", python_executable=sys.executable)

    assert error == ""
    assert data == {"ok": True, "checks": [{"name": "core_bridge", "ok": True}]}

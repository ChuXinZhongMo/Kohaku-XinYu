from __future__ import annotations

import json
from pathlib import Path

from xinyu_perception_event_layer import OCR_TRACE_REL as MODULE_OCR_TRACE_REL
from xinyu_perception_event_layer import PROACTIVE_REQUEST_STATE_REL as MODULE_PROACTIVE_REQUEST_STATE_REL
from xinyu_perception_event_layer import QQ_ACK_REL as MODULE_QQ_ACK_REL
from xinyu_perception_event_layer import QQ_TRACE_REL as MODULE_QQ_TRACE_REL
from xinyu_perception_event_layer import REPORT_REL as MODULE_REPORT_REL
from xinyu_perception_event_layer import STATE_REL as MODULE_STATE_REL
from xinyu_perception_event_layer import TRACE_REL as MODULE_TRACE_REL
from xinyu_perception_event_layer import VOICE_TRACE_RELS as MODULE_VOICE_TRACE_RELS
from xinyu_perception_event_layer_store import OCR_TRACE_REL
from xinyu_perception_event_layer_store import PROACTIVE_REQUEST_STATE_REL
from xinyu_perception_event_layer_store import QQ_ACK_REL
from xinyu_perception_event_layer_store import QQ_TRACE_REL
from xinyu_perception_event_layer_store import REPORT_REL
from xinyu_perception_event_layer_store import STATE_REL
from xinyu_perception_event_layer_store import TRACE_REL
from xinyu_perception_event_layer_store import VOICE_TRACE_RELS
from xinyu_perception_event_layer_store import append_perception_event_layer_trace_event
from xinyu_perception_event_layer_store import perception_event_layer_ack_spool_path
from xinyu_perception_event_layer_store import perception_event_layer_ocr_trace_path
from xinyu_perception_event_layer_store import perception_event_layer_proactive_request_state_path
from xinyu_perception_event_layer_store import perception_event_layer_qq_trace_path
from xinyu_perception_event_layer_store import perception_event_layer_report_path
from xinyu_perception_event_layer_store import perception_event_layer_state_path
from xinyu_perception_event_layer_store import perception_event_layer_trace_path
from xinyu_perception_event_layer_store import perception_event_layer_voice_trace_path
from xinyu_perception_event_layer_store import read_perception_event_layer_jsonl_tail
from xinyu_perception_event_layer_store import read_perception_event_layer_proactive_request_state_text
from xinyu_perception_event_layer_store import read_perception_event_layer_state_text
from xinyu_perception_event_layer_store import write_perception_event_layer_report_text
from xinyu_perception_event_layer_store import write_perception_event_layer_state_text


def test_perception_event_layer_store_exports_legacy_paths() -> None:
    assert REPORT_REL == MODULE_REPORT_REL
    assert STATE_REL == MODULE_STATE_REL
    assert TRACE_REL == MODULE_TRACE_REL
    assert QQ_TRACE_REL == MODULE_QQ_TRACE_REL
    assert QQ_ACK_REL == MODULE_QQ_ACK_REL
    assert PROACTIVE_REQUEST_STATE_REL == MODULE_PROACTIVE_REQUEST_STATE_REL
    assert OCR_TRACE_REL == MODULE_OCR_TRACE_REL
    assert VOICE_TRACE_RELS == MODULE_VOICE_TRACE_RELS
    assert REPORT_REL == Path("worklog/xinyu-perception-event-layer-latest.md")
    assert STATE_REL == Path("memory/context/perception_event_layer_state.md")
    assert TRACE_REL == Path("runtime/perception_event_layer_trace.jsonl")
    assert QQ_TRACE_REL == Path("runtime/qq_inbound_trace.jsonl")
    assert QQ_ACK_REL == Path("runtime/gateway_ack_spool.jsonl")
    assert PROACTIVE_REQUEST_STATE_REL == Path("memory/context/proactive_request_state.md")
    assert OCR_TRACE_REL == Path("runtime/learning_ocr_trace.jsonl")
    assert VOICE_TRACE_RELS[0] == Path("runtime/voice_input_trace.jsonl")


def test_perception_event_layer_store_resolves_paths(tmp_path: Path) -> None:
    root = tmp_path.resolve()

    assert perception_event_layer_report_path(tmp_path) == root / REPORT_REL
    assert perception_event_layer_report_path(tmp_path, Path("custom/report.md")) == root / "custom/report.md"
    assert perception_event_layer_report_path(tmp_path, tmp_path / "abs.md") == tmp_path / "abs.md"
    assert perception_event_layer_state_path(tmp_path) == root / STATE_REL
    assert perception_event_layer_trace_path(tmp_path) == root / TRACE_REL
    assert perception_event_layer_qq_trace_path(tmp_path) == root / QQ_TRACE_REL
    assert perception_event_layer_ack_spool_path(tmp_path) == root / QQ_ACK_REL
    assert perception_event_layer_proactive_request_state_path(tmp_path) == root / PROACTIVE_REQUEST_STATE_REL
    assert perception_event_layer_ocr_trace_path(tmp_path) == root / OCR_TRACE_REL
    assert perception_event_layer_voice_trace_path(tmp_path, VOICE_TRACE_RELS[1]) == root / VOICE_TRACE_RELS[1]


def test_perception_event_layer_store_reads_jsonl_tail_bom_safe(tmp_path: Path) -> None:
    path = tmp_path / QQ_TRACE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    older = {"message_id": "old"}
    recent = {"message_id": "recent"}
    newest = {"message_id": "newest"}
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

    rows = read_perception_event_layer_jsonl_tail(path, max_lines=4)

    assert rows == [recent, newest]
    assert read_perception_event_layer_jsonl_tail(tmp_path / "missing.jsonl", max_lines=2) == []


def test_perception_event_layer_store_reads_state_text(tmp_path: Path) -> None:
    assert read_perception_event_layer_state_text(tmp_path) == ""
    assert read_perception_event_layer_proactive_request_state_text(tmp_path) == ""

    state_path = tmp_path / PROACTIVE_REQUEST_STATE_REL
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text("- status: sent\n", encoding="utf-8")

    assert read_perception_event_layer_proactive_request_state_text(tmp_path) == "- status: sent\n"


def test_perception_event_layer_store_writes_report_state_and_trace(tmp_path: Path) -> None:
    report_path = write_perception_event_layer_report_text(tmp_path, "# Report\n")
    custom_path = write_perception_event_layer_report_text(
        tmp_path,
        "# Custom\n",
        output=Path("custom/report.md"),
    )
    state_path = write_perception_event_layer_state_text(tmp_path, "# State\n")
    trace_path = append_perception_event_layer_trace_event(tmp_path, {"b": 2, "a": "value"})

    assert report_path == tmp_path.resolve() / REPORT_REL
    assert custom_path == tmp_path.resolve() / "custom/report.md"
    assert state_path == tmp_path.resolve() / STATE_REL
    assert trace_path == tmp_path.resolve() / TRACE_REL
    assert report_path.read_text(encoding="utf-8") == "# Report\n"
    assert custom_path.read_text(encoding="utf-8") == "# Custom\n"
    assert state_path.read_text(encoding="utf-8") == "# State\n"
    assert json.loads(trace_path.read_text(encoding="utf-8")) == {"a": "value", "b": 2}
    assert trace_path.read_text(encoding="utf-8") == '{"a":"value","b":2}\n'

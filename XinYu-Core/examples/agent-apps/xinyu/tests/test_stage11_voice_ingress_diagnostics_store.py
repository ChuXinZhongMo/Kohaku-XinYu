from __future__ import annotations

import json
from pathlib import Path

from xinyu_stage11_voice_ingress_diagnostics import QQ_RICH_TRACE_REL as MODULE_QQ_RICH_TRACE_REL
from xinyu_stage11_voice_ingress_diagnostics import QQ_TRACE_REL as MODULE_QQ_TRACE_REL
from xinyu_stage11_voice_ingress_diagnostics import REPORT_REL as MODULE_REPORT_REL
from xinyu_stage11_voice_ingress_diagnostics import STATE_REL as MODULE_STATE_REL
from xinyu_stage11_voice_ingress_diagnostics import TRACE_REL as MODULE_TRACE_REL
from xinyu_stage11_voice_ingress_diagnostics import VOICE_TRACE_RELS as MODULE_VOICE_TRACE_RELS
from xinyu_stage11_voice_ingress_diagnostics_store import QQ_RICH_TRACE_REL
from xinyu_stage11_voice_ingress_diagnostics_store import QQ_TRACE_REL
from xinyu_stage11_voice_ingress_diagnostics_store import REPORT_REL
from xinyu_stage11_voice_ingress_diagnostics_store import STATE_REL
from xinyu_stage11_voice_ingress_diagnostics_store import TRACE_REL
from xinyu_stage11_voice_ingress_diagnostics_store import VOICE_TRACE_RELS
from xinyu_stage11_voice_ingress_diagnostics_store import append_stage11_voice_trace_event
from xinyu_stage11_voice_ingress_diagnostics_store import count_stage11_voice_jsonl_lines
from xinyu_stage11_voice_ingress_diagnostics_store import read_stage11_voice_jsonl_tail
from xinyu_stage11_voice_ingress_diagnostics_store import read_stage11_voice_transcript_rows
from xinyu_stage11_voice_ingress_diagnostics_store import stage11_voice_qq_rich_trace_path
from xinyu_stage11_voice_ingress_diagnostics_store import stage11_voice_qq_trace_path
from xinyu_stage11_voice_ingress_diagnostics_store import stage11_voice_report_path
from xinyu_stage11_voice_ingress_diagnostics_store import stage11_voice_state_path
from xinyu_stage11_voice_ingress_diagnostics_store import stage11_voice_trace_path
from xinyu_stage11_voice_ingress_diagnostics_store import stage11_voice_trace_path_for
from xinyu_stage11_voice_ingress_diagnostics_store import write_stage11_voice_report_text
from xinyu_stage11_voice_ingress_diagnostics_store import write_stage11_voice_state_text


def test_stage11_voice_store_exports_legacy_paths() -> None:
    assert REPORT_REL == MODULE_REPORT_REL
    assert STATE_REL == MODULE_STATE_REL
    assert TRACE_REL == MODULE_TRACE_REL
    assert QQ_TRACE_REL == MODULE_QQ_TRACE_REL
    assert QQ_RICH_TRACE_REL == MODULE_QQ_RICH_TRACE_REL
    assert VOICE_TRACE_RELS == MODULE_VOICE_TRACE_RELS
    assert REPORT_REL == Path("worklog/xinyu-stage11-voice-ingress-diagnostics-latest.md")
    assert VOICE_TRACE_RELS[0] == Path("runtime/voice_input_trace.jsonl")


def test_stage11_voice_store_resolves_paths(tmp_path: Path) -> None:
    assert stage11_voice_qq_trace_path(tmp_path) == tmp_path.resolve() / QQ_TRACE_REL
    assert stage11_voice_qq_rich_trace_path(tmp_path) == tmp_path.resolve() / QQ_RICH_TRACE_REL
    assert stage11_voice_trace_path_for(tmp_path, VOICE_TRACE_RELS[0]) == tmp_path.resolve() / VOICE_TRACE_RELS[0]
    assert stage11_voice_report_path(tmp_path) == tmp_path.resolve() / REPORT_REL
    assert stage11_voice_state_path(tmp_path) == tmp_path.resolve() / STATE_REL
    assert stage11_voice_trace_path(tmp_path) == tmp_path.resolve() / TRACE_REL


def test_stage11_voice_store_reads_jsonl_tail_and_counts_total_lines(tmp_path: Path) -> None:
    path = tmp_path / QQ_TRACE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    older = {"arrival_seq": 1}
    recent = {"arrival_seq": 2, "voice_count": 1}
    newest = {"arrival_seq": 3, "voice_count": 0}
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

    rows, total = read_stage11_voice_jsonl_tail(path, max_lines=4)

    assert read_stage11_voice_jsonl_tail(tmp_path / "missing.jsonl", max_lines=2) == ([], 0)
    assert rows == [recent, newest]
    assert total == 5
    assert count_stage11_voice_jsonl_lines(path) == 5
    assert count_stage11_voice_jsonl_lines(tmp_path / "missing.jsonl") == 0


def test_stage11_voice_store_reads_transcript_rows_with_trace_origin(tmp_path: Path) -> None:
    first_path = tmp_path / VOICE_TRACE_RELS[0]
    second_path = tmp_path / VOICE_TRACE_RELS[1]
    first_path.parent.mkdir(parents=True, exist_ok=True)
    first_path.write_text(
        json.dumps({"event_id": "old"}, ensure_ascii=False)
        + "\n"
        + json.dumps({"event_id": "recent"}, ensure_ascii=False)
        + "\n",
        encoding="utf-8",
    )
    second_path.write_text(json.dumps({"event_id": "speech"}, ensure_ascii=False) + "\n", encoding="utf-8")

    rows, file_count, line_count = read_stage11_voice_transcript_rows(tmp_path, max_lines=1)

    assert file_count == 2
    assert line_count == 3
    assert rows == [
        {"event_id": "recent", "_trace_rel": VOICE_TRACE_RELS[0].as_posix()},
        {"event_id": "speech", "_trace_rel": VOICE_TRACE_RELS[1].as_posix()},
    ]


def test_stage11_voice_store_writes_report_and_state(tmp_path: Path) -> None:
    relative = write_stage11_voice_report_text(tmp_path, "# Report\n", output=Path("custom/report.md"))
    absolute = write_stage11_voice_report_text(tmp_path, "# Absolute\n", output=tmp_path / "abs.md")
    state = write_stage11_voice_state_text(tmp_path, "# State\n")

    assert relative == tmp_path.resolve() / "custom/report.md"
    assert absolute == tmp_path / "abs.md"
    assert state == tmp_path.resolve() / STATE_REL
    assert relative.read_text(encoding="utf-8") == "# Report\n"
    assert absolute.read_text(encoding="utf-8") == "# Absolute\n"
    assert state.read_text(encoding="utf-8") == "# State\n"


def test_stage11_voice_store_appends_compact_sorted_trace(tmp_path: Path) -> None:
    path = append_stage11_voice_trace_event(tmp_path, {"b": 2, "a": "value"})

    assert path == tmp_path.resolve() / TRACE_REL
    assert path.read_text(encoding="utf-8") == '{"a":"value","b":2}\n'

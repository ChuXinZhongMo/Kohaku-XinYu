from __future__ import annotations

import json
from pathlib import Path

from xinyu_dialogue_archive import dialogue_archive_path
from xinyu_short_term_recall_diagnostics import REPORT_REL as MODULE_REPORT_REL
from xinyu_short_term_recall_diagnostics import SHORT_TRACE_REL as MODULE_SHORT_TRACE_REL
from xinyu_short_term_recall_diagnostics import STATE_REL as MODULE_STATE_REL
from xinyu_short_term_recall_diagnostics import TRACE_REL as MODULE_TRACE_REL
from xinyu_short_term_recall_diagnostics import WORKING_MEMORY_DIR_REL as MODULE_WORKING_MEMORY_DIR_REL
from xinyu_short_term_recall_diagnostics_store import REPORT_REL
from xinyu_short_term_recall_diagnostics_store import SHORT_TRACE_REL
from xinyu_short_term_recall_diagnostics_store import STATE_REL
from xinyu_short_term_recall_diagnostics_store import TRACE_REL
from xinyu_short_term_recall_diagnostics_store import WORKING_MEMORY_DIR_REL
from xinyu_short_term_recall_diagnostics_store import append_short_term_recall_trace_event
from xinyu_short_term_recall_diagnostics_store import read_json
from xinyu_short_term_recall_diagnostics_store import read_jsonl_tail
from xinyu_short_term_recall_diagnostics_store import read_short_term_recall_prompt_report
from xinyu_short_term_recall_diagnostics_store import read_short_term_recall_trace_tail
from xinyu_short_term_recall_diagnostics_store import short_term_recall_prompt_report_path
from xinyu_short_term_recall_diagnostics_store import short_term_recall_report_path
from xinyu_short_term_recall_diagnostics_store import short_term_recall_short_trace_path
from xinyu_short_term_recall_diagnostics_store import short_term_recall_state_path
from xinyu_short_term_recall_diagnostics_store import short_term_recall_storage_stats
from xinyu_short_term_recall_diagnostics_store import short_term_recall_trace_path
from xinyu_short_term_recall_diagnostics_store import short_term_recall_working_memory_dir
from xinyu_short_term_recall_diagnostics_store import write_short_term_recall_report_text
from xinyu_short_term_recall_diagnostics_store import write_short_term_recall_state_text


def test_short_term_recall_store_exports_legacy_paths() -> None:
    assert SHORT_TRACE_REL == MODULE_SHORT_TRACE_REL
    assert WORKING_MEMORY_DIR_REL == MODULE_WORKING_MEMORY_DIR_REL
    assert STATE_REL == MODULE_STATE_REL
    assert REPORT_REL == MODULE_REPORT_REL
    assert TRACE_REL == MODULE_TRACE_REL
    assert SHORT_TRACE_REL == Path("runtime/short_term_continuity_trace.jsonl")
    assert WORKING_MEMORY_DIR_REL == Path("runtime/dialogue_working_memory")


def test_short_term_recall_store_reads_json_and_jsonl_safely(tmp_path: Path) -> None:
    assert read_json(tmp_path / "missing.json") == {}
    assert read_jsonl_tail(tmp_path / "missing.jsonl", max_lines=10) == []
    assert read_short_term_recall_trace_tail(tmp_path, max_lines=10) == []
    assert read_short_term_recall_prompt_report(tmp_path) == {}

    prompt_path = short_term_recall_prompt_report_path(tmp_path)
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text("\ufeff{\"turn_id\":\"turn-store\"}", encoding="utf-8")
    assert read_short_term_recall_prompt_report(tmp_path) == {"turn_id": "turn-store"}
    prompt_path.write_text("[1, 2]", encoding="utf-8")
    assert read_short_term_recall_prompt_report(tmp_path) == {}

    trace_path = short_term_recall_short_trace_path(tmp_path)
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    trace_path.write_text(
        "\ufeff" + "\n".join(["{bad", '{"seq":1}', '{"seq":2}', '{"seq":3}']) + "\n",
        encoding="utf-8",
    )
    assert read_short_term_recall_trace_tail(tmp_path, max_lines=2) == [{"seq": 2}, {"seq": 3}]


def test_short_term_recall_store_reports_storage_stats_and_sqlite_failures(tmp_path: Path) -> None:
    working_dir = short_term_recall_working_memory_dir(tmp_path)
    working_dir.mkdir(parents=True)
    (working_dir / "a.jsonl").write_text("\ufeff{}\n\n{}\n", encoding="utf-8")
    (working_dir / "b.jsonl").write_text("{}\n", encoding="utf-8")
    archive_path = dialogue_archive_path(tmp_path)
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    archive_path.write_text("not sqlite", encoding="utf-8")

    stats = short_term_recall_storage_stats(tmp_path)

    assert stats["working_memory_file_count"] == 2
    assert stats["working_memory_row_count"] == 3
    assert stats["archive_db_exists"] is True
    assert stats["archive_message_count"] == 0


def test_short_term_recall_store_writes_report_with_output_resolution(tmp_path: Path) -> None:
    relative = write_short_term_recall_report_text(tmp_path, "# Recall\n", output=Path("custom/report.md"))
    absolute = write_short_term_recall_report_text(tmp_path, "# Absolute\n", output=tmp_path / "abs.md")

    assert short_term_recall_report_path(tmp_path) == tmp_path / REPORT_REL
    assert relative == tmp_path / "custom/report.md"
    assert absolute == tmp_path / "abs.md"
    assert relative.read_text(encoding="utf-8") == "# Recall\n"
    assert absolute.read_text(encoding="utf-8") == "# Absolute\n"


def test_short_term_recall_store_writes_state_and_compact_trace(tmp_path: Path) -> None:
    state_path = write_short_term_recall_state_text(tmp_path, "# State\n- status: pass\n")
    trace_path = append_short_term_recall_trace_event(
        tmp_path,
        {"generated_at": "2026-06-10T09:00:00+08:00", "status": "pass"},
    )

    assert state_path == short_term_recall_state_path(tmp_path)
    assert state_path == tmp_path / STATE_REL
    assert state_path.read_text(encoding="utf-8") == "# State\n- status: pass\n"
    assert trace_path == short_term_recall_trace_path(tmp_path)
    assert trace_path == tmp_path / TRACE_REL
    trace_text = trace_path.read_text(encoding="utf-8")
    assert trace_text == '{"generated_at":"2026-06-10T09:00:00+08:00","status":"pass"}\n'
    assert [json.loads(line) for line in trace_text.splitlines()] == [
        {"generated_at": "2026-06-10T09:00:00+08:00", "status": "pass"}
    ]

from __future__ import annotations

from pathlib import Path

from xinyu_bridge_learning_codex_reports_store import codex_report_is_file
from xinyu_bridge_learning_codex_reports_store import codex_report_mtime
from xinyu_bridge_learning_codex_reports_store import read_codex_report_text
from xinyu_bridge_learning_codex_reports_store import read_codex_report_text_for_update
from xinyu_bridge_learning_codex_reports_store import write_codex_report_text


def test_codex_report_store_text_roundtrip_and_stat(tmp_path: Path) -> None:
    path = tmp_path / "outbox/codex-report.md"

    assert codex_report_is_file(path) is False

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# Report\n", encoding="utf-8-sig")

    assert codex_report_is_file(path) is True
    assert codex_report_mtime(path) > 0
    assert read_codex_report_text(path) == "# Report\n"
    assert read_codex_report_text_for_update(path) == (True, "# Report")


def test_codex_report_store_write_returns_status(tmp_path: Path) -> None:
    path = tmp_path / "memory/knowledge/source_materials.md"

    assert write_codex_report_text(path, "# Source Materials\n") is False

    path.parent.mkdir(parents=True, exist_ok=True)
    assert write_codex_report_text(path, "# Source Materials\n") is True
    assert path.read_text(encoding="utf-8") == "# Source Materials\n"


def test_codex_report_store_update_read_missing_returns_false(tmp_path: Path) -> None:
    assert read_codex_report_text_for_update(tmp_path / "missing.md") == (False, "")

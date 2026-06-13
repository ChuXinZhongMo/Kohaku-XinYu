from __future__ import annotations

from pathlib import Path

from xinyu_voice_style_sampler import SAMPLE_REPORT_REL as MODULE_SAMPLE_REPORT_REL
from xinyu_voice_style_sampler_store import SAMPLE_REPORT_REL
from xinyu_voice_style_sampler_store import voice_style_sample_report_path
from xinyu_voice_style_sampler_store import write_voice_style_sample_report_text


def test_voice_style_sampler_store_exports_legacy_path(tmp_path: Path) -> None:
    assert SAMPLE_REPORT_REL == MODULE_SAMPLE_REPORT_REL
    assert SAMPLE_REPORT_REL == Path("memory/self/voice_style_sample_report.md")
    assert voice_style_sample_report_path(tmp_path) == tmp_path / SAMPLE_REPORT_REL


def test_voice_style_sampler_store_writes_exact_text(tmp_path: Path) -> None:
    path = write_voice_style_sample_report_text(tmp_path, "# Voice Style Sample Report\n- status: public\n")

    assert path == tmp_path / SAMPLE_REPORT_REL
    assert path.read_text(encoding="utf-8") == "# Voice Style Sample Report\n- status: public\n"

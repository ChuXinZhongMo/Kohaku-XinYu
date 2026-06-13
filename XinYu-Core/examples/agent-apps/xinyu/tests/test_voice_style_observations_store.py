from __future__ import annotations

from pathlib import Path

from xinyu_voice_style_observations import OBSERVATIONS_REL as MODULE_OBSERVATIONS_REL
from xinyu_voice_style_observations_store import OBSERVATIONS_REL
from xinyu_voice_style_observations_store import voice_style_observations_path
from xinyu_voice_style_observations_store import write_voice_style_observations_text


def test_voice_style_observations_store_exports_legacy_path(tmp_path: Path) -> None:
    assert OBSERVATIONS_REL == MODULE_OBSERVATIONS_REL
    assert OBSERVATIONS_REL == Path("memory/self/voice_style_observations.md")
    assert voice_style_observations_path(tmp_path) == tmp_path / OBSERVATIONS_REL


def test_voice_style_observations_store_writes_exact_text(tmp_path: Path) -> None:
    path = write_voice_style_observations_text(tmp_path, "# Voice Style Observations\n- status: public\n")

    assert path == tmp_path / OBSERVATIONS_REL
    assert path.read_text(encoding="utf-8") == "# Voice Style Observations\n- status: public\n"

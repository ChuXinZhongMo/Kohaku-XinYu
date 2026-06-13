from __future__ import annotations

from pathlib import Path

from xinyu_persona_health_report import DIMENSIONS_REL as MODULE_DIMENSIONS_REL
from xinyu_persona_health_report import EVAL_CASES_REL as MODULE_EVAL_CASES_REL
from xinyu_persona_health_report import EVOLUTION_REL as MODULE_EVOLUTION_REL
from xinyu_persona_health_report import GROWTH_LOG_REL as MODULE_GROWTH_LOG_REL
from xinyu_persona_health_report import PROFILE_REL as MODULE_PROFILE_REL
from xinyu_persona_health_report import REFLECTION_LOG_REL as MODULE_REFLECTION_LOG_REL
from xinyu_persona_health_report import REPORT_REL as MODULE_REPORT_REL
from xinyu_persona_health_report import SELF_REVIEW_REL as MODULE_SELF_REVIEW_REL
from xinyu_persona_health_report import TRIAL_FEEDBACK_REL as MODULE_TRIAL_FEEDBACK_REL
from xinyu_persona_health_report_store import DIMENSIONS_REL
from xinyu_persona_health_report_store import EVAL_CASES_REL
from xinyu_persona_health_report_store import EVOLUTION_REL
from xinyu_persona_health_report_store import GROWTH_LOG_REL
from xinyu_persona_health_report_store import PROFILE_REL
from xinyu_persona_health_report_store import REFLECTION_LOG_REL
from xinyu_persona_health_report_store import REPORT_REL
from xinyu_persona_health_report_store import SELF_REVIEW_REL
from xinyu_persona_health_report_store import TRIAL_FEEDBACK_REL
from xinyu_persona_health_report_store import persona_health_report_path
from xinyu_persona_health_report_store import persona_health_source_path
from xinyu_persona_health_report_store import read_persona_health_source_text
from xinyu_persona_health_report_store import read_persona_health_text
from xinyu_persona_health_report_store import write_persona_health_report_text


def test_persona_health_store_exports_legacy_paths() -> None:
    assert REPORT_REL == MODULE_REPORT_REL
    assert DIMENSIONS_REL == MODULE_DIMENSIONS_REL
    assert EVAL_CASES_REL == MODULE_EVAL_CASES_REL
    assert PROFILE_REL == MODULE_PROFILE_REL
    assert EVOLUTION_REL == MODULE_EVOLUTION_REL
    assert SELF_REVIEW_REL == MODULE_SELF_REVIEW_REL
    assert TRIAL_FEEDBACK_REL == MODULE_TRIAL_FEEDBACK_REL
    assert GROWTH_LOG_REL == MODULE_GROWTH_LOG_REL
    assert REFLECTION_LOG_REL == MODULE_REFLECTION_LOG_REL
    assert REPORT_REL == Path("worklog/xinyu-persona-health-latest.md")


def test_persona_health_store_resolves_paths(tmp_path: Path) -> None:
    root = tmp_path.resolve()

    assert persona_health_report_path(tmp_path) == tmp_path / REPORT_REL
    assert persona_health_report_path(Path("relative-root")) == Path("relative-root") / REPORT_REL
    assert persona_health_source_path(tmp_path, "dimensions") == root / DIMENSIONS_REL
    assert persona_health_source_path(tmp_path, "reflection_log") == root / REFLECTION_LOG_REL


def test_persona_health_store_reads_text_with_original_utf8_limit(tmp_path: Path) -> None:
    path = tmp_path / "memory/self/personality_dimensions.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("abcdef", encoding="utf-8")

    assert read_persona_health_text(path, limit=3) == "abc"
    assert read_persona_health_text(tmp_path / "missing.md") == ""
    assert read_persona_health_source_text(tmp_path, "dimensions", limit=4) == "abcd"


def test_persona_health_store_writes_report(tmp_path: Path) -> None:
    path = write_persona_health_report_text(tmp_path, "# Persona\n")

    assert path == tmp_path / REPORT_REL
    assert path.read_text(encoding="utf-8") == "# Persona\n"

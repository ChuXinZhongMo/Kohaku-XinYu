from __future__ import annotations

from pathlib import Path

from xinyu_memory_health_report import REPORT_REL as MODULE_REPORT_REL
from xinyu_memory_health_report import STAGE8_DUPLICATE_CONSOLIDATION_STATE_REL as MODULE_DUPLICATE_STATE_REL
from xinyu_memory_health_report import STAGE8_LEARNING_TRIAL_VALIDATION_STATE_REL as MODULE_LEARNING_STATE_REL
from xinyu_memory_health_report import STAGE8_STATE_REL as MODULE_STAGE8_STATE_REL
from xinyu_memory_health_report_store import MEMORY_HEALTH_SOURCE_RELS
from xinyu_memory_health_report_store import REPORT_REL
from xinyu_memory_health_report_store import STAGE8_DUPLICATE_CONSOLIDATION_STATE_REL
from xinyu_memory_health_report_store import STAGE8_LEARNING_TRIAL_VALIDATION_STATE_REL
from xinyu_memory_health_report_store import STAGE8_STATE_REL
from xinyu_memory_health_report_store import memory_health_report_path
from xinyu_memory_health_report_store import memory_health_source_path
from xinyu_memory_health_report_store import read_memory_health_source_text
from xinyu_memory_health_report_store import read_memory_health_text
from xinyu_memory_health_report_store import stage8_duplicate_consolidation_state_path
from xinyu_memory_health_report_store import stage8_learning_trial_validation_state_path
from xinyu_memory_health_report_store import stage8_memory_governance_state_path
from xinyu_memory_health_report_store import write_memory_health_report_text
from xinyu_memory_health_report_store import write_stage8_memory_governance_state_text


def test_memory_health_store_exports_legacy_paths() -> None:
    assert REPORT_REL == MODULE_REPORT_REL
    assert STAGE8_STATE_REL == MODULE_STAGE8_STATE_REL
    assert STAGE8_DUPLICATE_CONSOLIDATION_STATE_REL == MODULE_DUPLICATE_STATE_REL
    assert STAGE8_LEARNING_TRIAL_VALIDATION_STATE_REL == MODULE_LEARNING_STATE_REL
    assert REPORT_REL == Path("worklog/xinyu-memory-health-latest.md")
    assert STAGE8_STATE_REL == Path("memory/context/stage8_memory_governance_state.md")


def test_memory_health_store_resolves_paths_preserving_report_semantics(tmp_path: Path) -> None:
    root = tmp_path.resolve()

    assert memory_health_report_path(root) == root / REPORT_REL
    assert memory_health_report_path(root, Path("custom/report.md")) == root / "custom/report.md"
    assert memory_health_report_path(root, root / "absolute.md") == root / "absolute.md"
    assert memory_health_report_path(Path("relative-root")) == Path("relative-root/relative-root") / REPORT_REL
    assert stage8_memory_governance_state_path(tmp_path) == root / STAGE8_STATE_REL
    assert stage8_duplicate_consolidation_state_path(tmp_path) == root / STAGE8_DUPLICATE_CONSOLIDATION_STATE_REL
    assert stage8_learning_trial_validation_state_path(tmp_path) == root / STAGE8_LEARNING_TRIAL_VALIDATION_STATE_REL


def test_memory_health_store_reads_text_with_original_utf8_limit(tmp_path: Path) -> None:
    path = tmp_path / "state.md"
    path.write_text("abcdef", encoding="utf-8")

    assert read_memory_health_text(path, limit=3) == "abc"
    assert read_memory_health_text(tmp_path / "missing.md") == ""


def test_memory_health_store_reads_named_sources(tmp_path: Path) -> None:
    source = tmp_path / MEMORY_HEALTH_SOURCE_RELS["learning_closed_loop"]
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("# Learning\n", encoding="utf-8")

    assert memory_health_source_path(tmp_path, "learning_closed_loop") == source
    assert read_memory_health_source_text(tmp_path, "learning_closed_loop") == "# Learning\n"


def test_memory_health_store_writes_report_and_stage8_state(tmp_path: Path) -> None:
    report_path = write_memory_health_report_text(tmp_path, "# Report\n")
    custom_path = write_memory_health_report_text(tmp_path, "# Custom\n", output=Path("custom/report.md"))
    state_path = write_stage8_memory_governance_state_text(tmp_path, "# State\n")

    assert report_path == tmp_path / REPORT_REL
    assert custom_path == tmp_path / "custom/report.md"
    assert state_path == tmp_path.resolve() / STAGE8_STATE_REL
    assert report_path.read_text(encoding="utf-8") == "# Report\n"
    assert custom_path.read_text(encoding="utf-8") == "# Custom\n"
    assert state_path.read_text(encoding="utf-8") == "# State\n"

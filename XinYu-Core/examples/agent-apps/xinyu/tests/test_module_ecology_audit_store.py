from __future__ import annotations

from pathlib import Path

from xinyu_module_ecology_audit import SKIP_SCAN_DIRS as MODULE_SKIP_SCAN_DIRS
from xinyu_module_ecology_audit import SKIP_SCAN_PREFIXES as MODULE_SKIP_SCAN_PREFIXES
from xinyu_module_ecology_audit_store import SKIP_SCAN_DIRS
from xinyu_module_ecology_audit_store import SKIP_SCAN_PREFIXES
from xinyu_module_ecology_audit_store import collect_module_ecology_paths
from xinyu_module_ecology_audit_store import read_module_ecology_reference_sources
from xinyu_module_ecology_audit_store import read_module_ecology_status_file
from xinyu_module_ecology_audit_store import write_module_ecology_output


def test_module_ecology_audit_store_exports_legacy_scan_rules() -> None:
    assert SKIP_SCAN_DIRS == MODULE_SKIP_SCAN_DIRS
    assert SKIP_SCAN_PREFIXES == MODULE_SKIP_SCAN_PREFIXES
    assert "memory" in SKIP_SCAN_DIRS
    assert ("ops", "reports") in SKIP_SCAN_PREFIXES


def test_collect_module_ecology_paths_skips_private_and_report_bodies(tmp_path: Path) -> None:
    (tmp_path / "xinyu_scene_frame.py").write_text("def build_scene_frame(): pass\n", encoding="utf-8")
    (tmp_path / "memory/context").mkdir(parents=True)
    (tmp_path / "memory/context/private.md").write_text("secret body\n", encoding="utf-8")
    (tmp_path / "ops/reports").mkdir(parents=True)
    (tmp_path / "ops/reports/module_ecology.md").write_text("generated report\n", encoding="utf-8")
    (tmp_path / "ops/probes").mkdir(parents=True)
    (tmp_path / "ops/probes/check.py").write_text("print('ok')\n", encoding="utf-8")

    paths = collect_module_ecology_paths(tmp_path, max_items=20)

    assert paths == ["ops/probes/check.py", "xinyu_scene_frame.py"]


def test_read_module_ecology_reference_sources_reads_bom_safe_text(tmp_path: Path) -> None:
    (tmp_path / "xinyu_scene_frame.py").write_text("\ufeffdef build_scene_frame(): pass\n", encoding="utf-8")
    (tmp_path / "broken").mkdir()

    sources = read_module_ecology_reference_sources(tmp_path)

    assert sources == [("xinyu_scene_frame.py", "def build_scene_frame(): pass\n")]


def test_module_ecology_store_reads_status_file_with_bom(tmp_path: Path) -> None:
    status = tmp_path / "status.txt"
    status.write_text("\ufeff D old_smoke.py\n", encoding="utf-8")

    assert read_module_ecology_status_file(status) == " D old_smoke.py\n"


def test_module_ecology_store_writes_output_with_parent_creation(tmp_path: Path) -> None:
    output = tmp_path / "reports" / "module_ecology.md"

    write_module_ecology_output(output, "# Report\n")

    assert output.read_text(encoding="utf-8") == "# Report\n"

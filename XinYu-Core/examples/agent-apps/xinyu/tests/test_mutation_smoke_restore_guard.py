from __future__ import annotations

import sys
from pathlib import Path


OPS_VALIDATION = Path(__file__).resolve().parents[1] / "ops" / "validation"
if str(OPS_VALIDATION) not in sys.path:
    sys.path.insert(0, str(OPS_VALIDATION))

from mutation_smoke_restore_guard import build_restore_guard_report, inspect_smoke, render_markdown  # noqa: E402


def test_inspect_smoke_detects_restore_and_diff_suppression(tmp_path: Path) -> None:
    app = tmp_path / "app"
    smoke = app / "tests/smoke/learning/integration/example_smoke.py"
    smoke.parent.mkdir(parents=True)
    smoke.write_text(
        """
def _snapshot(): pass
def _restore_snapshot(): pass
TRACKED_FILES = []
print("=== MUTATION SUMMARY ===")
parser.add_argument("--restore-after", action="store_true")
parser.add_argument("--diff-lines", type=int, default=120)
""",
        encoding="utf-8",
    )

    entry = inspect_smoke(smoke, app_root=app)

    assert entry["mutation_capable"] is True
    assert entry["supports_restore_after"] is True
    assert entry["supports_diff_lines"] is True
    assert entry["recommended_args"] == ["--restore-after", "--diff-lines", "0"]


def test_restore_guard_report_does_not_need_memory_files(tmp_path: Path) -> None:
    app = tmp_path / "app"
    smoke_dir = Path("tests/smoke/learning/integration")
    (app / smoke_dir).mkdir(parents=True)
    (app / smoke_dir / "safe_smoke.py").write_text("print('no mutation')\n", encoding="utf-8")
    (app / smoke_dir / "mutating_smoke.py").write_text(
        """
def _snapshot(): pass
TRACKED_FILES = []
print("=== MUTATION SUMMARY ===")
""",
        encoding="utf-8",
    )

    report = build_restore_guard_report(app, smoke_dirs=(smoke_dir,))

    assert report["total_smokes"] == 2
    assert report["mutation_capable_count"] == 1
    assert report["missing_restore_count"] == 1
    assert "memory bodies" in report["privacy_note"]
    assert "mutating_smoke.py" in render_markdown(report)

from __future__ import annotations

import sys
from pathlib import Path


OPS_VALIDATION = Path(__file__).resolve().parents[1] / "ops" / "validation"
if str(OPS_VALIDATION) not in sys.path:
    sys.path.insert(0, str(OPS_VALIDATION))

from live_memory_recall_boundary_audit import (  # noqa: E402
    build_live_memory_recall_boundary_audit,
    render_markdown,
)


def test_live_memory_recall_boundary_passes_when_only_owner_imports_provider(tmp_path: Path) -> None:
    app = tmp_path / "XinYu-Core/examples/agent-apps/xinyu"
    app.mkdir(parents=True)
    (app / "xinyu_context_retrieval.py").write_text("def retrieve_recalled_context(): pass\n", encoding="utf-8")
    (app / "xinyu_living_memory_recall.py").write_text(
        "from xinyu_context_retrieval import retrieve_recalled_context\n"
        "def run_living_memory_recall_algorithm(): pass\n",
        encoding="utf-8",
    )
    (app / "xinyu_core_bridge.py").write_text(
        "from xinyu_living_memory_recall import run_living_memory_recall_algorithm\n"
        "run_living_memory_recall_algorithm()\n",
        encoding="utf-8",
    )

    audit = build_live_memory_recall_boundary_audit(tmp_path)

    assert audit["status"] == "pass"
    assert audit["provider_importers_outside_owner"] == []
    assert audit["canonical_importers"] == ["xinyu_core_bridge"]
    assert audit["runtime_entrypoints"]["run_living_memory_recall_algorithm"] == [
        "xinyu_core_bridge.py:1",
        "xinyu_core_bridge.py:2",
        "xinyu_living_memory_recall.py:2",
    ]


def test_live_memory_recall_boundary_flags_old_direct_provider_import(tmp_path: Path) -> None:
    app = tmp_path / "XinYu-Core/examples/agent-apps/xinyu"
    app.mkdir(parents=True)
    (app / "xinyu_context_retrieval.py").write_text("def retrieve_recalled_context(): pass\n", encoding="utf-8")
    (app / "xinyu_living_memory_recall.py").write_text(
        "from xinyu_context_retrieval import retrieve_recalled_context\n",
        encoding="utf-8",
    )
    (app / "xinyu_old_live_path.py").write_text(
        "import xinyu_context_retrieval\n"
        "xinyu_context_retrieval.retrieve_recalled_context()\n",
        encoding="utf-8",
    )

    audit = build_live_memory_recall_boundary_audit(tmp_path)

    assert audit["status"] == "fail"
    assert audit["provider_importers_outside_owner"] == ["xinyu_old_live_path"]


def test_live_memory_recall_boundary_report_is_privacy_safe() -> None:
    rendered = render_markdown(
        {
            "status": "pass",
            "canonical_owner": "xinyu_living_memory_recall.run_living_memory_recall_algorithm",
            "provider_module": "xinyu_context_retrieval",
            "provider_role": "provider/compatibility",
            "privacy_note": "Scans Python source paths/imports only; does not read memory bodies.",
            "provider_importers_outside_owner": [],
            "canonical_importers": ["xinyu_core_bridge"],
            "runtime_entrypoints": {"run_living_memory_recall_algorithm": ["xinyu_core_bridge.py:10"]},
        }
    )

    assert "Live Memory Recall Boundary Audit" in rendered
    assert "provider/compatibility" in rendered
    assert "does not read memory bodies" in rendered

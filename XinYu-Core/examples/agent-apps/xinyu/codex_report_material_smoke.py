from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from xinyu_bridge_learning import stage_codex_report_material


ROOT = Path(__file__).resolve().parent


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _prepare_root(root: Path) -> None:
    _write(
        root / "memory/knowledge/source_integration_gate_state.md",
        """---
title: Source Integration Gate State
memory_type: source_integration_gate_state
status: active
---

# Source Integration Gate State

## Gate Decision
- integration_permission: prepare_only
- gate_reason: smoke_codex_report_ready
""",
    )
    _write(
        root / "memory/knowledge/general.md",
        """---
title: General Knowledge
memory_type: general
status: active
---

# General Knowledge
""",
    )


def main() -> int:
    custom = ROOT / "custom"
    if str(custom) not in sys.path:
        sys.path.insert(0, str(custom))
    from learner_integration_engine import run_learner_integration

    with tempfile.TemporaryDirectory(prefix="xinyu-codex-report-material-") as tmp:
        root = Path(tmp)
        _prepare_root(root)
        report = root / "outbox" / "codex-smoke-report.md"
        _write(
            report,
            """# Codex Report

## Learning Triage

中文抽取应该保持可读，并且 Codex 搜索报告需要进入 source material，后续才可以变成可复用知识。
""",
        )
        staged = stage_codex_report_material(
            root,
            report_path=str(report),
            task_text="搜索中文资料并整理学习笔记",
            job_id="codex-smoke",
        )
        material_id = str(staged.get("material_id") or "")
        learner = run_learner_integration(root, mode="codex_report_material_smoke")
        source_materials = (root / "memory/knowledge/source_materials.md").read_text(encoding="utf-8-sig")
        general = (root / "memory/knowledge/general.md").read_text(encoding="utf-8-sig")
        report_text = report.read_text(encoding="utf-8-sig")

        checks = {
            "material_id": material_id.startswith("material-"),
            "source_material_recorded": f"## {material_id}" in source_materials,
            "codex_report_key_recorded": "- codex_report_key: " in source_materials,
            "report_backfilled": f"- material_id: {material_id}" in report_text,
            "learner_integrated": int(learner.get("newly_integrated_materials") or 0) == 1,
            "general_reusable": f"- source_material: {material_id}" in general,
            "chinese_preserved": "中文抽取应该保持可读" in general,
        }
        print("=== CODEX REPORT MATERIAL SMOKE ===")
        print("material_id:", material_id or "none")
        print("learner_integrated:", learner.get("newly_integrated_materials"))
        for key, value in checks.items():
            print(f"{key}:", "ok" if value else "missing")
        return 0 if all(checks.values()) else 4


if __name__ == "__main__":
    raise SystemExit(main())

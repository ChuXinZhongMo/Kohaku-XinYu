from __future__ import annotations

from pathlib import Path

from xinyu_bridge_learning_codex_reports import stage_codex_report_material


def test_stage_codex_report_material_reports_missing_file(tmp_path: Path) -> None:
    result = stage_codex_report_material(
        tmp_path,
        report_path="outbox/missing-report.md",
        task_text="summarize serviceization plan",
        job_id="codex-job-missing",
        registered_at="2026-06-11T02:00:00+08:00",
    )

    assert result == {
        "material_id": "",
        "registered": False,
        "status": "missing_report",
        "notes": ["codex_report_material_missing"],
    }


def test_stage_codex_report_material_is_idempotent_and_backfills_report(tmp_path: Path) -> None:
    report = tmp_path / "outbox/codex-report.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(
        "# Codex Report\n\n"
        "The offline learning path should keep reusable facts in source materials "
        "without changing stable memory directly.\n",
        encoding="utf-8",
    )

    first = stage_codex_report_material(
        tmp_path,
        report_path="outbox/codex-report.md",
        task_text="summarize serviceization plan",
        job_id="codex-job-123",
        registered_at="2026-06-11T02:01:00+08:00",
    )
    material_id = str(first["material_id"])

    assert first["registered"] is True
    assert first["status"] == "ready"
    assert first["notes"] == ["codex_report_material_staged"]
    assert material_id.startswith("material-")

    source_materials_path = tmp_path / "memory/knowledge/source_materials.md"
    source_materials = source_materials_path.read_text(encoding="utf-8-sig")
    report_text = report.read_text(encoding="utf-8-sig")

    assert f"## {material_id}" in source_materials
    assert "- source_question: summarize serviceization plan" in source_materials
    assert "- url: codex-report://codex-job-123" in source_materials
    assert "- source_type: codex_search_report" in source_materials
    assert "- learning_origin: codex_report" in source_materials
    assert "- codex_report_key: " in source_materials
    assert "- claim: " in source_materials
    assert "## XinYu Learning Registration" in report_text
    assert f"- material_id: {material_id}" in report_text
    assert "- registered_at: 2026-06-11T02:01:00+08:00" in report_text

    second = stage_codex_report_material(
        tmp_path,
        report_path=str(report),
        task_text="summarize serviceization plan again",
        job_id="codex-job-456",
        registered_at="2026-06-11T02:02:00+08:00",
    )

    assert second == {
        "material_id": material_id,
        "registered": False,
        "status": "already_staged",
        "notes": ["codex_report_material_already_staged"],
    }
    assert source_materials_path.read_text(encoding="utf-8-sig").count("- codex_report_key: ") == 1
    assert report.read_text(encoding="utf-8-sig").count("## XinYu Learning Registration") == 1

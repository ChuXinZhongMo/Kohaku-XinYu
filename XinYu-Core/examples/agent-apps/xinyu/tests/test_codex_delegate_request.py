from __future__ import annotations

from pathlib import Path

from xinyu_codex_delegate import _write_request


def test_write_request_preserves_multiline_self_code_task(tmp_path: Path) -> None:
    request_path = tmp_path / "Requests" / "codex-qq-test.md"
    workspace = tmp_path / "Workspace" / "codex-qq-test"
    report_path = workspace / "codex-qq-test-report.md"
    task_text = "\n".join(
        [
            "用 Codex 执行这个已批准的自行动作代码补丁任务。",
            "",
            "Self-code approval id: selfaction-decision-test",
            "Owner-approved Self Action Gateway patch executor task.",
            "Task:",
            "- Inspect the current XinYu app state.",
        ]
    )

    request_path.parent.mkdir(parents=True, exist_ok=True)
    _write_request(
        request_path=request_path,
        task_text=task_text,
        urls=[],
        workspace=workspace,
        report_path=report_path,
        owner_approved=True,
        local_write_approved=True,
    )

    text = request_path.read_text(encoding="utf-8")

    assert "## Goal\n```text\n用 Codex 执行" in text
    assert "\nSelf-code approval id: selfaction-decision-test\n" in text
    assert "\n- Inspect the current XinYu app state.\n```\n\n## Input URLs" in text
    assert "- output_report: " in text

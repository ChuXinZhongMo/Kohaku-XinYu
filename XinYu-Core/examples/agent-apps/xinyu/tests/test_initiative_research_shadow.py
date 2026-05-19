from __future__ import annotations

import json
from pathlib import Path

from xinyu_initiative_research_shadow import (
    InitiativeResearchCase,
    main,
    run_initiative_research_shadow,
)


def test_initiative_research_shadow_passes_without_outward_delivery(tmp_path: Path) -> None:
    report = run_initiative_research_shadow(tmp_path, run_id="research-shadow")
    report_text = (tmp_path / "runtime/initiative_research_shadow_report.json").read_text(encoding="utf-8")
    cases = {case["case_id"]: case for case in report["cases"]}

    assert report["research_gate"]["status"] == "passed"
    assert report["research_gate"]["passed"] is True
    assert report["research_gate"]["counts"]["outward_delivery_count"] == 0
    assert cases["quiet_without_recall_holds"]["status"] == "hold_private"
    assert cases["feedback_with_recall_can_surface_locally"]["status"] == "desktop_inbox"
    assert cases["feedback_with_recall_can_surface_locally"]["delivery_level"] == "dry_run"
    assert cases["feedback_with_recall_can_surface_locally"]["desktop_item_created"] is False
    assert "A grounded follow-up is ready" not in report_text
    assert "queue_owner_private" not in report_text


def test_initiative_research_shadow_uses_isolated_workspace(tmp_path: Path) -> None:
    run_initiative_research_shadow(tmp_path, run_id="isolated")

    assert not (tmp_path / "memory/context/initiative_lifecycle_state.md").exists()
    assert (tmp_path / "runtime/initiative_research_shadow_workspace/isolated/quiet_without_recall_holds").exists()


def test_initiative_research_shadow_gate_fails_on_expected_mismatch(tmp_path: Path) -> None:
    cases = (
        InitiativeResearchCase(
            case_id="bad-expectation",
            scene="casual_chat",
            posture="quiet_by_default",
            recall_count=0,
            expected_status="desktop_inbox",
            expected_recall_support=False,
        ),
    )

    report = run_initiative_research_shadow(tmp_path, cases=cases, run_id="research-fail")

    assert report["research_gate"]["status"] == "failed"
    assert report["research_gate"]["counts"]["mismatch_count"] == 1


def test_initiative_research_shadow_strict_gate_returns_nonzero_on_failure(tmp_path: Path, monkeypatch) -> None:
    def fake_run(root, *, run_id=None):
        return {"research_gate": {"passed": False}}

    monkeypatch.setattr("xinyu_initiative_research_shadow.run_initiative_research_shadow", fake_run)

    assert main(["--root", str(tmp_path), "--run-id", "strict", "--strict-gate"]) == 2


def test_initiative_research_shadow_cli_writes_report(tmp_path: Path) -> None:
    assert main(["--root", str(tmp_path), "--run-id", "cli", "--strict-gate"]) == 0

    report = json.loads((tmp_path / "runtime/initiative_research_shadow_report.json").read_text(encoding="utf-8"))
    assert report["research_gate"]["passed"] is True

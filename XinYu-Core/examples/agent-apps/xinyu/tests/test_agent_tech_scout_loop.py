from __future__ import annotations

import json
from pathlib import Path

from xinyu_agent_tech_scout_loop import run_agent_tech_scout_loop
from xinyu_skill_library import list_skills


def test_scout_loop_respects_disabled(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XINYU_AGENT_TECH_SCOUT", "0")
    result = run_agent_tech_scout_loop(tmp_path, force=False)
    assert result["ok"] is False
    assert result["reason"] == "disabled"


def test_scout_loop_fetch_and_micro_apply(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XINYU_AGENT_TECH_SCOUT", "1")
    monkeypatch.setenv("XINYU_AGENT_TECH_SCOUT_FORCE", "1")
    monkeypatch.setenv("XINYU_AGENT_TECH_SCOUT_AUTO_MICRO_APPLY", "1")
    monkeypatch.setenv("XINYU_DEVICE_RESOURCE_GATE", "0")
    monkeypatch.setenv("XINYU_AGENT_TECH_SCOUT_FETCH", "1")

    # Minimal knowledge files for iteration engines (may no-op safely).
    (tmp_path / "memory" / "knowledge").mkdir(parents=True, exist_ok=True)
    (tmp_path / "memory" / "self").mkdir(parents=True, exist_ok=True)
    (tmp_path / "memory" / "context").mkdir(parents=True, exist_ok=True)
    (tmp_path / "memory" / "knowledge" / "ai_domain.md").write_text("# AI Domain\n", encoding="utf-8")
    (tmp_path / "memory" / "knowledge" / "general.md").write_text("# general\n", encoding="utf-8")
    (tmp_path / "memory" / "context" / "owner_permission_grants.md").write_text(
        "- grant_autonomous_source_collect: approved_bounded_candidate_material_only\n"
        "- grant_ai_self_iteration_review: approved_for_non_stable_planning\n"
        "- grant_agent_tech_scout_full_open: approved_device_bounded_micro_apply\n",
        encoding="utf-8",
    )
    (tmp_path / "memory" / "context" / "capability_zones_state.md").write_text(
        "- autonomous_search_provider: enabled_duckduckgo_html_bounded_ai_domain\n"
        "- ai_self_iteration_review: approved_for_non_stable_planning\n",
        encoding="utf-8",
    )

    def fake_fetch(root, **kwargs):
        return {
            "ok": True,
            "fetched": 1,
            "notes": [],
            "hot_notes": ["最近刷到HN：Kimi K3 https://kimi.com/（公共信息）"],
            "linked_items": [
                {"title": "Kimi K3 Open Frontier", "url": "https://kimi.com/"},
                {"title": "openai/whisper", "url": "https://github.com/openai/whisper"},
            ],
            "urls": ["https://news.ycombinator.com/"],
            "prefer_ai": True,
            "prefer_papers": False,
        }

    monkeypatch.setattr("xinyu_agent_tech_scout_loop.fetch_public_hot_pages", fake_fetch)
    monkeypatch.setattr(
        "xinyu_agent_tech_scout_loop._run_search_activation",
        lambda root, checked_at: {"activation_permission": "provider_allowed"},
    )
    monkeypatch.setattr(
        "xinyu_agent_tech_scout_loop._run_github_learning",
        lambda root, checked_at: {"ok": True, "skipped": True},
    )
    monkeypatch.setattr(
        "xinyu_agent_tech_scout_loop._run_self_iteration",
        lambda root, checked_at: {"gate": {"gate_status": "growth_review_candidate"}, "review": {"proposal_count": 1}},
    )

    result = run_agent_tech_scout_loop(tmp_path, force=True, focus="agent")
    assert result["ok"] is True
    assert result["steps"]["micro_apply"]["applied"] >= 1
    skills = list_skills(tmp_path)
    assert skills
    assert any("agent" in " ".join(s.get("tags") or []).lower() or "scout" in _safe(s.get("skill_id")) for s in skills)
    report_path = tmp_path / "runtime/quality/agent_tech_scout_latest.json"
    assert report_path.is_file()
    data = json.loads(report_path.read_text(encoding="utf-8"))
    assert data.get("linked_items")


def _safe(value) -> str:
    return "" if value is None else str(value)

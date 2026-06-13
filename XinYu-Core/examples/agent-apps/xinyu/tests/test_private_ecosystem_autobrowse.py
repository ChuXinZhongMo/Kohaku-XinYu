from __future__ import annotations

import json
from pathlib import Path

import xinyu_private_ecosystem_grants as grants_mod
from xinyu_browser_control import ACTIONS_REL as BROWSER_ACTIONS_REL
from xinyu_external_plugins import save_external_plugin_control_patch
from xinyu_private_ecosystem import STATE_JSON_REL, load_goal_candidates, run_private_ecosystem_tick
from xinyu_private_ecosystem_journal import read_journal_events


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _enable_browser_plugin(root: Path, *, proactive: bool) -> None:
    save_external_plugin_control_patch(
        root, {"plugin_id": "xinyu_private_browser", "enabled": True, "proactive_enabled": proactive}
    )


def _whitelist(root: Path, urls: list[str]) -> None:
    grants_mod.save_grants_patch(
        root, {"private_browser": {"enabled": True, "read_only": True, "allowed_urls": urls}}
    )


def _bias_browse_goal(root: Path) -> None:
    _write_json(
        root / STATE_JSON_REL,
        {"goals": {"explore_browser_readonly": {"habit_weight": 0.2, "success_count": 1}}},
    )


def _browser_actions(root: Path) -> list[dict]:
    path = root / BROWSER_ACTIONS_REL
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _journal_kinds(root: Path) -> set[str]:
    return {e["event_kind"] for e in read_journal_events(root)}


def _force_no_engine(monkeypatch) -> None:
    # Keep tests offline + fast: never launch a real browser; the native
    # executor falls back to its honest simulated observation.
    def _raise(*args, **kwargs):
        raise RuntimeError("no_engine_in_test")

    monkeypatch.setattr("xinyu_browser_engine_playwright.create_browser_engine", _raise)


# -- goal visibility (unchanged behavior) -----------------------------------
def test_browse_goal_absent_without_whitelist(tmp_path: Path) -> None:
    grants = grants_mod.default_grants(env={})
    grants["private_browser"]["enabled"] = True
    goals = {c.goal_id for c in load_goal_candidates(tmp_path, {"memory_candidate_count": 0}, {}, grants)}
    assert "explore_browser_readonly" not in goals


def test_browse_goal_present_with_whitelist(tmp_path: Path) -> None:
    grants = grants_mod.default_grants(env={})
    grants["private_browser"]["enabled"] = True
    grants["private_browser"]["allowed_urls"] = ["https://example.com/news"]
    goals = {c.goal_id for c in load_goal_candidates(tmp_path, {"memory_candidate_count": 0}, {}, grants)}
    assert "explore_browser_readonly" in goals


def test_browse_goal_disabled_when_grant_off(tmp_path: Path) -> None:
    grants = grants_mod.default_grants(env={})
    grants["private_browser"]["enabled"] = False
    grants["private_browser"]["allowed_urls"] = ["https://example.com/news"]
    goals = {c.goal_id for c in load_goal_candidates(tmp_path, {"memory_candidate_count": 0}, {}, grants)}
    assert "explore_browser_readonly" not in goals


# -- autonomous execution goes through the plugin gate chain -----------------
def test_autobrowse_blocked_when_plugin_disabled(tmp_path: Path) -> None:
    _whitelist(tmp_path, ["https://example.com/news"])  # grant + whitelist, but plugin stays disabled
    _bias_browse_goal(tmp_path)
    result = run_private_ecosystem_tick(tmp_path, checked_at="2026-06-02T10:00:00+08:00", trigger="test")
    assert result["selected_goal_id"] == "explore_browser_readonly"
    assert result["action_status"] == "blocked"
    assert "action_blocked" in _journal_kinds(tmp_path)
    # Native executor never reached -> no browser action recorded.
    assert _browser_actions(tmp_path) == []
    assert result["counters"].get("low_risk_executed", 0) == 0


def test_autobrowse_blocked_when_proactive_disabled(tmp_path: Path) -> None:
    _whitelist(tmp_path, ["https://example.com/news"])
    _enable_browser_plugin(tmp_path, proactive=False)
    _bias_browse_goal(tmp_path)
    result = run_private_ecosystem_tick(tmp_path, checked_at="2026-06-02T10:00:00+08:00", trigger="test")
    assert result["selected_goal_id"] == "explore_browser_readonly"
    assert result["action_status"] == "blocked"
    assert "action_blocked" in _journal_kinds(tmp_path)


def test_autobrowse_executes_with_plugin_and_whitelist(tmp_path: Path, monkeypatch) -> None:
    _force_no_engine(monkeypatch)
    _whitelist(tmp_path, ["https://example.com/news"])
    _enable_browser_plugin(tmp_path, proactive=True)
    _bias_browse_goal(tmp_path)
    result = run_private_ecosystem_tick(tmp_path, checked_at="2026-06-02T10:00:00+08:00", trigger="test")
    assert result["selected_goal_id"] == "explore_browser_readonly"
    assert result["action_status"] == "completed"
    actions = _browser_actions(tmp_path)
    assert any(a["action_kind"] == "navigate_readonly" for a in actions)
    assert "action_executed" in _journal_kinds(tmp_path)
    # No stable memory writes from an autonomous browse.
    assert result["boundaries"]["stable_memory_write"] == "blocked"
    assert result["journal_summary"]["stable_memory_write_count"] == 0


def test_autobrowse_sensitive_url_blocked(tmp_path: Path, monkeypatch) -> None:
    _force_no_engine(monkeypatch)
    _whitelist(tmp_path, ["https://accounts.google.com/login"])  # owner mistakenly whitelisted a credential page
    _enable_browser_plugin(tmp_path, proactive=True)
    _bias_browse_goal(tmp_path)
    result = run_private_ecosystem_tick(tmp_path, checked_at="2026-06-02T10:00:00+08:00", trigger="test")
    assert result["selected_goal_id"] == "explore_browser_readonly"
    # The native executor's run_browser_action blocks the sensitive page.
    assert result["action_status"] == "blocked"
    assert "action_blocked" in _journal_kinds(tmp_path)


def test_autobrowse_no_whitelist_holds(tmp_path: Path) -> None:
    # Browser grant on but allowed_urls empty -> goal never appears; if forced,
    # the observe holds. Here we assert the goal is simply not selected.
    grants_mod.save_grants_patch(tmp_path, {"private_browser": {"enabled": True, "allowed_urls": []}})
    result = run_private_ecosystem_tick(tmp_path, checked_at="2026-06-02T10:00:00+08:00", trigger="test")
    assert result["selected_goal_id"] != "explore_browser_readonly"

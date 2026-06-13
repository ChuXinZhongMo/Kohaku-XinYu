from __future__ import annotations

import json
from pathlib import Path

from xinyu_browser_control import (
    ACTIONS_REL,
    ARTIFACTS_REL,
    SCREENSHOTS_REL,
    build_browser_snapshot,
    cleanup_screenshots,
    classify_browser_action,
    evaluate_browser_action,
    is_sensitive_url,
    run_browser_action,
)


def _grant(**over) -> dict:
    base = {"enabled": True, "read_only": True, "single_step_actions": False}
    base.update(over)
    return base


def _actions(tmp_path: Path) -> list:
    path = tmp_path / ACTIONS_REL
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


class StubBrowserEngine:
    def __init__(self) -> None:
        self.snapshot_calls = 0
        self.extract_calls = 0

    def navigate(self, url: str) -> dict:
        return {"url": url, "status": 200, "ok": True}

    def snapshot_dom(self) -> str:
        self.snapshot_calls += 1
        return "<html><body>dom</body></html>"

    def screenshot(self) -> bytes:
        return b"\x89PNG\r\n\x1a\nstub"

    def extract_text(self) -> str:
        self.extract_calls += 1
        return "visible text"


def test_sensitive_url_detection() -> None:
    assert is_sensitive_url("https://accounts.google.com/login")[0] is True
    assert is_sensitive_url("https://mybank.com/checkout")[0] is True
    assert is_sensitive_url("https://example.com/article/123")[0] is False


def test_read_only_snapshot_runs_and_stores_under_private_paths(tmp_path: Path) -> None:
    result = run_browser_action(
        tmp_path,
        action_kind="snapshot_dom",
        url="https://example.com/news",
        grant=_grant(),
        execute=True,
        evaluated_at="2026-06-02T10:00:00+08:00",
    )
    assert result["ok"] is True
    assert result["result"] in {"completed", "simulated"}
    dom_ref = result["dom_snapshot_ref"]
    assert dom_ref.startswith("runtime/private_ecosystem/browser_artifacts/")
    assert (tmp_path / dom_ref).exists()

    record = _actions(tmp_path)[-1]
    assert record["session_id"] == "xinyu-private-browser"
    assert record["risk"] == "read_only"
    # Structured marker, never parsed from text.
    assert record["last_action_marker"]["type"] == "none"


def test_extract_text_calls_engine_extract_text(tmp_path: Path) -> None:
    engine = StubBrowserEngine()
    result = run_browser_action(
        tmp_path,
        action_kind="extract_text",
        url="https://example.com/news",
        grant=_grant(),
        execute=True,
        engine=engine,
        evaluated_at="2026-06-02T10:00:00+08:00",
    )
    assert result["result"] == "completed"
    assert engine.extract_calls == 1
    assert engine.snapshot_calls == 0
    text_ref = result["dom_snapshot_ref"]
    assert text_ref.startswith(ARTIFACTS_REL.as_posix())
    assert (tmp_path / text_ref).read_text(encoding="utf-8") == "visible text"


def test_click_blocks_without_approval_or_grant(tmp_path: Path) -> None:
    result = run_browser_action(
        tmp_path,
        action_kind="click_element",
        url="https://example.com/news",
        element_id="btn-1",
        grant=_grant(),
        execute=True,
        evaluated_at="2026-06-02T10:00:00+08:00",
    )
    assert result["ok"] is False
    assert result["decision"]["reason"] == "approval_required"
    assert result["result"] == "blocked"


def test_click_allowed_with_single_step_grant_records_action(tmp_path: Path) -> None:
    decision = evaluate_browser_action(
        "click_element", url="https://example.com", grant=_grant(single_step_actions=True)
    )
    assert decision.ok is True
    assert decision.requires_approval is True
    # No real engine -> still blocked at execution with a typed reason, never simulated success.
    result = run_browser_action(
        tmp_path,
        action_kind="click_element",
        url="https://example.com",
        grant=_grant(single_step_actions=True),
        execute=True,
        evaluated_at="2026-06-02T10:00:00+08:00",
    )
    assert result["record"]["error_code"] == "browser_engine_unavailable"


def test_click_with_engine_is_unimplemented_not_fake_completed(tmp_path: Path) -> None:
    result = run_browser_action(
        tmp_path,
        action_kind="click_element",
        url="https://example.com",
        element_id="btn-1",
        grant=_grant(single_step_actions=True),
        execute=True,
        engine=StubBrowserEngine(),
        evaluated_at="2026-06-02T10:00:00+08:00",
    )
    assert result["result"] == "blocked"
    assert result["record"]["error_code"] == "browser_action_unimplemented"
    assert result["screenshot_ref"] == ""


def test_form_submission_blocks_by_default(tmp_path: Path) -> None:
    result = run_browser_action(
        tmp_path,
        action_kind="submit_form",
        url="https://example.com/form",
        grant=_grant(single_step_actions=True),
        approved=True,
        execute=True,
        evaluated_at="2026-06-02T10:00:00+08:00",
    )
    assert result["ok"] is False
    assert "high_risk_browser_action_blocked" in result["decision"]["reason"]


def test_sensitive_page_blocks_even_for_read_only(tmp_path: Path) -> None:
    result = run_browser_action(
        tmp_path,
        action_kind="navigate_readonly",
        url="https://accounts.google.com/login",
        grant=_grant(),
        execute=True,
        evaluated_at="2026-06-02T10:00:00+08:00",
    )
    assert result["ok"] is False
    assert result["decision"]["reason"].startswith("sensitive_page_blocked")


def test_browser_grant_disabled_blocks(tmp_path: Path) -> None:
    result = run_browser_action(
        tmp_path,
        action_kind="snapshot_dom",
        url="https://example.com",
        grant=_grant(enabled=False),
        execute=True,
        evaluated_at="2026-06-02T10:00:00+08:00",
    )
    assert result["ok"] is False
    assert result["decision"]["reason"] == "browser_grant_disabled"


def test_executable_download_is_high_blocked() -> None:
    assert classify_browser_action("download_file", file_type="exe") == ("high_blocked", True)
    assert classify_browser_action("download_file", file_type="pdf") == ("high_blocked", True)


def test_wait_for_text_is_unavailable(tmp_path: Path) -> None:
    result = run_browser_action(
        tmp_path,
        action_kind="wait_for_text",
        url="https://example.com",
        grant=_grant(),
        execute=True,
        evaluated_at="2026-06-02T10:00:00+08:00",
    )
    assert result["ok"] is False
    assert result["decision"]["reason"] == "browser_action_unavailable"


def test_screenshot_ttl_cleanup(tmp_path: Path) -> None:
    import os
    import time

    shots = tmp_path / SCREENSHOTS_REL
    shots.mkdir(parents=True, exist_ok=True)
    old = shots / "old.png"
    old.write_bytes(b"x")
    # Backdate the file ~48h.
    past = time.time() - 48 * 3600
    os.utime(old, (past, past))
    fresh = shots / "fresh.png"
    fresh.write_bytes(b"y")

    removed = cleanup_screenshots(tmp_path, ttl_hours=24)
    assert removed == 1
    assert not old.exists()
    assert fresh.exists()


def test_snapshot_reports_isolated_profile(tmp_path: Path) -> None:
    run_browser_action(
        tmp_path,
        action_kind="snapshot_dom",
        url="https://example.com",
        grant=_grant(),
        execute=True,
        evaluated_at="2026-06-02T10:00:00+08:00",
    )
    snap = build_browser_snapshot(tmp_path)
    assert snap["boundaries"]["uses_owner_browser_profile"] is False
    assert snap["actions_total"] >= 1

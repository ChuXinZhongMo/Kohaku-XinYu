from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from xinyu_browser_control import ACTIONS_REL as BROWSER_ACTIONS_REL
from xinyu_browser_control import ARTIFACTS_REL, run_browser_action
from xinyu_computer_control import run_computer_action


class StubBrowserEngine:
    """Minimal in-memory engine satisfying the BrowserEngine protocol."""

    def __init__(self) -> None:
        self.navigated: list[str] = []

    def navigate(self, url: str) -> dict[str, Any]:
        self.navigated.append(url)
        return {"url": url, "status": 200, "ok": True}

    def snapshot_dom(self) -> str:
        return "<html><body><h1>hello</h1></body></html>"

    def screenshot(self) -> bytes:
        return b"\x89PNG\r\n\x1a\nstub"

    def extract_text(self) -> str:
        return "hello"


class StubCaptureBackend:
    def __init__(self) -> None:
        self.calls = 0

    def screenshot(self, region: Any = None) -> bytes:
        self.calls += 1
        return b"\x89PNG\r\n\x1a\nstub"


def _browser_grant(**over) -> dict:
    base = {"enabled": True, "read_only": True, "single_step_actions": False}
    base.update(over)
    return base


def _computer_grant(**over) -> dict:
    base = {"enabled": True, "observe_only": True, "single_step_actions": False}
    base.update(over)
    return base


def test_browser_read_only_with_live_engine_writes_real_dom(tmp_path: Path) -> None:
    engine = StubBrowserEngine()
    result = run_browser_action(
        tmp_path,
        action_kind="navigate_readonly",
        url="https://example.com/news",
        grant=_browser_grant(),
        execute=True,
        engine=engine,
        evaluated_at="2026-06-02T10:00:00+08:00",
    )
    assert result["engine"] == "live"
    assert result["result"] == "completed"
    assert engine.navigated == ["https://example.com/news"]
    dom_ref = result["dom_snapshot_ref"]
    assert dom_ref.startswith(ARTIFACTS_REL.as_posix())
    assert "<h1>hello</h1>" in (tmp_path / dom_ref).read_text(encoding="utf-8")


def test_browser_single_step_with_engine_blocks_unimplemented(tmp_path: Path) -> None:
    engine = StubBrowserEngine()
    result = run_browser_action(
        tmp_path,
        action_kind="click_element",
        url="https://example.com",
        element_id="btn-1",
        grant=_browser_grant(single_step_actions=True),
        execute=True,
        engine=engine,
        evaluated_at="2026-06-02T10:00:00+08:00",
    )
    assert result["ok"] is False
    assert result["result"] == "blocked"
    assert result["record"]["error_code"] == "browser_action_unimplemented"
    assert result["screenshot_ref"] == ""
    record = json.loads((tmp_path / BROWSER_ACTIONS_REL).read_text(encoding="utf-8").splitlines()[-1])
    assert record["last_action_marker"]["type"] == "click"


def test_computer_observe_with_live_backend(tmp_path: Path) -> None:
    backend = StubCaptureBackend()
    result = run_computer_action(
        tmp_path,
        action_kind="screenshot",
        grant=_computer_grant(),
        execute=True,
        backend=backend,
        evaluated_at="2026-06-02T10:00:00+08:00",
    )
    assert result["backend"] == "live"
    assert result["result"] == "completed"
    assert backend.calls == 1
    assert (tmp_path / result["screenshot_ref"]).exists()


def test_computer_single_step_with_backend_completes(tmp_path: Path) -> None:
    backend = StubCaptureBackend()
    result = run_computer_action(
        tmp_path,
        action_kind="click",
        x=120,
        y=240,
        grant=_computer_grant(single_step_actions=True),
        execute=True,
        backend=backend,
        evaluated_at="2026-06-02T10:00:00+08:00",
    )
    assert result["ok"] is True
    assert result["result"] == "completed"
    assert result["screenshot_ref"]


def test_engine_adapters_import_without_optional_deps() -> None:
    # Importing the adapters must never require the optional packages.
    import xinyu_browser_engine_playwright as bp
    import xinyu_computer_capture_mss as cm

    assert hasattr(bp, "PlaywrightBrowserEngine")
    assert hasattr(cm, "MssCaptureBackend")
    assert isinstance(bp.playwright_available(), bool)
    assert isinstance(cm.mss_available(), bool)


class _StubChromium:
    def __init__(self, path: str) -> None:
        self.executable_path = path


class _StubPW:
    def __init__(self, path: str) -> None:
        self.chromium = _StubChromium(path)


def test_engine_honors_explicit_channel(tmp_path: Path) -> None:
    from xinyu_browser_engine_playwright import PlaywrightBrowserEngine

    engine = PlaywrightBrowserEngine(tmp_path, channel="chrome")
    # Explicit channel wins regardless of what is installed.
    assert engine._effective_channel(_StubPW("Z:/nope/chrome.exe")) == "chrome"
    # Root is resolved to an absolute path.
    assert engine._root.is_absolute()


def test_engine_falls_back_to_edge_when_chromium_unusable(tmp_path: Path) -> None:
    from xinyu_browser_engine_playwright import PlaywrightBrowserEngine

    engine = PlaywrightBrowserEngine(tmp_path, headless=True, channel=None)
    channel = engine._effective_channel(_StubPW("Z:/nonexistent/chrome.exe"))
    if PlaywrightBrowserEngine._edge_available():
        assert channel == "msedge"
    else:
        assert channel == ""

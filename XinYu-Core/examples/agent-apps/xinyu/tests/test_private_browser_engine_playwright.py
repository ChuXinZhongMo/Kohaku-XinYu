"""Live Playwright integration test for XinYu's private browser.

Skipped unless Playwright (and its Chromium) are installed. Serves a tiny page
from a loopback HTTP server — NO external network — and drives it through the
policy-gated run_browser_action with the real engine.

The sync Playwright API must not run inside a running asyncio loop, so each test
body runs in a worker thread — exactly how the bridge offloads browser work via
asyncio.to_thread in production.
"""
from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable

import pytest

from xinyu_browser_control import ARTIFACTS_REL, SCREENSHOTS_REL, run_browser_action

playwright_spec = pytest.importorskip("playwright", reason="playwright not installed")


def _run_in_thread(fn: Callable[[], None]) -> None:
    box: dict[str, BaseException] = {}

    def runner() -> None:
        try:
            fn()
        except BaseException as exc:  # noqa: BLE001 - re-raised on the main thread
            box["error"] = exc

    thread = threading.Thread(target=runner)
    thread.start()
    thread.join()
    if "error" in box:
        raise box["error"]


_PAGE = b"<html><head><title>XinYu Test</title></head><body><h1 id='h'>private hello</h1></body></html>"


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(_PAGE)))
        self.end_headers()
        self.wfile.write(_PAGE)

    def log_message(self, *args) -> None:  # silence
        return


_EDGE_PATHS = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
)


def _browser_channel() -> str | None:
    """Pick a usable browser: prefer system Edge (no CDN download needed)."""
    for path in _EDGE_PATHS:
        if Path(path).exists():
            return "msedge"
    return None  # could extend to chromium-headless-shell when present


_CHANNEL = _browser_channel()


@pytest.mark.skipif(_CHANNEL is None, reason="no system browser channel (edge) available")
def test_real_browser_read_only_observes_local_page(tmp_path: Path) -> None:
    from xinyu_browser_engine_playwright import PlaywrightBrowserEngine

    server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{port}/"
    grant = {"enabled": True, "read_only": True, "single_step_actions": False}

    def body() -> None:
        with PlaywrightBrowserEngine(tmp_path, headless=True, channel=_CHANNEL) as engine:
            nav = run_browser_action(
                tmp_path,
                action_kind="navigate_readonly",
                url=url,
                grant=grant,
                execute=True,
                engine=engine,
                evaluated_at="2026-06-02T10:00:00+08:00",
            )
            assert nav["engine"] == "live"
            assert nav["result"] == "completed"
            dom_ref = nav["dom_snapshot_ref"]
            assert dom_ref.startswith(ARTIFACTS_REL.as_posix())
            assert "private hello" in (tmp_path / dom_ref).read_text(encoding="utf-8")

            shot = run_browser_action(
                tmp_path,
                action_kind="screenshot",
                url=url,
                grant=grant,
                execute=True,
                engine=engine,
                evaluated_at="2026-06-02T10:00:01+08:00",
            )
            assert shot["result"] == "completed"
            ref = shot["screenshot_ref"]
            assert ref.startswith(SCREENSHOTS_REL.as_posix())
            assert (tmp_path / ref).stat().st_size > 0

        assert (tmp_path / "runtime/private_ecosystem/browser_profile").exists()

    try:
        _run_in_thread(body)
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.skipif(_CHANNEL is None, reason="no system browser channel (edge) available")
def test_real_browser_blocks_sensitive_page_before_engine(tmp_path: Path) -> None:
    # Policy must block a credential page even with a real engine available.
    from xinyu_browser_engine_playwright import PlaywrightBrowserEngine

    grant = {"enabled": True, "read_only": True}

    def body() -> None:
        with PlaywrightBrowserEngine(tmp_path, headless=True, channel=_CHANNEL) as engine:
            result = run_browser_action(
                tmp_path,
                action_kind="navigate_readonly",
                url="https://accounts.example.com/login",
                grant=grant,
                execute=True,
                engine=engine,
                evaluated_at="2026-06-02T10:00:00+08:00",
            )
        assert result["ok"] is False
        assert result["decision"]["reason"].startswith("sensitive_page_blocked")

    _run_in_thread(body)

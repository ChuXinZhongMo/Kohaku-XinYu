"""Real Playwright browser engine adapter for XinYu's private browser.

Implements the ``xinyu_browser_control.BrowserEngine`` Protocol with a
Playwright-driven Chromium that uses XinYu's ISOLATED persistent profile under
runtime/private_ecosystem/browser_profile — never the owner's real profile.

Security posture (dossier section 8.3):
  * No open CDP/debugging port: Playwright drives the browser over its own
    internal pipe; we never pass --remote-debugging-port or remote-allow-origins.
  * webSecurity / sandbox left at safe defaults (not disabled).
  * Isolated user-data-dir; cookies stay in the private profile only.
  * No stealth / anti-bot injection; no arbitrary page JS by default.
Policy (grant, sensitive-page blocking, approval) is enforced by
xinyu_browser_control.run_browser_action BEFORE this engine is ever called.

Playwright is an optional dependency. Importing this module is always safe;
the engine only requires Playwright when actually instantiated.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from xinyu_browser_control import PROFILE_REL

# A conservative allowance: read-only navigation waits for DOMContentLoaded then
# settles briefly. No downloads, no permissions, no geolocation.
_DEFAULT_TIMEOUT_MS = 15000
_DOM_SNAPSHOT_MAX_CHARS = 400_000


class PlaywrightBrowserEngine:
    """Single-session engine. Open once, pass to run_browser_action, then close."""

    def __init__(
        self,
        root: Path,
        *,
        headless: bool = True,
        timeout_ms: int = _DEFAULT_TIMEOUT_MS,
        channel: str | None = None,
    ) -> None:
        self._root = Path(root).resolve()
        self._headless = headless
        self._timeout_ms = max(1000, int(timeout_ms))
        # channel="msedge"/"chrome" uses an installed system browser instead of
        # a downloaded Chromium (useful when the Playwright CDN is blocked).
        self._channel = (channel if channel is not None else os.environ.get("XINYU_PRIVATE_BROWSER_CHANNEL", "")).strip()
        self._pw = None
        self._context = None
        self._page = None

    # -- engine selection ----------------------------------------------------
    _EDGE_PATHS = (
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    )

    @staticmethod
    def _edge_available() -> bool:
        return any(Path(p).exists() for p in PlaywrightBrowserEngine._EDGE_PATHS)

    def _chromium_usable(self, pw: Any) -> bool:
        try:
            exe = pw.chromium.executable_path
        except Exception:
            return False
        if not exe or not os.path.exists(exe):
            return False
        if self._headless:
            # Playwright's new headless mode needs the separate headless_shell
            # build; the headed chrome.exe alone is not enough.
            try:
                ms_root = Path(exe).resolve().parents[2]
                if not any(ms_root.glob("chromium_headless_shell-*")):
                    return False
            except Exception:
                return False
        return True

    def _effective_channel(self, pw: Any) -> str:
        """Honor an explicit channel; otherwise fall back to system Edge when the
        bundled Chromium cannot serve the requested (headless) mode."""
        if self._channel:
            return self._channel
        if not self._chromium_usable(pw) and self._edge_available():
            return "msedge"
        return ""

    # -- lifecycle -----------------------------------------------------------
    def open(self) -> "PlaywrightBrowserEngine":
        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:  # pragma: no cover - exercised only without playwright
            raise RuntimeError("playwright_not_installed") from exc

        profile_dir = self._root / PROFILE_REL
        profile_dir.mkdir(parents=True, exist_ok=True)

        self._pw = sync_playwright().start()
        channel = self._effective_channel(self._pw)
        # Persistent context = isolated, durable profile. No remote debugging
        # port, no remote-allow-origins, no disabled web security, no stealth.
        # Sandbox is kept ON explicitly. webSecurity stays at its safe default.
        launch_kwargs: dict[str, Any] = {
            "user_data_dir": str(profile_dir),
            "headless": self._headless,
            "accept_downloads": False,
            "chromium_sandbox": True,
            "args": ["--no-first-run", "--no-default-browser-check"],
        }
        if channel:
            launch_kwargs["channel"] = channel
        self._channel = channel
        self._context = self._pw.chromium.launch_persistent_context(**launch_kwargs)
        self._context.set_default_timeout(self._timeout_ms)
        self._page = self._context.pages[0] if self._context.pages else self._context.new_page()
        return self

    def close(self) -> None:
        try:
            if self._context is not None:
                self._context.close()
        finally:
            if self._pw is not None:
                self._pw.stop()
            self._context = None
            self._page = None
            self._pw = None

    def __enter__(self) -> "PlaywrightBrowserEngine":
        return self.open()

    def __exit__(self, *exc: Any) -> None:
        self.close()

    # -- BrowserEngine Protocol ---------------------------------------------
    def _require_page(self):
        if self._page is None:
            raise RuntimeError("browser_engine_not_open")
        return self._page

    def navigate(self, url: str) -> dict[str, Any]:
        page = self._require_page()
        response = page.goto(str(url), wait_until="domcontentloaded")
        status = response.status if response is not None else 0
        return {"url": page.url, "status": int(status), "ok": bool(response and response.ok)}

    def snapshot_dom(self) -> str:
        page = self._require_page()
        content = page.content()
        if len(content) > _DOM_SNAPSHOT_MAX_CHARS:
            content = content[:_DOM_SNAPSHOT_MAX_CHARS] + "\n<!-- truncated -->"
        return content

    def screenshot(self) -> bytes:
        page = self._require_page()
        return page.screenshot(full_page=False)

    def extract_text(self) -> str:
        page = self._require_page()
        try:
            text = page.inner_text("body")
        except Exception:
            text = ""
        if len(text) > _DOM_SNAPSHOT_MAX_CHARS:
            text = text[:_DOM_SNAPSHOT_MAX_CHARS] + " …(truncated)"
        return text


def create_browser_engine(root: Path, *, headless: bool = True) -> PlaywrightBrowserEngine:
    """Open and return a ready Playwright engine (raises if Playwright missing)."""
    return PlaywrightBrowserEngine(root, headless=headless).open()


def playwright_available() -> bool:
    import importlib.util

    return importlib.util.find_spec("playwright") is not None

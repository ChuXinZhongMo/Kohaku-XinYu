from __future__ import annotations

import pytest

from xinyu_bridge_cli import build_bridge_parser
from xinyu_bridge_cli_env_store import read_bridge_cli_env


def test_bridge_cli_env_store_reads_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("XINYU_BRIDGE_TOKEN", raising=False)

    assert read_bridge_cli_env("XINYU_BRIDGE_TOKEN") == ""
    assert read_bridge_cli_env("XINYU_BRIDGE_TOKEN", "fallback") == "fallback"

    monkeypatch.setenv("XINYU_BRIDGE_TOKEN", "token-1")

    assert read_bridge_cli_env("XINYU_BRIDGE_TOKEN") == "token-1"


def test_bridge_parser_uses_environment_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XINYU_BRIDGE_REQUEST_TIMEOUT_MARGIN_SECONDS", "7")
    monkeypatch.setenv("XINYU_RENDERER_MODE", "quality")
    monkeypatch.setenv("XINYU_DIALOGUE_SESSION_IDLE_TTL_SECONDS", "123")
    monkeypatch.setenv("XINYU_BRIDGE_TOKEN", "token-2")
    monkeypatch.setenv("XINYU_DESKTOP_EVENTS_HOST", "127.0.0.2")
    monkeypatch.setenv("XINYU_DESKTOP_EVENTS_PORT", "9876")
    monkeypatch.setenv("XINYU_DISABLE_DESKTOP_EVENTS", "1")

    args = build_bridge_parser().parse_args([])

    assert args.request_timeout_margin_seconds == 7
    assert args.renderer_mode == "quality"
    assert args.session_idle_ttl_seconds == 123
    assert args.bridge_token == "token-2"
    assert args.desktop_events_host == "127.0.0.2"
    assert args.desktop_events_port == 9876
    assert args.disable_desktop_events is True

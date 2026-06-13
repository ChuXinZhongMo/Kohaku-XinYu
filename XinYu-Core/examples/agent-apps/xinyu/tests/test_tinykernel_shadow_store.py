from __future__ import annotations

import json

import pytest

from xinyu_tinykernel_shadow import (
    ENABLED_ENV,
    ENDPOINT_ENV,
    TIMEOUT_ENV,
    TRACE_REL,
    record_tinykernel_shadow,
    shadow_enabled,
)
from xinyu_tinykernel_shadow_store import (
    append_tinykernel_shadow_trace_line,
    read_tinykernel_shadow_env,
)


def test_tinykernel_shadow_store_reads_env_and_appends_trace(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / TRACE_REL
    monkeypatch.delenv(ENABLED_ENV, raising=False)

    assert read_tinykernel_shadow_env(ENABLED_ENV) == ""
    assert shadow_enabled() is False

    monkeypatch.setenv(ENABLED_ENV, "1")
    append_tinykernel_shadow_trace_line(path, '{"ok": true}\n')

    assert read_tinykernel_shadow_env(ENABLED_ENV) == "1"
    assert shadow_enabled() is True
    assert path.read_text(encoding="utf-8") == '{"ok": true}\n'


def test_record_tinykernel_shadow_uses_store_backed_env_and_trace(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, float]] = []
    monkeypatch.setenv(ENDPOINT_ENV, "http://127.0.0.1:9999/custom")
    monkeypatch.setenv(TIMEOUT_ENV, "0.05")

    def fake_post(endpoint: str, payload: dict[str, object], timeout_seconds: float) -> dict[str, object]:
        calls.append((endpoint, timeout_seconds))
        return {
            "ok": True,
            "shadow_only": True,
            "mode": "shadow",
            "request_hash": "hash",
            "reply_candidate": "reply",
            "notes": ["ok"],
        }

    result = record_tinykernel_shadow(
        tmp_path,
        turn_id="turn-1",
        source="test",
        user_text="hello",
        enabled=True,
        post_fn=fake_post,
        observed_at="2026-01-01T08:00:00+08:00",
    )

    rows = [
        json.loads(line)
        for line in (tmp_path / TRACE_REL).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert result["recorded"] is True
    assert result["ok"] is True
    assert calls == [("http://127.0.0.1:9999/custom", 0.1)]
    assert rows[0]["event_kind"] == "tinykernel_compose_shadow_observation"
    assert rows[0]["turn_id"] == "turn-1"
    assert rows[0]["ok"] is True

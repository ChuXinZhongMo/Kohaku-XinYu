from __future__ import annotations

from xinyu_runtime_presence_markdown import render_presence_markdown


def test_render_presence_markdown_has_boundary_and_scrubbed_fields() -> None:
    md = render_presence_markdown(
        {
            "updated_at": "2026-07-13T12:00:00+08:00",
            "bridge_process": "running",
            "current_user_preview": "Bearer sk-abcdefghijklmnopqrst",
            "codex_status": "idle",
        }
    )
    assert "Runtime Self Presence" in md
    assert "scope: observed runtime facts only" in md
    assert "bridge_process: running" in md
    assert "sk-" not in md
    assert "[redacted-secret]" in md

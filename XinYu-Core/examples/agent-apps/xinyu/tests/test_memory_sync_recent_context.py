from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CUSTOM = ROOT / "custom"
SRC = ROOT.parents[2] / "src"
for path in (CUSTOM, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from memory_sync_plugin import _update_recent_context  # noqa: E402


def test_recent_context_repairs_content_envelope_and_keeps_event(tmp_path: Path) -> None:
    path = tmp_path / "memory/context/recent_context.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """2026-04-30 11:06：owner 留下了一次有轻微留痕意义的互动：现在你可以调用codex进行学习了？

content:---
last_updated: "2026-04-30T10:18:58+08:00"
---

# 近期上下文

## 当前时刻
- 2026年4月30日上午，广州的春末清晨
""",
        encoding="utf-8",
    )

    now = datetime(2026, 4, 30, 11, 30, tzinfo=timezone(timedelta(hours=8)))
    _update_recent_context(
        path,
        now,
        {"event_summary": "owner 留下了一次新的上下文确认"},
    )

    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert "content:---" not in text
    assert "## 近期关键事件" in text
    assert "- 2026-04-30 11:30：owner 留下了一次新的上下文确认" in text
    assert "- 2026-04-30 11:06：owner 留下了一次有轻微留痕意义的互动：现在你可以调用codex进行学习了？" in text

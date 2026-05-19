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

from memory_sync_plugin import _detect_signals, _update_recent_context  # noqa: E402


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


def test_detect_signals_tracks_light_hurt_residue() -> None:
    first = _detect_signals(
        "刚刚那句有点硌着我，但不用写得很重，你只留一点感觉就好。",
        "嗯，那句有点硌着。我只留一点，不写重。",
    )
    second = _detect_signals(
        "现在我正常回来了，你也不用立刻装作完全没事。",
        "嗯，不装完全没事。还留一点。",
    )

    assert first["hurt"] is True
    assert first["relationship_event"] is True
    assert first["emotion_event"] is True
    assert second["settle_after_hurt"] is True
    assert second["return_after_distance"] is True
    assert second["relationship_event"] is True


def test_recent_context_preserves_protected_anchor_when_events_roll(tmp_path: Path) -> None:
    path = tmp_path / "memory/context/recent_context.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """# 近期上下文

## 近期关键事件
- owner approved three quick fixes: restore recent_context, lower learning closed loop prompt weight, and cool down the repair loop.
- 2026-05-12 10:00：普通事件1
- 2026-05-12 10:01：普通事件2
- 2026-05-12 10:02：普通事件3
- 2026-05-12 10:03：普通事件4
- 2026-05-12 10:04：普通事件5
- 2026-05-12 10:05：普通事件6
- 2026-05-12 10:06：普通事件7
- 2026-05-12 10:07：普通事件8
""",
        encoding="utf-8",
    )

    now = datetime(2026, 5, 12, 11, 30, tzinfo=timezone(timedelta(hours=8)))
    _update_recent_context(
        path,
        now,
        {"event_summary": "owner 留下了一次短情绪摘要：我有点累"},
    )

    text = path.read_text(encoding="utf-8")
    assert "- 2026-05-12 11:30：owner 留下了一次短情绪摘要：我有点累" in text
    assert "## 持续锚点" in text
    assert "恢复最近聊天上下文" in text
    assert "recent_context" not in text

from __future__ import annotations

from datetime import datetime

from xinyu_bridge_state_text_time import build_payload_time_context_block, chinese_weekday_name


def test_chinese_weekday_name_monday_first() -> None:
    # 2026-07-14 is Tuesday
    dt = datetime.fromisoformat("2026-07-14T10:00:00+08:00")
    assert chinese_weekday_name(dt) == "周二"
    assert chinese_weekday_name(datetime.fromisoformat("2026-07-12T10:00:00+08:00")) == "周日"
    assert chinese_weekday_name(datetime.fromisoformat("2026-07-13T10:00:00+08:00")) == "周一"


def test_payload_time_context_includes_explicit_weekday() -> None:
    block = build_payload_time_context_block(
        {
            "timestamp": int(datetime.fromisoformat("2026-07-14T09:30:00+08:00").timestamp()),
        },
        observed_at=datetime.fromisoformat("2026-07-14T10:00:00+08:00"),
    )
    assert "current_local_weekday: 周二" in block
    assert "message_event_local_weekday: 周二" in block
    assert "current_local_date: 2026-07-14" in block
    assert "use current_local_weekday" in block

from __future__ import annotations

from typing import Any

from xinyu_bridge_values import safe_str


def codex_busy_reply(
    state: dict[str, Any],
    *,
    window_title: str,
) -> str:
    job_id = safe_str(state.get("job_id")).strip()
    window = safe_str(state.get("visible_window_title"), window_title).strip() or window_title
    job_part = f" {job_id}" if job_id else ""
    return (
        f"权限不是低，是执行位现在被 Codex{job_part} 占着，还在 {window} 窗口里跑。"
        "等它出结果，我再接代码改动；这次不会只停在“我想想”。"
    )

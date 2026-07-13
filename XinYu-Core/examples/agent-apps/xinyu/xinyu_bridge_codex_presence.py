from __future__ import annotations

from pathlib import Path
from typing import Any

from xinyu_bridge_codex_presence_reply import codex_busy_reply as _codex_busy_reply
from xinyu_bridge_codex_presence_status import (
    codex_delegate_running,
    codex_presence_status_from_result,
)
from xinyu_bridge_values import safe_str
from xinyu_runtime_presence import record_codex_presence

CODEX_DEFAULT_TIMEOUT_SECONDS = 3600
CODEX_VISIBLE_WINDOW_TITLE = "Xinyu codex"


def codex_delegate_running_for_runtime(runtime: Any) -> dict[str, Any]:
    return codex_delegate_running(
        runtime.xinyu_dir,
        delegate_locked=runtime._codex_delegate_lock.locked(),
        timeout_seconds=CODEX_DEFAULT_TIMEOUT_SECONDS,
        window_title=CODEX_VISIBLE_WINDOW_TITLE,
    )


def codex_busy_reply(
    state: dict[str, Any],
    *,
    window_title: str = CODEX_VISIBLE_WINDOW_TITLE,
) -> str:
    return _codex_busy_reply(state, window_title=window_title)


def codex_busy_reply_default(state: dict[str, Any]) -> str:
    return codex_busy_reply(state, window_title=CODEX_VISIBLE_WINDOW_TITLE)


def record_codex_delegate_presence_state(
    xinyu_dir: Path,
    payload: dict[str, Any],
    *,
    presence_paths: dict[str, Any],
    status: str,
    window_title: str = CODEX_VISIBLE_WINDOW_TITLE,
    presence_recorder: Any = record_codex_presence,
) -> None:
    presence_recorder(
        xinyu_dir,
        job_id=presence_paths["job_id"],
        status=status,
        request_path=presence_paths["request_path"],
        report_path=presence_paths["report_path"],
        visible_window_title=safe_str(payload.get("window_title"), window_title),
    )


def record_codex_delegate_presence_result(
    xinyu_dir: Path,
    payload: dict[str, Any],
    *,
    result: Any,
    presence_paths: dict[str, Any],
    window_title: str = CODEX_VISIBLE_WINDOW_TITLE,
    presence_recorder: Any = record_codex_presence,
) -> None:
    presence_recorder(
        xinyu_dir,
        job_id=presence_paths["job_id"],
        status=codex_presence_status_from_result(result),
        request_path=result.request_path or presence_paths["request_path"],
        report_path=result.report_path or presence_paths["report_path"],
        exit_code=result.exit_code,
        timed_out=result.timed_out,
        visible_window_title=safe_str(payload.get("window_title"), window_title),
    )


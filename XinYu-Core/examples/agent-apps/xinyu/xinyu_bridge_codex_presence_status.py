from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from xinyu_bridge_codex_presence_store import read_codex_presence_json
from xinyu_bridge_state_text import seconds_since_iso
from xinyu_bridge_values import safe_str

CODEX_PRESENCE_STATE_RELATIVE_PATH = Path("runtime/codex_presence_state.json")
CODEX_DEFAULT_TIMEOUT_SECONDS = 3600
CODEX_VISIBLE_WINDOW_TITLE = "Xinyu codex"
CODEX_RUNNING_STATUSES = frozenset({"running", "starting", "queued"})
CODEX_STALE_GRACE_SECONDS = 900


def unknown_codex_delegate_state() -> dict[str, Any]:
    return {"running": False, "status": "unknown"}


def locked_codex_delegate_state(*, window_title: str) -> dict[str, Any]:
    return {
        "running": True,
        "status": "running",
        "source": "lock",
        "visible_window_title": window_title,
    }


def read_codex_presence_state(xinyu_dir: Path) -> dict[str, Any] | None:
    path = xinyu_dir / CODEX_PRESENCE_STATE_RELATIVE_PATH
    return read_codex_presence_json(path)


def project_codex_delegate_state(
    data: dict[str, Any],
    *,
    timeout_seconds: int,
    window_title: str,
    seconds_since_iso_func: Callable[..., float] = seconds_since_iso,
) -> dict[str, Any]:
    status = safe_str(data.get("status")).strip().lower()
    updated_at = safe_str(data.get("updated_at")).strip()
    stale = bool(updated_at) and seconds_since_iso_func(updated_at, default=0.0) > (
        timeout_seconds + CODEX_STALE_GRACE_SECONDS
    )
    return {
        "running": status in CODEX_RUNNING_STATUSES and not stale,
        "status": status or "unknown",
        "job_id": safe_str(data.get("job_id")).strip(),
        "visible_window_title": safe_str(data.get("visible_window_title"), window_title).strip() or window_title,
        "report_label": safe_str(data.get("report_label")).strip(),
        "stale": stale,
    }


def codex_delegate_running(
    xinyu_dir: Path,
    *,
    delegate_locked: bool,
    timeout_seconds: int = CODEX_DEFAULT_TIMEOUT_SECONDS,
    window_title: str = CODEX_VISIBLE_WINDOW_TITLE,
    seconds_since_iso_func: Callable[..., float] = seconds_since_iso,
) -> dict[str, Any]:
    if delegate_locked:
        return locked_codex_delegate_state(window_title=window_title)
    data = read_codex_presence_state(xinyu_dir)
    if data is None:
        return unknown_codex_delegate_state()
    return project_codex_delegate_state(
        data,
        timeout_seconds=timeout_seconds,
        window_title=window_title,
        seconds_since_iso_func=seconds_since_iso_func,
    )


def codex_foreground_result_status(result: Any) -> str:
    if result.timed_out:
        return "timeout_staged" if result.accepted else "timeout"
    if result.accepted:
        return "done"
    return "failed"


def codex_presence_status_from_result(result: Any) -> str:
    if result.timed_out:
        return "timed_out"
    if result.accepted:
        return "finished"
    return "failed"

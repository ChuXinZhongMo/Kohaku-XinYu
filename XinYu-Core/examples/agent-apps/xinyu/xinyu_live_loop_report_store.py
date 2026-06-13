from __future__ import annotations

import json
import subprocess
from collections import deque
from pathlib import Path
from typing import Any


QQ_INBOUND_TRACE_REL = Path("runtime/qq_inbound_trace.jsonl")
VISIBLE_SEND_SHADOW_TRACE_REL = Path("runtime/answer_discipline_visible_send_shadow.jsonl")
GATEWAY_ACK_SPOOL_REL = Path("runtime/gateway_ack_spool.jsonl")


def live_loop_qq_inbound_trace_path(root: Path | str) -> Path:
    return Path(root).resolve() / QQ_INBOUND_TRACE_REL


def live_loop_visible_send_shadow_trace_path(root: Path | str) -> Path:
    return Path(root).resolve() / VISIBLE_SEND_SHADOW_TRACE_REL


def live_loop_gateway_ack_spool_path(root: Path | str) -> Path:
    return Path(root).resolve() / GATEWAY_ACK_SPOOL_REL


def read_live_loop_jsonl_tail(path: Path, max_lines: int = 500) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        if max_lines > 0:
            tail: deque[str] = deque(maxlen=max_lines)
            with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
                tail.extend(handle)
            lines = list(tail)
        else:
            raw_lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
            lines = raw_lines[-max_lines:]
    except OSError:
        return []
    rows: list[dict[str, Any]] = []
    for line in lines[-max_lines:]:
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            rows.append(value)
    return rows


def load_live_loop_status(
    root: Path | str,
    core_url: str,
    *,
    python_executable: str,
) -> tuple[dict[str, Any] | None, str]:
    root = Path(root).resolve()
    status_path = root / "xinyu_status.py"
    if not status_path.exists():
        return None, f"missing_status_script:{status_path}"
    command = [
        python_executable,
        str(status_path),
        "--json",
        "--root",
        str(root),
        "--core-url",
        core_url,
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=str(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f"status_error:{exc}"
    try:
        data = json.loads(completed.stdout)
    except json.JSONDecodeError:
        detail = completed.stderr.strip() or completed.stdout.strip()[:200] or "no_status_json"
        return None, f"status_json_error:{detail}"
    if not isinstance(data, dict):
        return None, "status_json_error:not_object"
    return data, ""

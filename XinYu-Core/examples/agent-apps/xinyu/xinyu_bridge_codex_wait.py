from __future__ import annotations

import re
from typing import Any

from xinyu_bridge_codex_payloads import (
    CODEX_DEFAULT_TIMEOUT_SECONDS,
    CODEX_VISIBLE_WINDOW_TITLE,
    build_model_codex_payload,
)
from xinyu_bridge_codex_wait_payloads import (
    build_wait_to_think_codex_payload as _build_wait_to_think_codex_payload,
    prepare_self_code_watchdog_payload as _prepare_self_code_watchdog_payload,
)
from xinyu_bridge_codex_wait_projection import (
    extract_wait_to_think_task as _extract_wait_to_think_task,
    wait_to_think_execution_plan as _wait_to_think_execution_plan,
)
from xinyu_bridge_reply_text import normalize_bridge_reply
from xinyu_bridge_values import safe_str
from xinyu_self_code_watchdog import create_self_code_snapshot


WAIT_TO_THINK_PATTERNS = (
    re.compile(r"\[WAIT_TO_THINK(?::\s*(?P<task>[^\]]+))?\]", re.I),
    re.compile(
        r"\[\[XINYU_WAIT_TO_THINK\]\]\s*(?P<task>.*?)\s*\[\[/XINYU_WAIT_TO_THINK\]\]",
        re.I | re.S,
    ),
)
WAIT_TO_THINK_WRITE_RISK_MARKERS = (
    " edit ",
    "write ",
    "delete",
    "move ",
    "install",
    "download",
    "modify",
    "patch",
    "apply",
    "淇敼",
    "鍐欏叆",
    "鍒犻櫎",
    "绉诲姩",
    "瀹夎",
    "涓嬭浇",
    "鏀逛唬鐮",
    "修改",
    "写入",
    "删除",
    "移动",
    "安装",
    "下载",
    "改代码",
)


def prepare_self_code_watchdog_payload(
    runtime: Any,
    payload: dict[str, Any],
    *,
    approval_id: str,
    snapshot_func: Any = create_self_code_snapshot,
) -> dict[str, Any]:
    return _prepare_self_code_watchdog_payload(
        runtime,
        payload,
        approval_id=approval_id,
        snapshot_func=snapshot_func,
        normalize_func=normalize_bridge_reply,
        safe_str_func=safe_str,
    )


def extract_wait_to_think_task(
    reply: str,
    *,
    user_text: str,
    session_key: str,
    patterns: tuple[re.Pattern[str], ...] = WAIT_TO_THINK_PATTERNS,
) -> str:
    return _extract_wait_to_think_task(
        reply,
        user_text=user_text,
        session_key=session_key,
        patterns=patterns,
        normalize_func=normalize_bridge_reply,
        safe_str_func=safe_str,
    )


def wait_to_think_execution_plan(
    wait_task: str,
    *,
    user_text: str,
    write_risk_markers: tuple[str, ...] = WAIT_TO_THINK_WRITE_RISK_MARKERS,
) -> str:
    return _wait_to_think_execution_plan(
        wait_task,
        user_text=user_text,
        write_risk_markers=write_risk_markers,
        normalize_func=normalize_bridge_reply,
    )


def build_wait_to_think_codex_payload(
    payload: dict[str, Any],
    *,
    session_key: str,
    wait_task: str,
    resume_id: str,
    user_text: str,
    timeout_seconds: int = CODEX_DEFAULT_TIMEOUT_SECONDS,
    window_title: str = CODEX_VISIBLE_WINDOW_TITLE,
) -> dict[str, Any]:
    return _build_wait_to_think_codex_payload(
        payload,
        session_key=session_key,
        wait_task=wait_task,
        resume_id=resume_id,
        user_text=user_text,
        timeout_seconds=timeout_seconds,
        window_title=window_title,
        execution_plan_func=wait_to_think_execution_plan,
        build_model_payload_func=build_model_codex_payload,
    )


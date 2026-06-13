from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any

from xinyu_bridge_codex_execution_timeout import (
    CODEX_DEFAULT_TIMEOUT_SECONDS,
    apply_codex_background_timeout_defaults,
)
from xinyu_bridge_values import as_bool, safe_str


CODEX_VISIBLE_WINDOW_TITLE = "Xinyu codex"
CODEX_QQ_EXECUTE_SOURCE = "qq_gateway_codex_execute_message"


def force_codex_visible_window(
    payload: dict[str, Any],
    *,
    window_title: str = CODEX_VISIBLE_WINDOW_TITLE,
) -> None:
    payload["visible_window"] = True
    payload["window_title"] = safe_str(payload.get("window_title"), window_title).strip() or window_title


def codex_execute_background_requested(payload: dict[str, Any]) -> bool:
    return safe_str(payload.get("source")) == CODEX_QQ_EXECUTE_SOURCE


def prepare_codex_execute_payload(
    payload: dict[str, Any],
    *,
    text: str,
    should_auto_study: Callable[[str], bool],
    observed_at: datetime | None = None,
    timeout_seconds: int = CODEX_DEFAULT_TIMEOUT_SECONDS,
    window_title: str = CODEX_VISIBLE_WINDOW_TITLE,
) -> dict[str, bool]:
    force_codex_visible_window(payload, window_title=window_title)
    auto_study = as_bool(
        payload.get("auto_study"),
        default=should_auto_study(text),
    )
    background = as_bool(
        payload.get("background"),
        default=codex_execute_background_requested(payload),
    )
    if background:
        apply_codex_background_timeout_defaults(
            payload,
            observed_at=observed_at,
            timeout_seconds=timeout_seconds,
        )
    return {"auto_study": auto_study, "background": background}

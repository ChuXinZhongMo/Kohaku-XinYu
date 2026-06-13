from __future__ import annotations

from datetime import datetime
from typing import Any


CODEX_DEFAULT_TIMEOUT_SECONDS = 3600
CODEX_BACKGROUND_JOB_ID_PREFIX = "codex-qq-"


def codex_background_job_id(observed_at: datetime) -> str:
    return f"{CODEX_BACKGROUND_JOB_ID_PREFIX}{observed_at.strftime('%Y%m%dT%H%M%S')}"


def apply_codex_background_timeout_defaults(
    payload: dict[str, Any],
    *,
    observed_at: datetime | None = None,
    timeout_seconds: int = CODEX_DEFAULT_TIMEOUT_SECONDS,
) -> None:
    observed_at = observed_at or datetime.now().astimezone()
    payload.setdefault("job_id", codex_background_job_id(observed_at))
    payload.setdefault("timeout_seconds", timeout_seconds)
    payload.setdefault("network_access", True)

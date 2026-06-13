from __future__ import annotations

import os
from pathlib import Path

from state_service import read_text_safe


def read_promise_owner_ids_env() -> str:
    return os.environ.get("XINYU_OWNER_USER_IDS", "")


def read_promise_owner_config_text(path: Path) -> str:
    return read_text_safe(path)

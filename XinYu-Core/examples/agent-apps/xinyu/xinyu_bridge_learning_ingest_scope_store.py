from __future__ import annotations

import os
from pathlib import Path


def read_learning_ingest_scope_env(name: str) -> str:
    return os.environ.get(name, "")


def resolve_learning_ingest_scope_root(text: str) -> Path:
    return Path(text).expanduser().resolve()

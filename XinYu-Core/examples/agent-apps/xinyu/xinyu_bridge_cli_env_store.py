from __future__ import annotations

import os


def read_bridge_cli_env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)

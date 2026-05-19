from __future__ import annotations

import sys
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[2]


def ensure_probe_paths(*relative_dirs: str) -> Path:
    if str(APP_ROOT) not in sys.path:
        sys.path.insert(0, str(APP_ROOT))
    for rel in relative_dirs:
        path = APP_ROOT / rel
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    return APP_ROOT

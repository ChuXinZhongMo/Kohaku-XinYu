from __future__ import annotations

import sys
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[2]


def ensure_app_root_on_path() -> Path:
    root = APP_ROOT
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return root

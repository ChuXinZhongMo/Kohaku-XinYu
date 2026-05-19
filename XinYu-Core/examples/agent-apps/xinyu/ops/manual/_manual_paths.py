from __future__ import annotations

import sys
from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[2]
CORE_SRC = APP_ROOT.parents[2] / "src"
CUSTOM_DIR = APP_ROOT / "custom"


def bootstrap_paths() -> Path:
    for path in (CORE_SRC, APP_ROOT, CUSTOM_DIR):
        text = str(path)
        if text not in sys.path:
            sys.path.insert(0, text)
    return APP_ROOT

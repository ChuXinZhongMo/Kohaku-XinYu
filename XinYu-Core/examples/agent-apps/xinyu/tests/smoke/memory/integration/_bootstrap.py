from __future__ import annotations

import sys
from pathlib import Path


def ensure_project_root_on_path() -> Path:
    root = Path(__file__).resolve().parents[4]
    root_text = str(root)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)
    custom = root / "custom"
    custom_text = str(custom)
    if custom.exists() and custom_text not in sys.path:
        sys.path.insert(0, custom_text)
    return root

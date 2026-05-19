from __future__ import annotations

import sys
from pathlib import Path


def ensure_project_root_on_path() -> Path:
    root = Path(__file__).resolve().parents[3]
    for path in (
        root,
        root / "custom",
    ):
        path_text = str(path)
        if path.exists() and path_text not in sys.path:
            sys.path.insert(0, path_text)
    return root

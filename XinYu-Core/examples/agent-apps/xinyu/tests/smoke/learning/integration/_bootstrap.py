from __future__ import annotations

import sys
from pathlib import Path


def ensure_project_root_on_path() -> Path:
    root = Path(__file__).resolve().parents[4]
    for path in (
        root,
        root / "custom",
        root / "tests" / "smoke" / "memory" / "integration",
        Path(__file__).resolve().parent,
    ):
        path_text = str(path)
        if path.exists() and path_text not in sys.path:
            sys.path.insert(0, path_text)
    return root

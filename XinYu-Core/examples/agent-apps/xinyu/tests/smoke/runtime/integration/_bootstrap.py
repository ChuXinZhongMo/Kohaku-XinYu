from __future__ import annotations

import sys
from pathlib import Path


def ensure_project_root_on_path() -> Path:
    root = Path(__file__).resolve().parents[4]
    root_text = str(root)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)
    memory_integration = root / "tests" / "smoke" / "memory" / "integration"
    memory_integration_text = str(memory_integration)
    if memory_integration.exists() and memory_integration_text not in sys.path:
        sys.path.insert(0, memory_integration_text)
    runtime_integration = root / "tests" / "smoke" / "runtime" / "integration"
    runtime_integration_text = str(runtime_integration)
    if runtime_integration.exists() and runtime_integration_text not in sys.path:
        sys.path.insert(0, runtime_integration_text)
    return root

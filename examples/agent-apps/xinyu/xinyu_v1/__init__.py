"""XinYu v1.0-RC runtime package."""

from __future__ import annotations

from .types import RuntimeMode, VectorBackendKind

__version__ = "1.0.0-rc.0"
__runtime_name__ = "XinYu v1"

__all__ = [
    "__runtime_name__",
    "__version__",
    "RuntimeMode",
    "VectorBackendKind",
]


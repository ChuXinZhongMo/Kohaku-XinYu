"""FastAPI dependencies."""

import os

from xinyu_runtime.serving import XinYuManager
from xinyu_runtime.utils.paths import xinyu_path

_manager: XinYuManager | None = None

_DEFAULT_SESSION_DIR = str(xinyu_path("sessions"))


def get_manager() -> XinYuManager:
    """Return the singleton XinYuManager instance."""
    global _manager
    if _manager is None:
        session_dir = (
            os.environ.get("XINYU_SESSION_DIR")
            or os.environ.get("KT_SESSION_DIR")
            or _DEFAULT_SESSION_DIR
        )
        _manager = XinYuManager(session_dir=session_dir)
    return _manager

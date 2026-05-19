"""Test path setup for the XinYu example app.

These tests import XinYu's local modules by their historical top-level names.
Keep that working when pytest is invoked from the repository root.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

XINYU_APP_DIR = Path(__file__).resolve().parents[1]
if str(XINYU_APP_DIR) not in sys.path:
    sys.path.insert(0, str(XINYU_APP_DIR))

XINYU_CORE_SRC = Path(__file__).resolve().parents[4] / "src"
if str(XINYU_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(XINYU_CORE_SRC))


def pytest_configure(config) -> None:
    if getattr(config.option, "basetemp", None):
        return
    basetemp_parent = XINYU_APP_DIR / "runtime" / "pytest-tmp"
    basetemp_parent.mkdir(parents=True, exist_ok=True)
    config.option.basetemp = str(basetemp_parent / f"run-{os.getpid()}")

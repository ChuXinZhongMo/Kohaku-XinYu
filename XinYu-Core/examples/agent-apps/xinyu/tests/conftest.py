"""Test path setup for the XinYu example app.

These tests import XinYu's local modules by their historical top-level names.
Keep that working when pytest is invoked from the repository root.
"""

from __future__ import annotations

import sys
from pathlib import Path

XINYU_APP_DIR = Path(__file__).resolve().parents[1]
if str(XINYU_APP_DIR) not in sys.path:
    sys.path.insert(0, str(XINYU_APP_DIR))

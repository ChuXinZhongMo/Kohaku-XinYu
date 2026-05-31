"""Test path setup for the XinYu example app.

These tests import XinYu's local modules by their historical top-level names.
Keep that working when pytest is invoked from the repository root.
"""

from __future__ import annotations

import os
import shutil
import sys
import time
from pathlib import Path

XINYU_APP_DIR = Path(__file__).resolve().parents[1]
if str(XINYU_APP_DIR) not in sys.path:
    sys.path.insert(0, str(XINYU_APP_DIR))

XINYU_CORE_SRC = Path(__file__).resolve().parents[4] / "src"
if str(XINYU_CORE_SRC) not in sys.path:
    sys.path.insert(0, str(XINYU_CORE_SRC))


def _positive_int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if not raw:
        return default
    try:
        return max(0, int(raw))
    except ValueError:
        return default


def _cleanup_old_pytest_runs(basetemp_parent: Path, current_run: Path) -> None:
    keep = _positive_int_env("XINYU_PYTEST_TMP_KEEP", 8)
    min_age_seconds = _positive_int_env("XINYU_PYTEST_TMP_MIN_AGE_SECONDS", 600)
    now = time.time()
    runs: list[tuple[float, Path]] = []

    for child in basetemp_parent.iterdir():
        if child == current_run or not child.is_dir():
            continue
        if not child.name.startswith("run-") or not child.name[4:].isdigit():
            continue
        try:
            runs.append((child.stat().st_mtime, child))
        except OSError:
            continue

    runs.sort(key=lambda item: item[0], reverse=True)
    for index, (mtime, path) in enumerate(runs):
        if index < keep or now - mtime < min_age_seconds:
            continue
        try:
            shutil.rmtree(path)
        except OSError:
            continue


def pytest_configure(config) -> None:
    if getattr(config.option, "basetemp", None):
        return
    basetemp_parent = XINYU_APP_DIR / "runtime" / "pytest-tmp"
    basetemp_parent.mkdir(parents=True, exist_ok=True)
    current_run = basetemp_parent / f"run-{os.getpid()}"
    _cleanup_old_pytest_runs(basetemp_parent, current_run)
    config.option.basetemp = str(current_run)

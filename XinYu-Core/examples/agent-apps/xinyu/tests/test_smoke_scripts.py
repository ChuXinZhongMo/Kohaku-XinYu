"""Make the standalone `*_smoke.py` integration scripts visible to pytest.

Historically the ~200 scripts under ``tests/smoke/`` were `main()`-style programs
run by hand (`python xxx_smoke.py`) and were never collected by pytest, so the
heaviest integration coverage was invisible to any automated run and free to rot.

This harness discovers them and runs each as an isolated subprocess, asserting a
0 exit code. They are marked ``smoke`` and excluded from the default run (see
pytest.ini ``-m "not smoke"``) because some need a live environment; run them
explicitly with ``pytest -m smoke`` (the CI ``python-smoke`` job does this,
non-blocking).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_APP_DIR = Path(__file__).resolve().parents[1]
_SMOKE_DIR = _APP_DIR / "tests" / "smoke"
_TIMEOUT_SECONDS = 300

_SMOKE_SCRIPTS = sorted(
    p for p in _SMOKE_DIR.rglob("*_smoke.py") if p.is_file() and p.name != "_bootstrap.py"
)


def _script_id(path: Path) -> str:
    return str(path.relative_to(_SMOKE_DIR)).replace("\\", "/")


@pytest.mark.smoke
@pytest.mark.parametrize("script", _SMOKE_SCRIPTS, ids=[_script_id(p) for p in _SMOKE_SCRIPTS])
def test_smoke_script(script: Path) -> None:
    if not _SMOKE_SCRIPTS:
        pytest.skip("no smoke scripts discovered")
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(_APP_DIR),
        capture_output=True,
        text=True,
        timeout=_TIMEOUT_SECONDS,
    )
    if proc.returncode != 0:
        tail = (proc.stdout or "")[-2000:] + "\n--- stderr ---\n" + (proc.stderr or "")[-2000:]
        pytest.fail(f"{_script_id(script)} exited {proc.returncode}\n{tail}")

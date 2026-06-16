"""Spawn the isolated heavy-maintenance worker as a subprocess.

Keeps the deterministic heavy lanes (candidate maintenance, skill synthesis,
consolidation, dream) off the live process's global turn lock and conversation
context. Controlled by ``XINYU_HEAVY_MAINTENANCE_SUBPROCESS`` (default on; set to
0/false/no/off to keep everything inline). Failures are swallowed so the
autonomous loop is never broken by a maintenance subprocess.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any

WORKER_SCRIPT = "run_heavy_maintenance.py"
_FALSE_VALUES = {"0", "false", "no", "off"}


def heavy_maintenance_subprocess_enabled() -> bool:
    return os.environ.get("XINYU_HEAVY_MAINTENANCE_SUBPROCESS", "").strip().lower() not in _FALSE_VALUES


async def spawn_heavy_maintenance(runtime: Any, *, timeout: float = 900.0) -> dict[str, Any]:
    if not heavy_maintenance_subprocess_enabled():
        return {"status": "disabled"}
    root = getattr(runtime, "xinyu_dir", None)
    if root is None:
        return {"status": "no_root"}
    root_path = Path(root)
    script = root_path / WORKER_SCRIPT
    if not script.exists():
        return {"status": "worker_missing"}
    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            str(script),
            "--root",
            str(root_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(root_path),
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except ProcessLookupError:
                pass
            return {"status": "timeout"}
        return {
            "status": "ok" if proc.returncode == 0 else "error",
            "returncode": proc.returncode,
            "stdout_tail": (stdout or b"").decode("utf-8", "replace")[-400:],
            "stderr_tail": (stderr or b"").decode("utf-8", "replace")[-400:],
        }
    except Exception as exc:
        return {"status": "spawn_failed", "error": repr(exc)}

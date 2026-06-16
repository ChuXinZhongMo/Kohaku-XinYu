"""Isolated heavy-maintenance worker.

The autonomous maintenance turn used to drive every heavy lane inline, in the live
bridge process, under the shared global turn lock and a full LLM turn. The heavy
lanes are actually deterministic, file-only processors that need no model, so this
script runs them in a separate process — off the turn lock, out of the live
conversation context.

Usable three ways:
  * spawned by the autonomous loop (see xinyu_bridge_heavy_maintenance.py),
  * a cron / scheduled task,
  * manually: ``python run_heavy_maintenance.py --root <xinyu_dir>``.

A single-flight lock file prevents overlapping heavy passes from colliding on the
shared ``memory/**/*_state.md`` files.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

APP_ROOT = Path(__file__).resolve().parent
for _p in (str(APP_ROOT), str(APP_ROOT / "custom")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

LOCK_REL = Path("runtime") / "heavy_maintenance.lock"
LOCK_TTL_SECONDS = 3600

# Order matters: candidate maintenance promotes/ages the candidates that skill
# synthesis then distils; consolidation and dream run last.
DEFAULT_LANES = ("candidate_maintenance", "skill_synthesis", "consolidation", "dream")


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _acquire_lock(root: Path) -> Path | None:
    lock_path = root / LOCK_REL
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    if lock_path.exists():
        try:
            age = time.time() - lock_path.stat().st_mtime
        except OSError:
            age = 0.0
        if age < LOCK_TTL_SECONDS:
            return None  # a fresh pass is already running
    try:
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        # lost a race, or a stale lock we just decided to steal
        try:
            if time.time() - lock_path.stat().st_mtime >= LOCK_TTL_SECONDS:
                lock_path.unlink(missing_ok=True)
                fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            else:
                return None
        except OSError:
            return None
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(f"{os.getpid()} {_now_iso()}")
    return lock_path


def _release_lock(lock_path: Path | None) -> None:
    if lock_path is not None:
        try:
            lock_path.unlink(missing_ok=True)
        except OSError:
            pass


def _lane_candidate_maintenance(root: Path, ts: str) -> dict[str, Any]:
    from xinyu_memory_candidate_maintenance import run_memory_candidate_maintenance

    return run_memory_candidate_maintenance(root, checked_at=ts)


def _lane_skill_synthesis(root: Path, ts: str) -> dict[str, Any]:
    from xinyu_skill_synthesis import run_skill_synthesis

    return run_skill_synthesis(root, checked_at=ts, mode="heavy_maintenance_skill_synthesis")


def _lane_consolidation(root: Path, ts: str) -> dict[str, Any]:
    from consolidation_engine import run_consolidation

    return run_consolidation(root, checked_at=ts, mode="heavy_maintenance_consolidation")


def _lane_dream(root: Path, ts: str) -> dict[str, Any]:
    from dream_output_engine import has_unconsumed_dream_seed, run_dream_output

    seeds_path = root / "memory" / "dreams" / "dream_seeds.md"
    seeds = seeds_path.read_text(encoding="utf-8-sig", errors="replace") if seeds_path.exists() else ""
    if not has_unconsumed_dream_seed(seeds):
        return {"skipped": "no_unconsumed_dream_seed"}
    return run_dream_output(root, produced_at=ts, mode="heavy_maintenance_dream")


_LANES: dict[str, Callable[[Path, str], dict[str, Any]]] = {
    "candidate_maintenance": _lane_candidate_maintenance,
    "skill_synthesis": _lane_skill_synthesis,
    "consolidation": _lane_consolidation,
    "dream": _lane_dream,
}


def run_heavy_maintenance(root: Path, *, lanes: tuple[str, ...] = DEFAULT_LANES) -> dict[str, Any]:
    root = Path(root).resolve()
    lock_path = _acquire_lock(root)
    if lock_path is None:
        return {"status": "skipped_locked", "lanes": {}}
    ts = _now_iso()
    results: dict[str, Any] = {}
    try:
        for lane in lanes:
            runner = _LANES.get(lane)
            if runner is None:
                results[lane] = {"error": "unknown_lane"}
                continue
            try:
                results[lane] = runner(root, ts)
            except Exception as exc:  # one lane must never abort the rest
                results[lane] = {"error": repr(exc)}
    finally:
        _release_lock(lock_path)
    return {"status": "ok", "checked_at": ts, "lanes": results}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run XinYu heavy maintenance lanes in isolation.")
    parser.add_argument("--root", required=True, help="XinYu app root (xinyu_dir).")
    parser.add_argument(
        "--lanes",
        default=",".join(DEFAULT_LANES),
        help="comma-separated lanes: " + ",".join(_LANES),
    )
    args = parser.parse_args(argv)
    lanes = tuple(lane.strip() for lane in args.lanes.split(",") if lane.strip())
    result = run_heavy_maintenance(Path(args.root), lanes=lanes)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

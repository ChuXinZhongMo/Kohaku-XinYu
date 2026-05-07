"""CLI: run one v1 maintenance pass."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from ..autonomy.scheduler import AutoHealingScheduler
from ..config import XinYuV1Config


async def _run(args: argparse.Namespace) -> None:
    config = XinYuV1Config.load(Path(args.root) if args.root else None)
    scheduler = AutoHealingScheduler(config.paths, config.maintenance)
    if args.force:
        scheduler.idle.last_human_monotonic = 0.0
    report = await scheduler.run_once_if_idle()
    print(json.dumps({"ran": report.ran, "notes": list(report.notes), "payload": report.payload}, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="")
    parser.add_argument("--force", action="store_true")
    asyncio.run(_run(parser.parse_args()))


if __name__ == "__main__":
    main()


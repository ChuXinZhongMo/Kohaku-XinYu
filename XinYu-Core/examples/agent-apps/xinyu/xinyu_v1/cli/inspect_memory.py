"""CLI: inspect v1 memory retrieval."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from ..config import XinYuV1Config
from ..memory.models import MemoryQuery
from ..memory.orchestrator import MemoryOrchestrator


async def _run(args: argparse.Namespace) -> None:
    config = XinYuV1Config.load(Path(args.root) if args.root else None)
    orchestrator = MemoryOrchestrator(runtime_root=config.paths.runtime_root)
    results = await orchestrator.retrieve(MemoryQuery(text=args.query, limit=args.limit))
    print(json.dumps([result.to_json() for result in results], ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--root", default="")
    parser.add_argument("--limit", type=int, default=8)
    asyncio.run(_run(parser.parse_args()))


if __name__ == "__main__":
    main()


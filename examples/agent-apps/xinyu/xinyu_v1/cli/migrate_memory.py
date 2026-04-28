"""CLI: migrate legacy Markdown memory into v1 vector memory."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from ..config import XinYuV1Config
from ..memory.migration import migrate_markdown_memory
from ..memory.vector_store import InMemoryVectorStore


async def _run(args: argparse.Namespace) -> None:
    config = XinYuV1Config.load(Path(args.root) if args.root else None)
    report = await migrate_markdown_memory(
        memory_root=config.paths.memory_root,
        vector_store=InMemoryVectorStore(),
        dry_run=not args.apply,
    )
    print(json.dumps(report.to_json(), ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="")
    parser.add_argument("--apply", action="store_true")
    asyncio.run(_run(parser.parse_args()))


if __name__ == "__main__":
    main()


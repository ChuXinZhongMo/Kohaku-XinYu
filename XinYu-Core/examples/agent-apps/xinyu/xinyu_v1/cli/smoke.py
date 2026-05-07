"""CLI: lightweight v1 smoke check."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from ..app import XinYuV1App


async def _run(args: argparse.Namespace) -> None:
    app = XinYuV1App.load(Path(args.root) if args.root else None)
    reply = await app.handle_payload({"text": "你好", "user_id": "smoke-user", "session_id": "smoke-session"})
    print(json.dumps(reply.to_json(), ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="")
    asyncio.run(_run(parser.parse_args()))


if __name__ == "__main__":
    main()


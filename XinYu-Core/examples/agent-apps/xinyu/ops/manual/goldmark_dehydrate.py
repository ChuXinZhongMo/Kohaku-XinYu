from __future__ import annotations

import argparse
import json
from pathlib import Path

from _manual_paths import bootstrap_paths


APP_ROOT = bootstrap_paths()

from xinyu_goldmark_dehydrate import run_goldmark_dehydration_maintenance


def main() -> int:
    parser = argparse.ArgumentParser(description="Run XinYu Goldmark vibe dehydration.")
    parser.add_argument("--root", default=str(APP_ROOT), help="XinYu app root.")
    parser.add_argument("--limit", type=int, default=5, help="Max entries to process.")
    parser.add_argument("--force", action="store_true", help="Reprocess done/failed entries.")
    parser.add_argument(
        "--provider",
        choices=("auto", "local", "llm"),
        default="auto",
        help="Dehydration provider. auto defaults to local unless explicitly configured for LLM.",
    )
    parser.add_argument("--timeout-seconds", type=int, default=45, help="Per-entry LLM timeout.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    args = parser.parse_args()

    result = run_goldmark_dehydration_maintenance(
        Path(args.root),
        limit=args.limit,
        force=args.force,
        provider=args.provider,
        timeout_seconds=args.timeout_seconds,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"status: {result.get('status')}")
        print(f"processed: {result.get('processed')}")
        print(f"succeeded: {result.get('succeeded')}")
        print(f"skipped: {result.get('skipped', 0)}")
        print(f"failed: {result.get('failed')}")
        print(f"recovered: {result.get('recovered', 0)}")
        print(f"provider: {result.get('provider')}")
    return 0 if int(result.get("failed") or 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

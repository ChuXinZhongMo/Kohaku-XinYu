from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect and advance Xinyu slow-reprocessing state."
    )
    parser.add_argument(
        "--show-state",
        action="store_true",
        help="Print reprocessing_state after update.",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    xinyu_dir = Path(__file__).resolve().parent
    custom_dir = xinyu_dir / "custom"
    if str(custom_dir) not in sys.path:
        sys.path.insert(0, str(custom_dir))

    from slow_reprocess_engine import run_slow_reprocess

    result = run_slow_reprocess(
        xinyu_dir,
        mode="manual_slow_reprocess",
    )

    print("Xinyu manual slow reprocess complete.")
    print(f"Reflection queue items: {result['reflection_count']}")
    print(f"Dream seed items: {result['dream_count']}")
    print(f"Archive queue items: {result['archive_count']}")
    print(f"Top topic: {result['top_topic']}")

    if args.show_state:
        state_path = xinyu_dir / "memory/reflection/reprocessing_state.md"
        print("\n--- memory/reflection/reprocessing_state.md ---")
        print(state_path.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

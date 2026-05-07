from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Advance Xinyu archive output stage conservatively."
    )
    parser.add_argument(
        "--show-state",
        action="store_true",
        help="Print archive files after update.",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    xinyu_dir = Path(__file__).resolve().parent
    custom_dir = xinyu_dir / "custom"
    if str(custom_dir) not in sys.path:
        sys.path.insert(0, str(custom_dir))

    from archive_output_engine import run_archive_output

    result = run_archive_output(
        xinyu_dir,
        mode="manual_archive_output",
    )

    print("Xinyu manual archive output complete.")
    print(f"Queue: {result['queue_count']}")
    print(f"Next action: {result['next_action']}")

    if args.show_state:
        for rel in [
            "memory/archive/archive_output_state.md",
            "memory/archive/archive_queue.md",
            "memory/archive/compressed.md",
            "memory/archive/dormant.md",
        ]:
            path = xinyu_dir / rel
            print(f"\n--- {rel} ---")
            print(path.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

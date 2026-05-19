from __future__ import annotations

import argparse

from _manual_paths import APP_ROOT, bootstrap_paths


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

    xinyu_dir = APP_ROOT
    bootstrap_paths()

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

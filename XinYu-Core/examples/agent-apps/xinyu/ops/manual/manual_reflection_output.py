from __future__ import annotations

import argparse

from _manual_paths import APP_ROOT, bootstrap_paths


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Promote reflection queue into reflection/growth outputs."
    )
    parser.add_argument(
        "--show-state",
        action="store_true",
        help="Print reflection output state after update.",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    xinyu_dir = APP_ROOT
    bootstrap_paths()

    from reflection_output_engine import run_reflection_output

    result = run_reflection_output(
        xinyu_dir,
        mode="manual_reflection_output",
    )

    print("Xinyu manual reflection output complete.")
    print(f"Topic: {result['topic']}")

    if args.show_state:
        for rel in [
            "memory/reflection/reflection_output_state.md",
            "memory/reflection/reflection_log.md",
            "memory/reflection/growth_log.md",
        ]:
            path = xinyu_dir / rel
            print(f"\n--- {rel} ---")
            print(path.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

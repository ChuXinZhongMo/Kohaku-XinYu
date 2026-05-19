from __future__ import annotations

import argparse

from _manual_paths import APP_ROOT, bootstrap_paths


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Advance Xinyu source-gate stage without external fetching."
    )
    parser.add_argument(
        "--show-state",
        action="store_true",
        help="Print source-gate files after update.",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    xinyu_dir = APP_ROOT
    bootstrap_paths()

    from source_gate_engine import run_source_gate

    result = run_source_gate(
        xinyu_dir,
        mode="manual_source_gate",
    )

    print("Xinyu manual source gate complete.")
    print(f"Candidates: {result['candidate_count']}")

    if args.show_state:
        for rel in [
            "memory/knowledge/source_gate_state.md",
            "memory/knowledge/source_notes.md",
            "memory/knowledge/general.md",
        ]:
            path = xinyu_dir / rel
            print(f"\n--- {rel} ---")
            print(path.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

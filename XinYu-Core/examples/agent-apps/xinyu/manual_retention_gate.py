from __future__ import annotations

import argparse
import json
from pathlib import Path

from custom.retention_gate_engine import run_retention_gate


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Xinyu retention gate manually.")
    parser.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parent),
        help="Root directory of the xinyu app.",
    )
    parser.add_argument(
        "--show-state",
        action="store_true",
        help="Print the retention gate result as JSON.",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    result = run_retention_gate(root, mode="manual_retention_gate")
    if args.show_state:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

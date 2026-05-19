from __future__ import annotations

import argparse
import json
from pathlib import Path

from _manual_paths import APP_ROOT, bootstrap_paths

bootstrap_paths()

from custom.consolidation_engine import run_consolidation


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Xinyu consolidation manually.")
    parser.add_argument(
        "--root",
        default=str(APP_ROOT),
        help="Root directory of the xinyu app.",
    )
    parser.add_argument(
        "--show-state",
        action="store_true",
        help="Print the consolidation result as JSON.",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    result = run_consolidation(root, mode="manual_consolidation")
    if args.show_state:
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

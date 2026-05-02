from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CUSTOM = ROOT / "custom"
if str(CUSTOM) not in sys.path:
    sys.path.insert(0, str(CUSTOM))

from research_handoff_engine import run_research_handoff_loop


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run XinYu self-thought research handoff.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--evaluated-at", default="")
    parser.add_argument(
        "--execution-level",
        choices=["state_only", "activate", "execute", "execute_codex"],
        default="state_only",
    )
    parser.add_argument("--allow-live-search", action="store_true")
    parser.add_argument("--allow-codex", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = run_research_handoff_loop(
        args.root.resolve(),
        evaluated_at=args.evaluated_at or None,
        execution_level=args.execution_level,
        allow_live_search=args.allow_live_search,
        allow_codex=args.allow_codex,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print("Research handoff state written")
        print(f"status: {result['status']}")
        print(f"route: {result['route']}")
        print(f"source_request_id: {result['source_request_id']}")
        print(f"activation_permission: {result['activation_permission']}")
        print(f"provider_results: {result['provider_results']}")
        print(f"codex_status: {result['codex_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

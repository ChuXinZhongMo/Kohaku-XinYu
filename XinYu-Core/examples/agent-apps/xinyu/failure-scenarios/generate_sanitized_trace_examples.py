from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
SCENARIO_DIR = ROOT / "scenarios"
DEFAULT_OUTPUT = ROOT / "examples" / "sanitized_trace_examples.jsonl"


def generate_rows(scenario_dir: Path = SCENARIO_DIR) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(scenario_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        scenario_id = str(data.get("id") or path.stem)
        route = str(data.get("expected_health_state", {}).get("operator", {}).get("route", "unknown"))
        status = str(data.get("expected_visible_behavior", {}).get("status", "ok"))
        for index, stage in enumerate(data.get("expected_trace_stages", [])[:4]):
            rows.append(
                {
                    "scenario_id": scenario_id,
                    "stage": str(stage),
                    "route": route if route != "unknown" else _route_for_stage(str(stage)),
                    "status": _status_for_stage(str(stage), fallback=status),
                    "notes": [f"scenario:{scenario_id}", f"step:{index + 1}"],
                }
            )
    return rows


def write_rows(rows: list[dict[str, Any]], output: Path = DEFAULT_OUTPUT) -> Path:
    output.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)
    output.write_text(text.rstrip() + "\n", encoding="utf-8")
    return output


def _route_for_stage(stage: str) -> str:
    if "intervention" in stage:
        return "owner_intervention"
    if "fast" in stage:
        return "semantic_fast"
    if stage in {"route_decided", "route_finished"}:
        return "slow_live"
    return "undecided"


def _status_for_stage(stage: str, *, fallback: str) -> str:
    lowered = stage.lower()
    if "timeout" in lowered:
        return "timeout"
    if "cancel" in lowered or "intervention_applied" in lowered:
        return "applied"
    if "blocked" in lowered or "rejected" in lowered:
        return "rejected"
    if "finished" in lowered:
        return "ok"
    if "decided" in lowered:
        return "accepted"
    return fallback if fallback not in {"", "unknown"} else "ok"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate sanitized trace examples from failure scenario JSON files.")
    parser.add_argument("--scenario-dir", type=Path, default=SCENARIO_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true", help="Exit non-zero if output differs.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    rows = generate_rows(args.scenario_dir)
    generated = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows).rstrip() + "\n"
    if args.check:
        try:
            existing = args.output.read_text(encoding="utf-8")
        except OSError:
            existing = ""
        if existing != generated:
            print(f"sanitized trace examples are out of date: {args.output}")
            return 1
        print("sanitized trace examples are up to date")
        return 0
    write_rows(rows, args.output)
    print(f"wrote {len(rows)} rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from common import DATA_DIR, PROJECT_ROOT, dump_json, read_jsonl, write_jsonl


DEFAULT_IN = DATA_DIR / "probes" / "maia_public_scenario_probes_v001.jsonl"
DEFAULT_OUT = DATA_DIR / "probes" / "maia_daily_life_review_slice_v001.jsonl"
DEFAULT_REPORT = PROJECT_ROOT / "eval" / "reports" / "maia_daily_life_review_slice_v001.json"


def count_by(rows: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key) or "")
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def sample_by_domain(rows: list[dict[str, Any]], per_domain: int, skip_per_domain: int = 0) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        domain = str(row.get("scenario_domain") or row.get("source") or "unknown")
        buckets[domain].append(row)

    selected: list[dict[str, Any]] = []
    for domain in sorted(buckets):
        selected.extend(buckets[domain][skip_per_domain : skip_per_domain + per_domain])
    return selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(DEFAULT_IN))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--per-domain", type=int, default=5)
    parser.add_argument("--skip-per-domain", type=int, default=0)
    args = parser.parse_args()

    rows = read_jsonl(Path(args.input))
    selected = sample_by_domain(rows, per_domain=args.per_domain, skip_per_domain=args.skip_per_domain)
    written = write_jsonl(Path(args.out), selected)
    report = {
        "input": str(args.input),
        "output": str(args.out),
        "row_count": written,
        "per_domain": args.per_domain,
        "skip_per_domain": args.skip_per_domain,
        "source_counts": count_by(selected, "source"),
        "domain_counts": count_by(selected, "scenario_domain"),
        "family_counts": count_by(selected, "scenario_family"),
        "assistant_answers_used": any(
            bool(row.get("sanitization", {}).get("assistant_answer_used")) for row in selected
        ),
        "with_attribution": sum(1 for row in selected if row.get("attribution", {}).get("item_url")),
        "training_targets_created": False,
        "shadow_only": True,
    }
    dump_json(Path(args.report), report)
    print(f"row_count={written}")
    print("domain_counts=" + json.dumps(report["domain_counts"], ensure_ascii=False, sort_keys=True))
    print("family_counts=" + json.dumps(report["family_counts"], ensure_ascii=False, sort_keys=True))
    print(f"out={args.out}")
    print(f"report={args.report}")
    return 0 if written else 1


if __name__ == "__main__":
    raise SystemExit(main())

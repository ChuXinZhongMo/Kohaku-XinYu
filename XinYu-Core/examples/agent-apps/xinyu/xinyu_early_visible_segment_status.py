from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from xinyu_early_visible_segment import CANARY_REVIEW_ACCEPTANCE_RATE_PCT
from xinyu_early_visible_segment import MIN_CANARY_REVIEW_ELIGIBLE
from xinyu_early_visible_segment import SUMMARY_WINDOW_ROWS
from xinyu_early_visible_segment import summarize_early_visible_segment_shadow


READY_STATE = "ready_for_owner_private_canary_review"


def build_status_report(root: Path | str, *, max_rows: int = SUMMARY_WINDOW_ROWS) -> dict[str, Any]:
    root_path = Path(root)
    summary = summarize_early_visible_segment_shadow(root_path, max_rows=max_rows)
    readiness = str(summary.get("canary_readiness") or "collect_more_shadow")
    eligible_count = _safe_int(summary.get("eligible_count"))
    acceptance_rate_pct = _safe_int(summary.get("acceptance_rate_pct"))
    privacy_violation_count = _safe_int(summary.get("privacy_violation_count"))
    top_reasons = _safe_list(summary.get("top_reasons"))

    blocking_reasons: list[str] = []
    missing_eligible_count = max(0, MIN_CANARY_REVIEW_ELIGIBLE - eligible_count)
    if privacy_violation_count:
        blocking_reasons.append("privacy_violation_count")
    if missing_eligible_count:
        blocking_reasons.append("eligible_count_below_minimum")
    if any(str(item).startswith("mechanic_or_backend_leak:") for item in top_reasons):
        blocking_reasons.append("mechanic_or_backend_leak_observed")
    if eligible_count and acceptance_rate_pct < CANARY_REVIEW_ACCEPTANCE_RATE_PCT:
        blocking_reasons.append("acceptance_rate_below_threshold")
    if readiness != READY_STATE and not blocking_reasons:
        blocking_reasons.append(readiness)

    return {
        "ok": True,
        "root": str(root_path),
        "shadow_only": True,
        "no_outbox_send": True,
        "canary_review_ready": readiness == READY_STATE and not blocking_reasons,
        "readiness": readiness,
        "blocking_reasons": blocking_reasons,
        "thresholds": {
            "min_eligible_count": MIN_CANARY_REVIEW_ELIGIBLE,
            "min_acceptance_rate_pct": CANARY_REVIEW_ACCEPTANCE_RATE_PCT,
            "window_rows": max_rows,
        },
        "missing_eligible_count": missing_eligible_count,
        "summary": summary,
    }


def render_text_report(report: dict[str, Any]) -> str:
    summary = _safe_dict(report.get("summary"))
    thresholds = _safe_dict(report.get("thresholds"))
    top_reasons = _safe_list(summary.get("top_reasons"))
    blocking_reasons = _safe_list(report.get("blocking_reasons"))
    lines = [
        "XinYu Early Visible Segment Shadow",
        f"readiness: {_safe_str(report.get('readiness'), 'unknown')}",
        f"canary_review_ready: {_bool_text(report.get('canary_review_ready'))}",
        f"shadow_only: {_bool_text(report.get('shadow_only'))}",
        f"no_outbox_send: {_bool_text(report.get('no_outbox_send'))}",
        (
            "samples: "
            f"eligible={_safe_int(summary.get('eligible_count'))}/{_safe_int(thresholds.get('min_eligible_count'))} "
            f"window_rows={_safe_int(summary.get('window_rows'))}"
        ),
        (
            "decisions: "
            f"accepted={_safe_int(summary.get('accepted_shadow_count'))} "
            f"rejected={_safe_int(summary.get('rejected_shadow_count'))} "
            f"no_candidate={_safe_int(summary.get('no_candidate_count'))} "
            f"not_eligible={_safe_int(summary.get('not_eligible_count'))}"
        ),
        (
            "quality: "
            f"acceptance_rate_pct={_safe_int(summary.get('acceptance_rate_pct'))} "
            f"threshold={_safe_int(thresholds.get('min_acceptance_rate_pct'))}"
        ),
        (
            "latency: "
            f"avg_elapsed_ms={_safe_int(summary.get('avg_elapsed_ms'))} "
            f"p95_elapsed_ms={_safe_int(summary.get('p95_elapsed_ms'))}"
        ),
        (
            "privacy: "
            f"violation_count={_safe_int(summary.get('privacy_violation_count'))} "
            f"raw_user_text_saved={_bool_text(summary.get('raw_user_text_saved'))} "
            f"raw_segment_saved={_bool_text(summary.get('raw_segment_saved'))}"
        ),
        f"top_reasons: {', '.join(str(item) for item in top_reasons) if top_reasons else 'none'}",
        f"blocking_reasons: {', '.join(str(item) for item in blocking_reasons) if blocking_reasons else 'none'}",
        f"missing_eligible_count: {_safe_int(report.get('missing_eligible_count'))}",
        f"next_action: {_safe_str(summary.get('next_action'), 'collect_shadow_observations')}",
    ]
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only early visible segment shadow readiness report.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--max-rows", type=int, default=SUMMARY_WINDOW_ROWS)
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    parser.add_argument("--require-ready", action="store_true", help="Exit non-zero unless canary review is ready.")
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args()
    report = build_status_report(args.root.resolve(), max_rows=max(1, args.max_rows))
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_text_report(report))
    if args.require_ready and not report.get("canary_review_ready"):
        return 1
    return 0


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return default


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value)
    return text if text else default


def _bool_text(value: Any) -> str:
    return "true" if bool(value) else "false"


if __name__ == "__main__":
    raise SystemExit(main())

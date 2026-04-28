from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig", errors="replace")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def extract_value(block: str, field: str, default: str = "unknown") -> str:
    match = re.search(rf"(?m)^- {re.escape(field)}:\s*(.+)$", block)
    return match.group(1).strip() if match else default


def split_requests(text: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    pattern = re.compile(r"(?ms)^## (?P<id>request-[^\n]+)\n(?P<body>.*?)(?=^## |\Z)")
    for match in pattern.finditer(text):
        body = match.group("body")
        items.append(
            {
                "id": match.group("id").strip(),
                "question_id": extract_value(body, "question_id"),
                "target": extract_value(body, "target"),
                "query": extract_value(body, "query"),
                "url": extract_value(body, "url", ""),
                "status": extract_value(body, "status"),
                "source_policy": extract_value(body, "source_policy"),
            }
        )
    return items


def owner_followthrough_granted(root: Path) -> bool:
    grants = read_text(root / "memory/context/owner_permission_grants.md")
    return (
        "grant_research_ready_request_followthrough: approved_fetch_compare_integrate_for_existing_ai_domain_ready_requests"
        in grants
        or "grant_high_autonomy_learning_search: approved_budgeted_ai_domain_and_quality_followup_search_through_gates"
        in grants
    )


def render_state(
    *,
    evaluated_at: str,
    mode: str,
    ai_requests: list[dict[str, str]],
    followthrough_granted: bool,
) -> str:
    planned_lines: list[str] = []
    next_action = (
        "approved_fetch_compare_integrate_through_gates"
        if followthrough_granted
        else "owner_visible_review_before_fetch_or_learning"
    )
    for item in ai_requests:
        planned_lines.append(
            "\n".join(
                [
                    f"## planned-{item['id']}",
                    f"- request_id: {item['id']}",
                    f"- question_id: {item['question_id']}",
                    f"- target: {item['target']}",
                    f"- query: {item['query']}",
                    f"- url: {item['url']}",
                    f"- status: {item['status']}",
                    f"- next_action: {next_action}",
                ]
            )
        )
    planned = "\n\n".join(planned_lines) if planned_lines else "- none"
    dry_run_permission = (
        "owner_approved_ready_request_followthrough"
        if followthrough_granted
        else "observe_only"
    )
    reason = (
        "owner_approved_existing_ai_domain_ready_request_followthrough"
        if followthrough_granted
        else "planning_ai_domain_source_work_without_live_search"
    )
    return f"""---
title: AI Research Loop Dry-Run State
memory_type: research_loop_dry_run_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-26T17:25:00+08:00
updated_at: {evaluated_at}
importance_score: 82
impact_score: 84
confidence_score: 94
status: active
tags: [knowledge, ai, research, dry_run]
---

# AI Research Loop Dry-Run State

## Last Dry Run
- evaluated_at: {evaluated_at}
- mode: {mode}
- dry_run_permission: {dry_run_permission}
- reason: {reason}
- ai_domain_ready_requests: {len(ai_requests)}
- planned_queries: {len({item['query'] for item in ai_requests})}

## Planned AI-Domain Source Work
{planned}

## Boundaries
- This state is for planning and owner-visible thoughts only.
- It does not search the web by itself.
- It does not fetch pages by itself.
- It does not learn or rewrite stable self memory.
- Owner-approved follow-through still means fetch, comparison, learner integration, and learning-quality gates must run before any knowledge-only result is accepted.
- Any live provider search still requires autonomous search activation and source gates.
"""


def run_research_loop_dry_run(
    root: Path,
    *,
    evaluated_at: str | None = None,
    mode: str = "runtime_research_loop_dry_run",
) -> dict[str, object]:
    evaluated_at = evaluated_at or datetime.now().astimezone().isoformat()
    requests = split_requests(read_text(root / "memory/knowledge/source_requests.md"))
    ai_requests = [
        item
        for item in requests
        if item.get("target") == "ai-self-understanding" and item.get("status") == "ready"
    ]
    followthrough_granted = owner_followthrough_granted(root)
    write_text(
        root / "memory/knowledge/research_loop_dry_run_state.md",
        render_state(
            evaluated_at=evaluated_at,
            mode=mode,
            ai_requests=ai_requests,
            followthrough_granted=followthrough_granted,
        ),
    )
    return {
        "evaluated_at": evaluated_at,
        "ai_domain_ready_requests": len(ai_requests),
        "planned_queries": len({item["query"] for item in ai_requests}),
        "followthrough_granted": followthrough_granted,
        "wrote_state": True,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Plan AI-domain research loop without live search or fetch.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = run_research_loop_dry_run(args.root.resolve())
    print("AI research loop dry-run state written")
    print(f"ai_domain_ready_requests: {result['ai_domain_ready_requests']}")
    print(f"planned_queries: {result['planned_queries']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

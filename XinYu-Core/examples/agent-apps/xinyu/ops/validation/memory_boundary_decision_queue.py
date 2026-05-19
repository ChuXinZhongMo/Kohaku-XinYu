from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from memory_library_cases_audit import BoundaryRecord, collect_boundary_records


@dataclass(frozen=True)
class DecisionRule:
    priority: str
    action: str
    target_boundary: str
    handling: str


RULES: dict[str, DecisionRule] = {
    "structured_data_inside_memory_review": DecisionRule(
        priority="P0",
        action="classify_structured_memory_file",
        target_boundary="memory/stores/runtime",
        handling=(
            "Decide whether this is stable retrievable memory, a durable store, or runtime/cache data "
            "before moving anything."
        ),
    ),
    "external_dataset_source_inside_memory": DecisionRule(
        priority="P0",
        action="move_public_source_toward_library",
        target_boundary="library",
        handling="If this is public/source material, migrate to library after reference checks; do not mix with private memory.",
    ),
    "library_file_has_memory_frontmatter": DecisionRule(
        priority="P1",
        action="remove_memory_semantics_from_library_or_move",
        target_boundary="library/memory",
        handling="Either strip memory frontmatter from public material or move the file into canonical memory after review.",
    ),
    "case_file_declares_non_case_memory_type": DecisionRule(
        priority="P1",
        action="normalize_case_metadata",
        target_boundary="cases",
        handling="Keep as case data only if it is an example; otherwise move to the correct memory boundary after review.",
    ),
    "runtime_file_has_stable_memory_frontmatter": DecisionRule(
        priority="P2",
        action="review_runtime_snapshot",
        target_boundary="runtime/archive",
        handling="Treat as a runtime copy or test artifact until proven canonical; do not promote it to stable memory automatically.",
    ),
    "legacy_fallback_review": DecisionRule(
        priority="P3",
        action="keep_or_archive_legacy_fallback",
        target_boundary="compat/archive",
        handling="Keep as compatibility fallback until live callers are audited; archive only after reference checks.",
    ),
}

DEFAULT_RULE = DecisionRule(
    priority="P9",
    action="manual_boundary_review",
    target_boundary="manual",
    handling="Review manually before changing boundaries.",
)


def build_decision_queue(records: list[BoundaryRecord]) -> dict[str, object]:
    items = []
    for record in records:
        if not record.concern:
            continue
        rule = RULES.get(record.concern, DEFAULT_RULE)
        items.append(
            {
                "priority": rule.priority,
                "path": record.path,
                "zone": record.zone,
                "declared_type": record.declared_type,
                "concern": record.concern,
                "action": rule.action,
                "target_boundary": rule.target_boundary,
                "handling": rule.handling,
                "safe_default": "review_only_no_auto_delete",
            }
        )

    items.sort(key=lambda item: (str(item["priority"]), str(item["concern"]), str(item["path"])))
    return {
        "total_review_items": len(items),
        "by_priority": dict(sorted(Counter(str(item["priority"]) for item in items).items())),
        "by_concern": dict(sorted(Counter(str(item["concern"]) for item in items).items())),
        "by_action": dict(sorted(Counter(str(item["action"]) for item in items).items())),
        "items": items,
        "privacy_note": "Generated from paths and small frontmatter metadata only; bodies and raw source values are not printed.",
    }


def render_markdown(queue: dict[str, object], max_items: int | None = None) -> str:
    lines = [
        "# XinYu Memory Boundary Decision Queue",
        "",
        "Generated from boundary audit records using paths and small frontmatter metadata only.",
        "It does not print memory bodies, raw QQ content, tokens, secrets, or raw source values.",
        "",
        f"- total_review_items: {queue['total_review_items']}",
        "",
        "## Priority Counts",
        "",
    ]
    for priority, count in (queue.get("by_priority") or {}).items():
        lines.append(f"- {priority}: {count}")
    lines.extend(["", "## Concern Counts", ""])
    for concern, count in (queue.get("by_concern") or {}).items():
        lines.append(f"- {concern}: {count}")
    lines.extend(["", "## Action Counts", ""])
    for action, count in (queue.get("by_action") or {}).items():
        lines.append(f"- {action}: {count}")
    lines.extend(["", "## Review Items", ""])
    items = list(queue.get("items") or [])
    if max_items is not None:
        items = items[:max_items]
    if not items:
        lines.append("- none")
    else:
        for item in items:
            lines.append(
                f"- `{item['path']}` | priority={item['priority']} | zone={item['zone']} | "
                f"type={item['declared_type'] or 'none'} | concern={item['concern']} | "
                f"action={item['action']} | target={item['target_boundary']}"
            )
    omitted = int(queue["total_review_items"]) - len(items)
    if omitted > 0:
        lines.extend(["", f"_Omitted {omitted} lower display items; JSON contains the full queue._"])
    lines.extend(
        [
            "",
            "## Safety Rule",
            "",
            "- Every item defaults to `review_only_no_auto_delete`.",
            "- Move, archive, or delete only after reference checks and per-file review.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a review-only decision queue for XinYu memory boundaries.")
    parser.add_argument("--repo-root", default="D:\\XinYu")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output", default="")
    parser.add_argument("--max-items", type=int, default=120)
    return parser


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = _build_parser().parse_args()
    queue = build_decision_queue(collect_boundary_records(Path(args.repo_root)))
    rendered = (
        json.dumps(queue, ensure_ascii=False, indent=2) + "\n"
        if args.json
        else render_markdown(queue, max_items=args.max_items)
    )
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

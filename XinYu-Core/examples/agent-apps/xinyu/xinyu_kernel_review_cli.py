"""CLI for Cognitive Kernel owner review inbox (K-010 desktop panel)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from kernel.bridge_access import apply_kernel_owner_reviews, grant_kernel_owner_scope, query_kernel_state
from kernel.owner_grants import load_owner_grants

_ALL_GRANT_SCOPES = ("self_model", "belief", "world_model", "reorganization")


def _granted_scopes(root: Path) -> list[str]:
    data = load_owner_grants(root)
    scopes: set[str] = set()
    for entry in data.get("grants", []):
        scope = entry.get("scope")
        if scope == "all":
            return list(_ALL_GRANT_SCOPES)
        if scope in _ALL_GRANT_SCOPES:
            scopes.add(scope)
    return sorted(scopes)


def _root_path(value: Path) -> Path:
    return value.resolve()


def kernel_governance_status(root: Path) -> dict[str, Any]:
    """Read-only kernel governance snapshot for desktop / status."""
    state = query_kernel_state(root)
    inbox = state.get("review_inbox") if isinstance(state.get("review_inbox"), dict) else {}
    meta = state.get("reorg_meta") if isinstance(state.get("reorg_meta"), dict) else {}
    return {
        "ok": bool(state.get("available")),
        "available": bool(state.get("available")),
        "loadedAt": __import__("datetime").datetime.now().astimezone().isoformat(timespec="seconds"),
        "self_id": state.get("self_id", ""),
        "error": state.get("error", ""),
        "pending_count": int(inbox.get("pending_count", 0)),
        "world_model_count": int(inbox.get("world_model_count", 0)),
        "reorganization_count": int(inbox.get("reorganization_count", 0)),
        "belief_count": int(inbox.get("belief_count", 0)),
        "followup_count": int(inbox.get("followup_count", 0)),
        "writes_blocked": bool(inbox.get("writes_blocked", False)),
        "items": inbox.get("items", []) if isinstance(inbox.get("items"), list) else [],
        "cycle_count": int(state.get("cycle_count", 0)),
        "slow_signal_count": int(state.get("slow_signal_count", 0)),
        "slow_escalation_threshold": int(meta.get("slow_escalation_threshold", 3)),
        "reorg_recommendation": str(meta.get("recommendation", "insufficient_data")),
        "reorg_meta": meta,
        "self_story_summary": str(state.get("self_story_summary", "")),
        "core_statements_count": int(state.get("core_statements_count", 0)),
        "active_goals_count": int(state.get("active_goals_count", 0)),
        "stable_beliefs_count": int(state.get("stable_beliefs_count", 0)),
        "world_facts_count": int(state.get("world_facts_count", 0)),
        "granted_scopes": _granted_scopes(root),
        "grantable_scopes": [s for s in _ALL_GRANT_SCOPES if s not in _granted_scopes(root)],
    }


def apply_kernel_review(
    root: Path,
    *,
    domain: str,
    item_id: str,
    action: str = "approve",
) -> dict[str, Any]:
    result = apply_kernel_owner_reviews(
        root,
        [{"domain": domain, "item_id": item_id, "action": action}],
    )
    first = result.get("results", [{}])[0] if isinstance(result.get("results"), list) else {}
    inbox = result.get("review_inbox") if isinstance(result.get("review_inbox"), dict) else {}
    applied = bool(first.get("applied"))
    rejected = bool(first.get("rejected"))
    return {
        "ok": applied or rejected,
        "applied": applied,
        "rejected": rejected,
        "domain": domain,
        "item_id": item_id,
        "action": action,
        "detail": first,
        "pending_count": int(inbox.get("pending_count", 0)),
        "review_inbox": inbox,
    }


def grant_kernel_scope(root: Path, *, scope: str, note: str = "") -> dict[str, Any]:
    result = grant_kernel_owner_scope(root, scope, note=note)
    status = kernel_governance_status(root)
    return {"ok": True, "grant": result, **status}


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Cognitive Kernel owner review CLI.")
    parser.add_argument("--root", type=_root_path, default=_root_path(Path(__file__).resolve().parent))
    sub = parser.add_subparsers(dest="command", required=True)

    status_parser = sub.add_parser("status")
    status_parser.add_argument("--json", action="store_true")

    apply_parser = sub.add_parser("apply")
    apply_parser.add_argument(
        "--domain",
        required=True,
        choices=["world_model", "reorganization", "belief", "self_model", "followup"],
    )
    apply_parser.add_argument("--item-id", required=True)
    apply_parser.add_argument("--action", default="approve", choices=["approve", "reject"])

    grant_parser = sub.add_parser("grant")
    grant_parser.add_argument("--scope", required=True, choices=["self_model", "belief", "world_model", "reorganization", "all"])
    grant_parser.add_argument("--note", default="")

    args = parser.parse_args(argv)
    root: Path = args.root

    if args.command == "status":
        result = kernel_governance_status(root)
    elif args.command == "apply":
        result = apply_kernel_review(root, domain=args.domain, item_id=args.item_id, action=args.action)
    else:
        result = grant_kernel_scope(root, scope=args.scope, note=args.note)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
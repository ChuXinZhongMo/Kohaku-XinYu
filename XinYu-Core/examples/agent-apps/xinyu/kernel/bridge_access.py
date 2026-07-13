"""Safe read/write paths from bridge to Cognitive Kernel (K-010)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .bridge_governance import apply_kernel_owner_review, get_kernel_review_inbox
from .bridge_integration import get_kernel_context
from .cognitive_cycle import run_full_cognitive_cycle
from .meta_learning import load_reorg_meta
from .runtime_self import get_or_create_runtime_self, persist_runtime_self, RUNTIME_SELF_ID
from .self import Self


def resolve_runtime_self(root: Path | None = None) -> Self:
    """Load or create the persistent runtime Self."""
    return get_or_create_runtime_self(root)


def query_kernel_state(root: Path | None = None) -> dict[str, Any]:
    """Read-only kernel snapshot for bridge / status / desktop."""
    try:
        s = resolve_runtime_self(root)
        inbox = get_kernel_review_inbox(s, root)
        ctx = get_kernel_context(s)
        story_summary = ""
        if root is not None:
            state_path = root / "memory" / "kernel" / "self_story_state.json"
            if state_path.exists():
                try:
                    import json

                    story_summary = json.loads(state_path.read_text(encoding="utf-8")).get("summary", "")
                except Exception:
                    pass

        return {
            "available": True,
            "self_id": s.self_id,
            "self_story_summary": story_summary[:300],
            "core_statements_count": len(s.get_self_model().get("core_statements", [])),
            "active_goals_count": len(s.get_active_goals()),
            "stable_beliefs_count": len(s.get_stable_beliefs(0.6)),
            "world_facts_count": len(s.world_model.facts),
            "working_memory_size": len(s.get_working_memory()),
            "cycle_count": s.cognitive_cycle_state.cycle_count,
            "slow_signal_count": s.cognitive_cycle_state.slow_signal_count,
            "review_inbox": inbox,
            "reorg_meta": load_reorg_meta(root) if root else {},
            "kernel_context": {
                "world_context": ctx.get("world_context", ""),
                "attention_context": ctx.get("attention_context", ""),
                "pending_reorg_count": ctx.get("pending_reorg_count", 0),
            },
        }
    except Exception as exc:
        return {"available": False, "self_id": RUNTIME_SELF_ID, "error": str(exc)}


def run_kernel_turn_update(
    root: Path,
    event_input: dict[str, Any],
    *,
    outcome_reality: str | None = None,
    source_event_id: str = "unknown",
) -> dict[str, Any]:
    """Controlled write: run full cognitive cycle and persist."""
    s = resolve_runtime_self(root)
    result = run_full_cognitive_cycle(
        s,
        event_input,
        outcome_reality=outcome_reality,
        source_event_id=source_event_id,
        event_root=root,
        persist=True,
    )
    result["review_inbox"] = get_kernel_review_inbox(s, root)
    return result


def apply_kernel_owner_reviews(
    root: Path,
    reviews: list[dict[str, Any]],
) -> dict[str, Any]:
    """Controlled write: batch owner review actions, then persist."""
    s = resolve_runtime_self(root)
    results = []
    for item in reviews:
        res = apply_kernel_owner_review(
            s,
            domain=item.get("domain", "reorganization"),
            item_id=str(item.get("item_id", "")),
            action=item.get("action", "approve"),
            root=root,
        )
        results.append(res)
    persist_runtime_self(s, root)
    return {
        "processed": len(results),
        "results": results,
        "review_inbox": get_kernel_review_inbox(s, root),
    }


def grant_kernel_owner_scope(
    root: Path,
    scope: str,
    *,
    note: str = "",
    event_id: str | None = None,
) -> dict[str, Any]:
    """Controlled write: record explicit owner grant for a kernel domain."""
    from .owner_grants import grant_owner_scope

    return grant_owner_scope(root, scope, note=note, event_id=event_id)  # type: ignore[arg-type]
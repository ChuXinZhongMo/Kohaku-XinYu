"""Kernel governance status for bridge / xinyu_status (K-010)."""

from __future__ import annotations

from pathlib import Path
from typing import Any


_ALL_GRANT_SCOPES = ("self_model", "belief", "world_model", "reorganization")


def _granted_scopes(root: Path) -> list[str]:
    from kernel.owner_grants import load_owner_grants

    data = load_owner_grants(root)
    scopes: set[str] = set()
    for entry in data.get("grants", []):
        scope = entry.get("scope")
        if scope == "all":
            return list(_ALL_GRANT_SCOPES)
        if scope in _ALL_GRANT_SCOPES:
            scopes.add(scope)
    return sorted(scopes)


def build_kernel_governance_status(root: Path) -> dict[str, Any]:
    try:
        from kernel.bridge_access import query_kernel_state

        state = query_kernel_state(root)
        inbox = state.get("review_inbox") or {}
        meta = state.get("reorg_meta") if isinstance(state.get("reorg_meta"), dict) else {}
        return {
            "available": state.get("available", False),
            "self_id": state.get("self_id"),
            "cycle_count": state.get("cycle_count", 0),
            "slow_signal_count": state.get("slow_signal_count", 0),
            "slow_escalation_threshold": int(meta.get("slow_escalation_threshold", 3)),
            "reorg_recommendation": str(meta.get("recommendation", "insufficient_data")),
            "fast_impact_rate": float(meta.get("fast_impact_rate", 0.0)),
            "slow_impact_rate": float(meta.get("slow_impact_rate", 0.0)),
            "pending_review_count": inbox.get("pending_count", 0),
            "world_model_pending": inbox.get("world_model_count", 0),
            "reorganization_pending": inbox.get("reorganization_count", 0),
            "belief_pending": inbox.get("belief_count", 0),
            "writes_blocked": inbox.get("writes_blocked", False),
            "working_memory_size": state.get("working_memory_size", 0),
            "self_story_summary": (state.get("self_story_summary") or "")[:120],
            "granted_scopes": _granted_scopes(root),
        }
    except Exception as exc:
        return {"available": False, "error": str(exc)}
"""Owner governance for Cognitive Kernel (K-010).

Unified review inbox and apply paths for all Self-owned structures:
Self Model, Beliefs, World Model, Reorg proposals.
"""

from __future__ import annotations

from typing import Any, Literal

from .self import Self

ReviewDomain = Literal["world_model", "reorganization", "belief", "self_model", "followup"]
ReviewAction = Literal["approve", "reject"]


def owner_review_gate_for_belief(content: str, confidence: float = 0.5) -> str:
    """Returns stable | candidate | review_only."""
    text = content.lower()
    high_impact = ("identity", "trust", "boundary", "core", "promise", "honesty", "owner")
    if confidence >= 0.85 and any(kw in text for kw in high_impact):
        return "review_only"
    if confidence >= 0.7 or any(kw in text for kw in high_impact):
        return "candidate"
    return "stable"


def owner_review_gate_for_self_model(proposal_type: str, content: str, confidence: float = 0.5) -> str:
    text = content.lower()
    if proposal_type in ("boundary", "identity") or confidence >= 0.8:
        return "review_only"
    if proposal_type in ("core_value", "self_observation") or confidence >= 0.65:
        return "candidate"
    if any(kw in text for kw in ("identity", "trust", "boundary", "core")):
        return "review_only"
    return "stable"


def _effective_review_status(domain: str, status: str, root: Any = None) -> str:
    if status != "review_only" or root is None:
        return status
    try:
        from .owner_grants import is_scope_granted

        scope_map = {
            "world_model": "world_model",
            "reorganization": "reorganization",
            "belief": "belief",
        }
        scope = scope_map.get(domain)
        if scope and is_scope_granted(root, scope):  # type: ignore[arg-type]
            return "candidate"
    except Exception:
        pass
    return status


def _load_followup_inbox_items(root: Any) -> list[dict[str, Any]]:
    if root is None:
        return []
    try:
        from pathlib import Path

        from xinyu_action_followup_proposals import load_followup_inbox

        items = []
        for row in load_followup_inbox(Path(root)):
            if str(row.get("review_status", "pending")).strip() != "pending":
                continue
            items.append(
                {
                    "domain": "followup",
                    "item_id": str(row.get("item_id", "")),
                    "content_preview": str(row.get("content_preview") or row.get("candidate", ""))[:120],
                    "proposal_kind": row.get("proposal_kind", "next_safe_challenge"),
                    "target_ecology": row.get("target_ecology", "maintenance"),
                    "review_status": "candidate",
                    "why_now": str(row.get("why_now", ""))[:120],
                }
            )
        return items
    except Exception:
        return []


def get_kernel_review_inbox(kernel_self: Self, root: Any = None) -> dict[str, Any]:
    """Aggregate pending owner-review items across kernel domains."""
    wm_pending = [
        {
            "domain": "world_model",
            "item_id": f["fact_id"],
            "content_preview": f["content"][:120],
            "confidence": f.get("confidence", 0.5),
            "review_status": _effective_review_status("world_model", "review_only", root),
        }
        for f in kernel_self.get_pending_world_facts()
    ]
    reorg_pending = [
        {
            "domain": "reorganization",
            "item_id": p["proposal_id"],
            "action_type": p.get("action_type"),
            "content_preview": p.get("content", "")[:120],
            "review_status": p.get("review_status", "review_only"),
            "source_event_id": p.get("source_event_id"),
        }
        for p in kernel_self.get_pending_reorg_proposals()
    ]
    belief_pending = [
        {
            "domain": "belief",
            "item_id": b.belief_id,
            "content_preview": b.content[:120],
            "confidence": b.confidence,
            "review_status": "candidate" if b.status == "candidate" else "stable",
        }
        for b in kernel_self.belief_engine.beliefs
        if b.status == "candidate" and b.confidence >= 0.65
    ]

    followup_pending = _load_followup_inbox_items(root)
    items = wm_pending + reorg_pending + belief_pending + followup_pending
    return {
        "pending_count": len(items),
        "world_model_count": len(wm_pending),
        "reorganization_count": len(reorg_pending),
        "belief_count": len(belief_pending),
        "followup_count": len(followup_pending),
        "items": items,
        "writes_blocked": len(items) > 0,
    }


def apply_kernel_owner_review(
    kernel_self: Self,
    *,
    domain: ReviewDomain,
    item_id: str,
    action: ReviewAction = "approve",
    root: Any = None,
) -> dict[str, Any]:
    """Explicit owner apply/reject for a pending kernel change."""
    if domain == "followup":
        if root is None:
            return {"applied": False, "rejected": False, "reason": "root_required", "domain": domain}
        try:
            from pathlib import Path

            from xinyu_action_followup_proposals import update_followup_review_status

            result = update_followup_review_status(Path(root), item_id, action=action)
            return {
                "applied": action == "approve" and bool(result.get("updated")),
                "rejected": action == "reject" and bool(result.get("updated")),
                "domain": domain,
                "item_id": item_id,
                "detail": result,
            }
        except Exception as exc:
            return {"applied": False, "rejected": False, "reason": str(exc), "domain": domain}

    if action == "reject":
        if domain == "reorganization":
            kernel_self.reorganization_loop.pending_proposals = [
                p for p in kernel_self.reorganization_loop.pending_proposals if p.proposal_id != item_id
            ]
            return {"applied": False, "rejected": True, "domain": domain, "item_id": item_id}
        if domain == "world_model":
            kernel_self.world_model.pending_review_facts = [
                f for f in kernel_self.world_model.pending_review_facts if f.fact_id != item_id
            ]
            return {"applied": False, "rejected": True, "domain": domain, "item_id": item_id}
        if domain == "belief":
            for b in kernel_self.belief_engine.beliefs:
                if b.belief_id == item_id:
                    b.status = "rejected"
                    return {"applied": False, "rejected": True, "domain": domain, "item_id": item_id}
        return {"applied": False, "rejected": False, "reason": "item_not_found", "domain": domain}

    if domain == "world_model":
        ok = kernel_self.apply_reviewed_world_fact(item_id)
        return {"applied": ok, "domain": domain, "item_id": item_id}
    if domain == "reorganization":
        return {**kernel_self.apply_reviewed_reorg(item_id), "domain": domain}
    if domain == "belief":
        for b in kernel_self.belief_engine.beliefs:
            if b.belief_id == item_id:
                b.status = "stable"
                return {"applied": True, "domain": domain, "item_id": item_id}
        return {"applied": False, "reason": "belief_not_found", "domain": domain}
    return {"applied": False, "reason": "unsupported_domain", "domain": domain}
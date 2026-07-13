"""Bridge integration helpers for Cognitive Kernel (K-007+).

Provides safe, non-breaking ways for the runtime bridge to:
- Get enriched context from Self (World Model, Beliefs, Attention, Goals)
- Trigger updates from turn outcomes/experiences

Keep kernel decoupled; bridge decides when/how to call.
"""

from __future__ import annotations

from typing import Any

from .self import Self


def get_kernel_context(kernel_self: Self) -> dict[str, Any]:
    """Return compact kernel context for prompts, narrative, codex, etc."""
    return {
        "self_model": kernel_self.get_self_model(),
        "active_goals": [g.model_dump() for g in kernel_self.get_active_goals(3)],
        "working_memory": kernel_self.get_working_memory(),
        "stable_beliefs": kernel_self.get_stable_beliefs(0.65),
        "world_context": kernel_self.world_model_to_context(),
        "attention_context": kernel_self.attention_to_context(),
        "pending_reorg_count": len(kernel_self.get_pending_reorg_proposals()),
    }


def augment_text_with_kernel_context(text: str, kernel_self: Self, prefix: str = "Kernel context:") -> str:
    """Augment prompt/text with kernel summary. Use sparingly."""
    ctx = get_kernel_context(kernel_self)
    parts = [text]
    if ctx.get("world_context"):
        parts.append(f"{prefix} {ctx['world_context']}")
    if ctx.get("attention_context"):
        parts.append(ctx["attention_context"])
    if ctx.get("active_goals"):
        goals = "; ".join(g["description"][:50] for g in ctx["active_goals"])
        parts.append(f"Current motivations: {goals}")
    return "\n\n".join(parts)


def update_kernel_from_turn_outcome(kernel_self: Self, outcome_text: str, source_event_id: str, importance: int = 50) -> dict[str, Any]:
    """After a turn/outcome, update kernel components (World Model, etc.).

    Called from sidecars or post-processing.
    Updates WM after real experience.
    """
    results = {}
    # Update world model from outcome (deeper hook after experience)
    if importance > 40:
        wm_res = kernel_self.update_world_model(
            from_error={"error_magnitude": min(0.9, importance/100.0), "source_event_id": source_event_id, "reality": outcome_text[:200]},
        )
        results["world_model"] = wm_res

    return results

def owner_review_gate_for_world_model(kernel_self: Self, change: dict[str, Any]) -> str:
    """Owner review gate for WM changes (K-007).

    Returns status: 'stable' | 'review_only' | 'candidate'
    High impact changes to World Model (core facts, high error) require explicit owner review.
    This follows existing review patterns in the project (e.g. claims, personality gates).
    """
    impact = float(change.get("error_magnitude", 0) or 0)
    content = str(change.get("reality", "")) + str(change.get("new_facts", ""))
    high_impact_keywords = ["identity", "trust", "boundary", "core", "promise", "honesty"]
    needs_review = (
        impact > 0.75 or
        any(kw in content.lower() for kw in high_impact_keywords)
    )
    if needs_review:
        return "review_only"
    if impact > 0.5:
        return "candidate"
    return "stable"

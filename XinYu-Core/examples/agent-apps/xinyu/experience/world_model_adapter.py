"""World Model adapter for K-007.

Allows high-value data (errors, beliefs, new experiences) to update the generative World Model.
"""

from __future__ import annotations

from typing import Any

from kernel.self import Self


def apply_to_world_model(
    kernel_self: Self | None,
    from_error: dict[str, Any] | None = None,
    new_facts: list[str] | None = None,
    new_rule: str | None = None,
    source_event_id: str | None = None,
) -> dict[str, Any]:
    """Update World Model and optionally trigger reorganization.

    Applies owner review gate for high-impact changes.
    """
    if kernel_self is None:
        return {"updated": False, "reason": "no_kernel_self"}
    from kernel.bridge_integration import owner_review_gate_for_world_model
    change = from_error or {"error_magnitude": 0.5}
    review_status = owner_review_gate_for_world_model(kernel_self, change)

    result = kernel_self.update_world_model(
        from_error=from_error,
        new_facts=new_facts,
        new_rule=new_rule,
    )

    result["review_status"] = review_status
    if review_status == "review_only":
        result["needs_owner_review"] = True

    # If significant change, could propose belief or attention update in full system
    if result.get("updated"):
        result["world_context"] = kernel_self.world_model_to_context()

    # 补细节: after update, sync WM with current Self state (beliefs/goals)
    try:
        kernel_self.sync_world_model()
        kernel_self.reorganize_world_model([from_error] if from_error else [], new_beliefs=None)
    except Exception:
        pass

    return result

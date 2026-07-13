"""Belief adapter for K-006.

Converts high-value Experience results and PredictionErrors into Belief proposals for Self.
"""

from __future__ import annotations

from typing import Any

from kernel.self import Self


def apply_to_beliefs(
    kernel_self: Self,
    proposals: list[dict[str, Any]],
    source_event_id: str,
    min_confidence: float = 0.5,
) -> dict[str, Any]:
    """Feed proposals (from Experience or Error) into Belief Engine.

    Returns summary of accepted beliefs.
    """
    accepted = []
    for p in proposals:
        content = p.get("content", "")
        conf = p.get("confidence", 0.5)
        if conf < min_confidence:
            continue

        res = kernel_self.propose_belief(
            content=content,
            confidence=conf,
            source_event_id=source_event_id,
        )
        if res.get("accepted"):
            accepted.append(res["belief_id"])

    return {
        "accepted_belief_ids": accepted,
        "count": len(accepted),
    }

"""Self Reorganization Loop for Cognitive Kernel (K-008).

Consumes Prediction Errors, Belief updates, and World Model changes, then
propagates structural impact back into Goals, Attention, and memory candidates.

Unlike K-007 WM-internal reorganize, this loop crosses kernel layers and
produces traceable reorg proposals with owner review gates.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

ReorgMode = Literal["fast", "slow", "skip"]
_DEFERRED_SLOW_ACTIONS = frozenset({"goal_priority_adjust", "memory_candidate", "self_model_proposal"})

ReorgActionType = Literal[
    "attention_boost",
    "goal_priority_adjust",
    "memory_candidate",
    "belief_reinforce",
    "self_model_proposal",
]

ReviewStatus = Literal["stable", "candidate", "review_only"]


class ReorgProposal(BaseModel):
    """A single structural change proposed by the reorganization loop."""

    proposal_id: str
    action_type: ReorgActionType
    content: str = Field(max_length=500)
    priority: float = Field(ge=0.0, le=1.0, default=0.5)
    source_event_id: str
    source_signals: list[str] = Field(default_factory=list)
    review_status: ReviewStatus = "candidate"
    payload: dict[str, Any] = Field(default_factory=dict)
    applied: bool = False


_HIGH_IMPACT_KEYWORDS = ("identity", "trust", "boundary", "core", "promise", "honesty", "memory")


def review_status_for_reorg(
    error_magnitude: float = 0.0,
    content: str = "",
    action_type: ReorgActionType = "attention_boost",
) -> ReviewStatus:
    """Owner review gate for reorg proposals (mirrors WM gate pattern)."""
    text = content.lower()
    if action_type == "memory_candidate":
        return "review_only"
    if error_magnitude > 0.75 or any(kw in text for kw in _HIGH_IMPACT_KEYWORDS):
        return "review_only"
    if error_magnitude > 0.5 or action_type in ("self_model_proposal", "goal_priority_adjust"):
        return "candidate"
    return "stable"


class ReorganizationLoop:
    """K-008: cross-layer reorganization owned by Self."""

    def __init__(self, self_id: str):
        self.self_id = self_id
        self.pending_proposals: list[ReorgProposal] = []
        self.applied_history: list[dict[str, Any]] = []
        self._proposal_counter = 0

    def _next_id(self, source_event_id: str) -> str:
        self._proposal_counter += 1
        return f"reorg-{self.self_id[:8]}-{source_event_id[:8]}-{self._proposal_counter}"

    def propose_from_signals(
        self,
        *,
        prediction_error: dict[str, Any] | None = None,
        belief_result: dict[str, Any] | None = None,
        world_model_result: dict[str, Any] | None = None,
        experience_result: dict[str, Any] | None = None,
        source_event_id: str = "unknown",
    ) -> list[ReorgProposal]:
        """Generate reorg proposals from upstream kernel signals."""
        proposals: list[ReorgProposal] = []
        signals: list[str] = []

        if prediction_error:
            signals.append("prediction_error")
            mag = float(prediction_error.get("error_magnitude", 0) or 0)
            reality = str(prediction_error.get("reality", ""))[:300]
            impacts = prediction_error.get("impact_on_self", [])

            if mag >= 0.4 and reality:
                proposals.append(
                    ReorgProposal(
                        proposal_id=self._next_id(source_event_id),
                        action_type="attention_boost",
                        content=reality,
                        priority=min(0.95, 0.5 + mag * 0.4),
                        source_event_id=source_event_id,
                        source_signals=list(signals),
                        review_status=review_status_for_reorg(mag, reality, "attention_boost"),
                        payload={
                            "item_type": "prediction_error",
                            "error_magnitude": mag,
                            "impact_on_self": impacts,
                        },
                    )
                )

            if mag >= 0.55:
                proposals.append(
                    ReorgProposal(
                        proposal_id=self._next_id(source_event_id),
                        action_type="goal_priority_adjust",
                        content=f"Re-prioritize goals after prediction error (mag={mag:.2f})",
                        priority=mag,
                        source_event_id=source_event_id,
                        source_signals=list(signals),
                        review_status=review_status_for_reorg(mag, reality, "goal_priority_adjust"),
                        payload={"delta": min(0.25, mag * 0.2), "impact_keywords": impacts},
                    )
                )

            if mag >= 0.6 and reality:
                proposals.append(
                    ReorgProposal(
                        proposal_id=self._next_id(source_event_id),
                        action_type="memory_candidate",
                        content=reality,
                        priority=mag,
                        source_event_id=source_event_id,
                        source_signals=list(signals),
                        review_status=review_status_for_reorg(mag, reality, "memory_candidate"),
                        payload={"candidate_type": "experience_derived", "importance": int(mag * 100)},
                    )
                )

            feedback = prediction_error.get("self_proposal_feedback") or {}
            if feedback.get("should_propose"):
                for p in feedback.get("proposals", []):
                    proposals.append(
                        ReorgProposal(
                            proposal_id=self._next_id(source_event_id),
                            action_type="self_model_proposal",
                            content=str(p.get("content", ""))[:400],
                            priority=float(p.get("confidence", 0.6)),
                            source_event_id=source_event_id,
                            source_signals=list(signals),
                            review_status=review_status_for_reorg(
                                mag, str(p.get("content", "")), "self_model_proposal"
                            ),
                            payload={
                                "proposal_type": p.get("proposal_type", "self_observation"),
                                "confidence": p.get("confidence", 0.6),
                            },
                        )
                    )

        if belief_result and belief_result.get("count", 0) > 0:
            signals.append("belief")
            for bid in belief_result.get("accepted_belief_ids", []):
                proposals.append(
                    ReorgProposal(
                        proposal_id=self._next_id(source_event_id),
                        action_type="belief_reinforce",
                        content=f"Reinforce belief {bid} after experience cycle",
                        priority=0.65,
                        source_event_id=source_event_id,
                        source_signals=list(signals),
                        review_status="stable",
                        payload={"belief_id": bid, "delta": 0.05},
                    )
                )

        if world_model_result and world_model_result.get("updated"):
            signals.append("world_model")
            wm_ctx = str(world_model_result.get("world_context", ""))[:300]
            mag = float(
                (prediction_error or {}).get("error_magnitude", 0)
                or world_model_result.get("error_magnitude", 0.5)
            )
            if wm_ctx:
                proposals.append(
                    ReorgProposal(
                        proposal_id=self._next_id(source_event_id),
                        action_type="attention_boost",
                        content=wm_ctx,
                        priority=0.55,
                        source_event_id=source_event_id,
                        source_signals=list(signals),
                        review_status=review_status_for_reorg(
                            mag, wm_ctx, "attention_boost"
                        ),
                        payload={"item_type": "world_model", "affected_facts": world_model_result.get("affected_facts", [])},
                    )
                )

        if experience_result:
            signals.append("experience")
            importance = int(experience_result.get("importance_score", 0) or 0)
            if importance >= 65:
                for p in experience_result.get("belief_update_proposals", [])[:3]:
                    content = p.get("content", "") if isinstance(p, dict) else getattr(p, "content", "")
                    if not content:
                        continue
                    proposals.append(
                        ReorgProposal(
                            proposal_id=self._next_id(source_event_id),
                            action_type="attention_boost",
                            content=str(content)[:300],
                            priority=min(0.9, importance / 100.0),
                            source_event_id=source_event_id,
                            source_signals=list(signals),
                            review_status=review_status_for_reorg(importance / 100.0, str(content)),
                            payload={"item_type": "experience_proposal"},
                        )
                    )

        for prop in proposals:
            if prop.review_status == "review_only":
                self.pending_proposals.append(prop)
        return proposals

    def apply_proposal(self, kernel_self: Any, proposal: ReorgProposal) -> dict[str, Any]:
        """Apply one reorg proposal to Goals / Attention / Beliefs / Self Model."""
        if proposal.applied:
            return {"applied": False, "reason": "already_applied", "proposal_id": proposal.proposal_id}

        result: dict[str, Any] = {"proposal_id": proposal.proposal_id, "action_type": proposal.action_type}

        if proposal.action_type == "attention_boost":
            from .attention import AttentionItem

            item = AttentionItem(
                item_id=f"reorg-{proposal.proposal_id}",
                content=proposal.content,
                item_type=proposal.payload.get("item_type", "reorg"),
                relevance_score=proposal.priority,
                source_event_id=proposal.source_event_id,
            )
            from_last_error = None
            if proposal.payload.get("error_magnitude"):
                from_last_error = {
                    "error_magnitude": proposal.payload["error_magnitude"],
                    "impact_on_self": proposal.payload.get("impact_on_self", []),
                    "reality": proposal.content,
                }
            kernel_self.update_attention(
                items=[item.model_dump()],
                from_self_model=True,
                from_goals=True,
                from_last_error=from_last_error,
            )
            result["applied"] = True
            result["working_memory_size"] = len(kernel_self.get_working_memory())

        elif proposal.action_type == "goal_priority_adjust":
            delta = float(proposal.payload.get("delta", 0.1))
            keywords = [str(k).lower() for k in proposal.payload.get("impact_keywords", [])]
            adjusted = []
            for goal in kernel_self.get_active_goals(10):
                desc = goal.description.lower()
                if not keywords or any(kw in desc for kw in keywords if kw):
                    if kernel_self.adjust_goal_priority(goal.goal_id, delta, proposal.source_event_id):
                        adjusted.append(goal.goal_id)
            if not adjusted and kernel_self.get_active_goals(1):
                top = kernel_self.get_active_goals(1)[0]
                if kernel_self.adjust_goal_priority(top.goal_id, delta * 0.5, proposal.source_event_id):
                    adjusted.append(top.goal_id)
            result["applied"] = bool(adjusted)
            result["adjusted_goal_ids"] = adjusted

        elif proposal.action_type == "memory_candidate":
            mem_id = f"mem-cand-{proposal.proposal_id}"
            kernel_self.claim_ownership(mem_id, "memory_candidate")
            result["applied"] = True
            result["memory_candidate_id"] = mem_id
            result["held_for_review"] = proposal.review_status == "review_only"

        elif proposal.action_type == "belief_reinforce":
            bid = proposal.payload.get("belief_id")
            delta = float(proposal.payload.get("delta", 0.05))
            if bid and kernel_self.reinforce_belief(bid, delta, proposal.source_event_id):
                result["applied"] = True
                result["belief_id"] = bid
            else:
                result["applied"] = False
                result["reason"] = "belief_not_found"

        elif proposal.action_type == "self_model_proposal":
            from experience.models import BeliefProposal

            bp = BeliefProposal(
                proposal_type=proposal.payload.get("proposal_type", "self_observation"),
                content=proposal.content,
                confidence=float(proposal.payload.get("confidence", proposal.priority)),
            )
            prop_res = kernel_self.propose_self_update(
                proposals=[bp],
                importance_score=int(proposal.priority * 100),
                source_event_id=proposal.source_event_id,
            )
            candidates = prop_res.get("candidates", [])
            if candidates:
                commit = kernel_self.commit_self_updates(candidates, proposal.source_event_id)
                result["applied"] = bool(commit.get("applied"))
                result["commit"] = commit
            else:
                result["applied"] = False
                result["reason"] = "no_candidates"

        if result.get("applied"):
            proposal.applied = True
            self.applied_history.append(
                {
                    "proposal_id": proposal.proposal_id,
                    "action_type": proposal.action_type,
                    "source_event_id": proposal.source_event_id,
                    "review_status": proposal.review_status,
                }
            )
        return result

    def apply_reviewed(self, kernel_self: Any, proposal_id: str) -> dict[str, Any]:
        """Owner explicitly approves a pending reorg proposal."""
        for i, prop in enumerate(self.pending_proposals):
            if prop.proposal_id == proposal_id:
                result = self.apply_proposal(kernel_self, prop)
                self.pending_proposals.pop(i)
                result["owner_reviewed"] = True
                return result
        return {"applied": False, "reason": "proposal_not_pending", "proposal_id": proposal_id}

    def run_cycle(
        self,
        kernel_self: Any,
        *,
        prediction_error: dict[str, Any] | None = None,
        belief_result: dict[str, Any] | None = None,
        world_model_result: dict[str, Any] | None = None,
        experience_result: dict[str, Any] | None = None,
        source_event_id: str = "unknown",
        auto_apply_stable: bool = True,
        reorg_mode: ReorgMode = "fast",
    ) -> dict[str, Any]:
        """Propose and optionally auto-apply reorg actions (K-008/K-009)."""
        if reorg_mode == "skip":
            return {
                "proposals_count": 0,
                "applied": [],
                "pending_review": [],
                "pending_count": len(self.pending_proposals),
                "working_memory_before": len(kernel_self.get_working_memory()),
                "working_memory_after": len(kernel_self.get_working_memory()),
                "structural_impact": False,
                "reorg_mode": reorg_mode,
            }

        proposals = self.propose_from_signals(
            prediction_error=prediction_error,
            belief_result=belief_result,
            world_model_result=world_model_result,
            experience_result=experience_result,
            source_event_id=source_event_id,
        )

        applied: list[dict[str, Any]] = []
        pending: list[dict[str, Any]] = []

        for prop in proposals:
            if prop.review_status == "review_only":
                pending.append(prop.model_dump())
                continue
            if reorg_mode == "slow" and prop.action_type in _DEFERRED_SLOW_ACTIONS:
                self.pending_proposals.append(prop)
                pending.append(prop.model_dump())
                continue
            if auto_apply_stable:
                res = self.apply_proposal(kernel_self, prop)
                applied.append(res)

        wm_before = len(kernel_self.get_working_memory())
        return {
            "proposals_count": len(proposals),
            "applied": applied,
            "pending_review": pending,
            "pending_count": len(self.pending_proposals),
            "working_memory_before": wm_before,
            "working_memory_after": len(kernel_self.get_working_memory()),
            "structural_impact": len(applied) > 0 or len(pending) > 0,
            "reorg_mode": reorg_mode,
        }

    def get_pending_proposals(self) -> list[dict[str, Any]]:
        return [p.model_dump() for p in self.pending_proposals]

    def to_dict(self) -> dict[str, Any]:
        return {
            "self_id": self.self_id,
            "pending_proposals": [p.model_dump() for p in self.pending_proposals],
            "applied_history": self.applied_history,
            "proposal_counter": self._proposal_counter,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReorganizationLoop":
        loop = cls(self_id=data.get("self_id", "unknown"))
        loop.applied_history = data.get("applied_history", [])
        loop._proposal_counter = int(data.get("proposal_counter", 0))
        for p in data.get("pending_proposals", []):
            loop.pending_proposals.append(ReorgProposal.model_validate(p))
        return loop
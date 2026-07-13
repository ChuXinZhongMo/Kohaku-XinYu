from __future__ import annotations

"""Ownership management for Self in the Cognitive Kernel.

This module provides the primary Self class that maintains identity
and manages ownership claims.

Self is the lowest level of the cognitive kernel: the persistent subject
that can own other objects (memories, beliefs, etc. in future).
"""

from typing import TYPE_CHECKING, Any

from .model import CoreStatement, CoreStatementType, SelfModel
from ..goals import Goal, GoalManager

# Lazy runtime import to break circular dependency
import importlib

if TYPE_CHECKING:
    from kernel.prediction import Prediction, PredictionError

_prediction_mod = None

def _get_prediction_engine():
    global _prediction_mod
    if _prediction_mod is None:
        _prediction_mod = importlib.import_module("kernel.prediction")
    return _prediction_mod.PredictionEngine

def _get_prediction():
    global _prediction_mod
    if _prediction_mod is None:
        _prediction_mod = importlib.import_module("kernel.prediction")
    return _prediction_mod.Prediction

def _get_prediction_error():
    global _prediction_mod
    if _prediction_mod is None:
        _prediction_mod = importlib.import_module("kernel.prediction")
    return _prediction_mod.PredictionError

# Import for adapter (avoid circular in real use)
try:
    from experience.models import BeliefProposal
except Exception:
    BeliefProposal = dict  # type: ignore


class Self:
    """The persistent owning subject (Cognitive Kernel primitive).

    A Self has:
    - A stable self_id
    - Ability to claim and verify ownership over arbitrary objects
    - Serialization support

    This class is intentionally minimal. It does not implement
    higher cognitive concepts (beliefs, emotions, etc.).
    """

    def __init__(
        self, model: SelfModel | None = None, *, self_id: str | None = None
    ) -> None:
        if model is not None:
            self._model = model
        else:
            if self_id:
                # Use provided stable id, create fresh model
                self._model = SelfModel(self_id=self_id)
            else:
                self._model = SelfModel()

        # K-003: Each Self owns its PredictionEngine (lazy to avoid cycle)
        PredictionEngine = _get_prediction_engine()
        self.prediction_engine = PredictionEngine(self_id=self.self_id)

        # K-004: Each Self owns its GoalManager
        self.goal_manager = GoalManager(self_id=self.self_id, self_model=self._model)

        # K-005: Each Self owns its AttentionBuffer
        from ..attention import AttentionBuffer
        self.attention_buffer = AttentionBuffer(self_id=self.self_id)

        # K-006: Each Self owns its BeliefEngine
        from ..belief import BeliefEngine
        self.belief_engine = BeliefEngine(self_id=self.self_id)

        # K-007: Each Self owns its WorldModel
        from ..world_model import WorldModel
        self.world_model = WorldModel(self_id=self.self_id)

        # K-008: Each Self owns its ReorganizationLoop
        from ..reorganization import ReorganizationLoop
        self.reorganization_loop = ReorganizationLoop(self_id=self.self_id)

        # K-009: Cognitive cycle state for slow-signal accumulation
        from ..cognitive_cycle import CognitiveCycleState
        self.cognitive_cycle_state = CognitiveCycleState(self_id=self.self_id)

    @property
    def self_id(self) -> str:
        """The unique identifier of this Self."""
        return self._model.self_id

    def claim_ownership(self, obj_id: str, obj_type: str) -> None:
        """Claim ownership of an object.

        Raises:
            OwnershipError: if the object is already claimed by this Self.
        """
        if not obj_id or not isinstance(obj_id, str):
            raise ValueError("obj_id must be a non-empty string")
        if not obj_type or not isinstance(obj_type, str):
            raise ValueError("obj_type must be a non-empty string")

        self._model.add_owned(obj_id, obj_type)

    def verify_ownership(self, obj_id: str) -> bool:
        """Check whether this Self owns the given object id."""
        if not obj_id or not isinstance(obj_id, str):
            return False
        return self._model.has_owned(obj_id)

    def get_owned_objects(self) -> list[dict[str, Any]]:
        """Return a list of currently owned objects (as plain dicts)."""
        return [o.model_dump() for o in self._model.owned_objects]

    def release_ownership(self, obj_id: str) -> bool:
        """Release ownership of an object if owned.

        Returns True if the object was previously owned and has now been released.
        """
        return self._model.remove_owned(obj_id)

    def to_dict(self) -> dict[str, Any]:
        """Serialize this Self including full kernel state (v2)."""
        return {
            "self_id": self.self_id,
            "model": self._model.to_dict(),
            "goals": self.goal_manager.to_dict(),
            "beliefs": self.belief_engine.to_dict(),
            "world_model": self.world_model.to_dict(),
            "attention": self.attention_buffer.to_dict(),
            "prediction": self.prediction_engine.to_dict(),
            "reorganization": self.reorganization_loop.to_dict(),
            "cognitive_cycle": self.cognitive_cycle_state.model_dump(),
            "version": 2,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Reconstruct a Self from a previously serialized dict."""
        if not isinstance(data, dict):
            raise ValueError("data must be a dict")

        version = data.get("version", 1)
        model_data = data.get("model") or {}
        if "self_id" in data and "model" not in data:
            model_data = data

        model = SelfModel.from_dict(model_data)
        s = cls(model=model)

        if version >= 2:
            from ..belief import BeliefEngine

            if data.get("goals"):
                s.goal_manager = GoalManager.from_dict(data["goals"], s._model)
            if data.get("beliefs"):
                s.belief_engine = BeliefEngine.from_dict(data["beliefs"])
            if data.get("world_model"):
                from ..world_model import WorldModel
                s.world_model = WorldModel.from_dict(data["world_model"])
            if data.get("attention"):
                from ..attention import AttentionBuffer
                s.attention_buffer = AttentionBuffer.from_dict(data["attention"])
            if data.get("prediction"):
                PredictionEngine = _get_prediction_engine()
                s.prediction_engine = PredictionEngine.from_dict(data["prediction"])
            if data.get("reorganization"):
                from ..reorganization import ReorganizationLoop
                s.reorganization_loop = ReorganizationLoop.from_dict(data["reorganization"])
            if data.get("cognitive_cycle"):
                from ..cognitive_cycle import CognitiveCycleState
                s.cognitive_cycle_state = CognitiveCycleState.model_validate(data["cognitive_cycle"])

        return s

    def __repr__(self) -> str:
        return f"Self(self_id={self.self_id!r}, owned={len(self._model.owned_objects)}, core_statements={len(self._model.core_statements)})"

    # === Self Model (K-002) extensions ===

    def get_self_model(self) -> dict[str, Any]:
        """Return the stable Self Model as a clean dict."""
        return {
            "self_id": self.self_id,
            "core_statements": [s.model_dump() for s in self._model.get_core_statements()],
            "core_summary": self._build_core_summary(),
        }

    def _build_core_summary(self) -> str:
        parts = []
        for t in ["identity", "core_value", "boundary", "long_term_orientation"]:
            stmts = self._model.get_core_statements(t)  # type: ignore
            if stmts:
                parts.append(f"{t}: {stmts[0].content}")
        return " | ".join(parts) or "No stable self model yet."

    def propose_self_update(
        self,
        proposals: list[BeliefProposal],
        importance_score: int,
        source_event_id: str,
    ) -> dict[str, Any]:
        """Stage 1: Validate proposals from Experience. Do NOT commit yet.

        Returns candidates ready for apply, plus rejected.
        This follows the plan: proposal -> gate -> apply (traceable).
        """
        candidates: list[CoreStatement] = []
        rejected = []
        min_importance = 65
        min_conf = 0.55

        for p in proposals:
            ptype = getattr(p, "proposal_type", p.get("proposal_type", "other") if isinstance(p, dict) else "other")
            content = getattr(p, "content", p.get("content", "") if isinstance(p, dict) else "")
            conf = getattr(p, "confidence", p.get("confidence", 0.5) if isinstance(p, dict) else 0.5)

            if importance_score < min_importance or conf < min_conf:
                rejected.append({"proposal": content[:80], "reason": "low_signal"})
                continue

            stmt_type = self._map_proposal_to_stmt_type(ptype)
            if not stmt_type:
                rejected.append({"proposal": content[:80], "reason": "not_self_relevant"})
                continue

            stmt = CoreStatement(
                statement_id=f"stmt-{source_event_id[:12]}-{len(self._model.core_statements) + len(candidates)}",
                statement_type=stmt_type,
                content=content[:350],
                confidence=float(conf),
                source_event_id=source_event_id,
            )
            candidates.append(stmt)

        return {"candidates": candidates, "rejected": rejected}

    def _map_proposal_to_stmt_type(self, proposal_type: str) -> CoreStatementType | None:
        mapping = {
            "boundary": "boundary",
            "self_observation": "identity",
            "preference": "core_value",
            "fact": None,  # facts go to belief later
        }
        return mapping.get(proposal_type)

    def apply_self_update(self, statement: CoreStatement, source_event_id: str, force: bool = False) -> bool:
        """Stage 2: Apply a validated CoreStatement (with gate).

        Gate is inspired by memory_consistency_gate_engine.
        Changes are always traceable via source_event_id.
        """
        if not force:
            # Stricter stability gate (reference consistency gate pattern)
            if statement.confidence < 0.75:
                return False

            existing_same_type = self._model.get_core_statements(statement.statement_type)
            if existing_same_type:
                latest = existing_same_type[0]
                # Prevent rapid flip on same type unless significantly higher confidence
                if latest.confidence >= 0.8 and statement.confidence < latest.confidence + 0.15:
                    return False

        self._model.replace_core_statement(statement)
        self.claim_ownership(statement.statement_id, f"core_statement:{statement.statement_type}")
        return True

    def commit_self_updates(self, candidates: list[CoreStatement], source_event_id: str) -> dict[str, Any]:
        """Commit multiple candidates after proposal stage (or external review)."""
        applied = []
        skipped = []
        for stmt in candidates:
            if self.apply_self_update(stmt, source_event_id):
                applied.append(stmt.statement_type)
            else:
                skipped.append(stmt.statement_type)
        return {"applied": applied, "skipped": skipped, "source": source_event_id}

    # === K-003: Prediction integration ===

    def generate_prediction(self, source_event_id: str | None = None) -> "Prediction":
        """Generate a prediction from current Self Model + Goals + Attention + Beliefs + World Model (K-007)."""
        model = self.get_self_model()
        goals_ctx = self.goals_to_prediction_context()
        attn_ctx = self.attention_to_context()
        beliefs_ctx = self.beliefs_to_context()
        world_ctx = self.world_model_to_context()
        return self.prediction_engine.generate_prediction(model, source_event_id, goals_ctx, attn_ctx, beliefs_ctx, world_ctx)

    def record_prediction_outcome(
        self, prediction_id: str, reality: str, source_event_id: str | None = None
    ) -> "PredictionError":
        """Record outcome and get PredictionError.

        High error can be used to propose Self Model update.
        """
        error = self.prediction_engine.record_outcome(prediction_id, reality, source_event_id)
        return error

    def error_to_self_proposal(self, error: PredictionError) -> dict[str, Any]:
        """Convert high-error outcome into a potential Self Model proposal.

        This closes the loop: Prediction Error -> Self reorganization.
        """
        if not self.prediction_engine.should_propose_self_update(error):
            return {"should_propose": False, "error_magnitude": error.error_magnitude}

        # Simple mapping from error impact to proposal
        proposals = []
        for impact in error.impact_on_self:
            if impact == "identity":
                content = f"Reality differed: {error.reality[:120]}. Adjust self-understanding."
            else:
                content = f"Outcome contradicted expectation (error={error.error_magnitude}). Review {impact}."
            proposals.append({
                "proposal_type": "self_observation" if impact == "identity" else "core_value",
                "content": content,
                "confidence": max(0.5, min(0.9, error.error_magnitude)),
            })

        return {
            "should_propose": True,
            "error_magnitude": error.error_magnitude,
            "proposals": proposals,
            "source_event_id": error.source_event_id,
        }

    # === K-004: Goals integration ===

    def propose_goal(
        self,
        description: str,
        priority: float = 0.5,
        source_event_id: str | None = None,
    ) -> Goal | None:
        """Propose a new goal from experience or error feedback."""
        return self.goal_manager.propose_goal(
            description=description,
            priority=priority,
            source_event_id=source_event_id,
        )

    def get_active_goals(self, top_k: int = 5) -> list[Goal]:
        return self.goal_manager.get_active_goals(top_k)

    def update_goal(self, goal_id: str, new_status: str, event_id: str | None = None) -> bool:
        return self.goal_manager.update_goal_status(goal_id, new_status, event_id)  # type: ignore

    def goals_to_prediction_context(self) -> str:
        """Inject active goals into prediction generation."""
        goals = self.get_active_goals(3)
        if not goals:
            return ""
        return "Current goals: " + "; ".join(g.description[:60] for g in goals)

    # === K-005: Attention integration ===

    def update_attention(
        self,
        items: list[dict[str, Any]] | None = None,
        from_self_model: bool = True,
        from_goals: bool = True,
        from_last_error: dict | None = None,
    ) -> None:
        """Update the attention buffer from various sources.

        This is the selection mechanism (K-005).
        """
        if items:
            from ..attention import AttentionItem
            for it in items:
                self.attention_buffer.add_item(AttentionItem(**it))

        if from_self_model:
            self.attention_buffer.update_from_self_model(self.get_self_model())

        if from_goals:
            active_goals = [g.model_dump() for g in self.get_active_goals(5)]
            self.attention_buffer.update_from_goals(active_goals)

        if from_last_error:
            self.attention_buffer.update_from_prediction_error(from_last_error)

    def get_working_memory(self) -> list[dict[str, Any]]:
        """Return current focused working memory for Narrative/Prediction/Decision."""
        return self.attention_buffer.get_working_memory()

    def attention_to_context(self) -> str:
        """Compact string for downstream use (e.g. in generate_prediction)."""
        wm = self.get_working_memory()
        if not wm:
            return ""
        return "Attending to: " + " | ".join(item["content"][:80] for item in wm[:3])

    # === K-006: Belief integration ===

    def propose_belief(
        self,
        content: str,
        confidence: float = 0.5,
        evidence_event_ids: list[str] | None = None,
        source_event_id: str | None = None,
    ) -> dict[str, Any]:
        """Propose belief from Experience or PredictionError."""
        belief = self.belief_engine.propose_belief(
            content=content,
            confidence=confidence,
            evidence_event_ids=evidence_event_ids,
            source_event_id=source_event_id,
        )
        if belief:
            # Claim ownership
            self.claim_ownership(belief.belief_id, "belief")
            self.belief_engine.commit_belief(belief)
            return {"accepted": True, "belief_id": belief.belief_id}
        return {"accepted": False, "reason": "low_confidence_or_gate"}

    def get_stable_beliefs(self, min_conf: float = 0.6) -> list[dict[str, Any]]:
        return [b.model_dump() for b in self.belief_engine.get_stable_beliefs(min_conf)]

    def beliefs_to_context(self) -> str:
        """Inject beliefs into prediction/attention."""
        return self.belief_engine.beliefs_to_context()

    # === K-007: World Model integration ===

    def update_world_model(self, from_error: dict | None = None, new_facts: list[str] | None = None, new_rule: str | None = None) -> dict[str, Any]:
        """Update World Model from Prediction Error or new data (reorganization)."""
        result: dict[str, Any] = {"updated": False}
        if from_error:
            affected = self.world_model.update_from_error(from_error, new_facts)
            result["affected_facts"] = affected
            result["updated"] = True
        if new_rule:
            self.world_model.add_generative_rule(new_rule)
            result["rule_added"] = new_rule
            result["updated"] = True
        return result

    def generate_world_prediction(self, context: str = "", horizon: str = "medium") -> dict[str, Any]:
        """Generative prediction from World Model (can be longer-horizon)."""
        wm_ctx = self.world_model.get_context()
        return self.world_model.generate_prediction(wm_ctx + " " + context, horizon)

    def generate_world_hypothetical(self, premise: str, steps: int = 2) -> dict[str, Any]:
        """Strengthened generative simulation using World Model."""
        return self.world_model.generate_hypothetical(premise, steps)

    def derive_world_expectation(self, from_belief_content: str, from_goal_desc: str = "") -> str:
        """Generative derivation of new expectation."""
        return self.world_model.derive_new_expectation(from_belief_content, from_goal_desc)

    def learn_world_rule(self, belief_content: str, goal_desc: str) -> str | None:
        """从信念+目标学习规则 (K-007 加强 generative)。"""
        return self.world_model.learn_rule_from_belief_and_goal(belief_content, goal_desc)

    def simulate_world(self, premise: str, beliefs: list[str], goals: list[str], steps: int = 3) -> list[dict]:
        """信念/目标驱动的完整 generative simulation。"""
        return self.world_model.simulate_with_beliefs_goals(premise, beliefs, goals, steps)

    def world_model_to_context(self) -> str:
        return self.world_model.get_context()

    def sync_world_model(self):
        """补细节: 让 World Model 从当前 Self 状态同步。"""
        model = self.get_self_model()
        active_beliefs = self.get_stable_beliefs()
        active_goals = [g.model_dump() for g in self.get_active_goals()]
        self.world_model.sync_with_self_state(model, active_beliefs, active_goals)

    def reorganize_world_model(self, errors: list[dict], new_beliefs: list[dict] = None, new_goals: list[dict] = None):
        """补细节: 触发 WM 重组。"""
        return self.world_model.reorganize(errors, new_beliefs, new_goals)

    def apply_reviewed_world_fact(self, fact_id: str) -> bool:
        """Owner explicitly approves a reviewed WM change."""
        return self.world_model.apply_reviewed_fact(fact_id)

    def get_pending_world_facts(self) -> list[dict]:
        return [f.model_dump() for f in self.world_model.get_pending_review_facts()]

    # === K-008: Self Reorganization Loop ===

    def adjust_goal_priority(self, goal_id: str, delta: float, event_id: str | None = None) -> bool:
        return self.goal_manager.adjust_priority(goal_id, delta, event_id)

    def reinforce_belief(self, belief_id: str, delta: float, event_id: str | None = None) -> bool:
        return self.belief_engine.reinforce(belief_id, delta, event_id)

    def run_reorganization_cycle(
        self,
        *,
        prediction_error: dict | None = None,
        belief_result: dict | None = None,
        world_model_result: dict | None = None,
        experience_result: dict | None = None,
        source_event_id: str = "unknown",
        auto_apply_stable: bool = True,
        reorg_mode: str = "fast",
    ) -> dict[str, Any]:
        """K-008: propose and apply cross-layer structural updates."""
        return self.reorganization_loop.run_cycle(
            self,
            prediction_error=prediction_error,
            belief_result=belief_result,
            world_model_result=world_model_result,
            experience_result=experience_result,
            source_event_id=source_event_id,
            auto_apply_stable=auto_apply_stable,
            reorg_mode=reorg_mode,  # type: ignore[arg-type]
        )

    def run_cognitive_cycle(
        self,
        event_input: dict,
        *,
        outcome_reality: str | None = None,
        source_event_id: str = "unknown",
        event_root: Any = None,
        persist: bool = True,
    ) -> dict[str, Any]:
        """K-009: run the full closed cognitive cycle."""
        from ..cognitive_cycle import run_full_cognitive_cycle

        return run_full_cognitive_cycle(
            self,
            event_input,
            outcome_reality=outcome_reality,
            source_event_id=source_event_id,
            event_root=event_root,
            persist=persist,
        )

    def apply_reviewed_reorg(self, proposal_id: str) -> dict[str, Any]:
        """Owner explicitly approves a pending reorg proposal."""
        return self.reorganization_loop.apply_reviewed(self, proposal_id)

    def get_pending_reorg_proposals(self) -> list[dict]:
        return self.reorganization_loop.get_pending_proposals()

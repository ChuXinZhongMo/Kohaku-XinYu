"""Cognitive Kernel package.

This is the foundation for XinYu's experience-driven cognitive architecture.
All higher-level constructs (beliefs, memory ownership, prediction, etc.)
will ultimately belong to a Self instance.

Current scope (K-002): Self Model with Core Statements updated via Experience.
"""

from pathlib import Path
from typing import Any

from .exceptions import KernelError, OwnershipError
from .attention import AttentionBuffer, AttentionItem
from .goals import Goal, GoalManager
from .belief import Belief, BeliefEngine
from .prediction import Prediction, PredictionEngine, PredictionError
from .self import Self, SelfModel
from .world_model import WorldFact, WorldModel
from .reorganization import ReorgProposal, ReorganizationLoop
from .cognitive_cycle import CognitiveCycleState, classify_reorg_mode, run_full_cognitive_cycle
from .runtime_self import get_or_create_runtime_self, persist_runtime_self, RUNTIME_SELF_ID
from .bridge_integration import augment_text_with_kernel_context, get_kernel_context, update_kernel_from_turn_outcome
from .bridge_access import apply_kernel_owner_reviews, query_kernel_state, resolve_runtime_self, run_kernel_turn_update
from .bridge_governance import apply_kernel_owner_review, get_kernel_review_inbox
from .narrative_builder import build_self_story, maybe_update_self_story
from .owner_grants import grant_owner_scope, is_scope_granted, load_owner_grants

__all__ = [
    "KernelError",
    "OwnershipError",
    "Self",
    "SelfModel",
    "Goal",
    "GoalManager",
    "Prediction",
    "PredictionEngine",
    "PredictionError",
    "AttentionBuffer",
    "AttentionItem",
    "Belief",
    "BeliefEngine",
    "WorldFact",
    "WorldModel",
    "ReorgProposal",
    "ReorganizationLoop",
    "CognitiveCycleState",
    "classify_reorg_mode",
    "run_full_cognitive_cycle",
    "get_or_create_runtime_self",
    "persist_runtime_self",
    "RUNTIME_SELF_ID",
    "get_kernel_context",
    "augment_text_with_kernel_context",
    "update_kernel_from_turn_outcome",
    "query_kernel_state",
    "resolve_runtime_self",
    "run_kernel_turn_update",
    "apply_kernel_owner_reviews",
    "get_kernel_review_inbox",
    "apply_kernel_owner_review",
    "build_self_story",
    "maybe_update_self_story",
    "grant_owner_scope",
    "is_scope_granted",
    "load_owner_grants",
    "get_kernel_self_model",
]


def get_kernel_self_model(
    self_id: str = RUNTIME_SELF_ID,
    persist_path: Path | None = None,
    root: Path | None = None,
) -> dict[str, Any]:
    """Safe query interface for bridge / runtime to read the current Self Model."""
    try:
        load_root = root or (persist_path.parent if persist_path else None)
        s = get_or_create_runtime_self(load_root) if load_root else Self(self_id=self_id)
        model = s.get_self_model()
        model["review_inbox_pending"] = get_kernel_review_inbox(s).get("pending_count", 0)
        return model
    except Exception as e:
        return {"self_id": self_id, "error": str(e), "core_statements": []}

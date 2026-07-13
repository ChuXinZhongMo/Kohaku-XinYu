"""K-010 bridge turn hooks: kernel participates in every live turn."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from xinyu_bridge_values import safe_str
from xinyu_group_memory_pipeline import is_group_source, is_owner_in_group_payload


def inject_kernel_pre_turn_context(runtime: Any, payload: dict[str, Any]) -> dict[str, Any]:
    """Pre-turn: attach read-only kernel snapshot to payload metadata."""
    try:
        from kernel.bridge_access import query_kernel_state

        root = Path(runtime.xinyu_dir)
        state = query_kernel_state(root)
        if not state.get("available"):
            return {"notes": ["kernel_pre_turn_unavailable"]}

        metadata = payload.get("metadata")
        if not isinstance(metadata, dict):
            metadata = {}
            payload["metadata"] = metadata

        metadata["kernel_pre_turn"] = {
            "self_id": state.get("self_id"),
            "working_memory_size": state.get("working_memory_size", 0),
            "pending_review_count": (state.get("review_inbox") or {}).get("pending_count", 0),
            "world_context": (state.get("kernel_context") or {}).get("world_context", "")[:200],
            "attention_context": (state.get("kernel_context") or {}).get("attention_context", "")[:200],
            "self_story_summary": (state.get("self_story_summary") or "")[:160],
            "reorg_recommendation": (state.get("reorg_meta") or {}).get("recommendation", "none"),
        }
        payload["kernel_context_included"] = True
        return {
            "included": True,
            "pending_review_count": metadata["kernel_pre_turn"]["pending_review_count"],
            "notes": ["kernel_pre_turn_injected"],
        }
    except Exception as exc:
        return {"notes": [f"kernel_pre_turn_error:{type(exc).__name__}"]}


def run_kernel_post_turn_cycle(
    runtime: Any,
    *,
    payload: dict[str, Any],
    text: str,
    reply: str,
    turn_id: str,
    event_sidecar: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Post-turn: run cognitive cycle with owner input + assistant outcome."""
    try:
        from kernel.bridge_access import run_kernel_turn_update

        root = Path(runtime.xinyu_dir)
        if event_sidecar and event_sidecar.get("cognitive_cycle_closed"):
            return {
                "skipped": True,
                "reason": "already_closed_in_event_sourcing",
                "reorg_mode": event_sidecar.get("cognitive_reorg_mode"),
            }

        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
        message_type = safe_str(payload.get("message_type") or metadata.get("message_type"))
        group_id = safe_str(payload.get("group_id")).strip()
        if group_id or message_type.startswith("group"):
            source_channel = "qq_group"
        else:
            source_channel = safe_str(payload.get("source") or "bridge")

        if is_owner_in_group_payload(payload):
            actor_scope = "owner"
        elif metadata:
            actor_scope = safe_str(metadata.get("actor_scope") or metadata.get("scope") or "owner")
        else:
            actor_scope = "owner"

        if is_group_source(source_channel, actor_scope) and actor_scope != "owner":
            user_label = "GroupMember"
        elif is_group_source(source_channel, actor_scope):
            user_label = "Owner(in-group)"
        else:
            user_label = "Owner"

        event_input = {
            "raw_text": text[:500],
            "source_channel": source_channel,
            "actor_scope": actor_scope,
            "turn_mode": safe_str(payload.get("turn_mode") or "chat"),
            "metadata": metadata,
        }
        outcome = f"{user_label}: {text[:200]}\nAssistant: {reply[:200]}"
        source_id = safe_str(event_sidecar.get("structured_id") if event_sidecar else "") or turn_id

        cycle = run_kernel_turn_update(
            root,
            event_input,
            outcome_reality=outcome,
            source_event_id=source_id,
        )
        return {
            "cycle_closed": cycle.get("cycle_closed", False),
            "reorg_mode": cycle.get("reorg_mode"),
            "structural_impact": cycle.get("structural_impact", False),
            "pending_review_count": (cycle.get("review_inbox") or {}).get("pending_count", 0),
            "notes": ["kernel_post_turn_cycle_complete"],
        }
    except Exception as exc:
        return {"notes": [f"kernel_post_turn_error:{type(exc).__name__}"]}
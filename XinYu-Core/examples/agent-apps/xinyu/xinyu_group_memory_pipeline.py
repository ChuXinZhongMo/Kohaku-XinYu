"""Group chat access to reflection, relationship candidates, kernel, and memory candidates.

Group material may enter review-gated candidate layers only — never stable owner memory.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

_CUSTOM_DIR = Path(__file__).resolve().parent / "custom"
if str(_CUSTOM_DIR) not in sys.path:
    sys.path.insert(0, str(_CUSTOM_DIR))

from memory_event_schema import (  # noqa: E402
    GROUP_SOURCE_CHANNELS,
    NON_OWNER_ACTOR_SCOPES,
    is_owner_relationship_candidate_layer,
    is_owner_relationship_stable_layer,
)

CONFIG_REL = Path("memory/context/group_memory_pipeline.json")

GROUP_PIPELINE_ALLOWED_LAYERS = (
    "context/group",
    "knowledge/source_candidates",
    "reflection",
    "relationships/owner_candidate",
    "self/voice_review",
    "memory/reflection/growth_log.md",
    "memory/people/owner.md",
    "memory/relationships/index.md",
    "memory/self/voice_calibration_log.md",
)

GROUP_PIPELINE_BLOCKED_LAYERS = (
    "relationships/owner",
    "stable_knowledge_direct_write",
    "stable_personality_direct_write",
    "stable_relationship_direct_write",
)


def _env_override() -> bool | None:
    raw = os.environ.get("XINYU_GROUP_FULL_MEMORY_PIPELINE", "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return None


def group_full_memory_pipeline_enabled(root: Path | None = None) -> bool:
    """Default on: group chat may enter candidate pipelines with review gates."""
    env = _env_override()
    if env is not None:
        return env
    if root is not None:
        config_path = root / CONFIG_REL
        if config_path.exists():
            try:
                data = json.loads(config_path.read_text(encoding="utf-8-sig"))
            except (OSError, json.JSONDecodeError):
                return True
            if isinstance(data, dict):
                return bool(data.get("enabled", True))
    return True


def is_group_source(source_channel: str, actor_scope: str = "") -> bool:
    channel = str(source_channel or "").strip()
    scope = str(actor_scope or "").strip()
    return channel in GROUP_SOURCE_CHANNELS or scope in NON_OWNER_ACTOR_SCOPES


def _payload_metadata(payload: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    metadata = payload.get("metadata")
    return metadata if isinstance(metadata, dict) else {}


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return default if value is None else bool(value)


def is_owner_in_group_payload(payload: dict[str, Any] | None) -> bool:
    payload = payload if isinstance(payload, dict) else {}
    metadata = _payload_metadata(payload)
    is_owner = _as_bool(
        metadata.get("is_owner_user") if "is_owner_user" in metadata else payload.get("is_owner_user"),
        default=False,
    )
    if not is_owner:
        return False
    group_id = str(payload.get("group_id") or "").strip()
    message_type = str(payload.get("message_type") or metadata.get("message_type") or "").strip().lower()
    return bool(group_id) or message_type.startswith("group")


def group_owner_relationship_candidates_allowed(root: Path | None, payload: dict[str, Any] | None) -> bool:
    return group_full_memory_pipeline_enabled(root) and is_owner_in_group_payload(payload)


def group_candidate_layer_allowed(
    root: Path | None,
    *,
    target_layer: str,
    claim_status: str = "candidate",
) -> bool:
    if not group_full_memory_pipeline_enabled(root):
        return False
    layer = str(target_layer or "").strip()
    status = str(claim_status or "").strip().lower()
    if status in {"stable"}:
        return False
    if is_owner_relationship_stable_layer(layer):
        return False
    return is_owner_relationship_candidate_layer(layer)


def structured_event_for_group(
    root: Path | None,
    *,
    source_channel: str,
    actor_scope: str,
    priority_learning: bool = False,
) -> dict[str, Any]:
    if priority_learning or not group_full_memory_pipeline_enabled(root):
        return {
            "allowed": ["context/group", "knowledge/source_candidates"],
            "blocked": ["relationships/owner", "stable_knowledge_direct_write"],
            "turn_mode": "observe_only" if priority_learning else "group_context_candidate",
            "salience": 58,
            "routing_extra": [],
        }
    salience = 64 if actor_scope == "owner" else 62
    turn_mode = "group_owner_full_pipeline_candidate" if actor_scope == "owner" else "group_full_pipeline_candidate"
    return {
        "allowed": list(GROUP_PIPELINE_ALLOWED_LAYERS),
        "blocked": list(GROUP_PIPELINE_BLOCKED_LAYERS),
        "turn_mode": turn_mode,
        "salience": salience,
        "routing_extra": ["group_full_memory_pipeline_candidate_only"],
    }
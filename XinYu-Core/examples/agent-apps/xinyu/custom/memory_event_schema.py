"""Schema helpers for XinYu memory event sourcing sidecars."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


RAW_EVENT_REQUIRED = (
    "event_id",
    "timestamp",
    "source_channel",
    "actor_scope",
    "raw_text",
    "raw_hash",
    "privacy_scope",
)

STRUCTURED_EVENT_REQUIRED = (
    "structured_id",
    "event_id",
    "event_kind",
    "turn_mode",
    "allowed_memory_layers",
    "blocked_memory_layers",
    "salience",
    "routing_notes",
)

CLAIM_REQUIRED = (
    "claim_id",
    "claim_type",
    "subject",
    "predicate",
    "object",
    "status",
    "target_memory_layer",
    "evidence_event_ids",
    "evidence_spans",
    "confidence",
)

SUMMARY_REQUIRED = (
    "summary_id",
    "summary_text",
    "retained_claim_ids",
    "source_event_ids",
    "loss_notes",
    "discarded_signals",
    "blocked_from_discard",
)

CLAIM_TYPES = {
    "fact",
    "preference",
    "emotion",
    "relationship_residue",
    "dream_residue",
    "source_candidate",
    "voice_correction",
    "question",
    "system_state",
}

CLAIM_STATUSES = {
    "candidate",
    "review_only",
    "stable",
    "rejected",
    "contradicted",
    "obsolete",
    "dream_only",
}

GROUP_SOURCE_CHANNELS = {"qq_group", "priority_learning_group", "group"}
NON_OWNER_ACTOR_SCOPES = {"non_owner", "group_member", "external_contact"}
DREAM_SOURCE_CHANNELS = {"dream", "dream_output"}
OWNER_RELATIONSHIP_LAYERS = {
    "relationships/owner",
    "relationship/owner",
    "owner_relationship",
    "memory/relationships/owner_patterns.md",
    "memory/relationships/index.md",
    "memory/people/owner.md",
}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        data = json.loads(line)
        if not isinstance(data, dict):
            raise ValueError(f"{path}:{line_number} JSONL row must be an object")
        rows.append(data)
    return rows


def dump_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)
    path.write_text(text + ("\n" if text else ""), encoding="utf-8")


def missing_fields(row: dict[str, Any], required: tuple[str, ...]) -> list[str]:
    return [field for field in required if field not in row or row.get(field) in (None, "")]


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def string_list(value: Any) -> list[str]:
    return [str(item).strip() for item in as_list(value) if str(item).strip()]


def is_group_or_non_owner(raw_event: dict[str, Any] | None) -> bool:
    if raw_event is None:
        return False
    source_channel = str(raw_event.get("source_channel", "")).strip()
    actor_scope = str(raw_event.get("actor_scope", "")).strip()
    return source_channel in GROUP_SOURCE_CHANNELS or actor_scope in NON_OWNER_ACTOR_SCOPES


def is_dream_event(raw_event: dict[str, Any] | None) -> bool:
    if raw_event is None:
        return False
    return str(raw_event.get("source_channel", "")).strip() in DREAM_SOURCE_CHANNELS


def is_owner_relationship_layer(layer: str) -> bool:
    normalized = layer.strip()
    if normalized in OWNER_RELATIONSHIP_LAYERS:
        return True
    return normalized.startswith("relationships/owner") or normalized.startswith("owner/")

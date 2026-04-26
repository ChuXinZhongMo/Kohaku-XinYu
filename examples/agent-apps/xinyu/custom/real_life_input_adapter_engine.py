from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


TEXT_CHANNELS = {"im", "private_chat"}
KNOWN_CHANNELS = {"im", "private_chat", "group_chat", "image", "voice_transcript", "system_context"}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def split_events(text: str) -> list[dict[str, str]]:
    parts = re.split(r"(?m)^## (event-[\w-]+)\n", text)
    events: list[dict[str, str]] = []
    if len(parts) < 3:
        return events
    for i in range(1, len(parts), 2):
        event_id = parts[i].strip()
        if event_id == "event-none":
            continue
        body = parts[i + 1]
        fields = {"event_id": event_id}
        for line in body.splitlines():
            stripped = line.strip()
            if not stripped.startswith("- ") or ": " not in stripped:
                continue
            key, value = stripped[2:].split(": ", 1)
            fields[key.strip()] = value.strip()
        events.append(fields)
    return events


def is_yes(value: str) -> bool:
    return value.strip().lower() in {"yes", "true", "1", "explicit"}


def is_explicit(value: str) -> bool:
    return value.strip().lower() == "explicit"


def classify_event(event: dict[str, str]) -> dict[str, str]:
    status = event.get("status", "hold")
    channel = event.get("source_channel", "unknown")
    relationship_scope = event.get("relationship_scope", "unknown")
    actor_id = event.get("actor_id", "unknown")
    content_type = event.get("content_type", "unknown")
    owner_private = is_yes(event.get("contains_owner_private", "no"))
    private_location = is_yes(event.get("contains_private_location", "no"))
    owner_intent = event.get("owner_intent", "none")
    interpretation_status = event.get("interpretation_status", "raw")

    base = {
        "event_id": event["event_id"],
        "channel": channel,
        "permission": "hold",
        "reason": "not_evaluated",
        "turn_mode_route": "turn_mode_required",
        "memory_route": "hold",
        "time_anchor_route": "none",
        "owner_relationship_write": "no",
    }

    if status != "candidate":
        return base | {"reason": "not_candidate"}
    if channel not in KNOWN_CHANNELS:
        return base | {"permission": "blocked", "reason": "unsupported_channel"}
    if private_location and not is_explicit(owner_intent):
        return base | {
            "permission": "blocked",
            "reason": "private_location_requires_explicit_owner_intent",
            "memory_route": "privacy_hold",
        }
    if owner_private and not is_explicit(owner_intent) and relationship_scope != "owner":
        return base | {
            "permission": "blocked",
            "reason": "owner_private_requires_explicit_owner_intent",
            "memory_route": "privacy_hold",
        }
    if channel == "image" and interpretation_status == "raw":
        return base | {
            "permission": "hold",
            "reason": "image_requires_interpretation_before_fact",
            "memory_route": "interpretation_hold",
            "time_anchor_route": "coarse_time_context_candidate",
        }
    if channel == "voice_transcript" and content_type == "voice_transcript":
        return base | {
            "permission": "allowed",
            "reason": "voice_transcript_candidate_requires_fact_confirmation",
            "memory_route": "transcript_candidate",
            "time_anchor_route": "coarse_time_context_candidate",
        }
    if channel == "group_chat":
        return base | {
            "permission": "allowed",
            "reason": "group_chat_context_not_owner_relationship_event",
            "memory_route": "group_context_candidate",
            "time_anchor_route": "coarse_time_context_candidate",
            "owner_relationship_write": "no",
        }
    if private_location and is_explicit(owner_intent):
        return base | {
            "permission": "allowed",
            "reason": "explicit_private_anchor_candidate",
            "memory_route": "protected_anchor_candidate",
            "time_anchor_route": "protected_real_world_anchor_candidate",
        }
    if channel in TEXT_CHANNELS and relationship_scope == "owner" and actor_id == "owner":
        return base | {
            "permission": "allowed",
            "reason": "owner_text_turn_mode_candidate",
            "memory_route": "relationship_emotion_review_candidate",
            "time_anchor_route": "coarse_time_context_candidate",
            "owner_relationship_write": "review_only",
        }
    if channel in TEXT_CHANNELS and relationship_scope == "non_owner":
        return base | {
            "permission": "allowed",
            "reason": "non_owner_text_person_candidate",
            "memory_route": "non_owner_person_review_candidate",
            "time_anchor_route": "coarse_time_context_candidate",
        }
    return base | {
        "permission": "hold",
        "reason": "insufficient_context_for_memory_route",
        "memory_route": "recent_context_only",
        "time_anchor_route": "coarse_time_context_candidate",
    }


def render_state(evaluated_at: str, mode: str, decisions: list[dict[str, str]]) -> str:
    allowed = [item for item in decisions if item["permission"] == "allowed"]
    held = [item for item in decisions if item["permission"] == "hold"]
    blocked = [item for item in decisions if item["permission"] == "blocked"]
    decision_lines = [
        f"- {item['event_id']}: permission={item['permission']}; channel={item['channel']}; "
        f"memory_route={item['memory_route']}; time_anchor_route={item['time_anchor_route']}; "
        f"owner_relationship_write={item['owner_relationship_write']}; reason={item['reason']}"
        for item in decisions
    ] or ["- none"]
    return f"""---
title: Real Life Input Adapter State
memory_type: real_life_input_adapter_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-26T00:00:00+08:00
updated_at: {evaluated_at}
last_confirmed_at: {evaluated_at}
importance_score: 82
impact_score: 82
confidence_score: 100
status: active
tags: [context, input_adapter, state]
---

# Real Life Input Adapter State

## Last Evaluation
- evaluated_at: {evaluated_at}
- mode: {mode}
- candidate_events: {len(decisions)}
- allowed_events: {len(allowed)}
- held_events: {len(held)}
- blocked_events: {len(blocked)}

## Event Decisions
{chr(10).join(decision_lines)}

## Boundary
- This state never reads real accounts, files, devices, microphones, cameras, or locations.
- It only classifies already-staged event candidates.
- Adapter decisions are review routes, not direct memory writes.
"""


def run_real_life_input_adapter(
    root: Path,
    evaluated_at: str | None = None,
    mode: str = "runtime_real_life_input_adapter",
) -> dict[str, object]:
    evaluated_at = evaluated_at or datetime.now().astimezone().isoformat()
    events = split_events(read_text(root / "memory/context/real_life_input_events.md"))
    decisions = [classify_event(event) for event in events]
    write_text(
        root / "memory/context/real_life_input_adapter_state.md",
        render_state(evaluated_at, mode, decisions),
    )
    return {
        "evaluated_at": evaluated_at,
        "candidate_events": len(decisions),
        "allowed_events": sum(1 for item in decisions if item["permission"] == "allowed"),
        "held_events": sum(1 for item in decisions if item["permission"] == "hold"),
        "blocked_events": sum(1 for item in decisions if item["permission"] == "blocked"),
        "decisions": decisions,
    }

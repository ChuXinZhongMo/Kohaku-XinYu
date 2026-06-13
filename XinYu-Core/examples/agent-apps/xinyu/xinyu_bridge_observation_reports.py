from __future__ import annotations

import re
from pathlib import Path

from xinyu_bridge_observation_payload import ObservationPayload, _timestamp_or_now_iso
from xinyu_bridge_observation_reports_store import (
    observation_report_exists,
    read_observation_report_text,
    read_observation_report_text_safe,
    write_observation_report_text,
)


def format_observation_block(observation: ObservationPayload) -> str:
    detected_urls = ", ".join(observation.urls) if observation.urls else "none"
    return f"""
## obs-{observation.observation_id}
- observed_at: {_timestamp_or_now_iso(observation.observed_at)}
- source_channel: qq_group
- group_id: {observation.group_id}
- priority_learning_group: {str(observation.priority).lower()}
- actor_hash: {observation.actor_hash}
- message_id_hash: {observation.message_id_hash}
- text_chars: {len(observation.text)}
- text_excerpt: {observation.text_excerpt}
- detected_urls: {detected_urls}
- learning_candidate: {observation.candidate}
- status: candidate
- reply_policy: no_reply
- memory_boundary: group context/source candidate only; not owner relationship memory
"""


def observation_event_entry(observation: ObservationPayload) -> dict[str, str]:
    return {
        "observation_id": observation.observation_id,
        "group_id": observation.group_id,
        "actor_hash": observation.actor_hash,
        "text_excerpt": observation.text_excerpt,
    }


def _append_section(path: Path, text: str) -> None:
    old = read_observation_report_text_safe(path)
    write_observation_report_text(path, old.rstrip() + "\n\n" + text.strip() + "\n")


def _header(
    *,
    title: str,
    memory_type: str,
    created_at: str,
    updated_at: str,
    tags: str,
) -> str:
    return f"""---
title: {title}
memory_type: {memory_type}
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: system
created_at: {_timestamp_or_now_iso(created_at)}
updated_at: {_timestamp_or_now_iso(updated_at)}
last_confirmed_at: {_timestamp_or_now_iso(updated_at)}
importance_score: 78
impact_score: 76
confidence_score: 90
status: active
tags: [{tags}]
---"""


def _ensure_observation_file(path: Path, observed_at: str) -> None:
    if observation_report_exists(path):
        text = read_observation_report_text(path)
        text = re.sub(r"(?m)^updated_at:\s*.+$", f"updated_at: {_timestamp_or_now_iso(observed_at)}", text, count=1)
        text = re.sub(
            r"(?m)^last_confirmed_at:\s*.+$",
            f"last_confirmed_at: {_timestamp_or_now_iso(observed_at)}",
            text,
            count=1,
        )
        write_observation_report_text(path, text.rstrip() + "\n")
        return
    safe_observed_at = _timestamp_or_now_iso(observed_at)
    write_observation_report_text(
        path,
        _header(
            title="Group Learning Observations",
            memory_type="group_learning_observations",
            created_at=safe_observed_at,
            updated_at=safe_observed_at,
            tags="qq, group, learning, observations, candidates",
        )
        + """

# Group Learning Observations

## Rule
- These are passive group observations, not accepted facts.
- Priority learning group material must pass source/context review before learning.
- Do not write group or non-owner private content into owner relationship memory.
- Do not reply to passive learning groups from this observation path.
""",
    )


def _update_real_life_events(memory_root: Path, observed_at: str, entry: dict[str, str]) -> None:
    path = memory_root / "context/real_life_input_events.md"
    safe_observed_at = _timestamp_or_now_iso(observed_at)
    if not observation_report_exists(path):
        write_observation_report_text(
            path,
            _header(
                title="Real Life Input Events",
                memory_type="real_life_input_events",
                created_at=safe_observed_at,
                updated_at=safe_observed_at,
                tags="context, input_adapter, events",
            )
            + "\n\n# Real Life Input Events\n",
        )
    text = read_observation_report_text(path)
    text = re.sub(r"(?m)^updated_at:\s*.+$", f"updated_at: {_timestamp_or_now_iso(observed_at)}", text, count=1)
    text = re.sub(
        r"(?m)^last_confirmed_at:\s*.+$",
        f"last_confirmed_at: {_timestamp_or_now_iso(observed_at)}",
        text,
        count=1,
    )
    event_block = f"""

## event-{entry['observation_id']}
- source_channel: qq_group
- source_context: priority_learning_group
- group_id: {entry['group_id']}
- actor_id: external_group_member:{entry['actor_hash']}
- relationship_scope: group_context
- content_type: text
- content_summary: {entry['text_excerpt']}
- observed_at: {_timestamp_or_now_iso(observed_at)}
- contains_owner_private: unknown
- contains_private_location: unknown
- owner_intent: priority_learning_group_monitoring
- interpretation_status: raw_candidate
- status: candidate
- reason: passive priority learning group observation; not a fact or owner-memory write
"""
    write_observation_report_text(path, text.rstrip() + event_block)

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from xinyu_memory_event_sourcing import record_learning_observe_event


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    if value is None:
        return default
    return bool(value)


def _one_line(text: str, limit: int = 1200) -> str:
    value = re.sub(r"\s+", " ", text).strip()
    if len(value) <= limit:
        return value
    return value[: limit - 1] + "..."


def _stable_hash(text: str, length: int = 12) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:length]


def _append_section(path: Path, text: str) -> None:
    old = ""
    try:
        old = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        pass
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(old.rstrip() + "\n\n" + text.strip() + "\n", encoding="utf-8")


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
created_at: {created_at}
updated_at: {updated_at}
last_confirmed_at: {updated_at}
importance_score: 78
impact_score: 76
confidence_score: 90
status: active
tags: [{tags}]
---"""


def _ensure_observation_file(path: Path, observed_at: str) -> None:
    if path.exists():
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        text = re.sub(r"(?m)^updated_at:\s*.+$", f"updated_at: {observed_at}", text, count=1)
        text = re.sub(r"(?m)^last_confirmed_at:\s*.+$", f"last_confirmed_at: {observed_at}", text, count=1)
        path.write_text(text.rstrip() + "\n", encoding="utf-8")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        _header(
            title="Group Learning Observations",
            memory_type="group_learning_observations",
            created_at=observed_at,
            updated_at=observed_at,
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
        encoding="utf-8",
    )


def _update_real_life_events(root: Path, observed_at: str, entry: dict[str, str]) -> None:
    path = root / "memory/context/real_life_input_events.md"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            _header(
                title="Real Life Input Events",
                memory_type="real_life_input_events",
                created_at=observed_at,
                updated_at=observed_at,
                tags="context, input_adapter, events",
            )
            + "\n\n# Real Life Input Events\n",
            encoding="utf-8",
        )
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    text = re.sub(r"(?m)^updated_at:\s*.+$", f"updated_at: {observed_at}", text, count=1)
    text = re.sub(r"(?m)^last_confirmed_at:\s*.+$", f"last_confirmed_at: {observed_at}", text, count=1)
    event_block = f"""

## event-{entry['observation_id']}
- source_channel: qq_group
- source_context: priority_learning_group
- group_id: {entry['group_id']}
- actor_id: external_group_member:{entry['actor_hash']}
- relationship_scope: group_context
- content_type: text
- content_summary: {entry['text_excerpt']}
- observed_at: {observed_at}
- contains_owner_private: unknown
- contains_private_location: unknown
- owner_intent: priority_learning_group_monitoring
- interpretation_status: raw_candidate
- status: candidate
- reason: passive priority learning group observation; not a fact or owner-memory write
"""
    path.write_text(text.rstrip() + event_block, encoding="utf-8")


def _learning_candidate(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return "no_empty_text"
    if re.search(r"https?://|www\.|github\.com|arxiv\.org|doi\.org|论文|文档|教程|仓库|框架|模型|agent|LLM|AI|记忆|上下文|工具|安全", stripped, re.I):
        return "yes_source_or_ai_topic_signal"
    if len(stripped) >= 80:
        return "maybe_long_context"
    return "low_chat_context"


def _detected_urls(text: str, limit: int = 5) -> list[str]:
    urls = re.findall(r"https?://[^\s<>()]+|www\.[^\s<>()]+", text, flags=re.I)
    cleaned: list[str] = []
    for url in urls:
        value = url.rstrip(".,，。;；!！?？)]}》")
        if value and value not in cleaned:
            cleaned.append(value)
        if len(cleaned) >= limit:
            break
    return cleaned


async def observe(
    *,
    xinyu_dir: Path,
    memory_root: Path,
    payload: dict[str, Any],
    cleanup_idle_sessions: Callable[..., Any],
    session_count: Callable[[], int],
    lock: Any,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {"accepted": False, "observed": False, "reply": "", "notes": ["invalid_payload"]}

    text = _safe_str(payload.get("text") or payload.get("raw_message")).strip()
    if not text:
        return {"accepted": True, "observed": False, "reply": "", "notes": ["empty_text"]}
    observed_at = _safe_str(payload.get("observed_at")).strip() or datetime.now().astimezone().isoformat()
    group_id = _safe_str(payload.get("group_id"), "unknown").strip() or "unknown"
    user_id = _safe_str(payload.get("user_id"), "unknown").strip() or "unknown"
    message_id = _safe_str(payload.get("message_id"), "unknown").strip() or "unknown"
    priority = _as_bool(payload.get("priority_learning_group"), default=False)
    actor_hash = _stable_hash(f"{group_id}:{user_id}")
    observation_id = f"{observed_at[:10]}-{_stable_hash(group_id + ':' + message_id + ':' + text, 10)}"
    text_excerpt = _one_line(text)
    candidate = _learning_candidate(text)
    urls = _detected_urls(text)

    async with lock:
        cleanup = await cleanup_idle_sessions()
        path = memory_root / "knowledge/group_learning_observations.md"
        _ensure_observation_file(path, observed_at)
        block = f"""
## obs-{observation_id}
- observed_at: {observed_at}
- source_channel: qq_group
- group_id: {group_id}
- priority_learning_group: {str(priority).lower()}
- actor_hash: {actor_hash}
- message_id_hash: {_stable_hash(message_id)}
- text_chars: {len(text)}
- text_excerpt: {text_excerpt}
- detected_urls: {", ".join(urls) if urls else "none"}
- learning_candidate: {candidate}
- status: candidate
- reply_policy: no_reply
- memory_boundary: group context/source candidate only; not owner relationship memory
"""
        _append_section(path, block)
        _update_real_life_events(
            memory_root,
            observed_at,
            {
                "observation_id": observation_id,
                "group_id": group_id,
                "actor_hash": actor_hash,
                "text_excerpt": text_excerpt,
            },
        )
        sidecar_result: dict[str, Any] = {"notes": ["event_sourcing_not_run"]}
        try:
            sidecar_result = record_learning_observe_event(xinyu_dir, payload, text=text)
        except Exception as exc:
            sidecar_result = {"notes": [f"event_sourcing_error:{type(exc).__name__}"]}

    notes = ["learning_observe", "no_agent_turn", "no_reply", "session_not_created"]
    if cleanup["cleaned_sessions"]:
        notes.append(f"cleaned_idle_sessions:{cleanup['cleaned_sessions']}")
    notes.extend(_safe_str(note) for note in sidecar_result.get("notes", [])[:4])
    return {
        "accepted": True,
        "observed": True,
        "reply": "",
        "memory_changed": True,
        "session_created": False,
        "sessions": session_count(),
        "observation_id": f"obs-{observation_id}",
        "learning_candidate": candidate,
        "notes": notes,
    }

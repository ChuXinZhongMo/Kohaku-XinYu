from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class ObservationPayload:
    text: str
    observed_at: str
    group_id: str
    user_id: str
    message_id: str
    priority: bool
    actor_hash: str
    message_id_hash: str
    observation_id: str
    text_excerpt: str
    candidate: str
    urls: tuple[str, ...]


def normalize_observation_payload(payload: dict[str, Any]) -> ObservationPayload | None:
    text = _safe_str(payload.get("text") or payload.get("raw_message")).strip()
    if not text:
        return None
    observed_at = _timestamp_or_now_iso(payload.get("observed_at"))
    group_id = _safe_str(payload.get("group_id"), "unknown").strip() or "unknown"
    user_id = _safe_str(payload.get("user_id"), "unknown").strip() or "unknown"
    message_id = _safe_str(payload.get("message_id"), "unknown").strip() or "unknown"
    return ObservationPayload(
        text=text,
        observed_at=observed_at,
        group_id=group_id,
        user_id=user_id,
        message_id=message_id,
        priority=_as_bool(payload.get("priority_learning_group"), default=False),
        actor_hash=_stable_hash(f"{group_id}:{user_id}"),
        message_id_hash=_stable_hash(message_id),
        observation_id=f"{observed_at[:10]}-{_stable_hash(group_id + ':' + message_id + ':' + text, 10)}",
        text_excerpt=_one_line(text),
        candidate=_learning_candidate(text),
        urls=tuple(_detected_urls(text)),
    )


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _timestamp_or_now_iso(value: Any) -> str:
    parsed = _parse_iso(value)
    if parsed is None:
        return datetime.now().astimezone().isoformat()
    return parsed.astimezone().isoformat()


def _parse_iso(value: Any) -> datetime | None:
    text = _safe_str(value).strip()
    if not text or text == "none":
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed


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


def _learning_candidate(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return "no_empty_text"
    if re.search(
        r"https?://|www\.|github\.com|arxiv\.org|doi\.org|论文|文档|教程|仓库|框架|模型|agent|LLM|AI|记忆|上下文|能力|安全",
        stripped,
        re.I,
    ):
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

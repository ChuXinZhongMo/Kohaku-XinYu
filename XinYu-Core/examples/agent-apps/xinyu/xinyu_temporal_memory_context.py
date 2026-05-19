from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any


@dataclass(frozen=True, slots=True)
class TemporalMemoryItemContext:
    recall_id: str
    relation: str
    age_minutes: int | None
    item_time: str
    human_hint: str


@dataclass(frozen=True, slots=True)
class TemporalMemoryContext:
    evaluated_at: str
    item_contexts: tuple[TemporalMemoryItemContext, ...]
    life_inferences: tuple[str, ...]
    notes: tuple[str, ...]

    def hint_for(self, recall_id: str) -> str:
        for item in self.item_contexts:
            if item.recall_id == recall_id:
                return item.human_hint
        return ""


SLEEP_START_MARKERS: tuple[str, ...] = (
    "nap",
    "sleep",
    "go to bed",
    "rest",
    "\u5348\u7761",
    "\u7761\u89c9",
    "\u7761\u4e86",
    "\u8865\u89c9",
    "\u4f11\u606f",
    "\u8eba\u4e00\u4f1a",
    "\u772f\u4e86\u53bb\u7761",
)

WAKE_MARKERS: tuple[str, ...] = (
    "wake",
    "woke",
    "awake",
    "got up",
    "\u9192\u4e86",
    "\u7761\u9192",
    "\u8d77\u4e86",
    "\u8d77\u5e8a",
)


def build_temporal_memory_context(
    items: tuple[Any, ...] | list[Any],
    *,
    user_text: str = "",
    evaluated_at: datetime | str | None = None,
) -> TemporalMemoryContext:
    now = _coerce_now(evaluated_at)
    item_contexts = tuple(_item_context(item, now) for item in items)
    inferences = _life_inferences(items, item_contexts, user_text=user_text, now=now)
    notes = ["temporal_memory_context_v1"]
    if any(context.age_minutes is not None for context in item_contexts):
        notes.append("temporal_context:absolute_time_available")
    if inferences:
        notes.extend(f"temporal_inference:{item.split('|', 1)[0]}" for item in inferences)
    return TemporalMemoryContext(
        evaluated_at=now.isoformat(timespec="minutes"),
        item_contexts=item_contexts,
        life_inferences=tuple(inferences),
        notes=tuple(notes),
    )


def render_temporal_memory_context(context: TemporalMemoryContext) -> str:
    if not context.item_contexts and not context.life_inferences:
        return ""
    lines = [
        "## Temporal Context",
        "purpose: interpret recalled items by recency and sequence; current owner message still wins.",
        f"evaluated_at: {context.evaluated_at}",
    ]
    for item in context.item_contexts[:8]:
        if item.age_minutes is None and item.relation == "time_unknown":
            continue
        lines.append(
            f"- item: {item.recall_id} | relation: {item.relation} | "
            f"age_minutes: {_safe_age(item.age_minutes)} | hint: {item.human_hint}"
        )
    for inference in context.life_inferences[:4]:
        inference_id, _, detail = inference.partition("|")
        lines.append(f"- inference: {inference_id} | {detail}")
    return "\n".join(lines).strip()


def parse_memory_time(value: str, *, default_tz: timezone | None = None) -> datetime | None:
    text = _safe_str(value).strip()
    if not text:
        return None
    lowered = text.lower()
    if lowered in {"now", "current session", "current_turn_tail", "stable memory file"}:
        return None
    normalized = (
        text.replace("\uff1a", ":")
        .replace("\u5e74", "-")
        .replace("\u6708", "-")
        .replace("\u65e5", " ")
        .replace("\u53f7", " ")
        .strip()
    )
    if "T" in normalized or re.search(r"[+-]\d{2}:\d{2}$", normalized) or normalized.endswith("Z"):
        try:
            parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
        except ValueError:
            parsed = None
        if parsed is not None:
            if parsed.tzinfo is None and default_tz is not None:
                parsed = parsed.replace(tzinfo=default_tz)
            return parsed
    match = re.search(
        r"(?P<year>20\d{2})[./-](?P<month>\d{1,2})[./-](?P<day>\d{1,2})"
        r"(?:[ T]+(?P<hour>\d{1,2}):(?P<minute>\d{2})(?::(?P<second>\d{2}))?)?",
        normalized,
    )
    if match:
        return datetime(
            int(match.group("year")),
            int(match.group("month")),
            int(match.group("day")),
            int(match.group("hour") or 0),
            int(match.group("minute") or 0),
            int(match.group("second") or 0),
            tzinfo=default_tz,
        )
    try:
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None and default_tz is not None:
        parsed = parsed.replace(tzinfo=default_tz)
    return parsed


def _item_context(item: Any, now: datetime) -> TemporalMemoryItemContext:
    recall_id = _safe_str(getattr(item, "recall_id", "")) or "recall"
    raw_time = _safe_str(getattr(item, "time", ""))
    item_time = parse_memory_time(raw_time, default_tz=_datetime_tz(now))
    if item_time is None:
        relation = _non_absolute_relation(raw_time)
        return TemporalMemoryItemContext(
            recall_id=recall_id,
            relation=relation,
            age_minutes=None,
            item_time=raw_time,
            human_hint=_hint_for_relation(relation, None),
        )
    if now.tzinfo is not None and item_time.tzinfo is None:
        item_time = item_time.replace(tzinfo=now.tzinfo)
    if now.tzinfo is None and item_time.tzinfo is not None:
        now = now.replace(tzinfo=item_time.tzinfo)
    age = now - item_time
    age_minutes = int(age.total_seconds() // 60)
    relation = _relation_for_age(age, now=now, item_time=item_time)
    return TemporalMemoryItemContext(
        recall_id=recall_id,
        relation=relation,
        age_minutes=age_minutes,
        item_time=item_time.isoformat(timespec="minutes"),
        human_hint=_hint_for_relation(relation, age_minutes),
    )


def _relation_for_age(age: timedelta, *, now: datetime, item_time: datetime) -> str:
    seconds = age.total_seconds()
    if seconds < -300:
        return "future_or_clock_skew"
    minutes = max(0, int(seconds // 60))
    if minutes <= 5:
        return "just_now"
    if minutes <= 30:
        return "very_recent"
    if minutes <= 150:
        return "recent_same_scene"
    if _same_local_day(now, item_time):
        return "today_earlier"
    if _same_local_day(now - timedelta(days=1), item_time):
        return "yesterday"
    if minutes <= 7 * 24 * 60:
        return "this_week"
    return "older_memory"


def _hint_for_relation(relation: str, age_minutes: int | None) -> str:
    if relation == "current_turn_tail":
        return "current session tail; treat as immediate context."
    if relation == "stable_or_plan_time":
        return "stable file or plan reference; use as background, not recent scene."
    if relation == "time_unknown":
        return "time unknown; do not infer recency."
    if relation == "future_or_clock_skew":
        return "timestamp is ahead of evaluated time; treat as clock skew unless verified."
    if age_minutes is None:
        return relation
    if relation == "just_now":
        return f"{age_minutes}m ago; treat as the same live moment."
    if relation == "very_recent":
        return f"{age_minutes}m ago; likely still part of the current scene."
    if relation == "recent_same_scene":
        return f"{age_minutes}m ago; likely still affects current physical/emotional state."
    if relation == "today_earlier":
        return f"{age_minutes}m ago today; use as same-day context."
    if relation == "yesterday":
        return "yesterday; relevant for continuity, not immediate state unless repeated."
    if relation == "this_week":
        return "within the last week; use as recent pattern evidence."
    return "older memory; use only as background or pattern evidence."


def _life_inferences(
    items: tuple[Any, ...] | list[Any],
    contexts: tuple[TemporalMemoryItemContext, ...],
    *,
    user_text: str,
    now: datetime,
) -> list[str]:
    by_id = {context.recall_id: context for context in contexts}
    sleep_events: list[tuple[Any, TemporalMemoryItemContext]] = []
    wake_events: list[tuple[Any, TemporalMemoryItemContext]] = []
    for item in items:
        context = by_id.get(_safe_str(getattr(item, "recall_id", "")))
        if context is None or context.age_minutes is None:
            continue
        text = _safe_str(getattr(item, "summary", ""))
        if _contains_any(text, SLEEP_START_MARKERS):
            sleep_events.append((item, context))
        if _contains_any(text, WAKE_MARKERS):
            wake_events.append((item, context))

    inferences: list[str] = []
    user_has_wake_marker = _contains_any(user_text, WAKE_MARKERS)
    for _sleep_item, sleep_context in sleep_events:
        sleep_time = parse_memory_time(sleep_context.item_time, default_tz=_datetime_tz(now))
        if sleep_time is None:
            continue
        wake_context = _nearest_wake_after(sleep_time, wake_events)
        minutes_since_sleep = max(0, int((now - sleep_time).total_seconds() // 60))
        rest_minutes = None
        if wake_context is not None:
            wake_time = parse_memory_time(wake_context.item_time, default_tz=_datetime_tz(now))
            if wake_time is not None:
                rest_minutes = max(0, int((wake_time - sleep_time).total_seconds() // 60))
        elif user_has_wake_marker:
            rest_minutes = minutes_since_sleep
        if rest_minutes is None:
            continue
        if 15 <= rest_minutes <= 180 and minutes_since_sleep <= 240:
            inferences.append(
                "recent_wake_from_nap|"
                f"sleep_to_wake_minutes: {rest_minutes}; "
                "reply should account for just-finished rest without overstating certainty."
            )
            break
    return inferences


def _nearest_wake_after(
    sleep_time: datetime,
    wake_events: list[tuple[Any, TemporalMemoryItemContext]],
) -> TemporalMemoryItemContext | None:
    candidates: list[TemporalMemoryItemContext] = []
    for _item, context in wake_events:
        wake_time = parse_memory_time(context.item_time, default_tz=_datetime_tz(sleep_time))
        if wake_time is None:
            continue
        if wake_time >= sleep_time and wake_time - sleep_time <= timedelta(hours=3):
            candidates.append(context)
    if not candidates:
        return None
    return sorted(candidates, key=lambda context: parse_memory_time(context.item_time) or datetime.max)[0]


def _non_absolute_relation(raw_time: str) -> str:
    lowered = _safe_str(raw_time).strip().lower()
    if lowered in {"now", "current session", "current session tail", "current_turn_tail"}:
        return "current_turn_tail"
    if "stable" in lowered or "plan" in lowered:
        return "stable_or_plan_time"
    return "time_unknown"


def _same_local_day(left: datetime, right: datetime) -> bool:
    if left.tzinfo is not None and right.tzinfo is not None:
        right = right.astimezone(left.tzinfo)
    return left.date() == right.date()


def _coerce_now(value: datetime | str | None) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str) and value.strip():
        parsed = parse_memory_time(value, default_tz=timezone.utc)
        if parsed is not None:
            return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
    return datetime.now().astimezone()


def _datetime_tz(value: datetime) -> timezone | None:
    tz = value.tzinfo
    return tz if isinstance(tz, timezone) else None


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    lowered = _safe_str(text).lower()
    return any(marker and marker.lower() in lowered for marker in markers)


def _safe_age(age_minutes: int | None) -> str:
    return "unknown" if age_minutes is None else str(age_minutes)


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)

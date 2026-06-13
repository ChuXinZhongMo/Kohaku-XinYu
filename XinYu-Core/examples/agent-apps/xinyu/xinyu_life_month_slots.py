from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from xinyu_life_month_slots_store import CURRENT_LIFE_MONTH_CONTEXT_REL
from xinyu_life_month_slots_store import LIFE_MONTH_SLOTS_REL
from xinyu_life_month_slots_store import current_life_month_context_path
from xinyu_life_month_slots_store import life_month_slots_path
from xinyu_life_month_slots_store import read_life_month_text
from xinyu_life_month_slots_store import write_current_life_month_context

VALID_STATUSES = {"empty", "light", "active", "important"}
VALID_SOURCES = {"owner_supplied", "inferred_style_anchor", "runtime_event", "unset"}
VALID_WORLD_SCOPES = {"none", "global", "china", "local", "technology", "culture"}

TOPIC_MARKERS = {
    "heat": (
        "guangzhou",
        "heat",
        "weather",
        "subway",
        "ac",
        "\u5e7f\u5dde",
        "\u70ed",
        "\u5929\u6c14",
        "\u5730\u94c1",
        "\u7a7a\u8c03",
    ),
    "study": (
        "study",
        "education",
        "homework",
        "tutoring",
        "exam",
        "physics",
        "double reduction",
        "\u5b66\u4e60",
        "\u4f5c\u4e1a",
        "\u8003\u8bd5",
        "\u8bd5\u5377",
        "\u7269\u7406",
        "\u8865\u8bfe",
    ),
    "ai": (
        " ai",
        "ai ",
        "chatgpt",
        "gpt",
        "model",
        "conversational ai",
        "\u4eba\u5de5\u667a\u80fd",
        "\u6a21\u578b",
    ),
    "pandemic": (
        "covid",
        "pandemic",
        "mask",
        "\u75ab\u60c5",
        "\u53e3\u7f69",
    ),
    "owner": (
        "owner",
        "qq",
        "private-chat",
        "style-pressure",
        "\u54e5",
        "\u54e5\u54e5",
        "\u5fc3\u7389",
    ),
}


@dataclass(frozen=True)
class LifeMonthSlot:
    year_month: str
    memory_status: str
    weight: int
    confidence: int
    source: str
    one_line_summary: str
    optional_expanded_notes: str
    emotional_residue: str
    relationship_effect: str
    decay_policy: str
    world_anchor: str = "none"
    world_anchor_scope: str = "none"
    world_anchor_effect: str = "none"
    world_anchor_boundary: str = "none"
    raw_body: str = ""

    @property
    def searchable_text(self) -> str:
        return "\n".join(
            [
                self.one_line_summary,
                self.optional_expanded_notes,
                self.emotional_residue,
                self.relationship_effect,
                self.world_anchor,
                self.world_anchor_effect,
                self.world_anchor_boundary,
            ]
        ).lower()


@dataclass(frozen=True)
class LifeMonthBlueprint:
    slot_start: str
    slot_end: str
    slot_count: int
    slots: dict[str, LifeMonthSlot]


@dataclass(frozen=True)
class SelectedLifeMonthSlot:
    slot: LifeMonthSlot
    relevance_score: int
    reasons: tuple[str, ...]


def _coerce_datetime(value: datetime | str | None) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.astimezone()
    if isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip())
            return parsed if parsed.tzinfo else parsed.astimezone()
        except ValueError:
            pass
    return datetime.now().astimezone()


def _read_text(path: Path) -> str:
    return read_life_month_text(path)


def _field(text: str, name: str, default: str = "") -> str:
    match = re.search(rf"(?m)^- {re.escape(name)}:\s*(.*)$", text)
    return match.group(1).strip() if match else default


def _int_field(text: str, name: str, default: int = 0) -> int:
    raw = _field(text, name, str(default))
    try:
        return int(raw)
    except ValueError:
        return default


def _month_count(start: str, end: str) -> int:
    start_year, start_month = [int(part) for part in start.split("-", 1)]
    end_year, end_month = [int(part) for part in end.split("-", 1)]
    return (end_year - start_year) * 12 + (end_month - start_month) + 1


def _month_in_range(year_month: str, start: str, end: str) -> bool:
    return start <= year_month <= end


def _split_slot_bodies(text: str) -> list[tuple[str, str]]:
    parts = re.split(r"(?m)^## slot ([0-9]{4}-[0-9]{2})\s*$", text)
    slots: list[tuple[str, str]] = []
    for index in range(1, len(parts), 2):
        slots.append((parts[index].strip(), parts[index + 1]))
    return slots


def parse_life_month_slots(root: Path) -> LifeMonthBlueprint:
    text = _read_text(life_month_slots_path(root))
    slot_start = _field(text, "slot_start", "2010-05")
    slot_end = _field(text, "slot_end", "2026-04")
    slot_count = _int_field(text, "slot_count", 192)
    slots: dict[str, LifeMonthSlot] = {}
    for slot_id, body in _split_slot_bodies(text):
        slot = LifeMonthSlot(
            year_month=_field(body, "year_month", slot_id),
            memory_status=_field(body, "memory_status", "empty"),
            weight=max(0, min(100, _int_field(body, "weight", 0))),
            confidence=max(0, min(100, _int_field(body, "confidence", 0))),
            source=_field(body, "source", "unset"),
            one_line_summary=_field(body, "one_line_summary", "none"),
            optional_expanded_notes=_field(body, "optional_expanded_notes", "none"),
            emotional_residue=_field(body, "emotional_residue", "none"),
            relationship_effect=_field(body, "relationship_effect", "none"),
            decay_policy=_field(body, "decay_policy", "stay_empty_until_evidence"),
            world_anchor=_field(body, "world_anchor", "none"),
            world_anchor_scope=_field(body, "world_anchor_scope", "none"),
            world_anchor_effect=_field(body, "world_anchor_effect", "none"),
            world_anchor_boundary=_field(body, "world_anchor_boundary", "none"),
            raw_body=body.strip(),
        )
        slots[slot_id] = slot
    return LifeMonthBlueprint(
        slot_start=slot_start,
        slot_end=slot_end,
        slot_count=slot_count,
        slots=slots,
    )


def validate_life_month_slots(root: Path) -> list[str]:
    blueprint = parse_life_month_slots(root)
    failures: list[str] = []
    if blueprint.slot_count != 192:
        failures.append(f"unexpected slot_count: {blueprint.slot_count}")
    try:
        expected_count = _month_count(blueprint.slot_start, blueprint.slot_end)
    except Exception:
        expected_count = -1
    if expected_count != blueprint.slot_count:
        failures.append(
            f"slot range does not match slot_count: {blueprint.slot_start}..{blueprint.slot_end} -> {expected_count}"
        )
    if len(blueprint.slots) > 32:
        failures.append(f"too many explicit month slots for sparse scaffold: {len(blueprint.slots)}")

    for slot_id, slot in blueprint.slots.items():
        if slot.year_month != slot_id:
            failures.append(f"{slot_id}: year_month mismatch: {slot.year_month}")
        if not _month_in_range(slot_id, blueprint.slot_start, blueprint.slot_end):
            failures.append(f"{slot_id}: out of range")
        if slot.memory_status not in VALID_STATUSES:
            failures.append(f"{slot_id}: invalid memory_status: {slot.memory_status}")
        if slot.source not in VALID_SOURCES:
            failures.append(f"{slot_id}: invalid source: {slot.source}")
        if slot.world_anchor_scope not in VALID_WORLD_SCOPES:
            failures.append(f"{slot_id}: invalid world_anchor_scope: {slot.world_anchor_scope}")
        if not 0 <= slot.weight <= 100:
            failures.append(f"{slot_id}: weight out of range: {slot.weight}")
        if not 0 <= slot.confidence <= 100:
            failures.append(f"{slot_id}: confidence out of range: {slot.confidence}")
        if not slot.one_line_summary or slot.one_line_summary == "none":
            failures.append(f"{slot_id}: missing one_line_summary")
        if slot.memory_status == "important":
            failures.append(f"{slot_id}: important slots require explicit owner review, not scaffold seeding")
        if slot.memory_status in {"active", "important"} and slot.source == "inferred_style_anchor":
            failures.append(f"{slot_id}: inferred_style_anchor cannot be active/important")
        if slot.world_anchor != "none" and slot.world_anchor_boundary in {"", "none"}:
            failures.append(f"{slot_id}: world_anchor missing boundary")
    return failures


def _topic_hits(user_text: str, slot: LifeMonthSlot) -> tuple[str, ...]:
    user_lower = f" {user_text.lower()} "
    slot_lower = f" {slot.searchable_text} "
    hits: list[str] = []
    for topic, markers in TOPIC_MARKERS.items():
        user_has = any(marker in user_lower for marker in markers)
        slot_has = any(marker in slot_lower for marker in markers)
        if user_has and slot_has:
            hits.append(topic)
    return tuple(hits)


def select_relevant_life_month_slots(
    root: Path,
    *,
    user_text: str = "",
    evaluated_at: datetime | str | None = None,
    max_slots: int = 6,
) -> list[SelectedLifeMonthSlot]:
    blueprint = parse_life_month_slots(root)
    current_month = _coerce_datetime(evaluated_at).strftime("%Y-%m")
    selected: list[SelectedLifeMonthSlot] = []
    for slot in blueprint.slots.values():
        reasons: list[str] = []
        score = slot.weight + round(slot.confidence * 0.2)
        topics = _topic_hits(user_text, slot)

        if slot.year_month == current_month:
            reasons.append("current_month")
            score += 40
        if slot.memory_status == "active":
            reasons.append("active_slot")
            score += 30
        elif slot.memory_status == "important":
            reasons.append("important_slot")
            score += 45
        if slot.source in {"owner_supplied", "runtime_event"} and slot.weight >= 50:
            reasons.append(f"{slot.source}_high_weight")
            score += 18
        if topics:
            reasons.append("topic:" + ",".join(topics))
            score += 28 + len(topics) * 4
        if slot.weight >= 70:
            reasons.append("high_weight")
            score += 10

        if reasons:
            selected.append(
                SelectedLifeMonthSlot(
                    slot=slot,
                    relevance_score=max(0, min(200, score)),
                    reasons=tuple(reasons),
                )
            )

    selected.sort(key=lambda item: (item.relevance_score, item.slot.year_month), reverse=True)
    return selected[:max_slots]


def render_current_life_month_context(
    root: Path,
    *,
    user_text: str = "",
    evaluated_at: datetime | str | None = None,
    max_slots: int = 6,
) -> str:
    evaluated = _coerce_datetime(evaluated_at)
    selected = select_relevant_life_month_slots(
        root,
        user_text=user_text,
        evaluated_at=evaluated,
        max_slots=max_slots,
    )
    if selected:
        selected_block = "\n\n".join(_render_selected_slot(item) for item in selected)
    else:
        selected_block = "- none"
    return f"""---
title: Current Life Month Context
memory_type: current_life_month_context
time_scope: immediate
subject_ids: [xinyu]
protected: true
source: xinyu_life_month_slots
created_at: 2026-04-28T00:00:00+08:00
updated_at: {evaluated.isoformat()}
importance_score: 74
impact_score: 78
confidence_score: 90
status: active
tags: [life, memory, month-slots, runtime-selection]
---

# Current Life Month Context

## Selection Policy
- selected_from: {LIFE_MONTH_SLOTS_REL}
- current_month: {evaluated.strftime("%Y-%m")}
- selection_rule: current month, active or important slots, high-weight owner/runtime slots, and topic-triggered low-weight anchors only
- boundary_rule: selected month slots are speech texture and continuity hints, not complete biography or proof of real-world childhood
- empty_rule: unselected months remain empty or irrelevant for this turn

## Selected Slots
{selected_block}
"""


def _render_selected_slot(item: SelectedLifeMonthSlot) -> str:
    slot = item.slot
    return "\n".join(
        [
            f"## selected_slot {slot.year_month}",
            f"- relevance_score: {item.relevance_score}",
            f"- selection_reason: {', '.join(item.reasons)}",
            f"- memory_status: {slot.memory_status}",
            f"- weight: {slot.weight}",
            f"- confidence: {slot.confidence}",
            f"- source: {slot.source}",
            f"- one_line_summary: {slot.one_line_summary}",
            f"- emotional_residue: {slot.emotional_residue}",
            f"- relationship_effect: {slot.relationship_effect}",
            f"- decay_policy: {slot.decay_policy}",
            f"- world_anchor: {slot.world_anchor}",
            f"- world_anchor_scope: {slot.world_anchor_scope}",
            f"- world_anchor_effect: {slot.world_anchor_effect}",
            f"- world_anchor_boundary: {slot.world_anchor_boundary}",
            "- usage_hint: use only as a small surface texture if relevant; do not invent new events",
        ]
    )


def refresh_current_life_month_context(
    root: Path,
    *,
    user_text: str = "",
    evaluated_at: datetime | str | None = None,
    max_slots: int = 6,
) -> str:
    text = render_current_life_month_context(
        root,
        user_text=user_text,
        evaluated_at=evaluated_at,
        max_slots=max_slots,
    )
    path = current_life_month_context_path(root)
    old = _read_text(path)
    if old != text:
        write_current_life_month_context(root, text)
    return text


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Validate or refresh XinYu life-month slot context.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--text", default="")
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    failures = validate_life_month_slots(root)
    if failures:
        print("Life month slot validation failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    if args.refresh:
        print(refresh_current_life_month_context(root, user_text=args.text))
    else:
        print("Life month slot validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

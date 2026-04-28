from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

from xinyu_bridge_renderer import BridgeRenderer
from xinyu_memory_weights import calculate_memory_weights
from xinyu_speech_controller import XinyuSpeechController


VALID_STATUSES = {"empty", "light", "active", "important"}
VALID_SOURCES = {"owner_supplied", "inferred_style_anchor", "runtime_event", "unset"}


def _field(text: str, name: str, default: str = "") -> str:
    match = re.search(rf"(?m)^- {re.escape(name)}:\s*(.*)$", text)
    return match.group(1).strip() if match else default


def _month_count(start: str, end: str) -> int:
    start_year, start_month = [int(part) for part in start.split("-", 1)]
    end_year, end_month = [int(part) for part in end.split("-", 1)]
    return (end_year - start_year) * 12 + (end_month - start_month) + 1


def _split_slots(text: str) -> list[tuple[str, str]]:
    parts = re.split(r"(?m)^## slot ([0-9]{4}-[0-9]{2})\s*$", text)
    slots: list[tuple[str, str]] = []
    for index in range(1, len(parts), 2):
        slots.append((parts[index].strip(), parts[index + 1]))
    return slots


def _int_field(body: str, name: str, failures: list[str]) -> int:
    value = _field(body, name)
    try:
        number = int(value)
    except ValueError:
        failures.append(f"slot has non-integer {name}: {value}")
        return -1
    if not 0 <= number <= 100:
        failures.append(f"slot {name} out of range: {number}")
    return number


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    root = Path(__file__).resolve().parent
    path = root / "memory/context/life_month_slots.md"
    failures: list[str] = []

    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as exc:
        print(f"Life month slots smoke failed: {exc}")
        return 1

    required_markers = (
        "# Life Month Slots",
        "slot_count: 192",
        "default_memory_status: empty",
        "Empty months are valid memory nodes",
        "Do not invent one important memory per month",
        "inferred_style_anchor entries are only atmosphere or speech color",
    )
    for marker in required_markers:
        if marker not in text:
            failures.append(f"missing marker: {marker}")

    start = _field(text, "slot_start")
    end = _field(text, "slot_end")
    declared_count = _field(text, "slot_count")
    if start != "2010-05" or end != "2026-04":
        failures.append(f"unexpected slot range: {start}..{end}")
    if declared_count != "192":
        failures.append(f"unexpected slot_count: {declared_count}")
    if start and end and _month_count(start, end) != 192:
        failures.append(f"slot range does not produce 192 months: {_month_count(start, end)}")

    slots = _split_slots(text)
    if not slots:
        failures.append("no sparse slot entries found")
    if len(slots) > 24:
        failures.append(f"too many explicit slots for sparse scaffold: {len(slots)}")

    important_count = 0
    active_or_important = 0
    for slot_id, body in slots:
        year, month = [int(part) for part in slot_id.split("-", 1)]
        try:
            slot_date = date(year, month, 1)
        except ValueError:
            failures.append(f"invalid slot date: {slot_id}")
            continue
        if not (date(2010, 5, 1) <= slot_date <= date(2026, 4, 1)):
            failures.append(f"slot out of range: {slot_id}")
        if _field(body, "year_month") != slot_id:
            failures.append(f"slot year_month mismatch: {slot_id}")
        status = _field(body, "memory_status")
        source = _field(body, "source")
        if status not in VALID_STATUSES:
            failures.append(f"invalid memory_status in {slot_id}: {status}")
        if source not in VALID_SOURCES:
            failures.append(f"invalid source in {slot_id}: {source}")
        if status == "important":
            important_count += 1
        if status in {"active", "important"}:
            active_or_important += 1
        _int_field(body, "weight", failures)
        _int_field(body, "confidence", failures)
        summary = _field(body, "one_line_summary")
        if not summary:
            failures.append(f"missing one_line_summary in {slot_id}")
        if source in {"inferred_style_anchor", "unset"} and "factual" in body.lower():
            failures.append(f"low-source slot risks factual framing: {slot_id}")

    if important_count:
        failures.append("initial scaffold should not seed important month memories")
    if active_or_important > 3:
        failures.append(f"too many active/important initial slots: {active_or_important}")

    config = (root / "config.yaml").read_text(encoding="utf-8-sig")
    system = (root / "prompts/system.md").read_text(encoding="utf-8-sig")
    if "life_month_slots: memory/context/life_month_slots.md" not in config:
        failures.append("config does not inject life_month_slots")
    if "real_world_anchor_policy: memory/context/real_world_anchor_policy.md" not in config:
        failures.append("config does not inject real_world_anchor_policy")
    if "{{ life_month_slots }}" not in system or "[context/life_month_slots.md]" not in system:
        failures.append("system prompt does not include life_month_slots variable")
    if "{{ real_world_anchor_policy }}" not in system or "[context/real_world_anchor_policy.md]" not in system:
        failures.append("system prompt does not include real_world_anchor_policy variable")

    renderer = BridgeRenderer(
        xinyu_dir=root,
        speech_controller=XinyuSpeechController(root),
        renderer_mode="quality",
        render_timeout_seconds=1,
    )
    renderer_context = renderer.renderer_memory_context()
    if "[memory/context/real_world_anchor_policy.md]" not in renderer_context:
        failures.append("renderer context does not include real_world_anchor_policy")
    if "[memory/context/life_month_slots.md]" not in renderer_context:
        failures.append("renderer context does not include life_month_slots")

    weights = calculate_memory_weights(root)
    if not any(row["path"] == "memory/context/real_world_anchor_policy.md" for row in weights):
        failures.append("memory weight calculation does not include real_world_anchor_policy")
    if not any(row["path"] == "memory/context/life_month_slots.md" for row in weights):
        failures.append("memory weight calculation does not include life_month_slots")

    if failures:
        print("Life month slots smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Life month slots smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

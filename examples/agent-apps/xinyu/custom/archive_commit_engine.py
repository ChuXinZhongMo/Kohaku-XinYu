from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

TERMINAL_STATUSES = {"compressed", "committed", "archived", "dormant"}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def extract_value(text: str, field: str, default: str = "unknown") -> str:
    pattern = re.compile(rf"^- {re.escape(field)}:\s*(.+)$", re.M)
    match = pattern.search(text)
    return match.group(1).strip() if match else default


def _split_archive_items(text: str) -> tuple[str, list[dict[str, object]]]:
    parts = re.split(r"(?m)^## (item-\d{4}-\d{2}-\d{2}-\d{3})\n", text)
    prefix = parts[0]
    items: list[dict[str, object]] = []
    for i in range(1, len(parts), 2):
        item_id = parts[i]
        body = parts[i + 1]
        fields = {"target": "none", "status": "hold", "reason": "none"}
        for line in body.splitlines():
            if line.startswith("- target: "):
                fields["target"] = line.removeprefix("- target: ").strip()
            elif line.startswith("- status: "):
                fields["status"] = line.removeprefix("- status: ").strip()
            elif line.startswith("- reason: "):
                fields["reason"] = line.removeprefix("- reason: ").strip()
        items.append({"item_id": item_id, "body": body, "fields": fields})
    return prefix, items


def _next_numbered_id(text: str, prefix: str, date_part: str) -> str:
    pattern = re.compile(rf"(?m)^## {re.escape(prefix)}-{re.escape(date_part)}-(\d{{3}})$")
    numbers = [int(match.group(1)) for match in pattern.finditer(text)]
    next_number = max(numbers, default=0) + 1
    return f"{prefix}-{date_part}-{next_number:03d}"


def _append_compressed(root: Path, checked_at: str, item: dict[str, object]) -> bool:
    path = root / "memory/archive/compressed.md"
    text = read_text(path).rstrip()
    fields = item["fields"]  # type: ignore[index]
    item_id = str(item["item_id"])
    if f"- source_item: {item_id}" in text:
        return False
    compressed_id = _next_numbered_id(text, "compressed", checked_at[:10])
    addition = (
        f"\n\n## {compressed_id}\n"
        f"- source_item: {item_id}\n"
        f"- compressed_at: {checked_at}\n"
        "- source_window: archive_queue\n"
        "- subjects: [xinyu, owner]\n"
        f"- reason: {fields['reason']}\n"
        f"- retained_meaning: {fields['target']}\n"
        "- retained_effect: preserved as a compressed long-term summary after the retention gate allowed compression\n"
        "- reality_boundary: compression is a summary of existing memory, not a new fact\n"
    )
    write_text(path, text + addition + "\n")
    return True


def _append_dormant(root: Path, checked_at: str, item: dict[str, object]) -> bool:
    path = root / "memory/archive/dormant.md"
    text = read_text(path).rstrip()
    fields = item["fields"]  # type: ignore[index]
    item_id = str(item["item_id"])
    if f"- source_item: {item_id}" in text:
        return False
    dormant_id = _next_numbered_id(text, "dormant", checked_at[:10])
    addition = (
        f"\n\n## {dormant_id}\n"
        f"- source_item: {item_id}\n"
        f"- entered_dormant_at: {checked_at}\n"
        f"- summary: {fields['target']}\n"
        "- subjects: [xinyu, owner]\n"
        "- wake_conditions: mentioned again by owner, reactivated by reflection, or matched by a future relationship pattern\n"
        f"- last_accessed_at: {checked_at}\n"
        "- dormant_boundary: dormant does not mean deleted; it means low-frequency recall unless triggered\n"
    )
    write_text(path, text + addition + "\n")
    return True


def _mark_queue_committed(queue_text: str, committed_ids: set[str], checked_at: str) -> str:
    prefix, items = _split_archive_items(queue_text)
    if not items:
        return queue_text
    rendered = [prefix.rstrip()]
    for item in items:
        item_id = str(item["item_id"])
        body = str(item["body"]).rstrip()
        if item_id in committed_ids:
            lines = []
            status_seen = False
            for line in body.splitlines():
                if line.startswith("- status: "):
                    lines.append("- status: compressed")
                    status_seen = True
                else:
                    lines.append(line)
            if not status_seen:
                lines.insert(0, "- status: compressed")
            if not any(line.startswith("- committed_at: ") for line in lines):
                lines.append(f"- committed_at: {checked_at}")
            if not any(line.startswith("- archive_commit: ") for line in lines):
                lines.append("- archive_commit: compressed-to-long-term-summary")
            body = "\n".join(lines).rstrip()
        rendered.append(f"\n\n## {item_id}\n{body}")
    return "".join(rendered).rstrip() + "\n"


def render_state(
    checked_at: str,
    mode: str,
    commit_action: str,
    commit_reason: str,
    committed_items: int,
    archive_permission: str,
    next_action: str,
    archive_queue_items: int,
    active_queue_items: int,
    committed_item_ids: list[str],
) -> str:
    committed_block = "\n".join(f"- {item_id}" for item_id in committed_item_ids) or "- none"
    return f"""---
title: Archive Commit State
memory_type: archive_commit_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-24T00:00:00+08:00
updated_at: {checked_at}
last_confirmed_at: {checked_at}
importance_score: 82
impact_score: 84
confidence_score: 100
status: active
tags: [archive, commit, state]
---

# Archive Commit State

## Last Evaluation
- checked_at: {checked_at}
- mode: {mode}

## Commit Decision
- commit_action: {commit_action}
- commit_reason: {commit_reason}
- committed_items: {committed_items}

## Inputs
- archive_permission: {archive_permission}
- next_action: {next_action}
- archive_queue_items: {archive_queue_items}
- active_archive_queue_items: {active_queue_items}

## Committed Item Ids
{committed_block}

## Rules
- Commit is the terminal archive step and must stay more conservative than archive output.
- No commit may happen while the retention gate is still holding.
- If commit is blocked, leave queue material intact.
- A committed queue item is compressed and dormant, not erased.
"""


def run_archive_commit(
    root: Path,
    checked_at: str | None = None,
    mode: str = "runtime_archive_commit",
) -> dict[str, object]:
    checked_at = checked_at or datetime.now().astimezone().isoformat()

    retention_gate = read_text(root / "memory/archive/retention_gate_state.md")
    archive_output = read_text(root / "memory/archive/archive_output_state.md")
    archive_queue = read_text(root / "memory/archive/archive_queue.md")

    archive_permission = extract_value(retention_gate, "archive_permission", "hold")
    next_action = extract_value(archive_output, "next_action", "keep_holding")
    _, items = _split_archive_items(archive_queue)
    archive_queue_items = len(items)
    active_items = [
        item for item in items
        if str(item["fields"]["status"]) not in TERMINAL_STATUSES  # type: ignore[index]
    ]
    active_queue_items = len(active_items)
    ready_items = [
        item for item in active_items
        if str(item["fields"]["status"]) != "hold"  # type: ignore[index]
    ]
    committed_ids: list[str] = []

    if archive_queue_items <= 0:
        commit_action = "idle"
        commit_reason = "no_archive_candidates"
    elif active_queue_items <= 0:
        commit_action = "idle"
        commit_reason = "no_active_archive_candidates"
    elif archive_permission != "compress_ready":
        commit_action = "blocked"
        commit_reason = "retention_gate_not_ready"
    elif next_action != "summarize_then_compress":
        commit_action = "blocked"
        commit_reason = "archive_output_not_ready"
    elif not ready_items:
        commit_action = "blocked"
        commit_reason = "no_ready_items"
    else:
        for item in ready_items:
            wrote_compressed = _append_compressed(root, checked_at, item)
            wrote_dormant = _append_dormant(root, checked_at, item)
            if wrote_compressed or wrote_dormant:
                committed_ids.append(str(item["item_id"]))
        if committed_ids:
            updated_queue = _mark_queue_committed(archive_queue, set(committed_ids), checked_at)
            write_text(root / "memory/archive/archive_queue.md", updated_queue)
            commit_action = "committed"
            commit_reason = "compressed_and_marked_dormant"
        else:
            commit_action = "idle"
            commit_reason = "ready_items_already_committed"

    write_text(
        root / "memory/archive/archive_commit_state.md",
        render_state(
            checked_at,
            mode,
            commit_action,
            commit_reason,
            len(committed_ids),
            archive_permission,
            next_action,
            archive_queue_items,
            active_queue_items,
            committed_ids,
        ),
    )

    return {
        "checked_at": checked_at,
        "commit_action": commit_action,
        "commit_reason": commit_reason,
        "committed_items": len(committed_ids),
        "committed_item_ids": committed_ids,
        "archive_permission": archive_permission,
        "next_action": next_action,
        "archive_queue_items": archive_queue_items,
        "active_queue_items": active_queue_items,
    }

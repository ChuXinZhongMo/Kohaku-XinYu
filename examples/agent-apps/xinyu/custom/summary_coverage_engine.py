"""Summary coverage gate before event-sourced archive compression."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from memory_consistency_gate_engine import run_memory_consistency_gate
from memory_event_schema import load_jsonl, string_list


TERMINAL_STATUSES = {"compressed", "committed", "archived", "dormant"}


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except OSError:
        return ""


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def extract_value(text: str, field: str, default: str = "unknown") -> str:
    pattern = re.compile(rf"^- {re.escape(field)}:\s*(.+)$", re.M)
    match = pattern.search(text)
    return match.group(1).strip() if match else default


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


def _field_list(value: str) -> list[str]:
    cleaned = value.strip()
    if not cleaned or cleaned.lower() in {"none", "[]"}:
        return []
    if cleaned.startswith("[") and cleaned.endswith("]"):
        cleaned = cleaned[1:-1]
    parts = []
    for part in re.split(r"[,，\s]+", cleaned):
        part = part.strip().strip("'\"[]")
        if part:
            parts.append(part)
    return parts


def extract_archive_items(text: str) -> list[dict[str, Any]]:
    parts = re.split(r"(?m)^## (item-\d{4}-\d{2}-\d{2}-\d{3})\n", text)
    items: list[dict[str, Any]] = []
    for index in range(1, len(parts), 2):
        item_id = parts[index].strip()
        body = parts[index + 1]
        fields = {
            "target": "none",
            "status": "hold",
            "reason": "none",
            "coverage_required": "false",
            "source_event_ids": "",
            "retained_claim_ids": "",
        }
        for line in body.splitlines():
            stripped = line.strip()
            if not stripped.startswith("- ") or ":" not in stripped:
                continue
            key, value = stripped[2:].split(":", 1)
            key = key.strip()
            if key in fields:
                fields[key] = value.strip()
        items.append({"item_id": item_id, "fields": fields, "body": body})
    return items


def _coverage_required(item: dict[str, Any]) -> bool:
    fields = item["fields"]
    return (
        _as_bool(fields.get("coverage_required"), default=False)
        or bool(_field_list(str(fields.get("source_event_ids", ""))))
        or bool(_field_list(str(fields.get("retained_claim_ids", ""))))
    )


def _summary_covers(
    summary: dict[str, Any],
    *,
    required_event_ids: set[str],
    required_claim_ids: set[str],
) -> bool:
    summary_event_ids = set(string_list(summary.get("source_event_ids")))
    summary_claim_ids = set(string_list(summary.get("retained_claim_ids")))
    return required_event_ids.issubset(summary_event_ids) and required_claim_ids.issubset(summary_claim_ids)


def _summary_has_coverage_fields(summary: dict[str, Any]) -> bool:
    return all(
        string_list(summary.get(field))
        for field in ("loss_notes", "discarded_signals", "blocked_from_discard")
    )


def _render_state(
    *,
    checked_at: str,
    mode: str,
    archive_next_action: str,
    archive_commit_permission: str,
    coverage_status: str,
    ready_items: int,
    coverage_required_items: int,
    covered_items: list[str],
    failure_count: int,
    failures: list[str],
) -> str:
    covered_block = "\n".join(f"- {item_id}" for item_id in covered_items) or "- none"
    failure_block = "\n".join(f"- {failure}" for failure in failures[:80]) or "- none"
    return f"""---
title: Summary Coverage State
memory_type: summary_coverage_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-28T01:45:00+08:00
updated_at: {checked_at}
last_confirmed_at: {checked_at}
importance_score: 86
impact_score: 88
confidence_score: 100
status: active
tags: [memory, event_sourcing, summary, archive, gate]
---

# Summary Coverage State

## Last Evaluation
- checked_at: {checked_at}
- mode: {mode}
- archive_next_action: {archive_next_action}
- archive_commit_permission: {archive_commit_permission}
- coverage_status: {coverage_status}

## Counts
- ready_archive_items: {ready_items}
- coverage_required_items: {coverage_required_items}
- covered_items: {len(covered_items)}
- failure_count: {failure_count}

## Covered Items
{covered_block}

## Failures
{failure_block}

## Rules
- Event-sourced archive items must cite source events and retained claims before compression.
- Summaries must include loss notes, discarded signals, and blocked-from-discard signals.
- Legacy archive items without coverage fields remain allowed until migrated.
"""


def run_summary_coverage_gate(
    root: Path,
    checked_at: str | None = None,
    mode: str = "runtime_summary_coverage_gate",
    *,
    write_state: bool = True,
) -> dict[str, Any]:
    checked_at = checked_at or datetime.now().astimezone().isoformat()
    archive_output = read_text(root / "memory/archive/archive_output_state.md")
    archive_queue = read_text(root / "memory/archive/archive_queue.md")
    archive_next_action = extract_value(archive_output, "next_action", "keep_holding")

    items = extract_archive_items(archive_queue)
    active_items = [item for item in items if str(item["fields"]["status"]) not in TERMINAL_STATUSES]
    ready_items = [item for item in active_items if str(item["fields"]["status"]) != "hold"]
    required_items = [item for item in ready_items if _coverage_required(item)]
    failures: list[str] = []
    covered_items: list[str] = []

    if archive_next_action != "summarize_then_compress" or not ready_items:
        archive_commit_permission = "not_required"
        coverage_status = "not_required"
    elif not required_items:
        archive_commit_permission = "allowed_legacy"
        coverage_status = "legacy_archive_without_event_coverage"
    else:
        consistency = run_memory_consistency_gate(root, mode=f"{mode}_consistency", write_state=True)
        if not consistency["passed"]:
            failures.append("memory_consistency_gate_blocked")
            failures.extend(str(item) for item in consistency.get("failures", [])[:20])

        event_dir = root / "memory/events"
        raw_events = load_jsonl(event_dir / "raw_events.jsonl")
        claims = load_jsonl(event_dir / "atomic_claims.jsonl")
        summaries = load_jsonl(event_dir / "summary_views.jsonl")
        event_ids = {str(row.get("event_id", "")).strip() for row in raw_events}
        claim_ids = {str(row.get("claim_id", "")).strip() for row in claims}

        for item in required_items:
            item_id = str(item["item_id"])
            fields = item["fields"]
            required_event_ids = set(_field_list(str(fields.get("source_event_ids", ""))))
            required_claim_ids = set(_field_list(str(fields.get("retained_claim_ids", ""))))
            if not required_event_ids:
                failures.append(f"{item_id}: missing source_event_ids")
            if not required_claim_ids:
                failures.append(f"{item_id}: missing retained_claim_ids")
            missing_events = sorted(required_event_ids - event_ids)
            missing_claims = sorted(required_claim_ids - claim_ids)
            if missing_events:
                failures.append(f"{item_id}: missing raw events: {', '.join(missing_events)}")
            if missing_claims:
                failures.append(f"{item_id}: missing claims: {', '.join(missing_claims)}")
            matching = [
                summary
                for summary in summaries
                if _summary_covers(
                    summary,
                    required_event_ids=required_event_ids,
                    required_claim_ids=required_claim_ids,
                )
            ]
            if not matching:
                failures.append(f"{item_id}: no summary covers required events and claims")
                continue
            if not any(_summary_has_coverage_fields(summary) for summary in matching):
                failures.append(f"{item_id}: covering summary lacks loss/discard/blocked coverage fields")
                continue
            if not missing_events and not missing_claims:
                covered_items.append(item_id)

        if failures:
            archive_commit_permission = "blocked"
            coverage_status = "blocked"
        else:
            archive_commit_permission = "allowed"
            coverage_status = "covered"

    if write_state:
        write_text(
            root / "memory/events/summary_coverage_state.md",
            _render_state(
                checked_at=checked_at,
                mode=mode,
                archive_next_action=archive_next_action,
                archive_commit_permission=archive_commit_permission,
                coverage_status=coverage_status,
                ready_items=len(ready_items),
                coverage_required_items=len(required_items),
                covered_items=covered_items,
                failure_count=len(failures),
                failures=failures,
            ),
        )

    return {
        "checked_at": checked_at,
        "archive_next_action": archive_next_action,
        "archive_commit_permission": archive_commit_permission,
        "coverage_status": coverage_status,
        "ready_items": len(ready_items),
        "coverage_required_items": len(required_items),
        "covered_items": covered_items,
        "failure_count": len(failures),
        "failures": failures,
    }

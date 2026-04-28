"""Consistency gate for source-traceable memory event sidecars."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from memory_event_schema import (
    CLAIM_REQUIRED,
    CLAIM_STATUSES,
    CLAIM_TYPES,
    RAW_EVENT_REQUIRED,
    STRUCTURED_EVENT_REQUIRED,
    SUMMARY_REQUIRED,
    is_dream_event,
    is_group_or_non_owner,
    is_owner_relationship_layer,
    load_jsonl,
    missing_fields,
    sha256_text,
    string_list,
)


def _event_dir(root: Path) -> Path:
    return root / "memory/events"


def _read_sidecars(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    event_dir = _event_dir(root)
    return (
        load_jsonl(event_dir / "raw_events.jsonl"),
        load_jsonl(event_dir / "structured_events.jsonl"),
        load_jsonl(event_dir / "atomic_claims.jsonl"),
        load_jsonl(event_dir / "summary_views.jsonl"),
    )


def _render_state(
    *,
    checked_at: str,
    mode: str,
    passed: bool,
    raw_event_count: int,
    structured_event_count: int,
    claim_count: int,
    summary_count: int,
    failure_count: int,
    failures: list[str],
) -> str:
    failure_lines = "\n".join(f"- {failure}" for failure in failures[:80]) or "- none"
    return f"""---
title: Memory Consistency Gate State
memory_type: memory_consistency_gate_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: system
created_at: 2026-04-28T01:20:00+08:00
updated_at: {checked_at}
last_confirmed_at: {checked_at}
importance_score: 86
impact_score: 90
confidence_score: 100
status: active
tags: [memory, event_sourcing, consistency, gate]
---

# Memory Consistency Gate State

## Last Evaluation
- checked_at: {checked_at}
- mode: {mode}
- gate_status: {"passed" if passed else "blocked"}

## Counts
- raw_events: {raw_event_count}
- structured_events: {structured_event_count}
- atomic_claims: {claim_count}
- summary_views: {summary_count}
- failure_count: {failure_count}

## Failures
{failure_lines}

## Rules
- Raw events are source material, not summaries.
- Claims must cite existing raw events.
- Summaries must cite retained claims and source events.
- Dream, group, non-owner, and source-candidate material must keep their boundaries.
"""


def _validate_raw_events(raw_events: list[dict[str, Any]], failures: list[str]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for row in raw_events:
        event_id = str(row.get("event_id", "")).strip()
        missing = missing_fields(row, RAW_EVENT_REQUIRED)
        if missing:
            failures.append(f"raw_event:{event_id or 'missing_id'} missing fields: {', '.join(missing)}")
            continue
        if event_id in index:
            failures.append(f"raw_event:{event_id} duplicate event_id")
        index[event_id] = row
        raw_text = str(row.get("raw_text", ""))
        expected_hash = sha256_text(raw_text)
        if str(row.get("raw_hash", "")).strip() != expected_hash:
            failures.append(f"raw_event:{event_id} raw_hash mismatch")
    return index


def _validate_structured_events(
    structured_events: list[dict[str, Any]],
    raw_index: dict[str, dict[str, Any]],
    failures: list[str],
) -> None:
    seen: set[str] = set()
    for row in structured_events:
        structured_id = str(row.get("structured_id", "")).strip()
        missing = missing_fields(row, STRUCTURED_EVENT_REQUIRED)
        if missing:
            failures.append(f"structured_event:{structured_id or 'missing_id'} missing fields: {', '.join(missing)}")
            continue
        if structured_id in seen:
            failures.append(f"structured_event:{structured_id} duplicate structured_id")
        seen.add(structured_id)
        event_id = str(row.get("event_id", "")).strip()
        if event_id not in raw_index:
            failures.append(f"structured_event:{structured_id} references missing event_id:{event_id}")
        if not isinstance(row.get("allowed_memory_layers"), list):
            failures.append(f"structured_event:{structured_id} allowed_memory_layers must be a list")
        if not isinstance(row.get("blocked_memory_layers"), list):
            failures.append(f"structured_event:{structured_id} blocked_memory_layers must be a list")


def _validate_span(
    *,
    claim_id: str,
    span: Any,
    raw_index: dict[str, dict[str, Any]],
    failures: list[str],
) -> None:
    if not isinstance(span, dict):
        failures.append(f"claim:{claim_id} evidence_span must be an object")
        return
    event_id = str(span.get("event_id", "")).strip()
    if event_id not in raw_index:
        failures.append(f"claim:{claim_id} evidence_span references missing event_id:{event_id}")
        return
    cited_text = str(span.get("text", ""))
    raw_text = str(raw_index[event_id].get("raw_text", ""))
    if cited_text and cited_text not in raw_text:
        failures.append(f"claim:{claim_id} evidence text not found in raw_event:{event_id}")
    if "start" in span and "end" in span and cited_text:
        try:
            start = int(span["start"])
            end = int(span["end"])
        except (TypeError, ValueError):
            failures.append(f"claim:{claim_id} evidence offsets must be integers")
            return
        if start < 0 or end < start or end > len(raw_text):
            failures.append(f"claim:{claim_id} evidence offsets out of range for raw_event:{event_id}")
        elif raw_text[start:end] != cited_text:
            failures.append(f"claim:{claim_id} evidence offsets do not match cited text")


def _validate_claims(
    claims: list[dict[str, Any]],
    raw_index: dict[str, dict[str, Any]],
    failures: list[str],
) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for row in claims:
        claim_id = str(row.get("claim_id", "")).strip()
        missing = missing_fields(row, CLAIM_REQUIRED)
        if missing:
            failures.append(f"claim:{claim_id or 'missing_id'} missing fields: {', '.join(missing)}")
            continue
        if claim_id in index:
            failures.append(f"claim:{claim_id} duplicate claim_id")
        index[claim_id] = row

        claim_type = str(row.get("claim_type", "")).strip()
        status = str(row.get("status", "")).strip()
        target_layer = str(row.get("target_memory_layer", "")).strip()
        evidence_event_ids = string_list(row.get("evidence_event_ids"))
        evidence_spans = row.get("evidence_spans")

        if claim_type not in CLAIM_TYPES:
            failures.append(f"claim:{claim_id} unsupported claim_type:{claim_type}")
        if status not in CLAIM_STATUSES:
            failures.append(f"claim:{claim_id} unsupported status:{status}")
        if status == "stable" and not evidence_event_ids:
            failures.append(f"claim:{claim_id} stable claim has no evidence_event_ids")

        evidence_events: list[dict[str, Any]] = []
        for event_id in evidence_event_ids:
            event = raw_index.get(event_id)
            if event is None:
                failures.append(f"claim:{claim_id} references missing event_id:{event_id}")
            else:
                evidence_events.append(event)

        if claim_type == "fact" and any(is_dream_event(event) for event in evidence_events):
            failures.append(f"claim:{claim_id} dream evidence cannot create factual memory")
        if any(is_group_or_non_owner(event) for event in evidence_events) and is_owner_relationship_layer(target_layer):
            failures.append(f"claim:{claim_id} group/non-owner evidence cannot target owner relationship memory")
        if claim_type == "source_candidate" and status == "stable":
            failures.append(f"claim:{claim_id} source_candidate cannot be stable without learning gates")
        if claim_type == "dream_residue" and status == "stable":
            failures.append(f"claim:{claim_id} dream_residue cannot be stable fact memory")

        if not isinstance(evidence_spans, list):
            failures.append(f"claim:{claim_id} evidence_spans must be a list")
        else:
            for span in evidence_spans:
                _validate_span(claim_id=claim_id, span=span, raw_index=raw_index, failures=failures)
    return index


def _validate_summaries(
    summaries: list[dict[str, Any]],
    raw_index: dict[str, dict[str, Any]],
    claim_index: dict[str, dict[str, Any]],
    failures: list[str],
) -> None:
    seen: set[str] = set()
    for row in summaries:
        summary_id = str(row.get("summary_id", "")).strip()
        missing = missing_fields(row, SUMMARY_REQUIRED)
        if missing:
            failures.append(f"summary:{summary_id or 'missing_id'} missing fields: {', '.join(missing)}")
            continue
        if summary_id in seen:
            failures.append(f"summary:{summary_id} duplicate summary_id")
        seen.add(summary_id)

        retained_claim_ids = string_list(row.get("retained_claim_ids"))
        source_event_ids = set(string_list(row.get("source_event_ids")))
        loss_notes = string_list(row.get("loss_notes"))
        discarded_signals = string_list(row.get("discarded_signals"))
        blocked_from_discard = string_list(row.get("blocked_from_discard"))

        if not retained_claim_ids:
            failures.append(f"summary:{summary_id} has no retained_claim_ids")
        if not source_event_ids:
            failures.append(f"summary:{summary_id} has no source_event_ids")
        if not loss_notes:
            failures.append(f"summary:{summary_id} has no loss_notes")
        if not discarded_signals:
            failures.append(f"summary:{summary_id} has no discarded_signals")
        if not blocked_from_discard:
            failures.append(f"summary:{summary_id} has no blocked_from_discard")

        for event_id in source_event_ids:
            if event_id not in raw_index:
                failures.append(f"summary:{summary_id} references missing source_event_id:{event_id}")
        for claim_id in retained_claim_ids:
            claim = claim_index.get(claim_id)
            if claim is None:
                failures.append(f"summary:{summary_id} references missing claim_id:{claim_id}")
                continue
            claim_events = set(string_list(claim.get("evidence_event_ids")))
            missing_events = sorted(claim_events - source_event_ids)
            if missing_events:
                failures.append(
                    f"summary:{summary_id} omits evidence events for claim:{claim_id}: {', '.join(missing_events)}"
                )


def run_memory_consistency_gate(
    root: Path,
    checked_at: str | None = None,
    mode: str = "runtime_memory_consistency_gate",
    *,
    write_state: bool = True,
) -> dict[str, Any]:
    checked_at = checked_at or datetime.now().astimezone().isoformat()
    raw_events, structured_events, claims, summaries = _read_sidecars(root)
    failures: list[str] = []

    raw_index = _validate_raw_events(raw_events, failures)
    _validate_structured_events(structured_events, raw_index, failures)
    claim_index = _validate_claims(claims, raw_index, failures)
    _validate_summaries(summaries, raw_index, claim_index, failures)

    passed = not failures
    if write_state:
        event_dir = _event_dir(root)
        event_dir.mkdir(parents=True, exist_ok=True)
        (event_dir / "consistency_gate_state.md").write_text(
            _render_state(
                checked_at=checked_at,
                mode=mode,
                passed=passed,
                raw_event_count=len(raw_events),
                structured_event_count=len(structured_events),
                claim_count=len(claims),
                summary_count=len(summaries),
                failure_count=len(failures),
                failures=failures,
            ),
            encoding="utf-8",
        )

    return {
        "checked_at": checked_at,
        "gate_status": "passed" if passed else "blocked",
        "passed": passed,
        "raw_events": len(raw_events),
        "structured_events": len(structured_events),
        "atomic_claims": len(claims),
        "summary_views": len(summaries),
        "failure_count": len(failures),
        "failures": failures,
    }

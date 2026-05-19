from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any


STATE_REL = Path("memory/context/contextual_self_observatory_state.md")
SUMMARY_REL = Path("runtime/contextual_self_observatory.json")
SELF_LOOP_TRACE_REL = Path("runtime/contextual_self_loop_trace.jsonl")
RECALL_TRACE_REL = Path("runtime/contextual_recall_trace.jsonl")
INITIATIVE_EVENTS_REL = Path("runtime/initiative_lifecycle_events.jsonl")
INITIATIVE_METRICS_REL = Path("runtime/initiative_metrics.json")
WINDOW_HOURS = 24
CANONICAL_RECALL_OWNER = "xinyu_living_memory_recall.run_living_memory_recall_algorithm"
CONTEXTUAL_SELF_OBSERVATORY_ROLE = "observability/no_behavior_change"
CONTEXTUAL_SELF_OBSERVATORY_BOUNDARY = "reads_runtime_traces_does_not_choose_recall"


def run_contextual_self_observatory(
    root: Path,
    *,
    observed_at: str | None = None,
    window_hours: int = WINDOW_HOURS,
) -> dict[str, Any]:
    root = root.resolve()
    observed_at = observed_at or datetime.now().astimezone().isoformat(timespec="seconds")
    summary = build_contextual_self_observatory_summary(
        root,
        observed_at=observed_at,
        window_hours=window_hours,
    )
    _write_json_atomic(root / SUMMARY_REL, summary)
    _write_state(root, summary)
    return summary


def build_contextual_self_observatory_summary(
    root: Path,
    *,
    observed_at: str,
    window_hours: int = WINDOW_HOURS,
) -> dict[str, Any]:
    self_events = _events_in_window(_read_jsonl(root / SELF_LOOP_TRACE_REL), observed_at=observed_at, hours=window_hours)
    recall_events = _events_in_window(_read_jsonl(root / RECALL_TRACE_REL), observed_at=observed_at, hours=window_hours)
    initiative_events = _events_in_window(_read_jsonl(root / INITIATIVE_EVENTS_REL), observed_at=observed_at, hours=window_hours)
    decision_events = [event for event in initiative_events if event.get("stage") == "decision"]
    feedback_events = [event for event in initiative_events if event.get("stage") == "feedback"]
    context_held = [
        event
        for event in decision_events
        if _has_context_gate_reason(event, "context_gate_") and _safe_str(event.get("status")) == "hold_private"
    ]
    context_allowed = [
        event
        for event in decision_events
        if "context_gate_passed" in {_safe_str(note) for note in event.get("gate", {}).get("notes", [])}
        or "context_gate_passed" in {_safe_str(note) for note in event.get("notes", [])}
    ]
    latest_self = self_events[-1] if self_events else {}
    latest_recall = recall_events[-1] if recall_events else {}
    initiative_metrics = _read_json(root / INITIATIVE_METRICS_REL)
    summary = {
        "updated_at": observed_at,
        "window_hours": window_hours,
        "self_loop_event_count_24h": len(self_events),
        "recall_event_count_24h": len(recall_events),
        "initiative_decision_count_24h": len(decision_events),
        "initiative_feedback_count_24h": len(feedback_events),
        "scene_counts_24h": _count_by(self_events, "current_scene"),
        "latest_scene": _safe_str(latest_self.get("current_scene"), "unknown"),
        "latest_working_self": _safe_str(latest_self.get("working_self"), "unknown"),
        "latest_initiative_posture": _safe_str(latest_self.get("initiative_posture"), "unknown"),
        "recall_admitted_count_24h": sum(_safe_int(event.get("admitted_recall_count")) for event in recall_events),
        "recall_suppressed_count_24h": sum(_safe_int(event.get("suppressed_recall_count")) for event in recall_events),
        "latest_recall_admitted_count": _safe_int(latest_recall.get("admitted_recall_count")),
        "latest_recall_source_count": _safe_int(latest_recall.get("source_count")),
        "initiative_held_by_context_count_24h": len(context_held),
        "initiative_allowed_by_context_count_24h": len(context_allowed),
        "quiet_default_hold_count_24h": sum(
            1 for event in context_held if _has_context_gate_reason(event, "context_gate_quiet_by_default")
        ),
        "feedback_after_context_allowed_count_24h": _feedback_after_allowed_count(context_allowed, feedback_events),
        "initiative_metrics": _compact_initiative_metrics(initiative_metrics),
        "posture": _observatory_posture(
            recall_events=recall_events,
            context_held_count=len(context_held),
            context_allowed_count=len(context_allowed),
        ),
        "notes": ["observatory_only", "no_behavior_change", "short_context_loop_visible"],
    }
    return _clean_json_value(summary)


def _write_state(root: Path, summary: dict[str, Any]) -> None:
    lines = [
        "---",
        "title: Contextual Self Observatory State",
        "memory_type: contextual_self_observatory_state",
        "time_scope: immediate_runtime",
        "subject_ids: [xinyu, owner]",
        "protected: true",
        "source: xinyu_contextual_self_observatory",
        f"updated_at: {_safe_str(summary.get('updated_at'))}",
        "status: active",
        "tags: [context, recall, initiative, observability]",
        "---",
        "",
        "# Contextual Self Observatory State",
        "",
        f"- updated_at: {_safe_str(summary.get('updated_at'))}",
        f"- window_hours: {_safe_str(summary.get('window_hours'))}",
        f"- self_loop_event_count_24h: {_safe_str(summary.get('self_loop_event_count_24h'))}",
        f"- recall_event_count_24h: {_safe_str(summary.get('recall_event_count_24h'))}",
        f"- initiative_decision_count_24h: {_safe_str(summary.get('initiative_decision_count_24h'))}",
        f"- initiative_feedback_count_24h: {_safe_str(summary.get('initiative_feedback_count_24h'))}",
        f"- latest_scene: {_safe_str(summary.get('latest_scene'))}",
        f"- latest_working_self: {_safe_str(summary.get('latest_working_self'))}",
        f"- latest_initiative_posture: {_safe_str(summary.get('latest_initiative_posture'))}",
        f"- recall_admitted_count_24h: {_safe_str(summary.get('recall_admitted_count_24h'))}",
        f"- recall_suppressed_count_24h: {_safe_str(summary.get('recall_suppressed_count_24h'))}",
        f"- latest_recall_admitted_count: {_safe_str(summary.get('latest_recall_admitted_count'))}",
        f"- initiative_held_by_context_count_24h: {_safe_str(summary.get('initiative_held_by_context_count_24h'))}",
        f"- initiative_allowed_by_context_count_24h: {_safe_str(summary.get('initiative_allowed_by_context_count_24h'))}",
        f"- quiet_default_hold_count_24h: {_safe_str(summary.get('quiet_default_hold_count_24h'))}",
        f"- feedback_after_context_allowed_count_24h: {_safe_str(summary.get('feedback_after_context_allowed_count_24h'))}",
        f"- posture: {_safe_str(summary.get('posture'))}",
        "",
        "## Boundaries",
        "- observatory_only: true",
        "- behavior_change: blocked",
        "- raw_history_dump: blocked",
        "",
        "## Scene Counts",
    ]
    scene_counts = summary.get("scene_counts_24h")
    if isinstance(scene_counts, dict) and scene_counts:
        lines.extend(f"- {key}: {value}" for key, value in scene_counts.items())
    else:
        lines.append("- none")
    _write_text_atomic(root / STATE_REL, "\n".join(lines).rstrip() + "\n")


def _observatory_posture(
    *,
    recall_events: list[dict[str, Any]],
    context_held_count: int,
    context_allowed_count: int,
) -> str:
    recall_admitted = sum(_safe_int(event.get("admitted_recall_count")) for event in recall_events)
    if context_held_count > context_allowed_count * 2 and context_held_count >= 3:
        return "watch_over_restraint"
    if context_allowed_count > context_held_count * 2 and context_allowed_count >= 3:
        return "watch_over_initiative"
    if recall_events and recall_admitted == 0:
        return "watch_recall_sparse"
    return "balanced_or_insufficient_data"


def _feedback_after_allowed_count(context_allowed: list[dict[str, Any]], feedback_events: list[dict[str, Any]]) -> int:
    allowed_ids = {_safe_str(event.get("candidate_id")) for event in context_allowed if _safe_str(event.get("candidate_id"))}
    return sum(1 for event in feedback_events if _safe_str(event.get("candidate_id")) in allowed_ids)


def _has_context_gate_reason(event: dict[str, Any], reason: str) -> bool:
    gate = event.get("gate") if isinstance(event.get("gate"), dict) else {}
    values: list[Any] = []
    for key in ("held_by", "negative_reasons", "notes"):
        value = gate.get(key)
        if isinstance(value, list):
            values.extend(value)
    value = event.get("notes")
    if isinstance(value, list):
        values.extend(value)
    return any(reason in _safe_str(item) for item in values)


def _compact_initiative_metrics(data: dict[str, Any]) -> dict[str, Any]:
    if not data:
        return {}
    wanted = (
        "updated_at",
        "desktop_shown_count_24h",
        "held_private_count_24h",
        "feedback_count_24h",
        "dismiss_count_24h",
        "reply_count_24h",
        "pending_feedback_count",
    )
    return {key: data[key] for key in wanted if key in data}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    except OSError:
        return []
    events: list[dict[str, Any]] = []
    for line in lines:
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            events.append(data)
    return events


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _events_in_window(events: list[dict[str, Any]], *, observed_at: str, hours: int) -> list[dict[str, Any]]:
    anchor = _parse_iso(observed_at)
    if anchor is None:
        return list(events)
    max_age = max(1, int(hours)) * 3600
    result: list[dict[str, Any]] = []
    for event in events:
        ts = _parse_iso(event.get("ts") or event.get("observed_at") or event.get("updated_at"))
        if ts is None:
            continue
        try:
            age = (anchor - ts).total_seconds()
        except TypeError:
            age = (anchor.replace(tzinfo=None) - ts.replace(tzinfo=None)).total_seconds()
        if 0 <= age <= max_age:
            result.append(event)
    return result


def _count_by(events: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        value = _safe_str(event.get(key), "unknown") or "unknown"
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _parse_iso(value: Any) -> datetime | None:
    text = _safe_str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    _write_text_atomic(path, json.dumps(_clean_json_value(data), ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def _write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        return str(value)
    except Exception:
        return default


def _clean_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _clean_json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean_json_value(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return _safe_str(value)

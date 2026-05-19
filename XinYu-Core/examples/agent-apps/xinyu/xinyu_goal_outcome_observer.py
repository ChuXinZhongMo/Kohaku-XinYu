from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

from state_service import append_jsonl, atomic_write_json, atomic_write_text
from xinyu_self_chosen_goal_ecology import (
    STATE_JSON_REL,
    STATE_MD_REL,
    TRACE_REL,
    record_self_chosen_goal_outcome,
)


OBSERVER_VERSION = 1
OBSERVER_STATE_REL = Path("runtime/self_chosen_goal_ecology/outcome_observer.json")
TECHNICAL_OK_NOTES = (
    "self_thought:",
    "daily_digest:",
    "creative_writing:",
    "review_inbox:",
    "memory_self_review:",
    "watched_source:",
    "github_learning:",
    "self_action:",
)
QUIET_MARKERS = ("quiet", "silence", "rest", "block proactive", "hold_proactive")


@dataclass(frozen=True, slots=True)
class OutcomeObservation:
    goal_id: str
    outcome: str
    reason_code: str
    signal_kind: str
    signal_strength: float
    signal_signature: str
    signal_refs: tuple[str, ...]


def run_goal_outcome_observer(
    root: Path,
    *,
    checked_at: str | None = None,
    trigger: str = "manual",
    maintenance_notes: Iterable[str] | None = None,
    write_state: bool = True,
) -> dict[str, Any]:
    root = Path(root)
    checked_at = _timestamp_or_now_iso(checked_at)
    notes = tuple(_safe_str(note) for note in (maintenance_notes or ()))
    ecology_state = _read_json(root / STATE_JSON_REL, default={})
    observer_state = _load_observer_state(root)
    selected_goal_id = _selected_goal_id(ecology_state)
    selected_at = _selected_at(ecology_state, selected_goal_id)
    signals = _collect_signals(root, maintenance_notes=notes)

    if not selected_goal_id:
        result = _skip_result("no_selected_goal", checked_at=checked_at, signals=signals)
        if write_state:
            _persist_skip(root, observer_state, checked_at=checked_at, result=result, signals=signals)
        return result

    observation = _infer_observation(
        selected_goal_id,
        selected_at=selected_at,
        signals=signals,
        checked_at=checked_at,
    )
    if observation is None:
        result = _skip_result("no_concrete_signal", checked_at=checked_at, goal_id=selected_goal_id, signals=signals)
        if write_state:
            _persist_skip(root, observer_state, checked_at=checked_at, result=result, signals=signals)
        return result

    previous_signature = _safe_str(observer_state.get("last_recorded_signature"))
    if previous_signature == observation.signal_signature:
        result = {
            "accepted": True,
            "status": "skipped_duplicate",
            "checked_at": checked_at,
            "goal_id": observation.goal_id,
            "outcome": observation.outcome,
            "reason_code": observation.reason_code,
            "signal_kind": observation.signal_kind,
            "notes": ["goal_outcome_duplicate_skipped"],
        }
        if write_state:
            _persist_skip(root, observer_state, checked_at=checked_at, result=result, signals=signals)
        return result

    if not write_state:
        return {
            "accepted": True,
            "status": "preview",
            "checked_at": checked_at,
            "goal_id": observation.goal_id,
            "outcome": observation.outcome,
            "reason_code": observation.reason_code,
            "signal_kind": observation.signal_kind,
            "signal_strength": observation.signal_strength,
            "notes": ["goal_outcome_observer_preview"],
        }

    outcome_result = record_self_chosen_goal_outcome(
        root,
        observation.goal_id,
        observation.outcome,
        observed_at=checked_at,
        note=f"auto:{observation.reason_code}:{observation.signal_signature}",
    )
    event = {
        "event_kind": "goal_ecology_outcome_observed",
        "version": OBSERVER_VERSION,
        "observed_at": _timestamp_or_now_iso(checked_at),
        "trigger": trigger,
        "goal_id": observation.goal_id,
        "outcome": observation.outcome,
        "reason_code": observation.reason_code,
        "signal_kind": observation.signal_kind,
        "signal_strength": observation.signal_strength,
        "signal_signature": observation.signal_signature,
        "signal_refs": list(observation.signal_refs),
        "habit_weight_before": outcome_result.get("habit_weight_before"),
        "habit_weight_after": outcome_result.get("habit_weight_after"),
    }
    append_jsonl(root / TRACE_REL, event)

    updated_observer = _update_observer_state(
        root,
        observer_state,
        checked_at=checked_at,
        observation=observation,
        outcome_result=outcome_result,
        signals=signals,
    )
    atomic_write_json(root / OBSERVER_STATE_REL, updated_observer)
    _write_goal_ecology_report(root, updated_observer.get("report", {}))
    return {
        "accepted": True,
        "status": "recorded",
        "checked_at": checked_at,
        "goal_id": observation.goal_id,
        "outcome": observation.outcome,
        "reason_code": observation.reason_code,
        "signal_kind": observation.signal_kind,
        "signal_strength": observation.signal_strength,
        "habit_weight_before": outcome_result.get("habit_weight_before"),
        "habit_weight_after": outcome_result.get("habit_weight_after"),
        "notes": ["goal_outcome_observed", f"reason:{observation.reason_code}"],
    }


def _selected_goal_id(ecology_state: Any) -> str:
    if not isinstance(ecology_state, dict):
        return ""
    return _safe_token(ecology_state.get("last_selected_goal_id"))


def _selected_at(ecology_state: Any, goal_id: str) -> str:
    if not isinstance(ecology_state, dict) or not goal_id:
        return ""
    goals = ecology_state.get("goals")
    if not isinstance(goals, dict):
        return ""
    goal_state = goals.get(goal_id)
    if not isinstance(goal_state, dict):
        return ""
    return _safe_str(goal_state.get("last_selected_at"))


def _infer_observation(
    goal_id: str,
    *,
    selected_at: str,
    signals: dict[str, Any],
    checked_at: str,
) -> OutcomeObservation | None:
    if _safe_int(signals.get("maintenance_error_count"), 0) > 0:
        return _observation(
            goal_id,
            "blocked",
            "maintenance_sidecar_error",
            "maintenance_notes",
            0.86,
            selected_at=selected_at,
            signals=signals,
            refs=("maintenance_notes:hash",),
        )

    if goal_id == "continue_bounded_work":
        if signals.get("codex_failed"):
            return _observation(
                goal_id,
                "failed",
                "codex_failure_signal",
                "codex_presence",
                0.92,
                selected_at=selected_at,
                signals=signals,
                refs=("runtime/codex_presence_state.json:summary",),
            )
        if signals.get("codex_success") or signals.get("clean_maintenance_pass"):
            return _observation(
                goal_id,
                "useful",
                "local_maintenance_completed",
                "maintenance_notes",
                0.72,
                selected_at=selected_at,
                signals=signals,
                refs=("maintenance_notes:hash",),
            )

    if goal_id == "curate_failure_replay":
        if _safe_int(signals.get("replay_selected_count"), 0) > 0 or signals.get("replay_baseline_present"):
            return _observation(
                goal_id,
                "useful",
                "replay_material_present",
                "replay_summary",
                0.68,
                selected_at=selected_at,
                signals=signals,
                refs=("runtime/replay_candidates/chat_replay_export_summary.json:counts",),
            )

    if goal_id == "absorb_feedback_repair":
        if signals.get("learning_repair_signal"):
            return _observation(
                goal_id,
                "useful",
                "learning_repair_signal",
                "learning_closed_loop",
                0.74,
                selected_at=selected_at,
                signals=signals,
                refs=("memory/self/learning_closed_loop_state.md:fields",),
            )

    if goal_id == "review_memory_pressure":
        if _safe_int(signals.get("memory_self_review_trace_rows"), 0) > 0:
            return _observation(
                goal_id,
                "useful",
                "memory_review_trace_present",
                "memory_self_review_trace",
                0.66,
                selected_at=selected_at,
                signals=signals,
                refs=("runtime/memory_self_review_trace.jsonl:count",),
            )

    if goal_id == "quiet_presence":
        if signals.get("quiet_pressure") and signals.get("proactive_status") in {"ready", "sent", "claimed"}:
            return _observation(
                goal_id,
                "blocked",
                "quiet_boundary_conflicted_with_proactive_state",
                "quiet_boundary",
                0.76,
                selected_at=selected_at,
                signals=signals,
                refs=("memory/context/current_life_posture.md:fields",),
            )
        if signals.get("quiet_pressure"):
            return _observation(
                goal_id,
                "useful",
                "quiet_boundary_held",
                "quiet_boundary",
                0.62,
                selected_at=selected_at,
                signals=signals,
                refs=("memory/context/current_life_posture.md:fields",),
            )

    if goal_id == "observe_environment":
        if _safe_int(signals.get("self_presence_trace_rows"), 0) > 0 or _safe_int(signals.get("qq_inbound_trace_rows"), 0) > 0:
            return _observation(
                goal_id,
                "useful",
                "environment_trace_present",
                "runtime_trace",
                0.58,
                selected_at=selected_at,
                signals=signals,
                refs=("runtime/self_presence_trace.jsonl:count", "runtime/qq_inbound_trace.jsonl:count"),
            )

    del checked_at
    return None


def _observation(
    goal_id: str,
    outcome: str,
    reason_code: str,
    signal_kind: str,
    signal_strength: float,
    *,
    selected_at: str,
    signals: dict[str, Any],
    refs: tuple[str, ...],
) -> OutcomeObservation:
    stable_payload = {
        "goal_id": goal_id,
        "outcome": outcome,
        "reason_code": reason_code,
        "selected_at": selected_at,
        "signals": _stable_signal_subset(signals),
    }
    return OutcomeObservation(
        goal_id=goal_id,
        outcome=outcome,
        reason_code=reason_code,
        signal_kind=signal_kind,
        signal_strength=round(signal_strength, 3),
        signal_signature=_hash_json(stable_payload, length=20),
        signal_refs=refs,
    )


def _collect_signals(root: Path, *, maintenance_notes: tuple[str, ...]) -> dict[str, Any]:
    note_text = "\n".join(maintenance_notes)
    note_hash = _hash_text(note_text, length=16) if note_text else ""
    note_errors = [note for note in maintenance_notes if _note_is_error(note)]
    codex_state = _read_json(root / "runtime/codex_presence_state.json", default={})
    codex_status = _safe_str(codex_state.get("status")).lower() if isinstance(codex_state, dict) else ""
    codex_exit = _safe_str(codex_state.get("exit_code")) if isinstance(codex_state, dict) else ""
    replay = _read_json(root / "runtime/replay_candidates/chat_replay_export_summary.json", default={})
    replay_selected = _safe_int(replay.get("selected_count"), 0) if isinstance(replay, dict) else 0
    learning = _markdown_fields(_read_text(root / "memory/self/learning_closed_loop_state.md"))
    posture_text = _read_text(root / "memory/context/current_life_posture.md")
    proactive = _markdown_fields(_read_text(root / "memory/context/proactive_request_state.md"))
    memory_review = _jsonl_summary(root / "runtime/memory_self_review_trace.jsonl")
    contextual_recall = _jsonl_summary(root / "runtime/contextual_recall_trace.jsonl")
    self_presence = _jsonl_summary(root / "runtime/self_presence_trace.jsonl")
    qq_inbound = _jsonl_summary(root / "runtime/qq_inbound_trace.jsonl")
    return {
        "maintenance_note_count": len(maintenance_notes),
        "maintenance_notes_hash": note_hash,
        "maintenance_error_count": len(note_errors),
        "maintenance_error_hash": _hash_text("\n".join(note_errors), length=16) if note_errors else "",
        "clean_maintenance_pass": len(maintenance_notes) >= 3
        and not note_errors
        and any(note.startswith(TECHNICAL_OK_NOTES) for note in maintenance_notes),
        "codex_status": codex_status,
        "codex_exit_code": codex_exit,
        "codex_success": codex_status in {"done", "completed", "success", "succeeded"} and codex_exit in {"", "0", "None"},
        "codex_failed": codex_status in {"failed", "error", "timed_out", "timeout"} or codex_exit not in {"", "0", "None"},
        "replay_selected_count": replay_selected,
        "replay_baseline_present": (root / "runtime/regression/last_live_chat_baseline.json").exists(),
        "learning_status": _safe_str(learning.get("status")),
        "learning_latest_failure_kind": _safe_str(learning.get("latest_failure_kind")),
        "learning_repair_count": _safe_int(learning.get("repair_count"), 0),
        "learning_repair_signal": _safe_int(learning.get("repair_count"), 0) > 0
        or _contains_any(" ".join(learning.values()), ("trial_active", "repair", "next_action")),
        "quiet_pressure": _contains_any(posture_text, QUIET_MARKERS),
        "proactive_status": _safe_str(proactive.get("status")).lower(),
        "memory_self_review_trace_rows": memory_review["row_count"],
        "memory_self_review_last_event": memory_review["last_event_kind"],
        "contextual_recall_trace_rows": contextual_recall["row_count"],
        "self_presence_trace_rows": self_presence["row_count"],
        "qq_inbound_trace_rows": qq_inbound["row_count"],
    }


def _note_is_error(note: str) -> bool:
    lowered = _safe_str(note).lower()
    return (
        "_error:" in lowered
        or lowered.endswith("/failed")
        or lowered.endswith("/failure")
        or ":failed/" in lowered
        or "/failed" in lowered
        or "/failure" in lowered
        or "/error" in lowered
    )


def _stable_signal_subset(signals: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "maintenance_notes_hash",
        "maintenance_error_count",
        "maintenance_error_hash",
        "clean_maintenance_pass",
        "codex_status",
        "codex_exit_code",
        "replay_selected_count",
        "replay_baseline_present",
        "learning_status",
        "learning_latest_failure_kind",
        "learning_repair_count",
        "quiet_pressure",
        "proactive_status",
        "memory_self_review_trace_rows",
        "contextual_recall_trace_rows",
        "self_presence_trace_rows",
        "qq_inbound_trace_rows",
    )
    return {key: signals.get(key) for key in keys}


def _update_observer_state(
    root: Path,
    state: dict[str, Any],
    *,
    checked_at: str,
    observation: OutcomeObservation,
    outcome_result: dict[str, Any],
    signals: dict[str, Any],
) -> dict[str, Any]:
    history = state.get("history") if isinstance(state.get("history"), list) else []
    record = {
        "observed_at": checked_at,
        "goal_id": observation.goal_id,
        "outcome": observation.outcome,
        "reason_code": observation.reason_code,
        "signal_kind": observation.signal_kind,
        "signal_strength": observation.signal_strength,
        "signal_signature": observation.signal_signature,
        "signal_refs": list(observation.signal_refs),
        "habit_weight_before": outcome_result.get("habit_weight_before"),
        "habit_weight_after": outcome_result.get("habit_weight_after"),
    }
    updated = {
        "version": OBSERVER_VERSION,
        "updated_at": checked_at,
        "last_checked_at": checked_at,
        "last_recorded_signature": observation.signal_signature,
        "last_observation": record,
        "history": [*history, record][-50:],
        "last_signal_snapshot": _stable_signal_subset(signals),
    }
    updated["report"] = _build_report(root, updated, checked_at=checked_at)
    return updated


def _persist_skip(
    root: Path,
    state: dict[str, Any],
    *,
    checked_at: str,
    result: dict[str, Any],
    signals: dict[str, Any],
) -> None:
    updated = dict(state)
    updated["version"] = OBSERVER_VERSION
    updated["updated_at"] = checked_at
    updated["last_checked_at"] = checked_at
    updated["last_skip"] = {
        "checked_at": checked_at,
        "status": result.get("status"),
        "reason": result.get("reason"),
        "goal_id": result.get("goal_id", ""),
    }
    updated["last_signal_snapshot"] = _stable_signal_subset(signals)
    updated["report"] = _build_report(root, updated, checked_at=checked_at)
    atomic_write_json(root / OBSERVER_STATE_REL, updated)
    _write_goal_ecology_report(root, updated.get("report", {}))


def _skip_result(reason: str, *, checked_at: str, signals: dict[str, Any], goal_id: str = "") -> dict[str, Any]:
    return {
        "accepted": True,
        "status": "skipped",
        "reason": reason,
        "checked_at": checked_at,
        "goal_id": goal_id,
        "signal_snapshot_hash": _hash_json(_stable_signal_subset(signals), length=16),
        "notes": [f"goal_outcome_observer_skipped:{reason}"],
    }


def _build_report(root: Path, observer_state: dict[str, Any], *, checked_at: str) -> dict[str, Any]:
    ecology_state = _read_json(root / STATE_JSON_REL, default={})
    goals = ecology_state.get("goals") if isinstance(ecology_state, dict) and isinstance(ecology_state.get("goals"), dict) else {}
    trace_rows = _read_jsonl_rows(root / TRACE_REL, max_rows=2000)
    outcome_rows = [
        row
        for row in trace_rows
        if row.get("event_kind") in {"goal_ecology_outcome_recorded", "goal_ecology_outcome_observed"}
        and _within_hours(row.get("observed_at") or row.get("checked_at"), checked_at, hours=24)
    ]
    selection_rows = [
        row
        for row in trace_rows
        if row.get("event_kind") == "goal_ecology_selected"
        and _within_hours(row.get("checked_at") or row.get("observed_at"), checked_at, hours=24)
    ]
    return {
        "updated_at": _timestamp_or_now_iso(checked_at),
        "last_observation": observer_state.get("last_observation") if isinstance(observer_state.get("last_observation"), dict) else {},
        "observations_24h": len(outcome_rows),
        "outcome_counts_24h": _outcome_counts(outcome_rows),
        "goal_switch_count_24h": _goal_switch_count(selection_rows),
        "consecutive_goal_count": _consecutive_goal_count(trace_rows),
        "cooled_goal_ids": _cooled_goal_ids(goals, checked_at),
        "habit_weights": _habit_weights(goals),
        "observer_policy": "local_state_only; hashes_counts_and_state_fields_only",
    }


def _write_goal_ecology_report(root: Path, report: Any) -> None:
    if not isinstance(report, dict):
        return
    path = root / STATE_MD_REL
    text = _read_text(path)
    if not text:
        return
    base = text.split("\n## Outcome Ecology Report\n", 1)[0].rstrip()
    lines = _report_markdown_lines(report)
    atomic_write_text(path, base + "\n\n" + "\n".join(lines))


def _report_markdown_lines(report: dict[str, Any]) -> list[str]:
    last = report.get("last_observation") if isinstance(report.get("last_observation"), dict) else {}
    outcome_counts = report.get("outcome_counts_24h") if isinstance(report.get("outcome_counts_24h"), dict) else {}
    habit_weights = report.get("habit_weights") if isinstance(report.get("habit_weights"), dict) else {}
    cooled = report.get("cooled_goal_ids") if isinstance(report.get("cooled_goal_ids"), list) else []
    return [
        "## Outcome Ecology Report",
        f"- report_updated_at: {_safe_str(report.get('updated_at'), 'missing')}",
        f"- last_observed_goal_id: {_safe_str(last.get('goal_id'), 'none')}",
        f"- last_outcome: {_safe_str(last.get('outcome'), 'none')}",
        f"- last_reason_code: {_safe_str(last.get('reason_code'), 'none')}",
        f"- last_signal_kind: {_safe_str(last.get('signal_kind'), 'none')}",
        f"- observations_24h: {_safe_str(report.get('observations_24h'), '0')}",
        f"- outcome_counts_24h: {_format_counts(outcome_counts)}",
        f"- goal_switch_count_24h: {_safe_str(report.get('goal_switch_count_24h'), '0')}",
        f"- consecutive_goal_count: {_safe_str(report.get('consecutive_goal_count'), '0')}",
        f"- cooled_goal_ids: {', '.join(_safe_str(item) for item in cooled) if cooled else 'none'}",
        f"- habit_weights: {_format_counts(habit_weights)}",
        f"- observer_policy: {_safe_str(report.get('observer_policy'), 'local_state_only')}",
    ]


def _load_observer_state(root: Path) -> dict[str, Any]:
    data = _read_json(root / OBSERVER_STATE_REL, default={})
    if not isinstance(data, dict):
        data = {}
    data["version"] = OBSERVER_VERSION
    data.setdefault("history", [])
    return data


def _outcome_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        outcome = _safe_token(row.get("outcome")) or "unknown"
        counts[outcome] = counts.get(outcome, 0) + 1
    return dict(sorted(counts.items()))


def _goal_switch_count(selection_rows: list[dict[str, Any]]) -> int:
    previous = ""
    switches = 0
    for row in selection_rows:
        goal = _safe_token(row.get("selected_goal_id"))
        if previous and goal and goal != previous:
            switches += 1
        if goal:
            previous = goal
    return switches


def _consecutive_goal_count(trace_rows: list[dict[str, Any]]) -> int:
    selected = [_safe_token(row.get("selected_goal_id")) for row in trace_rows if row.get("event_kind") == "goal_ecology_selected"]
    selected = [goal for goal in selected if goal]
    if not selected:
        return 0
    tail = selected[-1]
    count = 0
    for goal in reversed(selected):
        if goal != tail:
            break
        count += 1
    return count


def _cooled_goal_ids(goals: dict[str, Any], checked_at: str) -> list[str]:
    now = _parse_time(checked_at)
    cooled: list[str] = []
    for goal_id, state in goals.items():
        if not isinstance(state, dict):
            continue
        cooldown_until = _safe_str(state.get("cooldown_until"))
        if cooldown_until and _parse_time(cooldown_until) > now:
            cooled.append(_safe_token(goal_id))
    return sorted(item for item in cooled if item)


def _habit_weights(goals: dict[str, Any]) -> dict[str, float]:
    weights: dict[str, float] = {}
    for goal_id, state in goals.items():
        if isinstance(state, dict):
            weights[_safe_token(goal_id)] = round(_safe_float(state.get("habit_weight")), 3)
    return dict(sorted(weights.items()))


def _format_counts(values: dict[str, Any]) -> str:
    if not values:
        return "none"
    return ", ".join(f"{_safe_token(key)}={_safe_str(value)}" for key, value in sorted(values.items()))


def _markdown_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"^\s*-?\s*([A-Za-z0-9_]+):\s*(.*?)\s*$", line)
        if match:
            fields[match.group(1)] = match.group(2).strip()
    return fields


def _jsonl_summary(path: Path) -> dict[str, Any]:
    row_count = 0
    last_event = ""
    try:
        with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row_count += 1
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict):
                    last_event = _safe_str(row.get("event_kind") or row.get("kind") or row.get("status"))
    except OSError:
        pass
    return {"row_count": row_count, "last_event_kind": last_event}


def _read_jsonl_rows(path: Path, *, max_rows: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict):
                    rows.append(row)
                    if len(rows) > max_rows:
                        rows.pop(0)
    except OSError:
        return []
    return rows


def _within_hours(value: Any, checked_at: str, *, hours: int) -> bool:
    observed = _parse_time(value)
    now = _parse_time(checked_at)
    if not observed:
        return False
    return timedelta(0) <= now - observed <= timedelta(hours=hours)


def _read_json(path: Path, *, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return default


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


def _contains_any(text: str, markers: Iterable[str]) -> bool:
    lowered = _safe_str(text).lower()
    return any(marker.lower() in lowered for marker in markers if marker)


def _hash_json(value: Any, *, length: int) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return _hash_text(text, length=length)


def _hash_text(value: Any, *, length: int = 16) -> str:
    return hashlib.sha256(_safe_str(value).encode("utf-8", errors="replace")).hexdigest()[:length]


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _safe_token(value: Any) -> str:
    text = _safe_str(value).strip().lower()
    text = re.sub(r"[^a-z0-9_-]+", "_", text)
    return text.strip("_")[:80]


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _timestamp_or_now_iso(value: Any) -> str:
    return _parse_time(value).astimezone().isoformat(timespec="seconds")


def _parse_time(value: Any) -> datetime:
    try:
        text = _safe_str(value)
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
    except Exception:
        return datetime.now().astimezone()
    if parsed.tzinfo is None:
        return parsed.astimezone()
    return parsed.astimezone()


def main() -> int:
    parser = argparse.ArgumentParser(description="Observe local outcomes for XinYu self-chosen goal ecology.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--checked-at", default=None)
    parser.add_argument("--trigger", default="manual")
    parser.add_argument("--note", action="append", default=[])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = run_goal_outcome_observer(
        args.root,
        checked_at=args.checked_at,
        trigger=args.trigger,
        maintenance_notes=args.note,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"status={result.get('status')}")
        print(f"goal_id={result.get('goal_id', '')}")
        print(f"outcome={result.get('outcome', '')}")
        print(f"reason={result.get('reason_code') or result.get('reason', '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

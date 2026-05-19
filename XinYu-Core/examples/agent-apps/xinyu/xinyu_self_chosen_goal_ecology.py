from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

from state_service import atomic_write_json, atomic_write_text
from xinyu_self_choice_store import public_affect_band_from_state


ECOLOGY_VERSION = 1
STATE_JSON_REL = Path("runtime/self_chosen_goal_ecology/state.json")
STATE_MD_REL = Path("memory/context/self_chosen_goal_ecology_state.md")
TRACE_REL = Path("runtime/self_chosen_goal_ecology/trace.jsonl")
OUTCOME_OBSERVER_STATE_REL = Path("runtime/self_chosen_goal_ecology/outcome_observer.json")

OUTCOME_DELTAS = {
    "success": 0.08,
    "useful": 0.06,
    "neutral": 0.0,
    "ignored": -0.03,
    "stale": -0.04,
    "blocked": -0.10,
    "failed": -0.08,
}
OUTCOME_COOLDOWN_HOURS = {
    "success": 2,
    "useful": 2,
    "neutral": 4,
    "ignored": 8,
    "stale": 12,
    "blocked": 24,
    "failed": 18,
}

TECHNICAL_MARKERS = (
    "codex",
    "runtime",
    "pytest",
    "test",
    "retrieval",
    "replay",
    "fixture",
    "bridge",
    "gateway",
    "memory",
)
REPAIR_MARKERS = (
    "trial_active",
    "failure",
    "repair",
    "template",
    "mechanic",
    "voice",
    "next_action",
)
QUIET_MARKERS = (
    "rest",
    "silence",
    "quiet",
    "low_energy",
    "hold_proactive",
    "block proactive",
)


@dataclass(frozen=True, slots=True)
class GoalCandidate:
    goal_id: str
    label: str
    motive: str
    base_score: float
    habit_weight: float
    final_score: float
    status: str
    evidence_refs: tuple[str, ...]
    next_safe_action: str
    boundary: str


@dataclass(frozen=True, slots=True)
class GoalEcologyDecision:
    checked_at: str
    trigger: str
    selected_goal_id: str
    selected_label: str
    selected_score: float
    candidate_count: int
    action_policy: str
    next_safe_action: str
    boundary: str
    candidates: tuple[GoalCandidate, ...]
    notes: tuple[str, ...]


def run_self_chosen_goal_ecology(
    root: Path,
    *,
    checked_at: str | None = None,
    trigger: str = "manual",
    write_state: bool = True,
) -> dict[str, Any]:
    decision = build_self_chosen_goal_decision(root, checked_at=checked_at, trigger=trigger)
    if write_state:
        _write_goal_ecology_state(root, decision)
        _append_trace(root, "goal_ecology_selected", _decision_trace_payload(decision))
    return {
        "accepted": True,
        "checked_at": decision.checked_at,
        "selected_goal_id": decision.selected_goal_id,
        "selected_label": decision.selected_label,
        "selected_score": decision.selected_score,
        "candidate_count": decision.candidate_count,
        "action_policy": decision.action_policy,
        "next_safe_action": decision.next_safe_action,
        "notes": list(decision.notes),
    }


def build_self_chosen_goal_decision(
    root: Path,
    *,
    checked_at: str | None = None,
    trigger: str = "manual",
) -> GoalEcologyDecision:
    root = Path(root)
    checked_at = checked_at or _now_iso()
    state = _load_state(root)
    candidates = _build_candidates(root, state=state, checked_at=checked_at)
    ranked = sorted(candidates, key=lambda item: (item.final_score, item.goal_id), reverse=True)
    selected = ranked[0] if ranked else _fallback_candidate()
    notes = ["self_chosen_goal_ecology_v1", "state_only_selection", "no_outward_action"]
    if selected.status == "cooldown":
        notes.append("selected_goal_in_cooldown_fallback")
    return GoalEcologyDecision(
        checked_at=checked_at,
        trigger=trigger,
        selected_goal_id=selected.goal_id,
        selected_label=selected.label,
        selected_score=selected.final_score,
        candidate_count=len(ranked),
        action_policy="state_only_no_outward_action",
        next_safe_action=selected.next_safe_action,
        boundary=selected.boundary,
        candidates=tuple(ranked),
        notes=tuple(notes),
    )


def record_self_chosen_goal_outcome(
    root: Path,
    goal_id: str,
    outcome: str,
    *,
    observed_at: str | None = None,
    note: str = "",
) -> dict[str, Any]:
    root = Path(root)
    observed_at = _timestamp_or_now_iso(observed_at or _now_iso())
    goal = _safe_token(goal_id)
    outcome_key = _safe_token(outcome) or "neutral"
    if outcome_key not in OUTCOME_DELTAS:
        outcome_key = "neutral"
    state = _load_state(root)
    goals = state.setdefault("goals", {})
    goal_state = _goal_state(goals, goal)
    before = float(goal_state.get("habit_weight") or 0.0)
    after = _clamp(before + OUTCOME_DELTAS[outcome_key], low=-0.25, high=0.35)
    goal_state["habit_weight"] = round(after, 3)
    goal_state["last_outcome"] = outcome_key
    goal_state["last_outcome_at"] = _timestamp_or_now_iso(observed_at)
    goal_state["last_note_hash"] = _hash_text(note) if note else ""
    if outcome_key in {"success", "useful"}:
        goal_state["success_count"] = int(goal_state.get("success_count") or 0) + 1
    if outcome_key in {"blocked", "failed"}:
        goal_state["blocked_count"] = int(goal_state.get("blocked_count") or 0) + 1
    cooldown_hours = OUTCOME_COOLDOWN_HOURS[outcome_key]
    goal_state["cooldown_until"] = _iso(_parse_time(observed_at) + timedelta(hours=cooldown_hours))
    state["updated_at"] = _timestamp_or_now_iso(observed_at)
    _persist_state(root, state)
    payload = {
        "goal_id": goal,
        "outcome": outcome_key,
        "habit_weight_before": before,
        "habit_weight_after": after,
        "cooldown_hours": cooldown_hours,
        "note_hash": goal_state["last_note_hash"],
    }
    _append_trace(root, "goal_ecology_outcome_recorded", {"observed_at": _timestamp_or_now_iso(observed_at), **payload})
    return {
        "accepted": True,
        "observed_at": _timestamp_or_now_iso(observed_at),
        **payload,
        "notes": ["goal_outcome_recorded"],
    }


def _build_candidates(root: Path, *, state: dict[str, Any], checked_at: str) -> list[GoalCandidate]:
    context = _read_context(root)
    goals = state.get("goals") if isinstance(state.get("goals"), dict) else {}
    return [
        _score_candidate(
            "continue_bounded_work",
            "continue bounded technical work",
            "A bounded project thread has active technical residue.",
            0.16 + (0.42 if context["technical_pressure"] else 0.0),
            ("memory/context/recent_context.md", "memory/context/initiative_spine_state.md"),
            "continue the next safe local implementation or verification step",
            "state_only; no file edits or tool calls are executed by this selector",
            goals=goals,
            checked_at=checked_at,
            context=context,
        ),
        _score_candidate(
            "curate_failure_replay",
            "curate failure replay",
            "Recent replay or regression material can become future protection.",
            0.18 + (0.36 if context["replay_pressure"] else 0.0),
            ("runtime/replay_candidates/chat_replay_export_summary.json", "runtime/regression/last_live_chat_baseline.json"),
            "prepare or review replay candidates through the safe auto-promote path",
            "state_only; formal fixture promotion still requires exporter validation",
            goals=goals,
            checked_at=checked_at,
            context=context,
        ),
        _score_candidate(
            "absorb_feedback_repair",
            "absorb feedback repair",
            "A repeated failure or trial habit should influence future replies.",
            0.17 + (0.38 if context["repair_pressure"] else 0.0),
            ("memory/self/learning_closed_loop_state.md", "runtime/answer_discipline_visible_send_shadow.jsonl"),
            "summarize the active repair habit and keep it below the current owner turn",
            "state_only; does not rewrite stable memory or personality",
            goals=goals,
            checked_at=checked_at,
            context=context,
        ),
        _score_candidate(
            "review_memory_pressure",
            "review memory pressure",
            "Candidate memories or temporal traces may need cleanup.",
            0.16 + (0.30 if context["memory_pressure"] else 0.0),
            ("runtime/memory_self_review_trace.jsonl", "runtime/contextual_recall_trace.jsonl"),
            "inspect pending memory pressure without promoting stable memory automatically",
            "state_only; stable memory gates remain authoritative",
            goals=goals,
            checked_at=checked_at,
            context=context,
        ),
        _score_candidate(
            "quiet_presence",
            "quiet presence",
            "The current posture or affect favors low-interference presence.",
            0.22 + (0.38 if context["quiet_pressure"] else 0.0),
            ("memory/context/current_life_posture.md", "runtime/life_kernel/self_choice_state.json"),
            "stay quiet or keep a minimal companion posture until the owner gives direction",
            "state_only; never initiates contact by itself",
            goals=goals,
            checked_at=checked_at,
            context=context,
        ),
        _score_candidate(
            "observe_environment",
            "observe environment",
            "Low-risk background traces can be observed without action.",
            0.15 + (0.18 if context["environment_pressure"] else 0.0),
            ("runtime/qq_inbound_trace.jsonl", "runtime/self_presence_trace.jsonl"),
            "observe local traces and do nothing outward",
            "state_only; observation cannot send messages or claim work",
            goals=goals,
            checked_at=checked_at,
            context=context,
        ),
    ]


def _score_candidate(
    goal_id: str,
    label: str,
    motive: str,
    base_score: float,
    evidence_paths: tuple[str, ...],
    next_safe_action: str,
    boundary: str,
    *,
    goals: dict[str, Any],
    checked_at: str,
    context: dict[str, Any],
) -> GoalCandidate:
    goal_state = _goal_state(goals, goal_id)
    habit_weight = _clamp(goal_state.get("habit_weight") or 0.0, low=-0.25, high=0.35)
    cooldown_until = _safe_str(goal_state.get("cooldown_until"))
    status = "active"
    cooldown_penalty = 0.0
    if cooldown_until and _parse_time(cooldown_until) > _parse_time(checked_at):
        status = "cooldown"
        cooldown_penalty = -1.0
    diversity_penalty = _recent_selection_penalty(goal_state.get("last_selected_at"), checked_at)
    success_bonus = min(0.08, int(goal_state.get("success_count") or 0) * 0.015)
    blocked_penalty = min(0.12, int(goal_state.get("blocked_count") or 0) * 0.025)
    final_score = round(
        base_score + habit_weight + success_bonus - blocked_penalty + diversity_penalty + cooldown_penalty,
        4,
    )
    if status != "cooldown":
        goal_state["last_seen_score"] = final_score
    goal_state["last_seen_at"] = checked_at
    evidence_refs = tuple(_evidence_ref(context["texts"].get(path, ""), path) for path in evidence_paths)
    return GoalCandidate(
        goal_id=goal_id,
        label=label,
        motive=motive,
        base_score=round(base_score, 4),
        habit_weight=round(habit_weight, 4),
        final_score=final_score,
        status=status,
        evidence_refs=tuple(ref for ref in evidence_refs if ref),
        next_safe_action=next_safe_action,
        boundary=boundary,
    )


def _fallback_candidate() -> GoalCandidate:
    return GoalCandidate(
        goal_id="quiet_presence",
        label="quiet presence",
        motive="Fallback when no useful goal candidates exist.",
        base_score=0.0,
        habit_weight=0.0,
        final_score=0.0,
        status="fallback",
        evidence_refs=(),
        next_safe_action="stay quiet and wait for owner direction",
        boundary="state_only; no outward action",
    )


def _read_context(root: Path) -> dict[str, Any]:
    paths = (
        "memory/context/recent_context.md",
        "memory/context/initiative_spine_state.md",
        "runtime/replay_candidates/chat_replay_export_summary.json",
        "runtime/regression/last_live_chat_baseline.json",
        "memory/self/learning_closed_loop_state.md",
        "runtime/answer_discipline_visible_send_shadow.jsonl",
        "runtime/memory_self_review_trace.jsonl",
        "runtime/contextual_recall_trace.jsonl",
        "memory/context/current_life_posture.md",
        "runtime/life_kernel/self_choice_state.json",
        "runtime/qq_inbound_trace.jsonl",
        "runtime/self_presence_trace.jsonl",
    )
    texts = {path: _read(root / path, limit=6000) for path in paths}
    all_technical = "\n".join([texts["memory/context/recent_context.md"], texts["memory/context/initiative_spine_state.md"]])
    learning = texts["memory/self/learning_closed_loop_state.md"]
    replay_summary = _json_obj(texts["runtime/replay_candidates/chat_replay_export_summary.json"])
    replay_selected = int(replay_summary.get("selected_count") or 0) if isinstance(replay_summary, dict) else 0
    self_choice = _json_obj(texts["runtime/life_kernel/self_choice_state.json"])
    affect = public_affect_band_from_state(self_choice) if isinstance(self_choice, dict) else {}
    posture = texts["memory/context/current_life_posture.md"]
    return {
        "texts": texts,
        "technical_pressure": _contains_any(all_technical, TECHNICAL_MARKERS),
        "replay_pressure": replay_selected > 0 or bool(texts["runtime/regression/last_live_chat_baseline.json"]),
        "repair_pressure": _contains_any(learning, REPAIR_MARKERS),
        "memory_pressure": bool(texts["runtime/memory_self_review_trace.jsonl"] or texts["runtime/contextual_recall_trace.jsonl"]),
        "quiet_pressure": _contains_any(posture, QUIET_MARKERS)
        or affect.get("fatigue") in {"tired", "spent"}
        or affect.get("closure") == "withdrawn",
        "environment_pressure": bool(texts["runtime/qq_inbound_trace.jsonl"] or texts["runtime/self_presence_trace.jsonl"]),
    }


def _write_goal_ecology_state(root: Path, decision: GoalEcologyDecision) -> None:
    selected = next(
        (candidate for candidate in decision.candidates if candidate.goal_id == decision.selected_goal_id),
        _fallback_candidate(),
    )
    lines = [
        "---",
        "title: Self-Chosen Goal Ecology State",
        "memory_type: self_chosen_goal_ecology_state",
        "time_scope: short_term",
        "subject_ids: [xinyu]",
        "protected: true",
        "source: xinyu_self_chosen_goal_ecology",
        f"updated_at: {_timestamp_or_now_iso(decision.checked_at)}",
        "tags: [initiative, autonomy, goal-ecology, state-only]",
        "---",
        "",
        "# Self-Chosen Goal Ecology State",
        "",
        "## Selected Goal",
        f"- selected_goal_id: {decision.selected_goal_id}",
        f"- selected_label: {decision.selected_label}",
        f"- selected_score: {decision.selected_score}",
        f"- action_policy: {decision.action_policy}",
        f"- next_safe_action: {decision.next_safe_action}",
        f"- boundary: {decision.boundary}",
        f"- evidence_refs: {', '.join(selected.evidence_refs) if selected.evidence_refs else 'none'}",
        "",
        "## Candidate Scores",
    ]
    for candidate in decision.candidates:
        lines.append(
            "- "
            f"{candidate.goal_id}: score={candidate.final_score} "
            f"base={candidate.base_score} habit={candidate.habit_weight} status={candidate.status}"
        )
    outcome_report = _outcome_report_lines(root)
    if outcome_report:
        lines.extend(["", *outcome_report])
    lines.extend(
        [
            "",
            "## Boundary",
            "- this selector records an internal goal preference only",
            "- it never sends messages, edits files, calls tools, or rewrites stable memory by itself",
            "- owner direction, safety gates, and current-turn context outrank this goal",
        ]
    )
    atomic_write_text(root / STATE_MD_REL, "\n".join(lines))
    state = _load_state(root)
    goals = state.setdefault("goals", {})
    selected_state = _goal_state(goals, decision.selected_goal_id)
    selected_state["last_selected_at"] = decision.checked_at
    selected_state["last_selected_score"] = decision.selected_score
    state["updated_at"] = decision.checked_at
    state["last_selected_goal_id"] = decision.selected_goal_id
    _persist_state(root, state)


def _decision_trace_payload(decision: GoalEcologyDecision) -> dict[str, Any]:
    return {
        "checked_at": decision.checked_at,
        "trigger": decision.trigger,
        "selected_goal_id": decision.selected_goal_id,
        "selected_score": decision.selected_score,
        "candidate_count": decision.candidate_count,
        "action_policy": decision.action_policy,
        "next_safe_action": decision.next_safe_action,
        "notes": list(decision.notes),
        "candidates": [asdict(candidate) for candidate in decision.candidates],
    }


def _outcome_report_lines(root: Path) -> list[str]:
    data = _json_obj(_read(root / OUTCOME_OBSERVER_STATE_REL, limit=20000))
    if not isinstance(data, dict):
        return []
    report = data.get("report")
    if not isinstance(report, dict):
        return []
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


def _format_counts(values: dict[str, Any]) -> str:
    if not values:
        return "none"
    return ", ".join(f"{_safe_token(key)}={_safe_str(value)}" for key, value in sorted(values.items()))


def _load_state(root: Path) -> dict[str, Any]:
    try:
        data = json.loads((root / STATE_JSON_REL).read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    goals = data.get("goals") if isinstance(data.get("goals"), dict) else {}
    data["version"] = ECOLOGY_VERSION
    data["updated_at"] = _safe_str(data.get("updated_at")) or _now_iso()
    data["goals"] = goals
    data.setdefault("notes", ["self_chosen_goal_ecology_state_v1"])
    return data


def _persist_state(root: Path, state: dict[str, Any]) -> None:
    normalized = dict(state)
    normalized["version"] = ECOLOGY_VERSION
    normalized["goals"] = normalized.get("goals") if isinstance(normalized.get("goals"), dict) else {}
    atomic_write_json(root / STATE_JSON_REL, normalized)


def _touch_state(state: dict[str, Any], *, checked_at: str) -> dict[str, Any]:
    touched = dict(state)
    touched["updated_at"] = checked_at
    return touched


def _goal_state(goals: dict[str, Any], goal_id: str) -> dict[str, Any]:
    existing = goals.get(goal_id)
    if not isinstance(existing, dict):
        existing = {}
        goals[goal_id] = existing
    existing["habit_weight"] = _clamp(existing.get("habit_weight") or 0.0, low=-0.25, high=0.35)
    existing["success_count"] = max(0, int(existing.get("success_count") or 0))
    existing["blocked_count"] = max(0, int(existing.get("blocked_count") or 0))
    existing.setdefault("cooldown_until", "")
    existing.setdefault("last_selected_at", "")
    return existing


def _append_trace(root: Path, event_kind: str, payload: dict[str, Any]) -> None:
    event = {"event_kind": event_kind, "version": ECOLOGY_VERSION, **payload}
    path = root / TRACE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def _recent_selection_penalty(last_selected_at: Any, checked_at: str) -> float:
    if not _safe_str(last_selected_at).strip():
        return 0.0
    last = _parse_time(last_selected_at)
    now = _parse_time(checked_at)
    if not last or last >= now:
        return 0.0
    hours = (now - last).total_seconds() / 3600.0
    if hours < 2:
        return -0.12
    if hours < 8:
        return -0.05
    return 0.02


def _evidence_ref(text: str, path: str) -> str:
    if not text:
        return ""
    return f"{path}:sha256:{_hash_text(text, 10)}"


def _read(path: Path, *, limit: int) -> str:
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""
    if len(text) <= limit:
        return text
    return text[-limit:]


def _json_obj(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


def _contains_any(text: str, markers: Iterable[str]) -> bool:
    lowered = _safe_str(text).lower()
    return any(marker and marker.lower() in lowered for marker in markers)


def _safe_token(value: Any) -> str:
    text = _safe_str(value).strip().lower()
    text = re.sub(r"[^a-z0-9_-]+", "_", text)
    return text.strip("_")[:80]


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _hash_text(value: Any, length: int = 16) -> str:
    return hashlib.sha256(_safe_str(value).encode("utf-8", errors="replace")).hexdigest()[:length]


def _clamp(value: Any, *, low: float, high: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = 0.0
    return round(max(low, min(high, number)), 4)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _timestamp_or_now_iso(value: Any) -> str:
    return _iso(_parse_time(value))


def _parse_time(value: Any) -> datetime:
    try:
        parsed = datetime.fromisoformat(_safe_str(value))
    except Exception:
        return datetime.now().astimezone()
    if parsed.tzinfo is None:
        return parsed.astimezone()
    return parsed.astimezone()


def _iso(value: datetime) -> str:
    return value.astimezone().isoformat(timespec="seconds")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run XinYu self-chosen goal ecology.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--checked-at", default=None)
    parser.add_argument("--trigger", default="manual")
    parser.add_argument("--outcome-goal", default="")
    parser.add_argument("--outcome", default="")
    parser.add_argument("--note", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.outcome_goal:
        result = record_self_chosen_goal_outcome(
            args.root,
            args.outcome_goal,
            args.outcome or "neutral",
            observed_at=args.checked_at,
            note=args.note,
        )
    else:
        result = run_self_chosen_goal_ecology(args.root, checked_at=args.checked_at, trigger=args.trigger)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"selected_goal_id={result.get('selected_goal_id') or result.get('goal_id')}")
        print(f"notes={','.join(result.get('notes', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

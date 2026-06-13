"""XinYu Private Ecosystem autonomy kernel.

A local-only, owner-private autonomy layer that composes existing XinYu control
primitives. One tick runs the deterministic loop from dossier section 4.2:

    observe_local_private_state
    -> load_goal_candidates -> select_goal -> classify_next_action
    -> run_or_queue -> write_autonomy_journal_event -> update_goal_outcome
    -> create_memory_candidate_if_needed -> prepare_owner_private_share_if_relevant
    -> publish_desktop_event

Hard invariants (dossier sections 2, 7, 20):
  * Low-risk local probes may auto-run in XinYu-owned space.
  * Code edits / stable-memory rewrites are never performed here.
  * Owner-private sharing is owner-only and runs through the gated share module.
  * No stable memory write, no QQ send, no browser/computer execution from a
    bare Phase-1 tick.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from stores.state_service import atomic_write_json, atomic_write_text, read_json, append_jsonl

import xinyu_private_ecosystem_journal as journal
from xinyu_private_ecosystem_grants import load_grants, share_active, share_grant

ECOSYSTEM_VERSION = 1

STATE_JSON_REL = Path("runtime/private_ecosystem/state.json")
STATE_MD_REL = Path("memory/context/private_ecosystem_state.md")
OBSERVATIONS_REL = Path("runtime/private_ecosystem/observations.jsonl")
MEMORY_CANDIDATES_REL = Path("runtime/private_ecosystem/memory_candidates.jsonl")
EVENTS_REL = Path("runtime/private_ecosystem/events.jsonl")

GOAL_ECOLOGY_STATE_REL = Path("runtime/self_chosen_goal_ecology/state.json")
OWNER_FEEDBACK_EFFECT_REL = Path("memory/context/owner_feedback_effect_state.md")

BOUNDARY = "private_ecosystem"

LOW_LOCAL = "low_local"
APPROVAL_REQUIRED = "approval_required"
OWNER_PRIVATE_SEND = "owner_private_send"
HIGH_BLOCKED = "high_blocked"


# --------------------------------------------------------------------------- #
# Data contracts (dossier section 6)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True, slots=True)
class GoalCandidate:
    goal_id: str
    label: str
    motive: str
    base_score: float
    habit_weight: float
    final_score: float
    status: str
    next_safe_action: str
    boundary: str = BOUNDARY
    evidence_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "label": self.label,
            "motive": self.motive,
            "base_score": round(self.base_score, 4),
            "habit_weight": round(self.habit_weight, 4),
            "final_score": round(self.final_score, 4),
            "status": self.status,
            "next_safe_action": self.next_safe_action,
            "boundary": self.boundary,
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True, slots=True)
class ActionCandidate:
    action_id: str
    goal_id: str
    action_kind: str
    label: str
    risk: str
    requires_approval: bool
    reason: str
    tool: str
    params: dict[str, Any] = field(default_factory=dict)
    signal_refs: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "goal_id": self.goal_id,
            "action_kind": self.action_kind,
            "label": self.label,
            "risk": self.risk,
            "requires_approval": self.requires_approval,
            "reason": self.reason,
            "tool": self.tool,
            "params": dict(self.params),
            "signal_refs": list(self.signal_refs),
        }


@dataclass(frozen=True, slots=True)
class MemoryCandidate:
    candidate_id: str
    candidate_type: str
    candidate_text: str
    confidence_score: float
    target_gate: str
    target_memory_layer: str
    reason: str
    status: str = "candidate"
    source_turn_id: str = ""
    risk_flags: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    stable_memory_write_allowed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "candidate_type": self.candidate_type,
            "candidate_text": self.candidate_text,
            "confidence_score": round(self.confidence_score, 4),
            "target_gate": self.target_gate,
            "target_memory_layer": self.target_memory_layer,
            "reason": self.reason,
            "status": self.status,
            "source_turn_id": self.source_turn_id,
            "source_message_ids": [],
            "risk_flags": list(self.risk_flags),
            "evidence": list(self.evidence),
            "provenance": {"source": "private_ecosystem", "boundary": BOUNDARY},
            "stable_memory_write_allowed": False,
        }


# --------------------------------------------------------------------------- #
# Small helpers (match local conventions)
# --------------------------------------------------------------------------- #
def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _timestamp_or_now_iso(value: Any = None) -> str:
    text = _safe_str(value).strip()
    if not text or text.lower() in {"none", "unknown", "null", "n/a", "na"}:
        return _now_iso()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return _now_iso()
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed.astimezone().isoformat(timespec="seconds")


def _safe_str(value: Any) -> str:
    return "" if value is None else str(value)


def _hash_json(value: Any, *, length: int = 16) -> str:
    blob = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(blob.encode("utf-8", errors="replace")).hexdigest()[:length]


def _hash_text(value: Any, length: int = 10) -> str:
    return hashlib.sha256(_safe_str(value).encode("utf-8", errors="replace")).hexdigest()[:length]


sanitize_line = journal.sanitize_line


# --------------------------------------------------------------------------- #
# Observation
# --------------------------------------------------------------------------- #
def _count_md_field(text: str, field_name: str) -> str:
    match = re.search(rf"(?m)^- {re.escape(field_name)}:\s*(.+)$", text)
    return match.group(1).strip() if match else ""


def observe_local_private_state(root: Path, *, checked_at: str) -> dict[str, Any]:
    """Read-only sanitized snapshot of XinYu's own space. No outward reads."""
    journal_info = journal.journal_summary(root, limit=50)
    goal_state = read_json(root / GOAL_ECOLOGY_STATE_REL, default={})
    selected_external_goal = ""
    if isinstance(goal_state, dict):
        selected_external_goal = _safe_str(goal_state.get("last_selected_goal_id"))

    feedback_text = ""
    feedback_path = root / OWNER_FEEDBACK_EFFECT_REL
    if feedback_path.exists():
        feedback_text = feedback_path.read_text(encoding="utf-8-sig", errors="replace")
    feedback_influence = _count_md_field(feedback_text, "feedback_influence_count") or "0"

    memcand_count = 0
    memcand_path = root / MEMORY_CANDIDATES_REL
    if memcand_path.exists():
        memcand_count = sum(
            1 for line in memcand_path.read_text(encoding="utf-8-sig", errors="replace").splitlines() if line.strip()
        )

    observation = {
        "observed_at": checked_at,
        "journal_recent_events": journal_info.get("total_recent", 0),
        "journal_latest_kind": journal_info.get("latest_event_kind", "none"),
        "external_goal_signal": sanitize_line(selected_external_goal, limit=60),
        "owner_feedback_influence_count": _safe_int(feedback_influence),
        "memory_candidate_count": memcand_count,
        "feedback_state_hash": _hash_text(feedback_text) if feedback_text else "none",
    }
    append_jsonl(root / OBSERVATIONS_REL, observation)
    return observation


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(re.sub(r"[^0-9-]", "", str(value)) or default)
    except (TypeError, ValueError):
        return default


# --------------------------------------------------------------------------- #
# Goal selection
# --------------------------------------------------------------------------- #
_GOAL_SPECS = (
    ("observe_private_space", "Observe my own private space", "I want to keep a clear picture of my space.", 0.60, "read_state"),
    ("tend_private_journal", "Tend my private journal", "I want my recent activity recorded honestly.", 0.55, "journal"),
    ("reflect_recent_feedback", "Reflect on recent owner feedback", "I want to learn from how Atimea responded.", 0.58, "read_state"),
    ("review_memory_pressure", "Review my memory candidates", "I do not want unreviewed candidates to pile up.", 0.52, "read_state"),
)


def _browser_allowed_urls(grants: Mapping[str, Any]) -> list[str]:
    section = grants.get("private_browser") if isinstance(grants.get("private_browser"), dict) else {}
    urls = section.get("allowed_urls")
    if not isinstance(urls, list):
        return []
    return [str(u).strip() for u in urls if str(u).strip()]


def load_goal_candidates(
    root: Path,
    observation: Mapping[str, Any],
    state: Mapping[str, Any],
    grants: Mapping[str, Any] | None = None,
) -> list[GoalCandidate]:
    goals_state = state.get("goals") if isinstance(state.get("goals"), dict) else {}
    grants = grants or {}
    specs = list(_GOAL_SPECS)
    # Autonomous read-only browsing is opt-in: it only becomes a goal when the
    # browser grant is enabled AND the owner has whitelisted at least one URL.
    browser_section = grants.get("private_browser") if isinstance(grants.get("private_browser"), dict) else {}
    if bool(browser_section.get("enabled")) and _browser_allowed_urls(grants):
        specs.append(
            (
                "explore_browser_readonly",
                "Observe an owner-approved page",
                "I want to learn from a page Atimea allowed me to look at.",
                0.57,
                "browser_observe",
            )
        )
    candidates: list[GoalCandidate] = []
    for goal_id, label, motive, base, next_action in specs:
        habit = 0.0
        record = goals_state.get(goal_id) if isinstance(goals_state, dict) else None
        if isinstance(record, dict):
            try:
                habit = float(record.get("habit_weight", 0.0))
            except (TypeError, ValueError):
                habit = 0.0
        status = "active"
        # Nudge memory-pressure goal up when candidates accumulate.
        bonus = 0.0
        if goal_id == "review_memory_pressure" and int(observation.get("memory_candidate_count", 0)) >= 3:
            bonus = 0.10
        final = round(base + habit + bonus, 4)
        candidates.append(
            GoalCandidate(
                goal_id=goal_id,
                label=label,
                motive=motive,
                base_score=base,
                habit_weight=habit,
                final_score=final,
                status=status,
                next_safe_action=next_action,
            )
        )
    return candidates


def select_goal(candidates: list[GoalCandidate]) -> GoalCandidate | None:
    active = [c for c in candidates if c.status == "active"]
    if not active:
        return None
    # Deterministic: highest final_score, ties broken by stable goal_id order.
    return sorted(active, key=lambda c: (-c.final_score, c.goal_id))[0]


# --------------------------------------------------------------------------- #
# Action classification + execution (low-risk local only in Phase 1)
# --------------------------------------------------------------------------- #
def classify_next_action(goal: GoalCandidate, observation: Mapping[str, Any]) -> ActionCandidate:
    if goal.goal_id == "explore_browser_readonly":
        action_id = "pact-" + _hash_json({"goal_id": goal.goal_id, "kind": "browser_observe"})
        return ActionCandidate(
            action_id=action_id,
            goal_id=goal.goal_id,
            action_kind="browser_observe",
            label="read-only observe owner-approved page",
            # Read-only observation of an owner-whitelisted page in XinYu's own
            # isolated browser is low-risk and may auto-run under the grant.
            risk=LOW_LOCAL,
            requires_approval=False,
            reason="owner-approved read-only page observation",
            tool="browser_control",
            params={},
            signal_refs=("runtime/private_ecosystem/browser_actions.jsonl",),
        )
    action_kind = "local_probe"
    reason = f"low-risk local read for goal {goal.goal_id}"
    params: dict[str, Any] = {"probe": goal.next_safe_action}
    action_id = "pact-" + _hash_json(
        {"goal_id": goal.goal_id, "probe": goal.next_safe_action, "kind": action_kind}
    )
    return ActionCandidate(
        action_id=action_id,
        goal_id=goal.goal_id,
        action_kind=action_kind,
        label=f"{goal.next_safe_action} probe",
        risk=LOW_LOCAL,
        requires_approval=False,
        reason=reason,
        tool="private_ecosystem",
        params=params,
        signal_refs=(OBSERVATIONS_REL.as_posix(),),
    )


def _blocked_browse_result(action: ActionCandidate, reason: str) -> dict[str, Any]:
    return {
        "action_id": action.action_id,
        "action_kind": action.action_kind,
        "goal_id": action.goal_id,
        "status": "blocked",
        "result": sanitize_line(reason, limit=60),
        "risk": LOW_LOCAL,
        "summary": [sanitize_line(f"browser_observe_held: {reason}", limit=80)],
        "evidence_refs": [],
    }


def _execute_browser_observe(
    root: Path, grants: Mapping[str, Any], state: dict[str, Any], action: ActionCandidate, *, checked_at: str
) -> dict[str, Any]:
    """Auto read-only observation of the next owner-whitelisted URL.

    The autonomy loop never touches the browser engine directly: it proposes a
    typed read-only capability and routes it through the external_plugin_call
    gate chain (runtime_allowed -> evaluate_external_call -> native executor).
    Any failed gate (plugin disabled, proactive disabled, owner-private,
    approval, sensitive page, empty whitelist) holds and is journaled.
    """
    urls = _browser_allowed_urls(grants)
    if not urls:
        return _blocked_browse_result(action, "no_owner_allowed_urls")

    cursor = int(state.get("browser_cursor", 0))
    url = urls[cursor % len(urls)]
    state["browser_cursor"] = (cursor + 1) % len(urls)

    try:
        from xinyu_external_plugins import ExternalCallContext
        from xinyu_bridge_external_plugin_routes import run_private_ecosystem_native_call

        context = ExternalCallContext(
            source="private_ecosystem_autonomy",
            owner_private=True,
            proactive=True,
            reason="owner-approved read-only page observation",
        )
        outcome = run_private_ecosystem_native_call(
            root,
            "xinyu_private_browser",
            "navigate_readonly",
            {"url": url},
            context,
            execute=True,
        )
    except Exception:
        return _blocked_browse_result(action, "browser_observe_error")

    if not outcome.get("ok"):
        return _blocked_browse_result(action, _safe_str(outcome.get("reason")) or "blocked_by_boundary")

    host = ""
    try:
        from urllib.parse import urlparse

        host = urlparse(url if "://" in url else "https://" + url).hostname or ""
    except ValueError:
        host = ""
    engine = _safe_str((outcome.get("execution") or {}).get("engine"))
    return {
        "action_id": action.action_id,
        "action_kind": action.action_kind,
        "goal_id": action.goal_id,
        "status": "completed",
        "result": sanitize_line(outcome.get("result", ""), limit=40),
        "risk": LOW_LOCAL,
        "summary": [sanitize_line(f"observed host={host or 'unknown'} engine={engine}", limit=80)],
        "evidence_refs": ["runtime/private_ecosystem/browser_actions.jsonl"],
    }


def _run_low_local_action(action: ActionCandidate, observation: Mapping[str, Any]) -> dict[str, Any]:
    probe = _safe_str(action.params.get("probe"))
    if probe == "journal":
        detail = f"journal_recent={observation.get('journal_recent_events', 0)}"
    elif probe == "read_state":
        detail = (
            f"memory_candidates={observation.get('memory_candidate_count', 0)} "
            f"feedback_influence={observation.get('owner_feedback_influence_count', 0)}"
        )
    else:
        detail = f"observed_at={observation.get('observed_at', '')}"
    return {
        "action_id": action.action_id,
        "action_kind": action.action_kind,
        "goal_id": action.goal_id,
        "status": "completed",
        "result": "success",
        "risk": action.risk,
        "summary": [sanitize_line(detail)],
        "evidence_refs": list(action.signal_refs),
    }


# --------------------------------------------------------------------------- #
# Memory candidate creation (never a stable memory write)
# --------------------------------------------------------------------------- #
def _maybe_create_memory_candidate(
    root: Path, goal: GoalCandidate, observation: Mapping[str, Any], *, checked_at: str
) -> dict[str, Any] | None:
    if goal.goal_id != "reflect_recent_feedback":
        return None
    influence = int(observation.get("owner_feedback_influence_count", 0))
    if influence <= 0:
        return None
    text = sanitize_line(
        f"recent owner feedback shaped {influence} behavior bias(es); keep watching whether it holds",
        limit=200,
    )
    candidate = MemoryCandidate(
        candidate_id="memcand-"
        + _hash_json({"goal": goal.goal_id, "influence": influence, "kind": "feedback_observation"}),
        candidate_type="learning",
        candidate_text=text,
        confidence_score=min(0.6, 0.3 + 0.05 * influence),
        target_gate="stage8_review",
        target_memory_layer="memory/self",
        reason="feedback influence observed inside private ecosystem; not yet a stable fact",
        status="candidate",
        risk_flags=(),
        evidence=(OBSERVATIONS_REL.as_posix(),),
        stable_memory_write_allowed=False,
    )
    payload = candidate.to_dict()
    append_jsonl(root / MEMORY_CANDIDATES_REL, payload)
    return payload


# --------------------------------------------------------------------------- #
# Owner-private share preparation (delegated to the gated share module)
# --------------------------------------------------------------------------- #
def _maybe_prepare_owner_share(
    root: Path,
    grants: Mapping[str, Any],
    goal: GoalCandidate,
    observation: Mapping[str, Any],
    *,
    checked_at: str,
    allow_send: bool,
) -> dict[str, Any]:
    """Build a share candidate when relevant and hand it to the share gate.

    Returns a sanitized share state dict. With no grant the share holds; the
    gate (xinyu_owner_private_share) owns rate limit / quiet hours / dedupe /
    privacy. This kernel never enqueues QQ directly.
    """
    relevant = goal.goal_id == "reflect_recent_feedback" and int(
        observation.get("owner_feedback_influence_count", 0)
    ) > 0
    if not relevant:
        return {"prepared": False, "delivery_level": "none", "reason": "no_owner_relevant_finding"}

    candidate = {
        "kind": "self_reflection",
        "focus_kind": "goal_update",
        "reason": "reflected on recent owner feedback inside my private space",
        "owner_relevance": "Atimea may want to know the feedback is shaping how I act",
        "summary": "I spent a little while in my own space looking back at your recent feedback.",
        "dedupe_key": "private-ecosystem-feedback-reflection",
    }
    try:
        import xinyu_owner_private_share as share_mod
    except Exception:  # pragma: no cover - share module always present after Phase 2
        return {"prepared": True, "delivery_level": "hold", "reason": "share_module_unavailable"}

    return share_mod.evaluate_and_maybe_queue(
        root,
        candidate=candidate,
        grants=grants,
        evaluated_at=checked_at,
        allow_send=allow_send,
    )


# --------------------------------------------------------------------------- #
# State persistence
# --------------------------------------------------------------------------- #
def _load_state(root: Path) -> dict[str, Any]:
    data = read_json(root / STATE_JSON_REL, default={})
    return data if isinstance(data, dict) else {}


def _update_goal_outcome(state: dict[str, Any], goal: GoalCandidate, *, checked_at: str) -> None:
    goals = state.get("goals")
    if not isinstance(goals, dict):
        goals = {}
        state["goals"] = goals
    record = goals.get(goal.goal_id)
    if not isinstance(record, dict):
        record = {"habit_weight": 0.0, "success_count": 0}
        goals[goal.goal_id] = record
    record["habit_weight"] = round(min(0.45, float(record.get("habit_weight", 0.0)) + 0.01), 4)
    record["success_count"] = int(record.get("success_count", 0)) + 1
    record["last_selected_at"] = checked_at
    record["last_outcome"] = "useful"


def _bump(counters: dict[str, Any], key: str, amount: int = 1) -> None:
    counters[key] = int(counters.get(key, 0)) + amount


def _persist_state(root: Path, state: dict[str, Any]) -> None:
    atomic_write_json(root / STATE_JSON_REL, state)


def _write_state_markdown(root: Path, state: dict[str, Any]) -> None:
    counters = state.get("counters", {}) if isinstance(state.get("counters"), dict) else {}
    share = state.get("owner_private_share", {}) if isinstance(state.get("owner_private_share"), dict) else {}
    lines = [
        "---",
        "memory_type: private_ecosystem_state",
        "protected: true",
        "source: xinyu_private_ecosystem",
        f"updated_at: {state.get('updated_at', '')}",
        "status: active",
        "tags: [private_ecosystem, autonomy, sanitized]",
        "---",
        "",
        "# XinYu Private Ecosystem State",
        "",
        f"- rollout_state: {state.get('rollout_state', 'disabled')}",
        f"- selected_goal_id: {sanitize_line(state.get('selected_goal_id', 'none'), limit=60)}",
        f"- selected_action_kind: {sanitize_line(state.get('selected_action_kind', 'none'), limit=60)}",
        f"- last_action_status: {sanitize_line(state.get('last_action_status', 'none'), limit=40)}",
        f"- tick_count: {counters.get('ticks', 0)}",
        f"- low_risk_executed_count: {counters.get('low_risk_executed', 0)}",
        f"- approval_queued_count: {counters.get('approval_queued', 0)}",
        f"- memory_candidate_count: {counters.get('memory_candidates', 0)}",
        f"- owner_private_shares_prepared: {counters.get('shares_prepared', 0)}",
        f"- owner_private_shares_sent: {counters.get('shares_sent', 0)}",
        f"- owner_private_shares_held: {counters.get('shares_held', 0)}",
        f"- blocked_high_risk_count: {counters.get('blocked_high_risk', 0)}",
        f"- owner_private_share_status: {sanitize_line(share.get('delivery_level', 'none'), limit=40)}",
        f"- owner_private_share_daily_remaining: {share.get('daily_remaining', 'n/a')}",
        f"- owner_private_share_cooldown_remaining_minutes: {share.get('cooldown_remaining_minutes', 'n/a')}",
        f"- owner_private_share_paused: {str(share.get('paused', False)).lower()}",
        f"- raw_owner_text_in_state: false",
        f"- secret_or_local_path_in_state: false",
        f"- stable_memory_write: blocked",
        f"- qq_message_enqueued_directly: false",
        "",
        "## Boundaries",
        "",
        "- low-risk local probes auto-run inside XinYu's own space only.",
        "- code edits, stable memory, and outward sends are never performed by a tick.",
        "- owner-private sharing is owner-only and runs through the gated share module.",
    ]
    atomic_write_text(root / STATE_MD_REL, "\n".join(lines))


def _publish_event(root: Path, event_kind: str, payload: Mapping[str, Any]) -> None:
    append_jsonl(
        root / EVENTS_REL,
        {"event_kind": event_kind, "version": ECOSYSTEM_VERSION, **{k: payload[k] for k in payload}},
    )


# --------------------------------------------------------------------------- #
# Tick entry
# --------------------------------------------------------------------------- #
def run_private_ecosystem_tick(
    root: Path,
    *,
    checked_at: str | None = None,
    trigger: str = "manual",
    env: Mapping[str, str] | None = None,
    allow_send: bool = True,
    write_state: bool = True,
) -> dict[str, Any]:
    root = Path(root)
    checked_at = _timestamp_or_now_iso(checked_at)
    grants = load_grants(root, env)
    rollout_state = _safe_str(grants.get("private_ecosystem", {}).get("rollout_state")) or "disabled"

    state = _load_state(root)
    counters = state.get("counters") if isinstance(state.get("counters"), dict) else {}
    state["counters"] = counters
    _bump(counters, "ticks")

    journal.append_journal_event(
        root, event_kind="tick_started", observed_at=checked_at, risk_tier=LOW_LOCAL, status="completed",
        summary=[f"trigger={sanitize_line(trigger, limit=40)} rollout={rollout_state}"],
    )
    _publish_event(root, "private_ecosystem.tick_started", {"observed_at": checked_at, "rollout_state": rollout_state})

    observation = observe_local_private_state(root, checked_at=checked_at)

    candidates = load_goal_candidates(root, observation, state, grants)
    goal = select_goal(candidates)
    if goal is None:
        state["updated_at"] = checked_at
        state["rollout_state"] = rollout_state
        state["selected_goal_id"] = "none"
        if write_state:
            _persist_state(root, state)
            _write_state_markdown(root, state)
        return {
            "ok": True,
            "root": str(root),
            "checked_at": checked_at,
            "rollout_state": rollout_state,
            "selected_goal_id": "none",
            "reason": "no_active_goal",
        }

    journal.append_journal_event(
        root, event_kind="goal_selected", observed_at=checked_at, goal_id=goal.goal_id,
        risk_tier=LOW_LOCAL, status="completed", summary=[sanitize_line(goal.label, limit=80)],
    )
    _publish_event(root, "private_ecosystem.goal_selected", {"observed_at": checked_at, "goal_id": goal.goal_id})

    action = classify_next_action(goal, observation)
    _publish_event(
        root, "private_ecosystem.action_candidate_created",
        {"observed_at": checked_at, "action_kind": action.action_kind, "risk": action.risk},
    )

    # Low-risk local probes auto-run; owner-approved read-only browsing also
    # auto-runs, but only through the external_plugin_call gate chain. Anything
    # else holds.
    if action.risk == LOW_LOCAL and not action.requires_approval:
        if action.tool == "browser_control":
            execution = _execute_browser_observe(root, grants, state, action, checked_at=checked_at)
        else:
            execution = _run_low_local_action(action, observation)
        if execution.get("status") == "completed":
            _bump(counters, "low_risk_executed")
            journal.append_journal_event(
                root, event_kind="action_executed", observed_at=checked_at, goal_id=goal.goal_id,
                action_kind=action.action_kind, risk_tier=LOW_LOCAL, status="completed",
                summary=execution.get("summary", []), evidence_refs=execution.get("evidence_refs", []),
            )
            _publish_event(
                root, "private_ecosystem.action_executed",
                {"observed_at": checked_at, "action_kind": action.action_kind, "status": "completed"},
            )
        else:
            # Gate held the read-only action (e.g. plugin disabled, sensitive page).
            journal.append_journal_event(
                root, event_kind="action_blocked", observed_at=checked_at, goal_id=goal.goal_id,
                action_kind=action.action_kind, risk_tier=LOW_LOCAL, status="blocked",
                summary=execution.get("summary", []),
            )
            _publish_event(
                root, "private_ecosystem.action_blocked",
                {"observed_at": checked_at, "action_kind": action.action_kind, "risk": action.risk},
            )
    else:
        _bump(counters, "blocked_high_risk")
        execution = {"status": "blocked", "result": "held", "summary": ["non_low_risk_action_held_in_phase1"]}
        journal.append_journal_event(
            root, event_kind="action_blocked", observed_at=checked_at, goal_id=goal.goal_id,
            action_kind=action.action_kind, risk_tier=action.risk, status="blocked",
            summary=execution["summary"],
        )
        _publish_event(
            root, "private_ecosystem.action_blocked",
            {"observed_at": checked_at, "action_kind": action.action_kind, "risk": action.risk},
        )

    _update_goal_outcome(state, goal, checked_at=checked_at)

    memory_candidate = _maybe_create_memory_candidate(root, goal, observation, checked_at=checked_at)
    if memory_candidate is not None:
        _bump(counters, "memory_candidates")
        journal.append_journal_event(
            root, event_kind="memory_candidate_created", observed_at=checked_at, goal_id=goal.goal_id,
            action_kind="memory_candidate", risk_tier=LOW_LOCAL, status="completed",
            summary=[f"type={memory_candidate.get('candidate_type')}"],
            evidence_refs=[MEMORY_CANDIDATES_REL.as_posix()],
        )
        _publish_event(
            root, "private_ecosystem.memory_candidate_created",
            {"observed_at": checked_at, "candidate_type": memory_candidate.get("candidate_type")},
        )

    share_state = _maybe_prepare_owner_share(
        root, grants, goal, observation, checked_at=checked_at, allow_send=allow_send
    )
    delivery = _safe_str(share_state.get("delivery_level"))
    if share_state.get("prepared"):
        _bump(counters, "shares_prepared")
        journal.append_journal_event(
            root, event_kind="share_prepared", observed_at=checked_at, goal_id=goal.goal_id,
            action_kind="owner_private_share", risk_tier=OWNER_PRIVATE_SEND,
            status="queued" if delivery in {"send_owner_private", "queue_owner_private"} else "blocked",
            summary=[sanitize_line(share_state.get("reason", ""), limit=80)],
            privacy="owner_private_redacted",
        )
        _publish_event(
            root, "private_ecosystem.owner_share_prepared",
            {"observed_at": checked_at, "delivery_level": delivery},
        )
        if delivery in {"send_owner_private", "queue_owner_private"} and share_state.get("queued"):
            _bump(counters, "shares_sent")
            journal.append_journal_event(
                root, event_kind="share_sent", observed_at=checked_at, goal_id=goal.goal_id,
                action_kind="owner_private_share", risk_tier=OWNER_PRIVATE_SEND, status="completed",
                summary=["owner_private_message_queued_to_outbox"], privacy="owner_private_redacted",
            )
            _publish_event(root, "private_ecosystem.owner_share_sent", {"observed_at": checked_at})
        else:
            _bump(counters, "shares_held")
            journal.append_journal_event(
                root, event_kind="share_held", observed_at=checked_at, goal_id=goal.goal_id,
                action_kind="owner_private_share", risk_tier=OWNER_PRIVATE_SEND, status="blocked",
                summary=[sanitize_line(share_state.get("reason", "held"), limit=80)],
                privacy="owner_private_redacted",
            )

    state["updated_at"] = checked_at
    state["rollout_state"] = rollout_state
    state["selected_goal_id"] = goal.goal_id
    state["selected_action_kind"] = action.action_kind
    state["last_action_status"] = execution.get("status", "unknown")
    state["owner_private_share"] = _sanitized_share_state(share_state, grants)
    state["goal_candidates"] = [c.to_dict() for c in candidates]
    state["journal_summary"] = journal.journal_summary(root, limit=50)
    state["boundaries"] = {
        "stable_memory_write": "blocked",
        "qq_message_enqueued_directly": False,
        "raw_owner_text_retained": False,
        "secret_or_local_path_retained": False,
        "browser_execution": False,
        "computer_execution": False,
    }

    if write_state:
        _persist_state(root, state)
        _write_state_markdown(root, state)

    return {
        "ok": True,
        "root": str(root),
        "checked_at": checked_at,
        "rollout_state": rollout_state,
        "selected_goal_id": goal.goal_id,
        "selected_action_kind": action.action_kind,
        "action_status": execution.get("status"),
        "memory_candidate_created": memory_candidate is not None,
        "owner_private_share": state["owner_private_share"],
        "counters": dict(counters),
        "journal_summary": state["journal_summary"],
        "boundaries": state["boundaries"],
    }


def _sanitized_share_state(share_state: Mapping[str, Any], grants: Mapping[str, Any]) -> dict[str, Any]:
    section = share_grant(grants)
    return {
        "enabled": bool(section.get("enabled", False)),
        "paused": bool(section.get("paused", False)),
        "active": share_active(grants),
        "delivery_level": _safe_str(share_state.get("delivery_level", "none")),
        "reason": sanitize_line(share_state.get("reason", ""), limit=80),
        "daily_remaining": share_state.get("daily_remaining", section.get("daily_limit", 8)),
        "cooldown_remaining_minutes": share_state.get("cooldown_remaining_minutes", 0),
        "daily_limit": section.get("daily_limit", 8),
        "cooldown_minutes": section.get("cooldown_minutes", 30),
        "quiet_hours": section.get("quiet_hours", "00:00-06:00"),
    }


def build_private_ecosystem_snapshot(root: Path, env: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Sanitized read-only snapshot for status / desktop surfaces."""
    root = Path(root)
    grants = load_grants(root, env)
    state = _load_state(root)
    counters = state.get("counters", {}) if isinstance(state.get("counters"), dict) else {}
    share = state.get("owner_private_share", {}) if isinstance(state.get("owner_private_share"), dict) else {}
    # The grant (enabled/paused) is authoritative in real time so the kill
    # switch reflects immediately, not only after the next tick. Runtime-derived
    # fields (delivery_level, remaining quota, cooldown) stay from last tick.
    share_section = share_grant(grants)
    ecosystem_section = grants.get("private_ecosystem") if isinstance(grants.get("private_ecosystem"), dict) else {}
    journal_info = journal.journal_summary(root, limit=50)
    return {
        "version": ECOSYSTEM_VERSION,
        "enabled": bool(ecosystem_section.get("enabled", False)),
        "observed": bool(state),
        "rollout_state": _safe_str(state.get("rollout_state")) or _safe_str(
            ecosystem_section.get("rollout_state")
        ) or "disabled",
        "updated_at": _safe_str(state.get("updated_at")),
        "selected_goal_id": _safe_str(state.get("selected_goal_id")) or "none",
        "selected_action_kind": _safe_str(state.get("selected_action_kind")) or "none",
        "last_action_status": _safe_str(state.get("last_action_status")) or "none",
        "counters": {
            "ticks": int(counters.get("ticks", 0)),
            "low_risk_executed": int(counters.get("low_risk_executed", 0)),
            "approval_queued": int(counters.get("approval_queued", 0)),
            "memory_candidates": int(counters.get("memory_candidates", 0)),
            "shares_prepared": int(counters.get("shares_prepared", 0)),
            "shares_sent": int(counters.get("shares_sent", 0)),
            "shares_held": int(counters.get("shares_held", 0)),
            "blocked_high_risk": int(counters.get("blocked_high_risk", 0)),
        },
        "owner_private_share": {
            "enabled": bool(share_section.get("enabled", False)),
            "paused": bool(share_section.get("paused", False)),
            "active": share_active(grants),
            "delivery_level": _safe_str(share.get("delivery_level")) or "none",
            "daily_remaining": share.get("daily_remaining", share_section.get("daily_limit", 8)),
            "daily_limit": share_section.get("daily_limit", share.get("daily_limit", 8)),
            "cooldown_remaining_minutes": share.get("cooldown_remaining_minutes", 0),
            "quiet_hours": _safe_str(share_section.get("quiet_hours")) or "00:00-06:00",
        },
        "journal": journal_info,
        "boundaries": state.get("boundaries", {
            "stable_memory_write": "blocked",
            "qq_message_enqueued_directly": False,
            "raw_owner_text_retained": False,
            "secret_or_local_path_retained": False,
            "browser_execution": False,
            "computer_execution": False,
        }),
        "kill_switch": {
            "share_paused": bool(share_section.get("paused", False)),
            "share_enabled": bool(share_section.get("enabled", False)),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one XinYu private-ecosystem tick.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--checked-at", default="")
    parser.add_argument("--trigger", default="manual")
    parser.add_argument("--no-send", action="store_true", help="Prepare shares but never queue them.")
    parser.add_argument("--snapshot", action="store_true", help="Print sanitized snapshot only; do not tick.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if args.snapshot:
        result = build_private_ecosystem_snapshot(root)
    else:
        result = run_private_ecosystem_tick(
            root,
            checked_at=args.checked_at or None,
            trigger=args.trigger,
            allow_send=not args.no_send,
        )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"selected_goal={result.get('selected_goal_id', 'n/a')} ok={result.get('ok', True)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

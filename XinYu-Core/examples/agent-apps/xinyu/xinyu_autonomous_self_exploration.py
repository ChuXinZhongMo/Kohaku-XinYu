from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_autonomous_self_exploration_store import append_autonomous_self_exploration_trace
from xinyu_autonomous_self_exploration_store import read_autonomous_self_exploration_text
from xinyu_autonomous_self_exploration_store import read_autonomous_self_exploration_trace_rows
from xinyu_autonomous_self_exploration_store import write_autonomous_self_exploration_text
from xinyu_self_action_gateway import run_self_action_gateway


ROOT = Path(__file__).resolve().parent
CUSTOM = ROOT / "custom"
if str(CUSTOM) not in sys.path:
    sys.path.insert(0, str(CUSTOM))

from research_handoff_engine import run_research_handoff_loop  # noqa: E402


STATE_REL = Path("memory/context/autonomous_self_exploration_state.md")
TRACE_REL = Path("runtime/autonomous_self_exploration_trace.jsonl")

SELF_EXPLORATION_GRANT = "grant_autonomous_self_exploration_tick: approved_low_frequency_local_readonly_and_source_handoff"
SOURCE_COLLECT_GRANT = "grant_autonomous_source_collect: approved_bounded_candidate_material_only"
CODEX_RESEARCH_GRANT = "grant_autonomous_codex_research_collect: approved_visible_bounded_report_only"
DEFAULT_CODEX_MIN_INTERVAL_SECONDS = 21600
NONE_VALUES = {"", "none", "unknown", "missing", "null"}


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        text = str(value)
    except Exception:
        return default
    return text if text else default


def _one_line(value: Any, *, limit: int = 220, default: str = "none") -> str:
    text = re.sub(r"\s+", " ", _safe_str(value)).strip()
    text = re.sub(r"(?i)\b(?:authorization|api[_-]?key|token|password|cookie)\s*[:=]\s*[^\s<>'\"]+", "<secret>", text)
    text = re.sub(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{12,}", "<secret>", text)
    text = re.sub(r"(?i)\bsk-[a-z0-9_-]{12,}", "<secret>", text)
    text = re.sub(r"(?i)(?:[a-z]:\\|/users/|/home/|\\\\)[^\s<>'\"]+", "<local_path>", text)
    if not text:
        return default
    return text if len(text) <= limit else text[: max(0, limit - 3)].rstrip() + "..."


def _read_text(path: Path) -> str:
    return read_autonomous_self_exploration_text(path)


def _write_text(path: Path, text: str) -> None:
    write_autonomous_self_exploration_text(path, text)


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    append_autonomous_self_exploration_trace(path, row)


def _field(text: str, name: str, default: str = "none") -> str:
    match = re.search(rf"(?m)^\s*-\s*{re.escape(name)}:\s*(.*?)\s*$", text or "")
    if not match:
        match = re.search(rf"(?m)^\s*{re.escape(name)}:\s*(.*?)\s*$", text or "")
    return _one_line(match.group(1), limit=320, default=default) if match else default


def _parse_dt(value: str) -> datetime | None:
    text = _safe_str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _bool_text(value: Any) -> str:
    return "true" if bool(value) else "false"


def _env_enabled(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "enabled", "on"}


def _grants(root: Path) -> str:
    return _read_text(root / "memory/context/owner_permission_grants.md")


def _self_exploration_granted(root: Path) -> bool:
    return SELF_EXPLORATION_GRANT in _grants(root) or _env_enabled("XINYU_SELF_EXPLORATION_TICK")


def _source_collect_granted(root: Path) -> bool:
    grants = _grants(root)
    return SOURCE_COLLECT_GRANT in grants or _env_enabled("XINYU_AUTONOMOUS_SEARCH")


def _codex_research_granted(root: Path) -> bool:
    return CODEX_RESEARCH_GRANT in _grants(root) or _env_enabled("XINYU_AUTONOMOUS_CODEX_RESEARCH")


def _codex_cooldown_active(root: Path, evaluated_at: str, min_interval_seconds: int) -> bool:
    min_interval_seconds = max(0, int(min_interval_seconds))
    if min_interval_seconds <= 0:
        return False
    observed = _parse_dt(evaluated_at) or datetime.now().astimezone()
    if observed.tzinfo is None:
        observed = observed.astimezone()
    for row in reversed(read_autonomous_self_exploration_trace_rows(root / TRACE_REL)):
        if row.get("event_kind") != "autonomous_self_exploration":
            continue
        if row.get("research_execution_level") != "execute_codex":
            continue
        attempted = _parse_dt(_safe_str(row.get("evaluated_at")))
        if attempted is None:
            continue
        if attempted.tzinfo is None:
            attempted = attempted.astimezone()
        return 0 <= (observed - attempted).total_seconds() < min_interval_seconds
    return False


def _self_thought_handoff(root: Path) -> dict[str, str]:
    state = _read_text(root / "memory/context/self_thought_state.md")
    return {
        "research_needed": _field(state, "research_needed", "false"),
        "route": _field(state, "route", "none"),
        "handoff_target": _field(state, "handoff_target", "none"),
        "source_request_id": _field(state, "source_request_id", "none"),
        "question_id": _field(state, "question_id", "none"),
        "target": _field(state, "target", "none"),
        "codex_launch_permission": _field(state, "codex_launch_permission", "none"),
    }


def _research_execution_plan(
    root: Path,
    handoff: dict[str, str],
    *,
    allow_live_search: bool | None,
    allow_codex: bool | None,
) -> tuple[str, bool, bool]:
    route = handoff.get("route", "none")
    live_search = _source_collect_granted(root) if allow_live_search is None else bool(allow_live_search)
    codex = _codex_research_granted(root) if allow_codex is None else bool(allow_codex)
    if route == "source_search_provider":
        return ("execute" if live_search else "activate"), live_search, False
    if route == "codex_delegate_candidate":
        return ("execute_codex" if codex else "state_only"), False, codex
    return "state_only", False, False


def evaluate_autonomous_self_exploration_policy(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    handoff = _self_thought_handoff(root)
    granted = _self_exploration_granted(root)
    source_granted = _source_collect_granted(root)
    codex_granted = _codex_research_granted(root)
    blocks: list[str] = []
    if not granted:
        blocks.append("self_exploration_grant_missing")
    return {
        "allowed": granted,
        "grant_present": granted,
        "source_collect_grant_present": source_granted,
        "codex_research_grant_present": codex_granted,
        "research_needed": handoff["research_needed"] == "true",
        "research_route": handoff["route"],
        "source_request_id": handoff["source_request_id"],
        "question_id": handoff["question_id"],
        "blocks": blocks,
    }


def run_autonomous_self_exploration_tick(
    root: Path,
    *,
    evaluated_at: str | None = None,
    allow_live_search: bool | None = None,
    allow_codex: bool | None = None,
    execute_low_risk: bool = True,
    codex_min_interval_seconds: int = DEFAULT_CODEX_MIN_INTERVAL_SECONDS,
) -> dict[str, Any]:
    root = Path(root).resolve()
    evaluated_at = evaluated_at or _now_iso()
    policy = evaluate_autonomous_self_exploration_policy(root)
    local_probe: dict[str, Any] = {}
    research: dict[str, Any] = {}
    handoff = _self_thought_handoff(root)
    codex_cooldown = (
        allow_codex is None
        and handoff.get("route") == "codex_delegate_candidate"
        and _codex_research_granted(root)
        and _codex_cooldown_active(root, evaluated_at, codex_min_interval_seconds)
    )
    effective_allow_codex = False if codex_cooldown else allow_codex
    execution_level, live_search_allowed, codex_allowed = _research_execution_plan(
        root,
        handoff,
        allow_live_search=allow_live_search,
        allow_codex=effective_allow_codex,
    )

    if policy["allowed"]:
        local_probe = run_self_action_gateway(
            root,
            checked_at=evaluated_at,
            trigger="autonomous_self_exploration",
            execute_low_risk=execute_low_risk,
        )
        if handoff["research_needed"] == "true":
            research = run_research_handoff_loop(
                root,
                evaluated_at=evaluated_at,
                execution_level=execution_level,
                allow_live_search=live_search_allowed,
                allow_codex=codex_allowed,
            )

    status = "blocked"
    if policy["allowed"]:
        if research:
            status = _one_line(research.get("status"), limit=120)
        elif local_probe:
            status = "local_probe_completed"
        else:
            status = "no_candidate"

    result = {
        "accepted": True,
        "status": status,
        "evaluated_at": evaluated_at,
        "policy": policy,
        "local_probe_status": _one_line(local_probe.get("status"), limit=120),
        "local_probe_selected_goal_id": _one_line(local_probe.get("selected_goal_id"), limit=120),
        "local_probe_executed_action_count": int(local_probe.get("executed_action_count") or 0),
        "local_probe_queued_approval_count": int(local_probe.get("queued_approval_count") or 0),
        "research_status": _one_line(research.get("status"), limit=120),
        "research_route": _one_line(research.get("route") or handoff.get("route"), limit=120),
        "research_execution_level": execution_level,
        "live_search_allowed": live_search_allowed,
        "codex_allowed": codex_allowed,
        "codex_cooldown_active": codex_cooldown,
        "codex_min_interval_seconds": max(0, int(codex_min_interval_seconds)),
        "activation_permission": _one_line(research.get("activation_permission"), limit=120),
        "provider_results": int(research.get("provider_results") or 0),
        "codex_status": _one_line(research.get("codex_status"), limit=120),
        "notes": _notes(policy, local_probe, research),
    }
    _write_text(root / STATE_REL, _render_state(result))
    _append_jsonl(
        root / TRACE_REL,
        {
            "event_kind": "autonomous_self_exploration",
            "evaluated_at": evaluated_at,
            "status": status,
            "policy_allowed": bool(policy["allowed"]),
            "research_route": result["research_route"],
            "research_execution_level": execution_level,
            "live_search_allowed": live_search_allowed,
            "codex_allowed": codex_allowed,
            "codex_cooldown_active": codex_cooldown,
            "local_probe_executed_action_count": result["local_probe_executed_action_count"],
            "local_probe_queued_approval_count": result["local_probe_queued_approval_count"],
            "research_status": result["research_status"],
            "activation_permission": result["activation_permission"],
            "provider_results": result["provider_results"],
            "codex_status": result["codex_status"],
            "blocks": list(policy["blocks"]),
        },
    )
    return result


def _notes(policy: dict[str, Any], local_probe: dict[str, Any], research: dict[str, Any]) -> list[str]:
    if not policy.get("allowed"):
        return [f"blocked:{item}" for item in policy.get("blocks", [])] or ["blocked:unknown"]
    notes = [
        "local_probe:"
        f"{_one_line(local_probe.get('selected_goal_id'), limit=80)}/"
        f"{_one_line(local_probe.get('executed_action_count'), limit=20)}/"
        f"{_one_line(local_probe.get('queued_approval_count'), limit=20)}"
    ]
    if research:
        notes.append(
            "research:"
            f"{_one_line(research.get('route'), limit=80)}/"
            f"{_one_line(research.get('status'), limit=80)}/"
            f"{_one_line(research.get('activation_permission'), limit=80)}/"
            f"{_one_line(research.get('provider_results'), limit=20)}"
        )
    else:
        notes.append("research:none")
    return notes


def _render_state(result: dict[str, Any]) -> str:
    policy = result.get("policy") if isinstance(result.get("policy"), dict) else {}
    notes = "\n".join(f"- {_one_line(note, limit=180)}" for note in result.get("notes", [])) or "- none"
    blocks = ", ".join(_one_line(item, limit=120) for item in policy.get("blocks", [])) or "none"
    return f"""---
title: Autonomous Self Exploration State
memory_type: autonomous_self_exploration_state
time_scope: immediate_runtime
subject_ids: [xinyu]
protected: true
source: xinyu_autonomous_self_exploration
updated_at: {_one_line(result.get('evaluated_at'))}
status: active
tags: [autonomy, self-exploration, research, local-probe, audit]
---

# Autonomous Self Exploration State

## Last Evaluation
- evaluated_at: {_one_line(result.get('evaluated_at'))}
- status: {_one_line(result.get('status'))}
- allowed: {_bool_text(policy.get('allowed'))}
- blocks: {blocks}

## Local Probe
- local_probe_status: {_one_line(result.get('local_probe_status'))}
- local_probe_selected_goal_id: {_one_line(result.get('local_probe_selected_goal_id'))}
- local_probe_executed_action_count: {_one_line(result.get('local_probe_executed_action_count'), limit=40)}
- local_probe_queued_approval_count: {_one_line(result.get('local_probe_queued_approval_count'), limit=40)}

## Research Handoff
- research_needed: {_bool_text(policy.get('research_needed'))}
- research_route: {_one_line(result.get('research_route'))}
- research_execution_level: {_one_line(result.get('research_execution_level'))}
- live_search_allowed: {_bool_text(result.get('live_search_allowed'))}
- codex_allowed: {_bool_text(result.get('codex_allowed'))}
- codex_cooldown_active: {_bool_text(result.get('codex_cooldown_active'))}
- codex_min_interval_seconds: {_one_line(result.get('codex_min_interval_seconds'), limit=40)}
- activation_permission: {_one_line(result.get('activation_permission'))}
- provider_results: {_one_line(result.get('provider_results'), limit=40)}
- codex_status: {_one_line(result.get('codex_status'))}

## Grants
- self_exploration_grant_present: {_bool_text(policy.get('grant_present'))}
- source_collect_grant_present: {_bool_text(policy.get('source_collect_grant_present'))}
- codex_research_grant_present: {_bool_text(policy.get('codex_research_grant_present'))}

## Boundaries
- local_low_risk_probe_only_without_write_side_effect: true
- source_provider_candidate_urls_only: true
- source_results_must_pass_existing_gates: true
- no_qq_message_from_self_exploration: true
- no_stable_memory_write: true
- no_raw_owner_text_in_state: true

## Notes
{notes}
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one autonomous self-exploration tick.")
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--evaluated-at", default="")
    parser.add_argument("--allow-live-search", action="store_true")
    parser.add_argument("--block-live-search", action="store_true")
    parser.add_argument("--allow-codex", action="store_true")
    parser.add_argument("--block-codex", action="store_true")
    parser.add_argument("--codex-min-interval-seconds", type=int, default=DEFAULT_CODEX_MIN_INTERVAL_SECONDS)
    parser.add_argument("--no-low-risk-execute", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    allow_live_search = None
    if args.allow_live_search:
        allow_live_search = True
    if args.block_live_search:
        allow_live_search = False
    allow_codex = None
    if args.allow_codex:
        allow_codex = True
    if args.block_codex:
        allow_codex = False
    result = run_autonomous_self_exploration_tick(
        args.root,
        evaluated_at=args.evaluated_at or None,
        allow_live_search=allow_live_search,
        allow_codex=allow_codex,
        execute_low_risk=not args.no_low_risk_execute,
        codex_min_interval_seconds=args.codex_min_interval_seconds,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(_render_state(result))
    return 0 if result.get("accepted") else 1


if __name__ == "__main__":
    raise SystemExit(main())

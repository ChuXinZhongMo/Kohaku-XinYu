from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from autonomous_search_activation_engine import run_autonomous_search_activation
from source_search_provider_engine import run_source_search_provider


STATE_REL = Path("memory/context/research_handoff_state.md")
TRACE_REL = Path("runtime/research_handoff_trace.jsonl")
SELF_THOUGHT_REL = Path("memory/context/self_thought_state.md")

CODEX_WINDOW_TITLE = "Xinyu codex"
EXECUTION_LEVELS = {"state_only", "activate", "execute", "execute_codex"}

_FIELD_RE = re.compile(r"(?m)^\s*-\s*([A-Za-z0-9_]+):\s*(.*?)\s*$")
_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\bauthorization\s*:\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\bapi[_-]?key\s*[:=]\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\btoken\s*[:=]\s*[a-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\bsk-[a-z0-9_-]{12,}"),
)


def run_research_handoff_loop(
    root: Path,
    *,
    evaluated_at: str | None = None,
    execution_level: str = "state_only",
    allow_live_search: bool = False,
    allow_codex: bool = False,
) -> dict[str, Any]:
    root = root.resolve()
    evaluated_at = evaluated_at or datetime.now().astimezone().isoformat()
    execution_level = _clean_token(execution_level)
    if execution_level not in EXECUTION_LEVELS:
        execution_level = "state_only"

    self_thought = _read_text(root / SELF_THOUGHT_REL)
    handoff = _handoff_from_self_thought(self_thought)
    notes: list[str] = []
    activation: dict[str, Any] = {}
    provider: dict[str, Any] = {}
    codex: dict[str, Any] = {}

    if handoff["research_needed"] != "true":
        status = "none"
        notes.append("no_research_handoff")
    elif handoff["route"] == "source_search_provider":
        status = _handle_source_route(
            root,
            evaluated_at=evaluated_at,
            execution_level=execution_level,
            allow_live_search=allow_live_search,
            activation=activation,
            provider=provider,
            notes=notes,
        )
    elif handoff["route"] == "codex_delegate_candidate":
        status = _handle_codex_route(
            root,
            evaluated_at=evaluated_at,
            execution_level=execution_level,
            allow_codex=allow_codex,
            handoff=handoff,
            codex=codex,
            notes=notes,
        )
    else:
        status = "blocked"
        notes.append("unknown_research_route")

    result = {
        "evaluated_at": evaluated_at,
        "status": status,
        "execution_level": execution_level,
        "allow_live_search": allow_live_search,
        "allow_codex": allow_codex,
        "handoff": handoff,
        "activation": activation,
        "provider": provider,
        "codex": codex,
        "notes": sorted(set(_clean_token(note) for note in notes if note)),
    }
    _write_text(root / STATE_REL, _render_state(result))
    _append_trace(root, result)
    return {
        "accepted": True,
        "status": status,
        "route": handoff["route"],
        "source_request_id": handoff["source_request_id"],
        "question_id": handoff["question_id"],
        "execution_level": execution_level,
        "activation_permission": _safe_str(activation.get("activation_permission"), "none"),
        "provider_results": int(provider.get("provider_results") or 0),
        "codex_status": _safe_str(codex.get("status"), "none"),
        "notes": result["notes"],
    }


def _handle_source_route(
    root: Path,
    *,
    evaluated_at: str,
    execution_level: str,
    allow_live_search: bool,
    activation: dict[str, Any],
    provider: dict[str, Any],
    notes: list[str],
) -> str:
    if execution_level == "state_only":
        notes.append("source_route_state_only")
        return "source_candidate"

    activation.update(
        run_autonomous_search_activation(
            root,
            evaluated_at=evaluated_at,
            mode="self_thought_research_handoff_activation",
        )
    )
    permission = _safe_str(activation.get("activation_permission"), "blocked")
    if execution_level != "execute":
        return "activation_ready" if permission == "provider_allowed" else "waiting_activation"

    if not allow_live_search:
        notes.append("live_search_not_allowed_for_this_pass")
        return "activation_ready" if permission == "provider_allowed" else "waiting_activation"
    if permission != "provider_allowed":
        notes.append("provider_blocked_by_activation")
        return "waiting_activation"

    provider.update(
        run_source_search_provider(
            root,
            searched_at=evaluated_at,
            mode="self_thought_research_handoff_provider",
            require_activation=True,
        )
    )
    if int(provider.get("provider_results") or 0) > 0:
        return "source_provider_completed"
    notes.append(_safe_str(provider.get("skipped_reason"), "provider_no_results"))
    return "source_provider_no_results"


def _handle_codex_route(
    root: Path,
    *,
    evaluated_at: str,
    execution_level: str,
    allow_codex: bool,
    handoff: dict[str, str],
    codex: dict[str, Any],
    notes: list[str],
) -> str:
    codex["status"] = "candidate"
    codex["visible_window_required"] = "true"
    codex["window_title"] = CODEX_WINDOW_TITLE
    codex["launch_permission"] = handoff["codex_launch_permission"]
    if handoff["codex_launch_permission"] != "owner_granted_state_gated":
        notes.append("codex_collect_not_granted")
        return "codex_blocked"
    if execution_level != "execute_codex" or not allow_codex:
        notes.append("codex_execute_not_requested")
        return "codex_candidate"

    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from xinyu_codex_delegate import run_codex_delegate

    payload = {
        "text": _codex_task_text(handoff),
        "source": "self_thought_research_handoff",
        "background": False,
        "auto_study": False,
        "visible_window": True,
        "window_title": CODEX_WINDOW_TITLE,
        "network_access": False,
        "timeout_seconds": 1800,
        "metadata": {
            "is_owner_user": True,
            "source": "self_thought_research_handoff",
            "codex_auxiliary_brain": True,
            "direct_cli_execution": False,
        },
        "job_id": "codex-self-thought-" + _timestamp_id(evaluated_at),
    }
    result = run_codex_delegate(root, payload)
    codex.update(
        {
            "status": "finished" if result.accepted and not result.timed_out else ("timed_out" if result.timed_out else "failed"),
            "accepted": result.accepted,
            "timed_out": result.timed_out,
            "exit_code": result.exit_code,
            "report_label": Path(result.report_path).name if result.report_path else "none",
            "notes": ",".join(result.notes[:8]),
        }
    )
    return "codex_completed" if result.accepted and not result.timed_out else "codex_not_completed"


def _handoff_from_self_thought(text: str) -> dict[str, str]:
    return {
        "research_needed": _extract_value(text, "research_needed", "false"),
        "route": _extract_value(text, "route", "none"),
        "handoff_target": _extract_value(text, "handoff_target", "none"),
        "source_request_id": _extract_value(text, "source_request_id", "none"),
        "question_id": _extract_value(text, "question_id", "none"),
        "target": _extract_value(text, "target", "none"),
        "query": _extract_value(text, "query", "none"),
        "execution_ceiling": _extract_value(text, "execution_ceiling", "none"),
        "codex_launch_permission": _extract_value(text, "codex_launch_permission", "none"),
        "memory_boundary": _extract_value(text, "memory_boundary", "none"),
    }


def _codex_task_text(handoff: dict[str, str]) -> str:
    return _one_line(
        "Use Codex auxiliary brain for this XinYu self-thought research collection task. "
        f"Question id: {handoff['question_id']}. Target: {handoff['target']}. "
        f"Query: {handoff['query']}. "
        "Inspect only the authorized project/local scope if needed, write a report only, "
        "and do not rewrite stable memory.",
        limit=1600,
    )


def _render_state(result: dict[str, Any]) -> str:
    handoff = result["handoff"]
    activation = result["activation"]
    provider = result["provider"]
    codex = result["codex"]
    notes = "\n".join(f"- {note}" for note in result["notes"]) or "- none"
    return f"""---
title: Research Handoff State
memory_type: research_handoff_state
time_scope: short_term
subject_ids: [xinyu]
protected: true
source: research_handoff_engine
updated_at: {_one_line(result['evaluated_at'])}
status: active
tags: [self-thought, research, source, codex, boundary]
---

# Research Handoff State

## Last Evaluation
- evaluated_at: {_one_line(result['evaluated_at'])}
- status: {_one_line(result['status'])}
- execution_level: {_one_line(result['execution_level'])}
- allow_live_search: {str(bool(result['allow_live_search'])).lower()}
- allow_codex: {str(bool(result['allow_codex'])).lower()}

## Handoff
- research_needed: {_one_line(handoff['research_needed'])}
- route: {_one_line(handoff['route'])}
- handoff_target: {_one_line(handoff['handoff_target'])}
- source_request_id: {_one_line(handoff['source_request_id'])}
- question_id: {_one_line(handoff['question_id'])}
- target: {_one_line(handoff['target'])}
- query: {_one_line(handoff['query'])}
- execution_ceiling: {_one_line(handoff['execution_ceiling'])}
- memory_boundary: {_one_line(handoff['memory_boundary'])}

## Source Route
- activation_permission: {_one_line(activation.get('activation_permission', 'none'))}
- activation_reason: {_one_line(activation.get('activation_reason', 'none'))}
- allowed_queries: {_one_line(activation.get('allowed_queries', '0'))}
- provider: {_one_line(provider.get('provider', 'none'))}
- pending_requests: {_one_line(provider.get('pending_requests', '0'))}
- provider_results: {_one_line(provider.get('provider_results', '0'))}
- provider_skipped_reason: {_one_line(provider.get('skipped_reason', 'none'))}

## Codex Route
- codex_launch_permission: {_one_line(handoff['codex_launch_permission'])}
- visible_codex_window_required: true
- codex_window_title: {CODEX_WINDOW_TITLE}
- codex_status: {_one_line(codex.get('status', 'none'))}
- codex_report_label: {_one_line(codex.get('report_label', 'none'))}

## Boundaries
- candidate_material_only: true
- no_stable_memory_write: true
- source_results_must_pass_existing_gates: true
- codex_must_use_visible_xinyu_window: true
- no_qq_message_from_research_handoff: true

## Notes
{notes}
"""


def _append_trace(root: Path, result: dict[str, Any]) -> None:
    payload = {
        "evaluated_at": result["evaluated_at"],
        "status": result["status"],
        "execution_level": result["execution_level"],
        "route": result["handoff"]["route"],
        "source_request_id": result["handoff"]["source_request_id"],
        "question_id": result["handoff"]["question_id"],
        "activation_permission": _safe_str(result["activation"].get("activation_permission"), "none"),
        "provider_results": int(result["provider"].get("provider_results") or 0),
        "codex_status": _safe_str(result["codex"].get("status"), "none"),
        "notes": result["notes"],
    }
    path = root / TRACE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def _read_text(path: Path) -> str:
    try:
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _extract_value(text: str, field: str, default: str = "none") -> str:
    for match in _FIELD_RE.finditer(text or ""):
        if match.group(1) == field:
            return _one_line(match.group(2)) or default
    return default


def _one_line(value: Any, *, limit: int = 240) -> str:
    text = "" if value is None else str(value)
    text = " ".join(text.replace("\r\n", "\n").replace("\r", "\n").split())
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("<secret>", text)
    if len(text) > limit:
        text = text[: max(0, limit - 3)].rstrip() + "..."
    return text


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _clean_token(value: Any) -> str:
    text = _one_line(value, limit=80).lower().replace(" ", "_")
    text = re.sub(r"[^a-z0-9_-]+", "_", text).strip("_")
    return text or "unknown"


def _timestamp_id(value: str) -> str:
    return re.sub(r"[^0-9A-Za-z]+", "", value)[:20] or str(int(time.time()))

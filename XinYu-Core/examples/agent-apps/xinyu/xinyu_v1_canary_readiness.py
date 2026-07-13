from __future__ import annotations


__all__ = (
    "TRACE_REL",
    "STATE_REL",
    "OWNER_CONFIG_REL",
)

import os
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_qq_outbox import enqueue_qq_outbox_message
from xinyu_v1_canary_readiness_store import append_v1_canary_trace_event
from xinyu_v1_canary_readiness_store import read_v1_canary_text
from xinyu_v1_canary_readiness_store import read_v1_owner_config
from xinyu_v1_canary_readiness_store import read_v1_shadow_observation_tail
from xinyu_v1_canary_readiness_store import v1_owner_config_path
from xinyu_v1_canary_readiness_store import write_v1_canary_text
from xinyu_v1_canary_readiness_store import OWNER_CONFIG_REL, STATE_REL, TRACE_REL



DEFAULT_MIN_SHADOW_TURNS = 100
DEFAULT_MAX_ERROR_RATE = 0.02
DEFAULT_MIN_ROUTE_DIVERSITY = 1
DEFAULT_WINDOW_TURNS = 200
DEFAULT_PROPOSAL_COOLDOWN_SECONDS = 24 * 60 * 60
QQ_PROPOSAL_ENV = "XINYU_V1_CANARY_QQ_PROPOSAL_ENABLED"

_FIELD_RE = re.compile(r"^\s*-\s*([A-Za-z0-9_]+):\s*(.*?)\s*$")
_FRONTMATTER_FIELD_RE = re.compile(r"^\s*([A-Za-z0-9_]+):\s*(.*?)\s*$")
_LOCAL_PATH_RE = re.compile(r"(?i)(?:[a-z]:\\|/users/|/home/|\\\\)[^\s<>'\"]+")
_LONG_NUMERIC_ID_RE = re.compile(r"\b\d{8,}\b")
_SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\bauthorization\s*:\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\bapi[_-]?key\s*[:=]\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\btoken\s*[:=]\s*[a-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\bsk-[a-z0-9_-]{12,}"),
)


@dataclass(frozen=True)
class CanaryThresholds:
    min_shadow_turns: int
    max_error_rate: float
    min_route_diversity: int
    window_turns: int
    proposal_cooldown_seconds: int


def record_v1_shadow_observation(
    root: Path,
    *,
    accepted: bool,
    route: str = "",
    trace_id: str = "",
    elapsed_ms: int = 0,
    error: str = "",
    payload: dict[str, Any] | None = None,
    observed_at: str | None = None,
) -> dict[str, Any]:
    """Record one v1 shadow turn and update review-only canary readiness.

    This intentionally does not flip any runtime routing flag. Owner-visible QQ
    proposals are disabled by default and require an explicit environment gate.
    """

    root = Path(root)
    observed = _timestamp_or_now_iso(observed_at)
    thresholds = _thresholds_from_env()
    event = {
        "event_kind": "v1_shadow_observation",
        "observed_at": observed,
        "accepted": bool(accepted),
        "route": _token(route, default="none"),
        "trace_id": _token(trace_id, default="none"),
        "elapsed_ms": max(0, _safe_int(elapsed_ms, 0)),
        "error": _compact(error, limit=220, default="none"),
        "turn_scope": _turn_scope(payload),
    }
    _append_jsonl(root / TRACE_REL, event)

    recent_rows, total_rows = _read_shadow_observation_tail(root / TRACE_REL, thresholds.window_turns)
    metrics = _summarize_shadow_rows(recent_rows, total_rows=total_rows, thresholds=thresholds)
    proposal = _proposal_default()
    if metrics["readiness_decision"] == "ready_for_owner_canary_request":
        proposal = _maybe_enqueue_owner_canary_proposal(root, metrics, thresholds, observed)
        if proposal.get("proposal_status") == "queued":
            _append_jsonl(
                root / TRACE_REL,
                {
                    "event_kind": "v1_canary_owner_proposal_queued",
                    "observed_at": observed,
                    "sample_window_turns": metrics["sample_window_turns"],
                    "error_rate": metrics["error_rate"],
                    "route_diversity": metrics["route_diversity"],
                },
            )

    state = _state_payload(metrics, proposal, thresholds, observed)
    _write_state(root / STATE_REL, state)
    notes = _notes_for_state(state)
    return {
        "accepted": True,
        "readiness_decision": state["readiness_decision"],
        "proposal_status": state["proposal_status"],
        "notes": notes,
    }


def _thresholds_from_env() -> CanaryThresholds:
    min_shadow_turns = max(1, _env_int("XINYU_V1_CANARY_MIN_SHADOW_TURNS", DEFAULT_MIN_SHADOW_TURNS))
    max_error_rate = min(1.0, max(0.0, _env_float("XINYU_V1_CANARY_MAX_ERROR_RATE", DEFAULT_MAX_ERROR_RATE)))
    min_route_diversity = max(1, _env_int("XINYU_V1_CANARY_MIN_ROUTE_DIVERSITY", DEFAULT_MIN_ROUTE_DIVERSITY))
    window_turns = max(
        min_shadow_turns,
        _env_int("XINYU_V1_CANARY_WINDOW_TURNS", max(DEFAULT_WINDOW_TURNS, min_shadow_turns)),
    )
    proposal_cooldown_seconds = max(
        0,
        _env_int("XINYU_V1_CANARY_PROPOSAL_COOLDOWN_SECONDS", DEFAULT_PROPOSAL_COOLDOWN_SECONDS),
    )
    return CanaryThresholds(
        min_shadow_turns=min_shadow_turns,
        max_error_rate=max_error_rate,
        min_route_diversity=min_route_diversity,
        window_turns=window_turns,
        proposal_cooldown_seconds=proposal_cooldown_seconds,
    )


def _summarize_shadow_rows(
    rows: list[dict[str, Any]],
    *,
    total_rows: int,
    thresholds: CanaryThresholds,
) -> dict[str, Any]:
    sample_count = len(rows)
    failure_rows = [row for row in rows if _row_failed(row)]
    success_count = sample_count - len(failure_rows)
    route_counts = Counter(
        _token(row.get("route"), default="none")
        for row in rows
        if not _row_failed(row) and _token(row.get("route"), default="none") != "none"
    )
    elapsed_values = [max(0, _safe_int(row.get("elapsed_ms"), 0)) for row in rows if _safe_int(row.get("elapsed_ms"), 0) >= 0]
    average_elapsed_ms = int(sum(elapsed_values) / len(elapsed_values)) if elapsed_values else 0
    error_rate = (len(failure_rows) / sample_count) if sample_count else 1.0
    latest = rows[-1] if rows else {}
    route_diversity = len(route_counts)

    if sample_count < thresholds.min_shadow_turns:
        decision = "collecting_shadow_sample"
        next_action = "keep_shadow_observing"
    elif error_rate > thresholds.max_error_rate:
        decision = "blocked_shadow_errors"
        next_action = "fix_shadow_errors_before_canary"
    elif route_diversity < thresholds.min_route_diversity:
        decision = "collecting_route_coverage"
        next_action = "keep_shadow_observing"
    else:
        decision = "ready_for_owner_canary_request"
        next_action = "ask_owner_for_canary"

    return {
        "readiness_decision": decision,
        "next_action": next_action,
        "total_shadow_turns": total_rows,
        "sample_window_turns": sample_count,
        "success_count": success_count,
        "error_count": len(failure_rows),
        "error_rate": f"{error_rate:.3f}",
        "route_diversity": route_diversity,
        "routes": _route_summary(route_counts),
        "average_elapsed_ms": average_elapsed_ms,
        "latest_route": _token(latest.get("route"), default="none"),
        "latest_trace_id": _token(latest.get("trace_id"), default="none"),
        "latest_error": _compact(latest.get("error"), limit=220, default="none"),
    }


def _maybe_enqueue_owner_canary_proposal(
    root: Path,
    metrics: dict[str, Any],
    thresholds: CanaryThresholds,
    observed_at: str,
) -> dict[str, str]:
    previous = _read_state_fields(root / STATE_REL)
    last_proposal_at = previous.get("last_proposal_at", "")
    if not _canary_qq_proposal_enabled():
        return {
            "proposal_status": "held_review_only",
            "proposal_message_id": "none",
            "last_proposal_at": last_proposal_at or "none",
            "proposal_notes": f"{QQ_PROPOSAL_ENV}=false",
        }

    age = _age_seconds(last_proposal_at, now_text=observed_at)
    if age is not None and age < thresholds.proposal_cooldown_seconds:
        return {
            "proposal_status": "cooldown",
            "proposal_message_id": previous.get("proposal_message_id", "none") or "none",
            "last_proposal_at": last_proposal_at,
            "proposal_notes": "cooldown",
        }

    owner_user_id, owner_notes = _owner_user_id(root)
    if not owner_user_id:
        return {
            "proposal_status": "owner_config_missing",
            "proposal_message_id": "none",
            "last_proposal_at": last_proposal_at or "none",
            "proposal_notes": ",".join(owner_notes) or "missing_owner_user_id",
        }

    day_key = _proposal_day_key(observed_at)
    message = (
        "v1 旁路观察已经稳定："
        f"最近 {metrics['sample_window_turns']} 轮，错误率 {float(metrics['error_rate']) * 100:.1f}%，"
        f"平均 {metrics['average_elapsed_ms']}ms。"
        "要不要把 owner 私聊里的简单消息先切到 v1 小范围试运行？我不会自己全量切。"
    )
    result = enqueue_qq_outbox_message(
        root,
        user_id=owner_user_id,
        message=message,
        source="v1_canary_readiness",
        dedupe_key=f"v1-canary-owner-proposal-{day_key}",
        metadata={
            "readiness_decision": metrics["readiness_decision"],
            "switch_permission": "owner_approval_required",
            "sample_window_turns": metrics["sample_window_turns"],
            "error_rate": metrics["error_rate"],
            "route_diversity": metrics["route_diversity"],
        },
    )
    result_notes = [_compact(note, limit=80, default="none") for note in result.get("notes", [])]
    status = "queued" if result.get("queued") else "not_queued"
    if "duplicate_dedupe_key" in result_notes:
        status = "duplicate"
    if not result.get("accepted"):
        status = "rejected"
    proposal_at = observed_at if status in {"queued", "duplicate"} else (last_proposal_at or "none")
    return {
        "proposal_status": status,
        "proposal_message_id": _token(result.get("message_id"), default="none"),
        "last_proposal_at": proposal_at,
        "proposal_notes": ",".join(result_notes) or "none",
    }


def _proposal_default() -> dict[str, str]:
    return {
        "proposal_status": "not_due",
        "proposal_message_id": "none",
        "last_proposal_at": "none",
        "proposal_notes": "readiness_not_met",
    }


def _state_payload(
    metrics: dict[str, Any],
    proposal: dict[str, str],
    thresholds: CanaryThresholds,
    observed_at: str,
) -> dict[str, Any]:
    state = {
        "updated_at": observed_at,
        "status": "active",
        "switch_permission": "owner_approval_required",
        "shadow_mode_required": "true",
        "auto_full_switch": "false",
        "canary_scope": "owner_private_simple_messages_only",
        "proposal_qq_outbox_enabled": "true" if _canary_qq_proposal_enabled() else "false",
        "min_shadow_turns": thresholds.min_shadow_turns,
        "max_error_rate": f"{thresholds.max_error_rate:.3f}",
        "min_route_diversity": thresholds.min_route_diversity,
        "window_turns": thresholds.window_turns,
        "proposal_cooldown_seconds": thresholds.proposal_cooldown_seconds,
    }
    state.update(metrics)
    state.update(proposal)
    if state.get("readiness_decision") == "ready_for_owner_canary_request":
        if state.get("proposal_status") == "held_review_only":
            state["next_action"] = "review_readiness_locally_no_outbox"
        elif state.get("proposal_status") == "queued":
            state["next_action"] = "await_owner_canary_decision"
    return state


def _write_state(path: Path, state: dict[str, Any]) -> None:
    lines = [
        "---",
        "title: V1 Canary Readiness State",
        "memory_type: runtime_program_state",
        "time_scope: immediate_runtime",
        "subject_ids: [xinyu, xinyu_v1]",
        "protected: true",
        "source: xinyu_v1_canary_readiness",
        f"updated_at: {_timestamp_or_now_iso(state.get('updated_at'))}",
        "status: active",
        "tags: [runtime, v1, shadow, canary]",
        "---",
        "",
        "# V1 Canary Readiness State",
        "",
        "## Current Decision",
    ]
    ordered_keys = (
        "readiness_decision",
        "switch_permission",
        "shadow_mode_required",
        "auto_full_switch",
        "canary_scope",
        "proposal_qq_outbox_enabled",
        "proposal_status",
        "proposal_message_id",
        "last_proposal_at",
        "proposal_notes",
        "next_action",
        "total_shadow_turns",
        "sample_window_turns",
        "success_count",
        "error_count",
        "error_rate",
        "route_diversity",
        "routes",
        "average_elapsed_ms",
        "latest_route",
        "latest_trace_id",
        "latest_error",
        "min_shadow_turns",
        "max_error_rate",
        "min_route_diversity",
        "window_turns",
        "proposal_cooldown_seconds",
    )
    for key in ordered_keys:
        lines.append(f"- {key}: {_compact(state.get(key), limit=320, default='none')}")
    lines.extend(
        [
            "",
            "## Boundary",
            "- v1 remains shadow-only until owner approval is explicit.",
            f"- QQ owner proposals require {QQ_PROPOSAL_ENV}=true; default readiness is local review only.",
            "- This state must not edit runtime routing flags.",
            "- Full switch is outside this gate; only owner-private simple-message canary is proposed.",
            "",
        ]
    )
    _atomic_write_text(path, "\n".join(lines))


def _notes_for_state(state: dict[str, Any]) -> list[str]:
    decision = _token(state.get("readiness_decision"), default="unknown")
    proposal = _token(state.get("proposal_status"), default="unknown")
    notes = [f"v1_canary_decision:{decision}"]
    if decision == "collecting_shadow_sample":
        notes.append(f"v1_canary_collecting:{state.get('sample_window_turns')}/{state.get('min_shadow_turns')}")
    elif decision == "blocked_shadow_errors":
        notes.append(f"v1_canary_blocked_error_rate:{state.get('error_rate')}")
    elif decision == "ready_for_owner_canary_request":
        notes.append("v1_canary_ready_owner_review_required")
        if proposal == "held_review_only":
            notes.append("v1_canary_no_qq_outbox_default")
    if proposal != "not_due":
        notes.append(f"v1_canary_proposal:{proposal}")
    return notes


def _read_shadow_observation_tail(path: Path, limit: int) -> tuple[list[dict[str, Any]], int]:
    return read_v1_shadow_observation_tail(path, limit)


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    clean = _clean_json_value(row)
    append_v1_canary_trace_event(path, clean)


def _atomic_write_text(path: Path, text: str) -> None:
    write_v1_canary_text(path, _scrub(text))


def _clean_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {_safe_str(key): _clean_json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_clean_json_value(item) for item in value]
    if isinstance(value, tuple):
        return [_clean_json_value(item) for item in value]
    if isinstance(value, str):
        return _scrub(value)
    return value


def _read_state_fields(path: Path) -> dict[str, str]:
    fields: dict[str, str] = {}
    text = read_v1_canary_text(path)
    if not text:
        return fields
    for line in text.splitlines():
        match = _FIELD_RE.match(line)
        if not match:
            match = _FRONTMATTER_FIELD_RE.match(line)
        if not match:
            continue
        fields[match.group(1)] = _compact(match.group(2), limit=320, default="")
    return fields


def _owner_user_id(root: Path) -> tuple[str, list[str]]:
    for key in ("XINYU_OWNER_USER_IDS", "XINYU_OWNER_QQ"):
        for candidate in re.split(r"[,;\s]+", os.environ.get(key, "")):
            text = _owner_id_candidate(candidate)
            if text and text.lower() != "none":
                return text, []

    config_path = v1_owner_config_path(root)
    status, raw = read_v1_owner_config(config_path)
    if status == "not_found":
        return "", ["owner_config_not_found"]
    if status != "ok":
        return "", ["owner_config_unreadable"]
    if not isinstance(raw, dict):
        return "", ["owner_config_invalid"]
    for key in ("owner_user_ids", "whitelist_user_ids"):
        value = raw.get(key)
        candidates = value if isinstance(value, list) else [value]
        for item in candidates:
            user_id = _owner_id_candidate(item)
            if user_id and user_id.lower() != "none":
                return user_id, []
    return "", ["missing_owner_user_id"]


def _turn_scope(payload: dict[str, Any] | None) -> str:
    data = payload if isinstance(payload, dict) else {}
    metadata = data.get("metadata")
    meta = metadata if isinstance(metadata, dict) else {}
    if _as_bool(meta.get("is_owner_user"), default=False):
        return "owner_private"
    if _safe_str(data.get("group_id")).strip() or _safe_str(data.get("message_type")).lower().startswith("group"):
        return "group"
    if _safe_str(data.get("user_id")).strip():
        return "private"
    return "unknown"


def _row_failed(row: dict[str, Any]) -> bool:
    if not _as_bool(row.get("accepted"), default=False):
        return True
    error = _safe_str(row.get("error"), "none").strip().lower()
    return error not in {"", "none", "ok", "false", "0"}


def _route_summary(route_counts: Counter[str]) -> str:
    if not route_counts:
        return "none"
    return ",".join(f"{route}={count}" for route, count in sorted(route_counts.items()))


def _proposal_day_key(observed_at: str) -> str:
    parsed = _parse_iso(observed_at)
    return (parsed or datetime.now().astimezone()).strftime("%Y%m%d")


def _age_seconds(then_text: str, *, now_text: str) -> float | None:
    then = _parse_iso(then_text)
    now = _parse_iso(now_text)
    if then is None or now is None:
        return None
    return max(0.0, (now - then).total_seconds())


def _parse_iso(value: Any) -> datetime | None:
    text = _safe_str(value).strip()
    if not text or text.lower() == "none":
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.astimezone()
    return parsed


def _env_int(name: str, default: int) -> int:
    try:
        return int(_safe_str(os.environ.get(name), str(default)).strip())
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(_safe_str(os.environ.get(name), str(default)).strip())
    except ValueError:
        return default


def _canary_qq_proposal_enabled() -> bool:
    return _as_bool(os.environ.get(QQ_PROPOSAL_ENV), default=False)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = _safe_str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _timestamp_or_now_iso(value: Any) -> str:
    text = _safe_str(value).strip()
    if text:
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            parsed = None
        if parsed is not None:
            return parsed.astimezone().isoformat(timespec="seconds")
    return _now_iso()


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _owner_id_candidate(value: Any) -> str:
    return re.sub(r"\s+", "", _safe_str(value)).strip()[:64]


def _token(value: Any, *, default: str = "none", limit: int = 80) -> str:
    text = _compact(value, limit=limit, default=default)
    text = re.sub(r"[^A-Za-z0-9_.:-]+", "_", text).strip("_")
    return text or default


def _compact(value: Any, *, limit: int = 220, default: str = "none") -> str:
    text = re.sub(r"\s+", " ", _safe_str(value)).strip()
    text = _scrub(text)
    if not text:
        return default
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _scrub(value: Any) -> str:
    text = _safe_str(value)
    text = _LOCAL_PATH_RE.sub("[local-path]", text)
    text = _LONG_NUMERIC_ID_RE.sub("[id]", text)
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("[secret]", text)
    return text

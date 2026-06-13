from __future__ import annotations

import asyncio
import hashlib
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

from xinyu_early_visible_segment_store import append_early_visible_segment_shadow_trace
from xinyu_early_visible_segment_store import read_recent_early_visible_segment_shadow_rows
from xinyu_early_visible_segment_store import write_early_visible_segment_shadow_state


TRACE_REL = Path("runtime/early_visible_segment_shadow.jsonl")
STATE_REL = Path("memory/context/early_visible_segment_shadow_state.md")
SUMMARY_WINDOW_ROWS = 200
MIN_CANARY_REVIEW_ELIGIBLE = 20
CANARY_REVIEW_ACCEPTANCE_RATE_PCT = 70

TERMINATORS = ".!?\n\u3002\uff01\uff1f\uff1b\u2026"
SOFT_BREAKS = ",;\uff0c\uff1b"
MAX_SEGMENT_CHARS = 96
MIN_MEANINGFUL_CHARS = 3

LOW_INFORMATION_PHRASES = {
    "\u55ef",
    "\u554a",
    "\u597d",
    "\u597d\u7684",
    "\u6536\u5230",
    "\u660e\u767d",
    "\u61c2\u4e86",
    "\u77e5\u9053\u4e86",
    "\u6211\u5728",
    "\u6211\u5728\u60f3",
    "\u6211\u61c2",
}

GENERIC_PREFIXES = (
    "\u6536\u5230",
    "\u6211\u5728",
    "\u6211\u660e\u767d",
    "\u6211\u7406\u89e3",
    "\u6211\u5148",
    "\u5148\u522b\u8ba9\u4f60",
)

MECHANIC_MARKERS = (
    "runtime",
    "core",
    "bridge",
    "prompt",
    "system",
    "sidecar",
    "outbox",
    "\u540e\u53f0",
    "\u7cfb\u7edf",
    "\u6a21\u578b",
    "\u94fe\u8def",
    "\u5de5\u5177\u8c03\u7528",
    "\u6b63\u5728\u751f\u6210",
    "\u6b63\u5728\u56de\u590d",
)

REPORTISH_MARKERS = (
    "\u6211\u4f1a\u8c03\u6574",
    "\u6211\u4f1a\u6539",
    "\u6211\u4f1a\u6ce8\u610f",
    "\u611f\u8c22\u53cd\u9988",
    "\u4f5c\u4e3a",
    "\u5bf9\u4e0d\u8d77",
    "\u62b1\u6b49",
)


@dataclass(frozen=True)
class EarlyVisibleSegmentDecision:
    status: str
    segment: str = ""
    elapsed_ms: int = 0
    observed_chars: int = 0
    reasons: tuple[str, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def accepted_shadow(self) -> bool:
        return self.status == "accepted_shadow"


def extract_first_natural_segment(text: str, *, max_chars: int = MAX_SEGMENT_CHARS) -> str:
    normalized = _compact_visible_text(text)
    if not normalized:
        return ""

    for index, char in enumerate(normalized):
        if char not in TERMINATORS:
            continue
        end = index + 1
        while end < len(normalized) and normalized[end] in TERMINATORS:
            end += 1
        candidate = normalized[:end].strip()
        if len(candidate) <= max_chars:
            return candidate
        return ""

    for index, char in enumerate(normalized):
        if char not in SOFT_BREAKS:
            continue
        candidate = normalized[: index + 1].strip()
        if MIN_MEANINGFUL_CHARS <= len(_semantic_core(candidate)) <= max_chars // 2:
            return candidate
    return ""


def evaluate_early_visible_segment(
    user_text: str,
    segment: str,
    *,
    visible_turn: Any | None = None,
) -> EarlyVisibleSegmentDecision:
    del visible_turn
    normalized = _compact_visible_text(segment)
    reasons: list[str] = []
    if not normalized:
        return EarlyVisibleSegmentDecision(status="no_candidate", reasons=("empty_segment",))

    semantic = _semantic_core(normalized)
    if len(semantic) < MIN_MEANINGFUL_CHARS:
        reasons.append("too_short_or_empty")
    if semantic in LOW_INFORMATION_PHRASES:
        reasons.append("low_information_phrase")
    if any(normalized.startswith(prefix) for prefix in GENERIC_PREFIXES):
        reasons.append("generic_presence_or_meta_prefix")

    lowered = normalized.lower()
    mechanic_hits = [marker for marker in MECHANIC_MARKERS if marker.lower() in lowered]
    if mechanic_hits:
        reasons.append("mechanic_or_backend_leak")
    if any(marker in normalized for marker in REPORTISH_MARKERS):
        reasons.append("reportish_or_apology_marker")
    if len(normalized) > MAX_SEGMENT_CHARS:
        reasons.append("too_long_for_early_segment")
    if _looks_like_repeating_user_text(user_text, normalized):
        reasons.append("echoes_user_text")

    if reasons:
        return EarlyVisibleSegmentDecision(
            status="rejected_shadow",
            segment=normalized,
            reasons=tuple(dict.fromkeys(reasons)),
        )
    return EarlyVisibleSegmentDecision(
        status="accepted_shadow",
        segment=normalized,
        reasons=(),
        notes=("specific_first_segment_candidate",),
    )


async def observe_early_visible_segment_shadow(
    root: Path | str,
    chunks: Sequence[str],
    *,
    payload: dict[str, Any],
    user_text: str,
    turn_id: str,
    session_key: str = "",
    visible_turn: Any | None = None,
    started_monotonic: float = 0.0,
    stop_event: asyncio.Event | None = None,
    poll_seconds: float = 0.05,
    max_observe_seconds: float = 30.0,
) -> EarlyVisibleSegmentDecision:
    if not _payload_allows_shadow(payload):
        decision = EarlyVisibleSegmentDecision(status="not_eligible", reasons=("not_owner_private_or_local_regression",))
        _record_shadow(root, decision, payload=payload, user_text=user_text, turn_id=turn_id, session_key=session_key)
        return decision

    loop = asyncio.get_running_loop()
    start = started_monotonic or loop.time()
    stop = stop_event or asyncio.Event()
    latest_text = ""
    while True:
        latest_text = "".join(chunks)
        segment = extract_first_natural_segment(latest_text)
        if segment:
            decision = evaluate_early_visible_segment(user_text, segment, visible_turn=visible_turn)
            decision = _with_observation(decision, elapsed_ms=_elapsed_ms(loop.time(), start), observed_text=latest_text)
            _record_shadow(root, decision, payload=payload, user_text=user_text, turn_id=turn_id, session_key=session_key)
            return decision
        if stop.is_set():
            break
        if loop.time() - start >= max_observe_seconds:
            break
        await asyncio.sleep(max(0.01, poll_seconds))

    final_segment = extract_first_natural_segment(latest_text)
    if final_segment:
        decision = evaluate_early_visible_segment(user_text, final_segment, visible_turn=visible_turn)
    else:
        decision = EarlyVisibleSegmentDecision(status="no_candidate", reasons=("no_natural_segment_observed",))
    decision = _with_observation(decision, elapsed_ms=_elapsed_ms(loop.time(), start), observed_text=latest_text)
    _record_shadow(root, decision, payload=payload, user_text=user_text, turn_id=turn_id, session_key=session_key)
    return decision


def summarize_early_visible_segment_shadow(
    root: Path | str,
    *,
    max_rows: int = SUMMARY_WINDOW_ROWS,
) -> dict[str, Any]:
    rows = _read_recent_shadow_rows(Path(root), max_rows=max_rows)
    if not rows:
        return {
            "status": "no_data",
            "checked_at": "",
            "latest_status": "none",
            "window_rows": 0,
            "eligible_count": 0,
            "accepted_shadow_count": 0,
            "rejected_shadow_count": 0,
            "no_candidate_count": 0,
            "not_eligible_count": 0,
            "acceptance_rate_pct": 0,
            "avg_elapsed_ms": 0,
            "p95_elapsed_ms": 0,
            "avg_segment_chars": 0,
            "top_reasons": [],
            "privacy_violation_count": 0,
            "raw_user_text_saved": False,
            "raw_segment_saved": False,
            "behavior_change": "none_shadow_only",
            "canary_readiness": "collect_more_shadow",
            "next_action": "collect_shadow_observations",
        }

    latest = rows[-1]
    status_counts = Counter(_safe_str(row.get("status"), "unknown") for row in rows)
    reason_counts: Counter[str] = Counter()
    elapsed_values: list[int] = []
    segment_char_values: list[int] = []
    privacy_violation_count = 0
    for row in rows:
        elapsed_values.append(_safe_int(row.get("elapsed_ms"), 0))
        segment_char_values.append(_safe_int(row.get("segment_chars"), 0))
        reasons = row.get("reasons")
        if isinstance(reasons, list):
            reason_counts.update(_safe_str(item) for item in reasons if _safe_str(item))
        if row.get("raw_user_text_saved") is not False or row.get("raw_segment_saved") is not False:
            privacy_violation_count += 1

    accepted_count = status_counts["accepted_shadow"]
    rejected_count = status_counts["rejected_shadow"]
    no_candidate_count = status_counts["no_candidate"]
    not_eligible_count = status_counts["not_eligible"]
    eligible_count = accepted_count + rejected_count + no_candidate_count
    acceptance_rate_pct = int(round((accepted_count / eligible_count) * 100)) if eligible_count else 0
    canary_readiness = _canary_readiness(
        eligible_count=eligible_count,
        acceptance_rate_pct=acceptance_rate_pct,
        privacy_violation_count=privacy_violation_count,
        reason_counts=reason_counts,
    )

    return {
        "status": "privacy_blocked" if privacy_violation_count else "shadow_observing",
        "checked_at": _safe_str(latest.get("checked_at")),
        "latest_status": _safe_str(latest.get("status"), "unknown"),
        "window_rows": len(rows),
        "eligible_count": eligible_count,
        "accepted_shadow_count": accepted_count,
        "rejected_shadow_count": rejected_count,
        "no_candidate_count": no_candidate_count,
        "not_eligible_count": not_eligible_count,
        "acceptance_rate_pct": acceptance_rate_pct,
        "avg_elapsed_ms": _average_int(elapsed_values),
        "p95_elapsed_ms": _percentile_int(elapsed_values, 95),
        "avg_segment_chars": _average_int(segment_char_values),
        "top_reasons": [f"{reason}:{count}" for reason, count in reason_counts.most_common(5)],
        "privacy_violation_count": privacy_violation_count,
        "raw_user_text_saved": False,
        "raw_segment_saved": False,
        "behavior_change": "none_shadow_only",
        "canary_readiness": canary_readiness,
        "next_action": _next_action_for_readiness(canary_readiness),
    }


def _with_observation(
    decision: EarlyVisibleSegmentDecision,
    *,
    elapsed_ms: int,
    observed_text: str,
) -> EarlyVisibleSegmentDecision:
    return EarlyVisibleSegmentDecision(
        status=decision.status,
        segment=decision.segment,
        elapsed_ms=elapsed_ms,
        observed_chars=len(_compact_visible_text(observed_text)),
        reasons=decision.reasons,
        notes=decision.notes,
    )


def _record_shadow(
    root: Path | str,
    decision: EarlyVisibleSegmentDecision,
    *,
    payload: dict[str, Any],
    user_text: str,
    turn_id: str,
    session_key: str,
) -> None:
    try:
        root_path = Path(root)
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        row = {
            "event_kind": "early_visible_segment_shadow",
            "checked_at": now,
            "turn_id_hash": _hash_text(turn_id),
            "session_key_hash": _hash_text(session_key),
            "user_text_hash": _hash_text(user_text),
            "status": decision.status,
            "accepted_shadow": decision.accepted_shadow,
            "elapsed_ms": decision.elapsed_ms,
            "observed_chars": decision.observed_chars,
            "segment_hash": _hash_text(decision.segment),
            "segment_chars": len(decision.segment),
            "reasons": list(decision.reasons),
            "notes": list(decision.notes),
            "raw_user_text_saved": False,
            "raw_segment_saved": False,
            "message_type": _safe_str(payload.get("message_type"))[:80],
            "platform": _safe_str(payload.get("platform"))[:80],
        }
        append_early_visible_segment_shadow_trace(root_path / TRACE_REL, row)
        _write_state(root_path)
    except Exception:
        return


def _write_state(root: Path) -> None:
    summary = summarize_early_visible_segment_shadow(root)
    reasons_text = ", ".join(_safe_str(item) for item in summary.get("top_reasons", []) or []) or "none"
    lines = [
        "---",
        "memory_type: early_visible_segment_shadow_state",
        "updated_at: " + (_safe_str(summary.get("checked_at")) or datetime.now().astimezone().isoformat(timespec="seconds")),
        "privacy: hash_and_counts_only",
        "---",
        "",
        "# Early Visible Segment Shadow",
        "",
        "- status: " + _safe_str(summary.get("status"), "unknown"),
        "- checked_at: " + _safe_str(summary.get("checked_at")),
        "- latest_status: " + _safe_str(summary.get("latest_status"), "unknown"),
        "- window_rows: " + str(_safe_int(summary.get("window_rows"), 0)),
        "- eligible_count: " + str(_safe_int(summary.get("eligible_count"), 0)),
        "- accepted_shadow_count: " + str(_safe_int(summary.get("accepted_shadow_count"), 0)),
        "- rejected_shadow_count: " + str(_safe_int(summary.get("rejected_shadow_count"), 0)),
        "- no_candidate_count: " + str(_safe_int(summary.get("no_candidate_count"), 0)),
        "- not_eligible_count: " + str(_safe_int(summary.get("not_eligible_count"), 0)),
        "- acceptance_rate_pct: " + str(_safe_int(summary.get("acceptance_rate_pct"), 0)),
        "- avg_elapsed_ms: " + str(_safe_int(summary.get("avg_elapsed_ms"), 0)),
        "- p95_elapsed_ms: " + str(_safe_int(summary.get("p95_elapsed_ms"), 0)),
        "- avg_segment_chars: " + str(_safe_int(summary.get("avg_segment_chars"), 0)),
        "- top_reasons: " + reasons_text,
        "- privacy_violation_count: " + str(_safe_int(summary.get("privacy_violation_count"), 0)),
        "- raw_user_text_saved: false",
        "- raw_segment_saved: false",
        "- behavior_change: none_shadow_only",
        "- canary_readiness: " + _safe_str(summary.get("canary_readiness"), "collect_more_shadow"),
        "- next_action: " + _safe_str(summary.get("next_action"), "collect_shadow_observations"),
        "",
        "This is shadow-only evidence for possible first natural segment delivery.",
    ]
    write_early_visible_segment_shadow_state(root / STATE_REL, "\n".join(lines))


def _read_recent_shadow_rows(root: Path, *, max_rows: int) -> list[dict[str, Any]]:
    return read_recent_early_visible_segment_shadow_rows(root / TRACE_REL, max_rows=max_rows)


def _canary_readiness(
    *,
    eligible_count: int,
    acceptance_rate_pct: int,
    privacy_violation_count: int,
    reason_counts: Counter[str],
) -> str:
    if privacy_violation_count:
        return "blocked_privacy_flags"
    if eligible_count < MIN_CANARY_REVIEW_ELIGIBLE:
        return "collect_more_shadow"
    if reason_counts.get("mechanic_or_backend_leak", 0) > 0:
        return "hold_mechanic_leak_observed"
    if acceptance_rate_pct < CANARY_REVIEW_ACCEPTANCE_RATE_PCT:
        return "hold_low_acceptance_rate"
    return "ready_for_owner_private_canary_review"


def _next_action_for_readiness(readiness: str) -> str:
    if readiness == "ready_for_owner_private_canary_review":
        return "review_aggregate_shadow_before_owner_private_canary"
    if readiness.startswith("hold_") or readiness.startswith("blocked_"):
        return "tighten_rejection_rules_before_any_send"
    return "collect_shadow_observations"


def _payload_allows_shadow(payload: dict[str, Any]) -> bool:
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    if bool(metadata.get("local_regression_baseline")):
        return True
    if not bool(metadata.get("is_owner_user")):
        return False
    message_type = _safe_str(payload.get("message_type") or metadata.get("message_type")).lower()
    session_id = _safe_str(payload.get("session_id") or metadata.get("session_id")).lower()
    if "private" in message_type or session_id.startswith("qq:private:"):
        return True
    return False


def _compact_visible_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", _safe_str(text)).strip()
    return cleaned.strip("\"'` \t\r\n")


def _semantic_core(text: str) -> str:
    cleaned = re.sub(r"[\s.!?,;:\-_'\"`\u3002\uff01\uff1f\uff0c\uff1b\uff1a\u2026]+", "", _safe_str(text))
    return cleaned.strip()


def _looks_like_repeating_user_text(user_text: str, segment: str) -> bool:
    user_core = _semantic_core(user_text)
    segment_core = _semantic_core(segment)
    if len(user_core) < 6 or len(segment_core) < 6:
        return False
    return segment_core in user_core or user_core in segment_core


def _hash_text(text: str) -> str:
    text = _safe_str(text)
    if not text:
        return ""
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _elapsed_ms(now: float, start: float) -> int:
    return max(0, int((now - start) * 1000))


def _average_int(values: Sequence[int]) -> int:
    if not values:
        return 0
    return int(round(sum(values) / len(values)))


def _percentile_int(values: Sequence[int], pct: int) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = int(round(((max(0, min(100, pct)) / 100) * (len(ordered) - 1))))
    return ordered[max(0, min(len(ordered) - 1, index))]


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(_safe_str(value)))
    except (TypeError, ValueError):
        return default


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)

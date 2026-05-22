from __future__ import annotations

import asyncio
import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

from state_service import append_jsonl, atomic_write_text


TRACE_REL = Path("runtime/early_visible_segment_shadow.jsonl")
STATE_REL = Path("memory/context/early_visible_segment_shadow_state.md")

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
        append_jsonl(root_path / TRACE_REL, row)
        _write_state(root_path, row)
    except Exception:
        return


def _write_state(root: Path, row: dict[str, Any]) -> None:
    reasons_text = ", ".join(_safe_str(item) for item in row.get("reasons", []) or []) or "none"
    lines = [
        "---",
        "memory_type: early_visible_segment_shadow_state",
        "updated_at: " + _safe_str(row.get("checked_at")),
        "privacy: hash_and_counts_only",
        "---",
        "",
        "# Early Visible Segment Shadow",
        "",
        "- status: " + _safe_str(row.get("status"), "unknown"),
        "- accepted_shadow: " + str(bool(row.get("accepted_shadow"))).lower(),
        "- elapsed_ms: " + str(int(row.get("elapsed_ms") or 0)),
        "- observed_chars: " + str(int(row.get("observed_chars") or 0)),
        "- segment_chars: " + str(int(row.get("segment_chars") or 0)),
        "- reasons: " + reasons_text,
        "- raw_user_text_saved: false",
        "- raw_segment_saved: false",
        "",
        "This is shadow-only evidence for possible first natural segment delivery.",
    ]
    atomic_write_text(root / STATE_REL, "\n".join(lines))


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


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)

from __future__ import annotations

import hashlib
import re
from collections import Counter
from typing import Any


ACTIVE_REVIEW_STATUSES = {
    "pending",
    "owner_review_required",
    "self_approved_recent_context",
    "self_approved_voice_review",
    "observe_more_owner_preference",
    "observe_more_relationship_signal",
    "observe_more_unknown",
    "approved",
}

NEGATIVE_MARKERS = (
    "do not",
    "don't",
    "dont",
    "never",
    "avoid",
    "disable",
    "dislike",
    "dislikes",
    "not ",
    "no ",
    "off",
    "\u4e0d\u8981",
    "\u522b",
    "\u4e0d\u559c\u6b22",
    "\u4e0d\u60f3",
    "\u7981\u6b62",
    "\u7981\u7528",
    "\u5173\u95ed",
    "\u4e0d\u9700\u8981",
    "\u4e0d\u7528",
)

POSITIVE_MARKERS = (
    "prefers",
    "prefer",
    "likes",
    "like",
    "wants",
    "want",
    "remember",
    "use",
    "enable",
    "allow",
    "keep",
    "yes",
    "on",
    "\u559c\u6b22",
    "\u5e0c\u671b",
    "\u60f3",
    "\u9700\u8981",
    "\u8bb0\u4f4f",
    "\u53ef\u4ee5",
    "\u542f\u7528",
    "\u5f00\u542f",
    "\u5141\u8bb8",
    "\u4fdd\u7559",
)

STOP_WORDS = {
    "a",
    "an",
    "and",
    "be",
    "candidate",
    "do",
    "does",
    "fact",
    "for",
    "i",
    "me",
    "memory",
    "my",
    "not",
    "owner",
    "please",
    "project",
    "reply",
    "should",
    "that",
    "the",
    "this",
    "to",
    "turn",
    "visible",
    "with",
    "xinyu",
}

STOP_MARKERS = (
    "owner_turn",
    "visible_reply",
    "owner preference candidate",
    "project fact candidate",
    "relationship signal candidate",
    "voice correction candidate",
    "stable voice rewrite blocked",
    "temporary mood must not become stable",
    "not a fixed owner label",
    "keep separate from relationship memory",
    "learning gate still authoritative",
    "\u6211",
    "\u4f60",
    "\u5979",
    "\u5b83",
    "\u8bb0\u4f4f",
    "\u559c\u6b22",
    "\u4e0d\u559c\u6b22",
    "\u4e0d\u8981",
    "\u522b",
)


def candidate_claim_metadata(
    *,
    candidate_type: str,
    target_memory_layer: str,
    source_scope: str,
    candidate_text: str,
) -> dict[str, Any]:
    claim_text = _claim_source_text(candidate_text)
    polarity = _claim_polarity(claim_text)
    topic_basis = _topic_basis(claim_text)
    scope = _safe_str(source_scope).strip() or "unknown"
    ctype = _safe_str(candidate_type).strip() or "unknown"
    layer = _safe_str(target_memory_layer).strip().replace("\\", "/") or "unknown"
    topic_seed = f"{ctype}|{layer}|{scope}|{topic_basis}"
    topic_key = _hash(topic_seed, length=18)
    claim_key = _hash(f"{topic_key}|{polarity}", length=18)
    return {
        "claim_key": claim_key,
        "claim_topic_key": topic_key,
        "claim_polarity": polarity,
        "claim_text_hash": _hash(claim_text, length=24),
        "claim_basis_hash": _hash(topic_basis, length=24),
        "claim_basis_token_count": len(_tokens(topic_basis)),
    }


def candidate_claim_metadata_from_row(row: dict[str, Any]) -> dict[str, Any]:
    evidence = _dict_field(row, "evidence")
    provenance = _dict_field(row, "provenance")
    source_scope = (
        _safe_str(evidence.get("source_scope"))
        or _safe_str(provenance.get("dialogue_scope"))
        or _scope_from_flags(row.get("risk_flags", []))
    )
    return candidate_claim_metadata(
        candidate_type=_safe_str(row.get("candidate_type")),
        target_memory_layer=_safe_str(row.get("target_memory_layer")),
        source_scope=source_scope,
        candidate_text=_safe_str(row.get("candidate_text")),
    )


def candidate_review_context(row: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    current_id = _safe_str(row.get("candidate_id"))
    current_meta = candidate_claim_metadata_from_row(row)
    current_topic = _safe_str(current_meta.get("claim_topic_key"))
    current_polarity = _safe_str(current_meta.get("claim_polarity"), "unknown")
    related: list[dict[str, Any]] = []
    supporting: list[dict[str, Any]] = []
    conflicting: list[dict[str, Any]] = []

    for other in rows:
        other_id = _safe_str(other.get("candidate_id"))
        if not other_id or other_id == current_id:
            continue
        if _safe_str(other.get("status")) not in ACTIVE_REVIEW_STATUSES:
            continue
        other_meta = candidate_claim_metadata_from_row(other)
        if other_meta.get("claim_topic_key") != current_topic:
            continue
        related.append(other)
        other_polarity = _safe_str(other_meta.get("claim_polarity"), "unknown")
        if _same_claim_polarity(current_polarity, other_polarity):
            supporting.append(other)
        elif _opposite_claim_polarity(current_polarity, other_polarity):
            conflicting.append(other)

    status_counts = Counter(_safe_str(item.get("status"), "unknown") for item in [row, *related])
    source_turns = {
        _safe_str(item.get("source_turn_id")).strip()
        for item in [row, *supporting]
        if _safe_str(item.get("source_turn_id")).strip()
    }
    source_messages: set[int] = set()
    for item in [row, *supporting]:
        for message_id in item.get("source_message_ids", []) or []:
            if isinstance(message_id, int):
                source_messages.add(message_id)
    evidence_count = 1 + len(supporting)
    conflict_count = len(conflicting)
    return {
        "claim_key": current_meta["claim_key"],
        "claim_topic_key": current_meta["claim_topic_key"],
        "claim_polarity": current_meta["claim_polarity"],
        "evidence_count": evidence_count,
        "related_candidate_ids": _candidate_ids(related),
        "supporting_candidate_ids": _candidate_ids(supporting),
        "conflicting_candidate_ids": _candidate_ids(conflicting),
        "conflict_count": conflict_count,
        "distinct_source_turn_count": len(source_turns),
        "distinct_source_message_count": len(source_messages),
        "status_counts": dict(sorted(status_counts.items())),
        "recommendation": _review_recommendation(row, evidence_count=evidence_count, conflict_count=conflict_count),
    }


def _review_recommendation(row: dict[str, Any], *, evidence_count: int, conflict_count: int) -> str:
    if conflict_count:
        return "hold_conflict_review"
    if _safe_str(row.get("candidate_type")) in {"owner_preference", "relationship_signal", "voice_correction"}:
        if evidence_count >= 2:
            return "repeated_evidence_ready_for_owner_review"
        return "hold_for_more_evidence"
    if evidence_count >= 2:
        return "corroborated_candidate_review"
    return "single_candidate_review"


def _claim_source_text(text: str) -> str:
    owner_lines: list[str] = []
    fallback_lines: list[str] = []
    for line in _safe_str(text).splitlines():
        clean = line.strip()
        if not clean:
            continue
        lowered = clean.lower()
        if lowered.startswith("owner_turn:"):
            owner_lines.append(clean.split(":", 1)[1].strip())
        elif not lowered.startswith("visible_reply:"):
            fallback_lines.append(clean)
    return " ".join(owner_lines or fallback_lines or [_safe_str(text)])


def _claim_polarity(text: str) -> str:
    lowered = _safe_str(text).lower()
    if _has_marker(lowered, NEGATIVE_MARKERS):
        return "negative"
    if _has_marker(lowered, POSITIVE_MARKERS):
        return "positive"
    return "unknown"


def _topic_basis(text: str) -> str:
    lowered = _safe_str(text).lower()
    markers = sorted((*NEGATIVE_MARKERS, *POSITIVE_MARKERS, *STOP_MARKERS), key=len, reverse=True)
    for marker in markers:
        lowered = _remove_marker(lowered, marker.lower())
    tokens = [token for token in _tokens(lowered) if token not in STOP_WORDS]
    if tokens:
        return " ".join(tokens[:32])
    compact = re.sub(r"\s+", "", lowered)
    return compact[:120] or "empty"


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9_+#./-]{2,}|[\u4e00-\u9fff]", _safe_str(text).lower())


def _has_marker(text: str, markers: tuple[str, ...]) -> bool:
    return any(_marker_pattern(marker).search(text) for marker in markers if marker)


def _remove_marker(text: str, marker: str) -> str:
    return _marker_pattern(marker).sub(" ", text)


def _marker_pattern(marker: str) -> re.Pattern[str]:
    clean = _safe_str(marker).strip().lower()
    if re.fullmatch(r"[a-z0-9][a-z0-9 ]*[a-z0-9]", clean):
        return re.compile(rf"(?<![a-z0-9]){re.escape(clean)}(?![a-z0-9])")
    return re.compile(re.escape(clean))


def _same_claim_polarity(left: str, right: str) -> bool:
    if left == right and left != "unknown":
        return True
    return left == "unknown" and right == "unknown"


def _opposite_claim_polarity(left: str, right: str) -> bool:
    return {left, right} == {"positive", "negative"}


def _candidate_ids(rows: list[dict[str, Any]]) -> list[str]:
    return sorted(_safe_str(row.get("candidate_id")) for row in rows if _safe_str(row.get("candidate_id")))


def _scope_from_flags(flags: Any) -> str:
    if not isinstance(flags, list):
        return ""
    for flag in flags:
        text = _safe_str(flag)
        if text.startswith("scope:"):
            return text.split(":", 1)[1].strip()
    return ""


def _dict_field(row: dict[str, Any], key: str) -> dict[str, Any]:
    value = row.get(key)
    return value if isinstance(value, dict) else {}


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        text = str(value)
    except Exception:
        return default
    return text if text else default


def _hash(text: str, *, length: int) -> str:
    return hashlib.sha256(_safe_str(text).encode("utf-8", errors="replace")).hexdigest()[:length]

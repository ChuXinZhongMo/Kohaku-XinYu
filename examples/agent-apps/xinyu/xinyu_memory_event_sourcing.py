"""Runtime sidecar recording for source-traceable memory events."""

from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


CUSTOM_DIR = Path(__file__).resolve().parent / "custom"
if str(CUSTOM_DIR) not in sys.path:
    sys.path.insert(0, str(CUSTOM_DIR))

from memory_consistency_gate_engine import run_memory_consistency_gate  # noqa: E402
from memory_event_schema import dump_jsonl, load_jsonl, sha256_text  # noqa: E402


URL_RE = re.compile(r"https?://[^\s<>()]+|www\.[^\s<>()]+", re.I)
VOICE_CORRECTION_MARKERS = (
    "像客服",
    "客服感",
    "不像你",
    "ai味",
    "AI味",
    "gpt味",
    "GPT味",
    "太正式",
    "太客气",
    "不喜欢",
    "别这样",
    "不要这样",
    "说话方式",
    "语气",
    "回复",
)
MEMORY_SELECTIVITY_MARKERS = (
    "不是每句话",
    "重要的部分",
    "不重要的可以忘",
    "选择性",
    "有选择",
    "值得记",
    "可以淡去",
)


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    if value is None:
        return default
    return bool(value)


def _stable_hash(text: str, length: int = 12) -> str:
    return sha256_text(text)[:length]


def _timestamp(value: Any = None) -> str:
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value)).astimezone().isoformat()
    text = _safe_str(value).strip()
    if text:
        return text
    return datetime.now().astimezone().isoformat()


def _event_dir(root: Path) -> Path:
    return root / "memory/events"


def _append_unique(path: Path, row: dict[str, Any], id_field: str) -> bool:
    rows = load_jsonl(path)
    row_id = _safe_str(row.get(id_field)).strip()
    if any(_safe_str(existing.get(id_field)).strip() == row_id for existing in rows):
        return False
    rows.append(row)
    dump_jsonl(path, rows)
    return True


def _payload_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    metadata = payload.get("metadata")
    return metadata if isinstance(metadata, dict) else {}


def _source_context(payload: dict[str, Any], *, default_source_channel: str = "") -> tuple[str, str, str]:
    metadata = _payload_metadata(payload)
    message_type = _safe_str(payload.get("message_type")).strip()
    group_id = _safe_str(payload.get("group_id")).strip()
    is_owner = _as_bool(metadata.get("is_owner_user"), default=False)
    priority_group = _as_bool(payload.get("priority_learning_group") or metadata.get("priority_learning_group"), False)

    if priority_group:
        source_channel = "priority_learning_group"
    elif default_source_channel:
        source_channel = default_source_channel
    elif group_id or message_type.startswith("group_"):
        source_channel = "qq_group"
    elif is_owner:
        source_channel = "owner_private"
    else:
        source_channel = "qq_private"

    if is_owner:
        actor_scope = "owner"
    elif group_id or source_channel in {"qq_group", "priority_learning_group"}:
        actor_scope = "group_member"
    else:
        actor_scope = "external_contact"

    if source_channel == "owner_private":
        privacy_scope = "owner_private"
    elif source_channel in {"qq_group", "priority_learning_group"}:
        privacy_scope = "group_context"
    else:
        privacy_scope = "external_private"
    return source_channel, actor_scope, privacy_scope


def _raw_event_id(payload: dict[str, Any], text: str, source_channel: str) -> str:
    stamp = _timestamp(payload.get("observed_at") or payload.get("timestamp"))
    message_id = _safe_str(payload.get("message_id") or _payload_metadata(payload).get("message_id"))
    session_id = _safe_str(payload.get("session_id"))
    user_id = _safe_str(payload.get("user_id"))
    group_id = _safe_str(payload.get("group_id"))
    key = f"{source_channel}|{session_id}|{group_id}|{user_id}|{message_id}|{text}"
    return f"evt-{stamp[:10]}-{_stable_hash(key, 12)}"


def _raw_event(
    payload: dict[str, Any],
    *,
    text: str,
    source_channel: str,
    actor_scope: str,
    privacy_scope: str,
) -> dict[str, Any]:
    timestamp = _timestamp(payload.get("observed_at") or payload.get("timestamp"))
    metadata = _payload_metadata(payload)
    return {
        "event_id": _raw_event_id(payload, text, source_channel),
        "timestamp": timestamp,
        "source_channel": source_channel,
        "actor_scope": actor_scope,
        "raw_text": text,
        "raw_hash": sha256_text(text),
        "privacy_scope": privacy_scope,
        "adapter": _safe_str(payload.get("platform"), "qq"),
        "message_type": _safe_str(payload.get("message_type") or metadata.get("message_type")),
        "session_hash": _stable_hash(_safe_str(payload.get("session_id"))),
        "user_hash": _stable_hash(_safe_str(payload.get("user_id"))),
        "group_hash": _stable_hash(_safe_str(payload.get("group_id"))),
        "message_hash": _stable_hash(_safe_str(payload.get("message_id") or metadata.get("message_id"))),
    }


def _structured_event(raw: dict[str, Any], payload: dict[str, Any], *, event_kind: str) -> dict[str, Any]:
    source_channel = _safe_str(raw.get("source_channel"))
    actor_scope = _safe_str(raw.get("actor_scope"))
    if source_channel == "owner_private":
        allowed = ["reflection", "self/voice_review", "relationships/owner_candidate"]
        blocked = ["stable_personality_direct_write"]
        turn_mode = "owner_private_visible_turn"
        salience = 64
    elif source_channel in {"qq_group", "priority_learning_group"} or actor_scope == "group_member":
        allowed = ["context/group", "knowledge/source_candidates"]
        blocked = ["relationships/owner", "stable_knowledge_direct_write"]
        turn_mode = "observe_only" if source_channel == "priority_learning_group" else "group_context_candidate"
        salience = 58
    else:
        allowed = ["context/external_contact", "knowledge/source_candidates"]
        blocked = ["relationships/owner"]
        turn_mode = "external_private_candidate"
        salience = 45

    return {
        "structured_id": "se-" + _safe_str(raw["event_id"]).removeprefix("evt-"),
        "event_id": raw["event_id"],
        "event_kind": event_kind,
        "turn_mode": turn_mode,
        "allowed_memory_layers": allowed,
        "blocked_memory_layers": blocked,
        "salience": salience,
        "routing_notes": [
            "event_sourcing_sidecar",
            "no_stable_write_from_sidecar",
            f"source_channel:{source_channel}",
            f"actor_scope:{actor_scope}",
        ],
    }


def _find_urls(text: str) -> list[str]:
    urls: list[str] = []
    for match in URL_RE.finditer(text):
        url = match.group(0).rstrip(".,，。;；!！?？)]}》")
        if url and url not in urls:
            urls.append(url)
    return urls


def _span_for_text(event_id: str, raw_text: str, target: str) -> dict[str, Any]:
    start = raw_text.find(target)
    span: dict[str, Any] = {"event_id": event_id, "text": target}
    if start >= 0:
        span["start"] = start
        span["end"] = start + len(target)
    return span


def _claims_for_text(raw: dict[str, Any], payload: dict[str, Any], *, event_kind: str) -> list[dict[str, Any]]:
    event_id = _safe_str(raw["event_id"])
    raw_text = _safe_str(raw.get("raw_text"))
    source_channel = _safe_str(raw.get("source_channel"))
    actor_scope = _safe_str(raw.get("actor_scope"))
    claims: list[dict[str, Any]] = []

    for url in _find_urls(raw_text):
        claims.append(
            {
                "claim_id": f"claim-source-{_stable_hash(event_id + url, 12)}",
                "claim_type": "source_candidate",
                "subject": "external_source",
                "predicate": "candidate_url",
                "object": url,
                "status": "candidate",
                "target_memory_layer": "knowledge/source_candidates",
                "evidence_event_ids": [event_id],
                "evidence_spans": [_span_for_text(event_id, raw_text, url)],
                "confidence": 70 if source_channel == "priority_learning_group" else 62,
            }
        )

    if actor_scope == "owner" and any(marker in raw_text for marker in VOICE_CORRECTION_MARKERS):
        claims.append(
            {
                "claim_id": f"claim-voice-{_stable_hash(event_id + raw_text, 12)}",
                "claim_type": "voice_correction",
                "subject": "xinyu_visible_reply_style",
                "predicate": "owner_feedback",
                "object": "possible voice or reply-style correction",
                "status": "review_only",
                "target_memory_layer": "self/voice_review",
                "evidence_event_ids": [event_id],
                "evidence_spans": [{"event_id": event_id, "text": raw_text}],
                "confidence": 78,
            }
        )

    if actor_scope == "owner" and any(marker in raw_text for marker in MEMORY_SELECTIVITY_MARKERS):
        marker = next((item for item in MEMORY_SELECTIVITY_MARKERS if item in raw_text), raw_text[:40])
        claims.append(
            {
                "claim_id": f"claim-memory-policy-{_stable_hash(event_id + marker, 12)}",
                "claim_type": "preference",
                "subject": "xinyu_memory_policy",
                "predicate": "owner_prefers_selective_retention",
                "object": "retain important parts and allow low-value details to fade",
                "status": "review_only",
                "target_memory_layer": "memory/context/memory_policy_review",
                "evidence_event_ids": [event_id],
                "evidence_spans": [_span_for_text(event_id, raw_text, marker)],
                "confidence": 86,
            }
        )

    if event_kind == "learning_ingest":
        file_name = _safe_str(payload.get("file_name") or payload.get("name") or "learning_material")
        object_value = file_name or raw_text[:120]
        claims.append(
            {
                "claim_id": f"claim-material-{_stable_hash(event_id + object_value, 12)}",
                "claim_type": "source_candidate",
                "subject": "learning_material",
                "predicate": "candidate_material",
                "object": object_value,
                "status": "candidate",
                "target_memory_layer": "knowledge/source_materials",
                "evidence_event_ids": [event_id],
                "evidence_spans": [_span_for_text(event_id, raw_text, object_value)],
                "confidence": 74,
            }
        )

    return claims


def _summary_for_claims(raw: dict[str, Any], claims: list[dict[str, Any]], *, event_kind: str) -> dict[str, Any] | None:
    if not claims:
        return None
    event_id = _safe_str(raw["event_id"])
    claim_ids = [_safe_str(claim["claim_id"]) for claim in claims]
    blocked = ["source URL" if claim["claim_type"] == "source_candidate" else "owner correction" for claim in claims]
    return {
        "summary_id": f"summary-{_stable_hash(event_id + '|'.join(claim_ids), 12)}",
        "summary_text": f"{event_kind} sidecar retained {len(claims)} typed claim(s).",
        "retained_claim_ids": claim_ids,
        "source_event_ids": [event_id],
        "loss_notes": ["raw wording remains in raw_events.jsonl; summary is not authoritative"],
        "discarded_signals": ["low-value filler not promoted"],
        "blocked_from_discard": sorted(set(blocked)),
    }


def _record(
    root: Path,
    payload: dict[str, Any],
    *,
    text: str,
    event_kind: str,
    default_source_channel: str = "",
) -> dict[str, Any]:
    if not text.strip():
        return {"recorded": False, "gate_status": "skipped", "notes": ["event_sourcing_empty_text"]}
    source_channel, actor_scope, privacy_scope = _source_context(payload, default_source_channel=default_source_channel)
    raw = _raw_event(
        payload,
        text=text.strip(),
        source_channel=source_channel,
        actor_scope=actor_scope,
        privacy_scope=privacy_scope,
    )
    structured = _structured_event(raw, payload, event_kind=event_kind)
    claims = _claims_for_text(raw, payload, event_kind=event_kind)
    summary = _summary_for_claims(raw, claims, event_kind=event_kind)
    event_dir = _event_dir(root)
    event_dir.mkdir(parents=True, exist_ok=True)
    changed = False
    changed |= _append_unique(event_dir / "raw_events.jsonl", raw, "event_id")
    changed |= _append_unique(event_dir / "structured_events.jsonl", structured, "structured_id")
    for claim in claims:
        changed |= _append_unique(event_dir / "atomic_claims.jsonl", claim, "claim_id")
    if summary is not None:
        changed |= _append_unique(event_dir / "summary_views.jsonl", summary, "summary_id")
    gate = run_memory_consistency_gate(root, mode=f"runtime_{event_kind}_sidecar")
    return {
        "recorded": changed,
        "event_id": raw["event_id"],
        "claim_count": len(claims),
        "gate_status": gate["gate_status"],
        "failure_count": gate["failure_count"],
        "notes": [
            "event_sourcing_sidecar",
            f"event_sourcing_gate:{gate['gate_status']}",
            f"event_sourcing_claims:{len(claims)}",
        ],
    }


def record_chat_event(root: Path, payload: dict[str, Any], *, text: str) -> dict[str, Any]:
    return _record(root, payload, text=text, event_kind="chat_input")


def record_learning_observe_event(root: Path, payload: dict[str, Any], *, text: str) -> dict[str, Any]:
    return _record(
        root,
        payload,
        text=text,
        event_kind="learning_observe",
        default_source_channel="priority_learning_group",
    )


def record_learning_ingest_event(root: Path, payload: dict[str, Any], *, result: dict[str, Any] | None = None) -> dict[str, Any]:
    result = result or {}
    metadata = payload.get("metadata")
    metadata_map = metadata if isinstance(metadata, dict) else {}
    file_name = _safe_str(payload.get("file_name") or payload.get("name") or result.get("learning_item_id"))
    reason = _safe_str(payload.get("reason") or metadata_map.get("text"))
    url = _safe_str(payload.get("file_url") or payload.get("url"))
    material_id = _safe_str(result.get("material_id"))
    parts = ["learning ingest"]
    if file_name:
        parts.append(f"file_name={file_name}")
    if reason:
        parts.append(f"reason={reason}")
    if url:
        parts.append(f"url={url}")
    if material_id:
        parts.append(f"material_id={material_id}")
    text = "; ".join(parts)
    source_channel = "owner_file_ingest" if _as_bool(metadata_map.get("is_owner_user"), False) else "external_file_ingest"
    return _record(
        root,
        payload,
        text=text,
        event_kind="learning_ingest",
        default_source_channel=source_channel,
    )

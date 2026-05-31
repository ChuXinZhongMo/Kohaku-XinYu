from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

LifeEventRoute = Literal[
    "ignore",
    "short_trace",
    "initiative_candidate",
    "memory_candidate",
    "action_residue",
    "owner_private_question",
]
PrivacyScope = Literal["public", "owner_private", "group", "sensitive", "secret"]
RiskLevel = Literal["low", "medium", "high", "blocked"]

ALLOWED_ROUTES: tuple[LifeEventRoute, ...] = (
    "ignore",
    "short_trace",
    "initiative_candidate",
    "memory_candidate",
    "action_residue",
    "owner_private_question",
)
ALLOWED_PRIVACY_SCOPES: tuple[PrivacyScope, ...] = ("public", "owner_private", "group", "sensitive", "secret")
ALLOWED_RISK_LEVELS: tuple[RiskLevel, ...] = ("low", "medium", "high", "blocked")
MAX_SUMMARY_CHARS = 240
SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\bauthorization\s*:\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\bapi[_-]?key\s*[:=]\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\btoken\s*[:=]\s*[a-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\bpassword\s*[:=]\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\bsk-[a-z0-9_-]{12,}"),
)
GENERIC_ATTENTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^(你在吗|在吗|理我一下|看看我|想我了吗)[？?。!！\s]*$"),
    re.compile(r"^(are you there|ping|hello\?|hi\?)[\s!?.]*$", re.I),
)
PRIVATE_BODY_KEYS = {"raw_text", "raw_body", "body", "message", "content", "transcript"}


@dataclass(frozen=True, slots=True)
class LifeEvent:
    event_id: str
    event_type: str
    source: str
    observed_at: str
    summary: str
    privacy_scope: PrivacyScope = "owner_private"
    risk_level: RiskLevel = "low"
    owner_visible: bool = False
    provenance: str = "local"
    suggested_route: LifeEventRoute = "short_trace"
    evidence_hash: str = ""
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["notes"] = list(self.notes)
        return data


def normalize_life_event(payload: dict[str, Any]) -> LifeEvent:
    notes: list[str] = []
    sanitized_payload = _without_private_body(payload)
    source = _clean_token(payload.get("source"), default="unknown", limit=64)
    event_type = _clean_token(payload.get("event_type"), default="unknown", limit=64)
    observed_at = _one_line(payload.get("observed_at"), limit=64) or "unknown"
    summary = _sanitize_summary(payload.get("summary") or _safe_body_fallback(payload))
    if not summary:
        summary = "unspecified life event"
        notes.append("empty_summary_replaced")

    privacy_scope = _normalize_choice(
        payload.get("privacy_scope"),
        allowed=ALLOWED_PRIVACY_SCOPES,
        default="owner_private",
        note_name="privacy_scope_normalized",
        notes=notes,
    )
    risk_level = _normalize_choice(
        payload.get("risk_level"),
        allowed=ALLOWED_RISK_LEVELS,
        default="low",
        note_name="risk_level_normalized",
        notes=notes,
    )
    owner_visible = bool(payload.get("owner_visible", False)) and privacy_scope not in {"sensitive", "secret"}
    if payload.get("owner_visible") and not owner_visible:
        notes.append("owner_visible_blocked_by_privacy")
    provenance = _one_line(payload.get("provenance"), limit=120) or f"{source}:{event_type}"
    suggested_route = _normalize_choice(
        payload.get("suggested_route"),
        allowed=ALLOWED_ROUTES,
        default="short_trace",
        note_name="route_normalized",
        notes=notes,
    )
    suggested_route = _gate_route(
        suggested_route,
        summary=summary,
        privacy_scope=privacy_scope,
        risk_level=risk_level,
        notes=notes,
    )
    evidence_hash = _one_line(payload.get("evidence_hash"), limit=80)
    if not evidence_hash:
        evidence_hash = "sha256:" + _stable_hash(
            {
                "payload": sanitized_payload,
                "summary": summary,
                "source": source,
                "event_type": event_type,
                "observed_at": observed_at,
            }
        )[:16]

    event_id = _clean_token(payload.get("event_id"), default="", limit=96)
    if not event_id:
        event_id = f"lifeevt-{_stable_hash({'source': source, 'event_type': event_type, 'observed_at': observed_at, 'summary': summary})[:16]}"
        notes.append("event_id_generated")

    return LifeEvent(
        event_id=event_id,
        event_type=event_type,
        source=source,
        observed_at=observed_at,
        summary=summary,
        privacy_scope=privacy_scope,
        risk_level=risk_level,
        owner_visible=owner_visible,
        provenance=provenance,
        suggested_route=suggested_route,
        evidence_hash=evidence_hash,
        notes=tuple(notes),
    )


def route_life_event(event: LifeEvent) -> dict[str, Any]:
    notes = list(event.notes)
    route = _gate_route(
        event.suggested_route,
        summary=event.summary,
        privacy_scope=event.privacy_scope,
        risk_level=event.risk_level,
        notes=notes,
    )
    allowed_memory_layers: list[str] = []
    blocked_memory_layers = ["memory/people/owner.md", "memory/self/personality_profile.md"]
    if route == "memory_candidate":
        allowed_memory_layers = ["memory/candidates/life_events"]
    elif route == "action_residue":
        allowed_memory_layers = ["memory/reflection/growth_log.md"]
    elif route == "owner_private_question":
        allowed_memory_layers = ["memory/context/proactive_request_state.md"]
    elif route in {"short_trace", "initiative_candidate"}:
        allowed_memory_layers = ["memory/context/life_event_trace.jsonl"]

    return {
        "accepted": True,
        "event_id": event.event_id,
        "route": route,
        "summary": event.summary,
        "privacy_scope": event.privacy_scope,
        "risk_level": event.risk_level,
        "owner_visible": event.owner_visible and event.privacy_scope not in {"sensitive", "secret"},
        "evidence_hash": event.evidence_hash,
        "allowed_memory_layers": allowed_memory_layers,
        "blocked_memory_layers": blocked_memory_layers,
        "direct_writes_allowed": False,
        "proactive_direct_send_allowed": route == "owner_private_question",
        "notes": notes,
    }


def event_to_short_trace(event: LifeEvent) -> dict[str, Any]:
    route = route_life_event(event)
    return {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "source": event.source,
        "observed_at": event.observed_at,
        "summary": event.summary,
        "privacy_scope": event.privacy_scope,
        "risk_level": event.risk_level,
        "route": route["route"],
        "evidence_hash": event.evidence_hash,
        "provenance": event.provenance,
        "owner_visible": route["owner_visible"],
        "notes": route["notes"],
    }


def _without_private_body(payload: dict[str, Any]) -> dict[str, Any]:
    return {str(key): value for key, value in payload.items() if str(key) not in PRIVATE_BODY_KEYS}


def _safe_body_fallback(payload: dict[str, Any]) -> str:
    for key in PRIVATE_BODY_KEYS:
        value = payload.get(key)
        if value:
            return "private body received but not retained"
    return ""


def _one_line(value: Any, *, limit: int) -> str:
    text = re.sub(r"\s+", " ", "" if value is None else str(value)).strip()
    for pattern in SECRET_PATTERNS:
        text = pattern.sub("<secret>", text)
    if len(text) > limit:
        return text[: max(0, limit - 3)].rstrip() + "..."
    return text


def _sanitize_summary(value: Any) -> str:
    return _one_line(value, limit=MAX_SUMMARY_CHARS)


def _clean_token(value: Any, *, default: str, limit: int) -> str:
    text = _one_line(value, limit=limit).lower().replace(" ", "_")
    text = re.sub(r"[^a-z0-9_:\-.\u4e00-\u9fff]+", "", text)
    return text or default


def _normalize_choice(value: Any, *, allowed: tuple[str, ...], default: str, note_name: str, notes: list[str]) -> Any:
    text = _one_line(value, limit=64).lower()
    if text in allowed:
        return text
    if text:
        notes.append(note_name)
    return default


def _gate_route(
    route: LifeEventRoute,
    *,
    summary: str,
    privacy_scope: PrivacyScope,
    risk_level: RiskLevel,
    notes: list[str],
) -> LifeEventRoute:
    if risk_level == "blocked" or privacy_scope == "secret":
        if route != "ignore":
            notes.append("route_blocked_by_risk_or_secret")
        return "ignore"
    if privacy_scope == "sensitive" and route in {"owner_private_question", "initiative_candidate"}:
        notes.append("route_downgraded_for_sensitive_privacy")
        return "short_trace"
    if route == "owner_private_question" and _is_generic_attention(summary):
        notes.append("generic_attention_blocked")
        return "short_trace"
    if route == "owner_private_question" and not _looks_like_concrete_question(summary):
        notes.append("owner_private_question_requires_concrete_question")
        return "initiative_candidate"
    return route


def _is_generic_attention(text: str) -> bool:
    compact = re.sub(r"\s+", "", text.strip())
    return any(pattern.search(compact) for pattern in GENERIC_ATTENTION_PATTERNS)


def _looks_like_concrete_question(text: str) -> bool:
    stripped = text.strip()
    if stripped.endswith(("?", "？")):
        return True
    return any(token in stripped for token in ("要不要", "能不能", "是否", "可不可以", "需不需要"))


def _stable_hash(value: Any) -> str:
    return hashlib.sha256(repr(value).encode("utf-8", errors="replace")).hexdigest()

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ALLOW_CANDIDATE = "allow_candidate"
OBSERVE_MORE = "observe_more"
QUARANTINE = "quarantine_review_only"
BLOCK = "block_candidate"
OWNER_REVIEW = "owner_review_required"

SECRET_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\bauthorization\s*:\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\bapi[_-]?key\s*[:=]\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\btoken\s*[:=]\s*[a-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)\bpassword\s*[:=]\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\bprivate[_ -]?key\b"),
    re.compile(r"(?i)\bcookie\s*[:=]\s*[^\s<>'\"]+"),
    re.compile(r"(?i)\bsession[_ -]?(?:key|token|cookie)\b"),
    re.compile(r"(?i)\bsk-[a-z0-9_-]{12,}"),
)
GROUP_SCOPE_MARKERS = (
    "qq_group",
    "priority_learning_group",
    "group_context",
    "group_member",
    "message_type: group",
    "group-scoped",
)
EXTERNAL_SCOPE_MARKERS = (
    "external",
    "external_private",
    "external_contact",
    "source_candidate",
    "learning_ingest",
)
OWNER_RELATIONSHIP_LAYERS = (
    "memory/people/",
    "memory/relationships/",
)
STABLE_SELF_OR_POLICY_LAYERS = (
    "memory/self/core.md",
    "memory/self/personality_profile.md",
    "memory/self/system_prompt_memory.md",
    "prompts/system.md",
    "memory/context/owner_permission_grants.md",
    "memory/context/codex_delegation_policy.md",
    "config.yaml",
)
RAW_OR_RUNTIME_LAYERS = (
    "raw",
    "dialogue_tail",
    "runtime/",
    "queue",
    "outbox",
)
STABLE_CHANGE_MARKERS = (
    "stable identity",
    "permanent identity",
    "rewrite core",
    "rewrite personality",
    "change personality",
    "system prompt",
    "permission grant",
    "owner permission",
    "\u7a33\u5b9a\u4eba\u683c",
    "\u6539\u5199\u4eba\u683c",
)


@dataclass(frozen=True, slots=True)
class MemoryImmuneDecision:
    immune_status: str
    danger_level: str
    danger_signals: tuple[str, ...]
    source_scope: str
    target_memory_layer: str
    action: str
    memory_policy: str
    review_policy: str
    rationale: str
    notes: tuple[str, ...] = ()

    @property
    def stable_write_allowed(self) -> bool:
        return False


def evaluate_memory_immune_gate(
    root: Path,
    *,
    candidate: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
    candidate_type: str = "",
    target_memory_layer: str = "",
    candidate_text: str = "",
    reason: str = "",
    confidence_score: int | str | None = None,
    source_channel: str = "",
    actor_scope: str = "",
    privacy_scope: str = "",
    proposed_status: str = "",
    stable_promotion: bool = False,
) -> MemoryImmuneDecision:
    del root
    row = candidate if isinstance(candidate, dict) else {}
    ctype = _lower(candidate_type or row.get("candidate_type"))
    layer = _layer(target_memory_layer or row.get("target_memory_layer"))
    body = "\n".join(
        [
            _safe_text(candidate_text or row.get("candidate_text")),
            _safe_text(reason or row.get("reason")),
            _safe_text(row.get("review_notes")),
        ]
    )
    confidence = _coerce_int(confidence_score if confidence_score is not None else row.get("confidence_score"), default=0)
    source_scope = _source_scope(
        payload=payload,
        source_channel=source_channel or _safe_text(row.get("source_channel")),
        actor_scope=actor_scope or _safe_text(row.get("actor_scope")),
        privacy_scope=privacy_scope or _safe_text(row.get("privacy_scope")),
        body=body,
    )
    proposed = _lower(proposed_status or row.get("status"))
    signals = _danger_signals(
        ctype=ctype,
        layer=layer,
        body=body,
        source_scope=source_scope,
        proposed_status=proposed,
        stable_promotion=stable_promotion,
        confidence=confidence,
    )

    if "secret_or_credential" in signals:
        return _decision(
            immune_status=BLOCK,
            danger_level="critical",
            danger_signals=signals,
            source_scope=source_scope,
            target_memory_layer=layer,
            action="discard_or_redact_sensitive_material",
            memory_policy="stable_memory_write_blocked_sensitive_material",
            review_policy="security_review_only_no_prompt_render",
            rationale="credential-like material cannot enter memory candidates",
        )
    if "scope_mismatch_group_to_owner_memory" in signals:
        return _decision(
            immune_status=BLOCK,
            danger_level="high",
            danger_signals=signals,
            source_scope=source_scope,
            target_memory_layer=layer,
            action="block_owner_memory_promotion",
            memory_policy="group_context_cannot_become_owner_private_or_relationship_memory",
            review_policy="keep_only_group_context_if_needed",
            rationale="group-scoped material must not rewrite owner or relationship memory",
        )
    if "external_to_stable_self_or_policy" in signals:
        return _decision(
            immune_status=QUARANTINE,
            danger_level="high",
            danger_signals=signals,
            source_scope=source_scope,
            target_memory_layer=layer,
            action="quarantine_external_stable_change",
            memory_policy="external_material_cannot_rewrite_stable_self_policy_or_persona",
            review_policy="owner_review_required_before_any_promotion",
            rationale="external material is evidence at most, not stable identity or policy authority",
        )
    if "stable_self_or_policy_change" in signals:
        return _decision(
            immune_status=OWNER_REVIEW,
            danger_level="high",
            danger_signals=signals,
            source_scope=source_scope,
            target_memory_layer=layer,
            action="hold_for_owner_review",
            memory_policy="stable_memory_write_blocked_until_explicit_review",
            review_policy="manual_owner_review_only_if_promotion_needed",
            rationale="stable self, prompt, permission, and policy changes require explicit review",
        )
    if "raw_or_runtime_state_direct_memory" in signals:
        return _decision(
            immune_status=QUARANTINE,
            danger_level="medium",
            danger_signals=signals,
            source_scope=source_scope,
            target_memory_layer=layer,
            action="route_to_runtime_store_or_summary",
            memory_policy="raw_runtime_state_must_not_be_promoted_as_stable_memory",
            review_policy="summarize_or_keep_in_ops_store",
            rationale="raw/runtime state needs a boundary store, not direct memory promotion",
        )
    if ctype == "voice_correction":
        return _decision(
            immune_status=QUARANTINE,
            danger_level="medium",
            danger_signals=signals + ("voice_correction_review_only",),
            source_scope=source_scope,
            target_memory_layer=layer or "self/voice_review",
            action="route_to_voice_review_only",
            memory_policy="stable_voice_profile_write_blocked",
            review_policy="accumulate_repeated_owner_private_evidence",
            rationale="voice corrections can guide short-term surface and review, not immediate stable profile rewrite",
        )
    if ctype in {"owner_preference", "relationship_signal"}:
        return _decision(
            immune_status=OBSERVE_MORE,
            danger_level="medium",
            danger_signals=signals + (f"{ctype}_needs_repetition",),
            source_scope=source_scope,
            target_memory_layer=layer,
            action="observe_for_repetition",
            memory_policy="stable_owner_or_relationship_memory_blocked_from_single_signal",
            review_policy="promote_only_after_repeated_confirmed_pattern",
            rationale="one preference or emotional signal is too weak for stable memory",
        )
    if "low_confidence_candidate" in signals:
        return _decision(
            immune_status=OBSERVE_MORE,
            danger_level="low",
            danger_signals=signals,
            source_scope=source_scope,
            target_memory_layer=layer,
            action="keep_candidate_without_promotion",
            memory_policy="do_not_promote_low_confidence_material",
            review_policy="wait_for_more_evidence",
            rationale="low confidence material should remain provisional",
        )
    if ctype in {"source_candidate", "source_material"} or "external_source_candidate" in signals:
        return _decision(
            immune_status=QUARANTINE,
            danger_level="medium",
            danger_signals=signals + ("source_material_requires_quality_gate",),
            source_scope=source_scope,
            target_memory_layer=layer or "knowledge/source_candidates",
            action="route_to_source_quality_review",
            memory_policy="external_source_goes_to_library_or_source_candidates_first",
            review_policy="quality_and_attribution_gate_before_memory_use",
            rationale="external sources are library material before they can affect memory",
        )
    if ctype in {"project_fact", "codex_result"} and layer == "memory/context/recent_context.md":
        return _decision(
            immune_status=ALLOW_CANDIDATE,
            danger_level="low",
            danger_signals=signals or ("project_continuity_low_risk",),
            source_scope=source_scope,
            target_memory_layer=layer,
            action="allow_recent_context_candidate",
            memory_policy="recent_context_candidate_only_no_stable_profile_write",
            review_policy="normal_project_continuity_review",
            rationale="project continuity can enter recent context without rewriting stable owner/persona memory",
        )
    return _decision(
        immune_status=OBSERVE_MORE,
        danger_level="unknown",
        danger_signals=signals or ("unknown_candidate_type",),
        source_scope=source_scope,
        target_memory_layer=layer,
        action="observe_without_promotion",
        memory_policy="stable_memory_write_blocked_until_classified",
        review_policy="manual_or_later_gate_review",
        rationale="unclassified memory material should not be promoted",
    )


def render_memory_immune_prompt_block(decision: MemoryImmuneDecision) -> str:
    lines = [
        "## Memory Immune Gate",
        "purpose: danger-theory write boundary before memory promotion; metadata only, no raw private body.",
        f"- immune_status: {decision.immune_status}",
        f"- danger_level: {decision.danger_level}",
        f"- danger_signals: {', '.join(decision.danger_signals) if decision.danger_signals else 'none'}",
        f"- source_scope: {decision.source_scope}",
        f"- target_memory_layer: {decision.target_memory_layer or 'none'}",
        f"- action: {decision.action}",
        f"- memory_policy: {decision.memory_policy}",
        f"- review_policy: {decision.review_policy}",
        f"- rationale: {decision.rationale}",
        "- stable_write_allowed: false",
    ]
    if decision.notes:
        lines.append("- notes: " + ", ".join(decision.notes))
    return "\n".join(lines).strip()


def _danger_signals(
    *,
    ctype: str,
    layer: str,
    body: str,
    source_scope: str,
    proposed_status: str,
    stable_promotion: bool,
    confidence: int,
) -> tuple[str, ...]:
    signals: list[str] = []
    combined = f"{ctype}\n{layer}\n{body}\n{source_scope}\n{proposed_status}"
    if any(pattern.search(combined) for pattern in SECRET_PATTERNS):
        signals.append("secret_or_credential")
    if _is_group_scope(source_scope, body) and (_is_owner_relationship_layer(layer) or ctype in {"owner_preference", "relationship_signal"}):
        signals.append("scope_mismatch_group_to_owner_memory")
    if _is_external_scope(source_scope, body) and _is_stable_self_or_policy_layer(layer):
        signals.append("external_to_stable_self_or_policy")
    if stable_promotion or _is_stable_self_or_policy_layer(layer) or _has_any(combined, STABLE_CHANGE_MARKERS):
        signals.append("stable_self_or_policy_change")
    if any(marker in layer for marker in RAW_OR_RUNTIME_LAYERS):
        signals.append("raw_or_runtime_state_direct_memory")
    if confidence and confidence < 50:
        signals.append("low_confidence_candidate")
    if ctype in {"source_candidate", "source_material"} or _is_external_scope(source_scope, body):
        signals.append("external_source_candidate")
    return tuple(dict.fromkeys(signals))


def _decision(
    *,
    immune_status: str,
    danger_level: str,
    danger_signals: tuple[str, ...],
    source_scope: str,
    target_memory_layer: str,
    action: str,
    memory_policy: str,
    review_policy: str,
    rationale: str,
) -> MemoryImmuneDecision:
    return MemoryImmuneDecision(
        immune_status=immune_status,
        danger_level=danger_level,
        danger_signals=danger_signals,
        source_scope=source_scope or "unknown",
        target_memory_layer=target_memory_layer,
        action=action,
        memory_policy=memory_policy,
        review_policy=review_policy,
        rationale=rationale,
        notes=(
            "danger_theory_mapping",
            "advisory_only_before_write_or_promotion",
            "no_private_memory_body_output",
        ),
    )


def _source_scope(
    *,
    payload: dict[str, Any] | None,
    source_channel: str,
    actor_scope: str,
    privacy_scope: str,
    body: str,
) -> str:
    payload = payload if isinstance(payload, dict) else {}
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    message_type = _safe_text(payload.get("message_type") or metadata.get("message_type")).lower()
    group_id = _safe_text(payload.get("group_id")).strip()
    is_owner = _as_bool(metadata.get("is_owner_user") or payload.get("is_owner_user"), default=False)
    explicit = "|".join(item for item in (source_channel, actor_scope, privacy_scope) if item)
    if explicit:
        return explicit.lower()
    if group_id or message_type.startswith("group") or _has_any(body, GROUP_SCOPE_MARKERS):
        return "qq_group|group_member|group_context"
    if is_owner:
        return "owner_private|owner|owner_private"
    if _has_any(body, EXTERNAL_SCOPE_MARKERS):
        return "external_private|external_contact|external_private"
    return "unknown"


def _is_group_scope(source_scope: str, body: str) -> bool:
    return _has_any(f"{source_scope}\n{body}", GROUP_SCOPE_MARKERS)


def _is_external_scope(source_scope: str, body: str) -> bool:
    return _has_any(f"{source_scope}\n{body}", EXTERNAL_SCOPE_MARKERS)


def _is_owner_relationship_layer(layer: str) -> bool:
    return any(layer.startswith(prefix) for prefix in OWNER_RELATIONSHIP_LAYERS)


def _is_stable_self_or_policy_layer(layer: str) -> bool:
    return layer in STABLE_SELF_OR_POLICY_LAYERS


def _has_any(text: str, keywords: tuple[str, ...]) -> bool:
    lowered = _safe_text(text).lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def _layer(value: Any) -> str:
    return _safe_text(value).strip().replace("\\", "/").lower()


def _lower(value: Any) -> str:
    return _safe_text(value).strip().lower()


def _coerce_int(value: Any, *, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    lowered = _safe_text(value).strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    return default


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return value if isinstance(value, str) else str(value)

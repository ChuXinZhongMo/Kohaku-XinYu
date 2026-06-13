from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from xinyu_prompt_lean import lean_prompt_enabled, lean_sidecar_admitted
from xinyu_prompt_pressure_store import write_prompt_pressure_report_json
from xinyu_text_variants import readable_markers


PROMPT_PRESSURE_REPORT_REL = Path("runtime/prompt_pressure/last_live_prompt_pressure.json")

CONTEXT_REFERENCE_MARKERS = readable_markers(
    "\u521a\u624d",
    "\u521a\u521a",
    "\u4e0a\u6b21",
    "\u7ee7\u7eed",
    "\u63a5\u7740",
    "\u65ad\u5728",
    "\u6ca1\u5b8c",
    "\u8fdb\u5ea6",
    "\u53d1\u751f\u4e86\u4ec0\u4e48",
    "\u4ec0\u4e48\u60c5\u51b5",
    "\u4e0a\u4e00\u53e5",
    "\u4e0a\u4e00\u8f6e",
    "这三件",
    "这三个",
    "哪三件",
    "哪三个",
    "三件事",
    "三个事",
    "这件事",
    "刚才那个",
    "刚才说的",
    "那个呢",
    "continue",
    "just now",
    "what happened",
    "where did we stop",
    "last turn",
)

STATUS_REFERENCE_MARKERS = readable_markers(
    "\u72b6\u6001",
    "\u8fd0\u884c",
    "\u5065\u5eb7\u68c0\u67e5",
    "\u662f\u4ec0\u4e48\u72b6\u6001",
    "status",
    "runtime",
    "health",
    "running",
    "bridge",
)
STATUS_ACTION_MARKERS = readable_markers(
    "\u67e5",
    "\u770b",
    "\u68c0\u67e5",
    "\u770b\u770b",
    "status",
    "health",
)
RUNTIME_STATUS_OBJECT_MARKERS = readable_markers(
    "\u8fd0\u884c",
    "\u8fd0\u884c\u72b6\u6001",
    "\u7cfb\u7edf",
    "\u7cfb\u7edf\u72b6\u6001",
    "\u670d\u52a1",
    "\u670d\u52a1\u72b6\u6001",
    "\u540e\u53f0",
    "\u961f\u5217",
    "\u8fdb\u7a0b",
    "\u7aef\u53e3",
    "\u8fde\u63a5",
    "\u7f51\u5173",
    "xinyu status",
    "core",
    "bridge",
    "gateway",
    "qq",
    "napcat",
    "runtime",
    "server",
    "api",
)
RUNTIME_HEALTH_MARKERS = readable_markers(
    "\u5728\u7ebf",
    "\u6b63\u5e38",
    "\u8fde\u4e0a",
    "\u80fd\u7528",
    "\u53ef\u7528",
    "\u901a\u5417",
    "alive",
)
PERSONAL_STATE_REFERENCE_MARKERS = readable_markers(
    "\u4e2b\u5934",
    "\u4f60\u73b0\u5728",
    "\u4f60\u8fd9\u8fb9",
    "\u4f60\u81ea\u5df1",
    "\u611f\u89c9",
    "\u611f\u53d7",
    "\u5fc3\u60c5",
    "\u600e\u4e48\u6837",
    "\u548b\u6837",
    "\u5982\u4f55",
    "\u4ec0\u4e48\u72b6\u6001",
    "\u8fd8\u597d\u5417",
    "\u8fd8\u597d\u4e48",
    "\u4f60\u8fd8\u597d",
    "\u7d2f\u4e0d\u7d2f",
    "\u56f0\u4e0d\u56f0",
)

DIGEST_REFERENCE_MARKERS = readable_markers(
    "\u603b\u7ed3",
    "\u65e5\u62a5",
    "\u4eca\u5929\u505a\u4e86\u4ec0\u4e48",
    "\u590d\u76d8",
    "digest",
    "summary",
)

OWNER_QUIET_TURN_KINDS = {
    "ordinary_owner_chat",
    "daily_life",
    "owner_style_pressure",
    "owner_no_change_pressure",
    "owner_relationship_pressure",
    "rest_silence",
}


@dataclass(frozen=True)
class PromptSidecar:
    name: str
    parts: tuple[str, ...]
    required: bool = False
    admission: str = "support"

    @classmethod
    def from_parts(
        cls,
        name: str,
        parts: Iterable[Any],
        *,
        required: bool = False,
        admission: str = "support",
    ) -> "PromptSidecar":
        cleaned: list[str] = []
        for part in parts:
            clean = _clean_part(part)
            if clean:
                cleaned.append(clean)
        clean_parts = tuple(cleaned)
        return cls(name=name, parts=clean_parts, required=required, admission=admission)

    @property
    def char_count(self) -> int:
        return len("\n".join(self.parts))


@dataclass(frozen=True)
class PromptSidecarDecision:
    sidecar: PromptSidecar
    admitted: bool
    reason: str


@dataclass(frozen=True)
class PromptPressureSelection:
    decisions: tuple[PromptSidecarDecision, ...]
    mode: str
    turn_kind: str
    owner_private: bool
    context_reference: bool
    status_reference: bool
    digest_reference: bool

    @property
    def admitted(self) -> tuple[PromptSidecar, ...]:
        return tuple(decision.sidecar for decision in self.decisions if decision.admitted)

    @property
    def blocked(self) -> tuple[PromptSidecarDecision, ...]:
        return tuple(decision for decision in self.decisions if not decision.admitted)

    @property
    def admitted_chars(self) -> int:
        return sum(sidecar.char_count for sidecar in self.admitted)

    @property
    def candidate_chars(self) -> int:
        return sum(decision.sidecar.char_count for decision in self.decisions)

    def flat_lines(self) -> list[str]:
        lines: list[str] = []
        for sidecar in self.admitted:
            lines.extend(sidecar.parts)
        return lines

    def to_report(
        self,
        *,
        live_prompt_chars: int,
        session_key: str,
        turn_id: str,
        source: str,
        speaker_relation: str,
        user_text_chars: int,
    ) -> dict[str, Any]:
        return {
            "generated_at": datetime.now().astimezone().isoformat(),
            "session_key": session_key or "unknown",
            "turn_id": turn_id or "unknown",
            "source": source,
            "speaker_relation": speaker_relation,
            "turn_kind": self.turn_kind,
            "mode": self.mode,
            "owner_private": self.owner_private,
            "context_reference": self.context_reference,
            "status_reference": self.status_reference,
            "digest_reference": self.digest_reference,
            "user_text_chars": user_text_chars,
            "live_prompt_chars": live_prompt_chars,
            "candidate_sidecar_count": len(self.decisions),
            "admitted_sidecar_count": len(self.admitted),
            "blocked_sidecar_count": len(self.blocked),
            "candidate_sidecar_chars": self.candidate_chars,
            "admitted_sidecar_chars": self.admitted_chars,
            "blocked_sidecar_chars": sum(decision.sidecar.char_count for decision in self.blocked),
            "admitted_sidecars": [
                _decision_entry(decision) for decision in self.decisions if decision.admitted
            ],
            "blocked_sidecars": [
                _decision_entry(decision) for decision in self.decisions if not decision.admitted
            ],
        }


def select_prompt_sidecars(
    candidates: Iterable[PromptSidecar],
    *,
    payload: dict[str, Any] | None,
    user_text: str,
    visible_turn: Any | None,
) -> PromptPressureSelection:
    payload = payload if isinstance(payload, dict) else {}
    metadata = payload.get("metadata")
    metadata = metadata if isinstance(metadata, dict) else {}
    is_owner = _as_bool(metadata.get("is_owner_user"), default=False)
    message_type = _safe_str(payload.get("message_type")).lower()
    group_id = _safe_str(payload.get("group_id")).strip()
    owner_private = is_owner and not group_id and not message_type.startswith("group")

    turn_kind = _safe_str(getattr(visible_turn, "turn_kind", ""), "unknown") or "unknown"
    technical_work = _as_bool(getattr(visible_turn, "technical_work", False), default=False)
    owner_pressure = any(
        _as_bool(getattr(visible_turn, attr, False), default=False)
        for attr in ("owner_style_pressure", "owner_no_change_pressure", "relationship_pressure", "rest_silence")
    )
    context_reference = _contains_any(user_text, CONTEXT_REFERENCE_MARKERS) or any(
        _as_bool(metadata.get(flag), default=False)
        for flag in ("attachment_followup_after_ingest", "qq_coalesced_owner_messages")
    )
    context_reference = context_reference or bool(_safe_str(metadata.get("desktop_proactive_candidate_id")).strip())
    status_reference = _looks_like_runtime_status_reference(user_text)
    digest_reference = _contains_any(user_text, DIGEST_REFERENCE_MARKERS)

    quiet_owner_mode = owner_private and turn_kind in OWNER_QUIET_TURN_KINDS and not technical_work
    if not owner_private:
        mode = "preserve_non_owner"
    elif technical_work:
        mode = "technical_context"
    elif context_reference:
        mode = "context_reference"
    elif status_reference:
        mode = "status_reference"
    elif owner_pressure:
        mode = "owner_pressure_quiet"
    else:
        mode = "ordinary_owner_quiet"

    decisions: list[PromptSidecarDecision] = []
    for candidate in candidates:
        if not candidate.parts:
            continue
        admitted, reason = _admission_decision(
            candidate,
            owner_private=owner_private,
            quiet_owner_mode=quiet_owner_mode,
            technical_work=technical_work,
            owner_pressure=owner_pressure,
            context_reference=context_reference,
            status_reference=status_reference,
            digest_reference=digest_reference,
        )
        decisions.append(PromptSidecarDecision(candidate, admitted, reason))

    return PromptPressureSelection(
        decisions=tuple(decisions),
        mode=mode,
        turn_kind=turn_kind,
        owner_private=owner_private,
        context_reference=context_reference,
        status_reference=status_reference,
        digest_reference=digest_reference,
    )


def write_prompt_pressure_report(root: Path, report: dict[str, Any]) -> None:
    write_prompt_pressure_report_json(root / PROMPT_PRESSURE_REPORT_REL, report)


def _admission_decision(
    candidate: PromptSidecar,
    *,
    owner_private: bool,
    quiet_owner_mode: bool,
    technical_work: bool,
    owner_pressure: bool,
    context_reference: bool,
    status_reference: bool,
    digest_reference: bool,
) -> tuple[bool, str]:
    if lean_prompt_enabled():
        if lean_sidecar_admitted(candidate.name):
            return True, "lean_whitelist_admitted"
        return False, "lean_meta_state_dropped"
    if candidate.required:
        return True, "required"
    if candidate.admission == "conversation_experience":
        if technical_work or owner_pressure or context_reference or status_reference:
            return True, "conversation_experience_relevant"
        if not owner_private:
            return False, "conversation_experience_deferred_non_owner_low_pressure"
        return False, "conversation_experience_deferred_quiet_turn"
    if not owner_private:
        return True, "non_owner_preserve_existing_context"

    admission = candidate.admission
    if admission in {"core", "current_turn", "support"}:
        return True, f"{admission}_admitted"
    if admission == "proactive_reply":
        return True, "current_turn_proactive_reply"
    if admission == "repair":
        if quiet_owner_mode and not (technical_work or owner_pressure or context_reference or status_reference):
            return False, "repair_bias_deferred_in_quiet_owner_turn"
        return True, "repair_bias_relevant"
    if admission == "episodic":
        if technical_work or context_reference or status_reference:
            return True, "episodic_context_requested"
        return False, "episodic_context_deferred"
    if admission == "continuity":
        if technical_work or context_reference:
            return True, "continuity_requested"
        return False, "continuity_deferred_current_message_wins"
    if admission == "status":
        if status_reference:
            return True, "runtime_status_requested"
        return False, "runtime_status_deferred"
    if admission == "digest":
        if digest_reference:
            return True, "digest_requested"
        return False, "digest_deferred"
    if admission == "background":
        if technical_work:
            return True, "background_allowed_for_task"
        return False, "background_deferred"
    return True, "default_admitted"


def _decision_entry(decision: PromptSidecarDecision) -> dict[str, Any]:
    sidecar = decision.sidecar
    return {
        "name": sidecar.name,
        "admission": sidecar.admission,
        "required": sidecar.required,
        "char_count": sidecar.char_count,
        "reason": decision.reason,
    }


def _clean_part(value: Any) -> str:
    return _safe_str(value).strip()


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    lowered = _safe_str(value).strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    return default


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    compact = _safe_str(text).lower()
    return any(marker and marker.lower() in compact for marker in markers)


def _compact_text(text: str) -> str:
    return "".join(_safe_str(text).split()).lower()


def _contains_compact_any(compact: str, markers: tuple[str, ...]) -> bool:
    return any(_compact_text(marker) in compact for marker in markers if marker)


def _looks_like_runtime_status_reference(text: str) -> bool:
    compact = _compact_text(text)
    if not compact:
        return False
    if compact.startswith("/status") or compact in {"status", "\u72b6\u6001"}:
        return True

    has_status_object = _contains_any(text, STATUS_REFERENCE_MARKERS)
    has_action = _contains_any(text, STATUS_ACTION_MARKERS)
    has_runtime_object = _contains_compact_any(compact, RUNTIME_STATUS_OBJECT_MARKERS)
    has_health_marker = _contains_compact_any(compact, RUNTIME_HEALTH_MARKERS)
    has_personal_state = _contains_compact_any(compact, PERSONAL_STATE_REFERENCE_MARKERS)

    if has_runtime_object and (has_status_object or has_action or has_health_marker):
        return True
    if has_personal_state:
        return False
    return has_status_object and has_action

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Sequence


_INTERNAL_LABEL_NEEDLES = (
    "retrieval_pressure",
    "evidence_sufficiency",
    "answer_discipline",
    "current_scene",
    "contextual_recall",
    "contextual recall",
    "hidden context",
    "prompt_hash",
    "reply_hash",
    "source_hash",
    "calibration_gate",
    "shadow_gate",
    "log_shadow_gate",
)

_SOURCE_REFERENCE_NEEDLES = (
    "runtime/",
    "memory/context",
    "memory/self",
    "tests/fixtures",
    ".jsonl",
    ".pytest_cache",
)

_UNCERTAINTY_NEEDLES = (
    "cannot verify",
    "can't verify",
    "unable to verify",
    "not sure",
    "cannot tell",
    "can't tell",
    "not enough",
    "missing",
    "uncertain",
    "do not know",
    "don't know",
    "\u4e0d\u786e\u5b9a",
    "\u65e0\u6cd5\u786e\u8ba4",
    "\u4e0d\u80fd\u786e\u8ba4",
    "\u4e0d\u77e5\u9053",
    "\u8bb0\u4e0d\u6e05",
    "\u7f3a\u5c11",
    "\u4e0d\u8db3",
)

_UNSUPPORTED_HISTORY_CLAIMS = (
    "definitely said",
    "previous conversation definitely",
    "previous dialogue definitely",
    "as we discussed",
    "as you said earlier",
    "you said earlier",
    "we already established",
    "\u4e4b\u524d\u660e\u786e\u8bf4\u8fc7",
    "\u524d\u9762\u660e\u786e\u8bf4\u8fc7",
    "\u4e0a\u6b21\u8bf4\u8fc7",
    "\u6211\u4eec\u524d\u9762\u5df2\u7ecf",
)

_CASUAL_TEMPLATE_NEEDLES = (
    "cannot verify the previous dialogue",
    "unable to verify the previous dialogue",
    "no usable prior evidence",
    "missing prior evidence",
    "answer only the current message",
    "\u65e0\u6cd5\u786e\u8ba4\u524d\u9762",
    "\u7f3a\u5c11\u524d\u6587",
)

_PATH_RE = re.compile(r"(?:[a-zA-Z]:\\|/[\w.-]+/|\\[\w.$-]+\\)")


@dataclass(frozen=True, slots=True)
class VisibleReplyConstraints:
    constraint_id: str
    requires_uncertainty: bool
    forbids_unsupported_history_claim: bool
    allows_supported_recall: bool
    answer_current_only: bool
    normal_current_reply: bool
    notes: tuple[str, ...] = ()

    def to_report(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class VisibleReplyGuardResult:
    passed: bool
    constraint_id: str
    flags: dict[str, bool]
    notes: tuple[str, ...] = ()

    def to_report(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "constraint_id": self.constraint_id,
            "flags": dict(self.flags),
            "notes": list(self.notes),
        }


def answer_discipline_visible_constraints(result: dict[str, Any]) -> VisibleReplyConstraints:
    pressure = str(result.get("retrieval_pressure") or "").strip()
    evidence = str(result.get("evidence_sufficiency") or "").strip()
    discipline = str(result.get("answer_discipline") or "").strip()

    if pressure == "high" and evidence == "none":
        return VisibleReplyConstraints(
            constraint_id="high_missing_evidence",
            requires_uncertainty=True,
            forbids_unsupported_history_claim=True,
            allows_supported_recall=False,
            answer_current_only=True,
            normal_current_reply=False,
            notes=("acknowledge_missing_prior_evidence", "do_not_invent_history"),
        )
    if pressure == "high" and evidence == "weak":
        return VisibleReplyConstraints(
            constraint_id="high_weak_evidence",
            requires_uncertainty=True,
            forbids_unsupported_history_claim=True,
            allows_supported_recall=True,
            answer_current_only=False,
            normal_current_reply=False,
            notes=("use_uncertainty", "only_supported_recall"),
        )
    if pressure == "high" and evidence == "usable":
        return VisibleReplyConstraints(
            constraint_id="high_usable_evidence",
            requires_uncertainty=False,
            forbids_unsupported_history_claim=False,
            allows_supported_recall=True,
            answer_current_only=False,
            normal_current_reply=False,
            notes=("compact_supported_evidence_allowed", "no_overclaim"),
        )
    if discipline == "answer_current_only_acknowledge_missing_evidence":
        return VisibleReplyConstraints(
            constraint_id="missing_evidence_by_discipline",
            requires_uncertainty=True,
            forbids_unsupported_history_claim=True,
            allows_supported_recall=False,
            answer_current_only=True,
            normal_current_reply=False,
            notes=("discipline_requires_missing_evidence_ack",),
        )
    return VisibleReplyConstraints(
        constraint_id="current_message_normal",
        requires_uncertainty=False,
        forbids_unsupported_history_claim=False,
        allows_supported_recall=False,
        answer_current_only=False,
        normal_current_reply=True,
        notes=("answer_current_message_normally",),
    )


def evaluate_visible_reply_for_answer_discipline(
    reply: str,
    result: dict[str, Any],
) -> VisibleReplyGuardResult:
    constraints = answer_discipline_visible_constraints(result)
    text = str(reply or "").strip()
    lowered = text.lower()
    uncertainty = _has_any(lowered, _UNCERTAINTY_NEEDLES)
    leaked_internal_label = _has_any(lowered, _INTERNAL_LABEL_NEEDLES)
    leaked_source_reference = _has_any(lowered, _SOURCE_REFERENCE_NEEDLES) or bool(_PATH_RE.search(text))
    leaked_gate_or_hash = "gate" in lowered or "hash" in lowered
    unsupported_history_claim = (
        constraints.forbids_unsupported_history_claim and _has_any(lowered, _UNSUPPORTED_HISTORY_CLAIMS)
    )
    missing_required_uncertainty = constraints.requires_uncertainty and bool(text) and not uncertainty
    overconfident_without_evidence = bool(
        constraints.constraint_id in {"high_missing_evidence", "missing_evidence_by_discipline"}
        and text
        and (missing_required_uncertainty or unsupported_history_claim)
    )
    template_like_casual_reply = bool(
        constraints.normal_current_reply and _has_any(lowered, _CASUAL_TEMPLATE_NEEDLES)
    )
    flags = {
        "blank_reply": not bool(text),
        "leaked_internal_label": leaked_internal_label or leaked_source_reference or leaked_gate_or_hash,
        "leaked_source_reference": leaked_source_reference,
        "leaked_gate_or_hash": leaked_gate_or_hash,
        "acknowledged_uncertainty": uncertainty,
        "missing_required_uncertainty": missing_required_uncertainty,
        "unsupported_history_claim": unsupported_history_claim,
        "overconfident_without_evidence": overconfident_without_evidence,
        "template_like_casual_reply": template_like_casual_reply,
    }
    passed = not any(
        flags[name]
        for name in (
            "blank_reply",
            "leaked_internal_label",
            "missing_required_uncertainty",
            "unsupported_history_claim",
            "overconfident_without_evidence",
            "template_like_casual_reply",
        )
    )
    return VisibleReplyGuardResult(
        passed=passed,
        constraint_id=constraints.constraint_id,
        flags=flags,
        notes=_guard_notes(flags),
    )


def synthetic_visible_reply_for_constraints(result: dict[str, Any]) -> str:
    constraints = answer_discipline_visible_constraints(result)
    if constraints.constraint_id in {"high_missing_evidence", "missing_evidence_by_discipline"}:
        return "I cannot verify the previous dialogue, so I can only answer the current message."
    if constraints.constraint_id == "high_weak_evidence":
        return "I am not sure the available context is enough, so I will only use the supported part."
    if constraints.constraint_id == "high_usable_evidence":
        return "Based on the available context, use the recalled point briefly without overstating it."
    return "ok"


def _has_any(text: str, needles: Sequence[str]) -> bool:
    return any(needle in text for needle in needles)


def _guard_notes(flags: dict[str, bool]) -> tuple[str, ...]:
    notes = [name for name, active in flags.items() if active]
    return tuple(notes)

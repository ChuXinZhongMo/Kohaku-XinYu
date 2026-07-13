from __future__ import annotations


__all__ = (
    "TRIAL_FEEDBACK_REL",
    "GROWTH_LOG_REL",
    "EVAL_CASES_REL",
    "DIMENSIONS_REL",
    "EVOLUTION_REL",
    "PROFILE_REL",
    "REFLECTION_LOG_REL",
    "REPORT_REL",
    "SELF_REVIEW_REL",
)

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_persona_health_report_store import read_persona_health_source_text
from xinyu_persona_health_report_store import read_persona_health_text
from xinyu_persona_health_report_store import write_persona_health_report_text
from xinyu_persona_health_report_store import DIMENSIONS_REL, EVAL_CASES_REL, EVOLUTION_REL, GROWTH_LOG_REL, PROFILE_REL, REFLECTION_LOG_REL, REPORT_REL, SELF_REVIEW_REL, TRIAL_FEEDBACK_REL







BLOCKED_STABLE_WRITE = "review_only_not_auto_apply"
BLOCKED_OWNER_WRITE = "blocked_without_explicit_owner_apply"


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _read_text(path: Path, *, limit: int = 80000) -> str:
    return read_persona_health_text(path, limit=limit)


def _extract_dash_value(text: str, key: str, default: str = "unknown") -> str:
    match = re.search(rf"(?m)^-\s*{re.escape(key)}:\s*(.+)$", text)
    if not match:
        match = re.search(rf"(?m)^{re.escape(key)}:\s*(.+)$", text)
    return match.group(1).strip() if match else default


def _section_count(text: str) -> int:
    return len(re.findall(r"(?m)^##\s+", text))


def _dimension_names(text: str) -> list[str]:
    names: list[str] = []
    for match in re.finditer(r"(?m)^-\s*([a-zA-Z0-9_]+):\s*([^\n]+)$", text):
        name = match.group(1).strip()
        if name not in {"active_trial_habit", "owner_feedback_channel", "promotion_rule"}:
            names.append(name)
    return names


def _case_names(text: str) -> list[str]:
    return [match.group(1).strip() for match in re.finditer(r"(?m)^##\s+Case:\s*(.+)$", text)]


def build_persona_health_report(root: Path) -> dict[str, Any]:
    root = root.resolve()
    dimensions = read_persona_health_source_text(root, "dimensions")
    eval_cases = read_persona_health_source_text(root, "eval_cases")
    profile = read_persona_health_source_text(root, "profile")
    evolution = read_persona_health_source_text(root, "evolution")
    self_review = read_persona_health_source_text(root, "self_review")
    trial_feedback = read_persona_health_source_text(root, "trial_feedback")
    growth = read_persona_health_source_text(root, "growth_log")
    reflection = read_persona_health_source_text(root, "reflection_log")
    combined_state = "\n".join([evolution, self_review, trial_feedback])

    dimension_names = _dimension_names(dimensions)
    case_names = _case_names(eval_cases)
    evolution_stage = _extract_dash_value(combined_state, "evolution_stage", "baseline_observation")
    gate_decision = _extract_dash_value(combined_state, "gate_decision", "observe_more")
    trial_permission = _extract_dash_value(combined_state, "trial_permission", "runtime_trial_only")
    stable_permission = _extract_dash_value(
        combined_state + "\n" + dimensions,
        "stable_profile_write_permission",
        BLOCKED_STABLE_WRITE,
    )
    profile_changed = _extract_dash_value(combined_state, "profile_changed", "false")
    active_trial_habit = _extract_dash_value(combined_state, "active_trial_habit", "none")
    deprecated_reaction = _extract_dash_value(combined_state, "deprecated_reaction", "none")

    risks: list[str] = []
    if stable_permission != BLOCKED_STABLE_WRITE:
        risks.append("stable_profile_write_permission_not_blocked")
    if _extract_dash_value(dimensions, "owner_memory_write_permission", BLOCKED_OWNER_WRITE) != BLOCKED_OWNER_WRITE:
        risks.append("owner_memory_write_permission_not_blocked")
    if not dimensions:
        risks.append("missing_personality_dimensions")
    if not eval_cases:
        risks.append("missing_persona_eval_cases")
    if profile_changed.lower() == "true":
        risks.append("stable_profile_changed_requires_review_trace")

    recommendations = [
        "keep_stable_profile_write_review_only",
        "keep_owner_memory_write_blocked_without_explicit_apply",
        "run_persona_eval_cases_before_any_profile_change",
        "record_owner_feedback_before_promoting_trial_habits",
    ]
    if active_trial_habit != "none":
        recommendations.append("keep_active_trial_runtime_only_until_feedback_is_evaluated")
    if len(case_names) < 5:
        recommendations.append("add_more_persona_regression_cases")
    if len(dimension_names) < 6:
        recommendations.append("expand_personality_dimensions_before_refinement")

    return {
        "ok": not any(risk.endswith("not_blocked") for risk in risks),
        "generated_at": _now_iso(),
        "root": str(root),
        "mode": "read_only_persona_preparation",
        "persona_state": {
            "evolution_stage": evolution_stage,
            "gate_decision": gate_decision,
            "trial_permission": trial_permission,
            "stable_profile_write_permission": stable_permission,
            "owner_memory_write_permission": BLOCKED_OWNER_WRITE,
            "profile_changed": profile_changed,
            "active_trial_habit": active_trial_habit,
            "deprecated_reaction": deprecated_reaction,
        },
        "persona_assets": {
            "stable_profile_exists": bool(profile),
            "dimensions_exists": bool(dimensions),
            "dimension_count": len(dimension_names),
            "dimension_names": dimension_names,
            "eval_cases_exists": bool(eval_cases),
            "eval_case_count": len(case_names),
            "eval_case_names": case_names,
            "trial_feedback_exists": bool(trial_feedback),
        },
        "evidence_counts": {
            "growth_entry_estimate": _section_count(growth),
            "reflection_entry_estimate": _section_count(reflection),
        },
        "risk_flags": risks,
        "privacy_boundary": {
            "stable_personality_write": "blocked_review_only",
            "owner_memory_write": BLOCKED_OWNER_WRITE,
            "private_owner_text_in_report": "not_included",
        },
        "recommendations": recommendations,
    }


def build_persona_refinement_proposals(report: dict[str, Any]) -> list[dict[str, Any]]:
    state = report.get("persona_state") if isinstance(report.get("persona_state"), dict) else {}
    assets = report.get("persona_assets") if isinstance(report.get("persona_assets"), dict) else {}
    evidence = report.get("evidence_counts") if isinstance(report.get("evidence_counts"), dict) else {}
    proposals: list[dict[str, Any]] = []

    if state.get("active_trial_habit") and state.get("active_trial_habit") != "none":
        proposals.append(
            {
                "proposal_id": "persona-proposal-active-trial-feedback",
                "target": str(TRIAL_FEEDBACK_REL),
                "type": "trial_feedback_review",
                "suggestion": "collect_owner_feedback_before_any_stable_profile_promotion",
                "evidence": {
                    "active_trial_habit": state.get("active_trial_habit"),
                    "deprecated_reaction": state.get("deprecated_reaction"),
                },
                "risk": "medium_persona_drift_if_auto_applied",
                "auto_apply": False,
                "requires_owner_review": True,
            }
        )

    if int(assets.get("eval_case_count", 0) or 0) >= 5:
        proposals.append(
            {
                "proposal_id": "persona-proposal-run-regression-cases",
                "target": str(EVAL_CASES_REL),
                "type": "persona_regression_check",
                "suggestion": "run_or_review_eval_cases_before_stable_persona_edits",
                "evidence": {"eval_case_count": assets.get("eval_case_count", 0)},
                "risk": "low_read_only",
                "auto_apply": False,
                "requires_owner_review": False,
            }
        )

    if int(evidence.get("growth_entry_estimate", 0) or 0) > int(evidence.get("reflection_entry_estimate", 0) or 0):
        proposals.append(
            {
                "proposal_id": "persona-proposal-evidence-balance",
                "target": str(GROWTH_LOG_REL),
                "type": "evidence_balance_review",
                "suggestion": "pair_growth_evidence_with_reflection_or_owner_feedback_before_profile_change",
                "evidence": evidence,
                "risk": "medium_if_growth_is_treated_as_stable_persona",
                "auto_apply": False,
                "requires_owner_review": True,
            }
        )

    return proposals


def render_persona_health_report(report: dict[str, Any], proposals: list[dict[str, Any]] | None = None) -> str:
    proposals = proposals or []
    state = report.get("persona_state") if isinstance(report.get("persona_state"), dict) else {}
    assets = report.get("persona_assets") if isinstance(report.get("persona_assets"), dict) else {}
    evidence = report.get("evidence_counts") if isinstance(report.get("evidence_counts"), dict) else {}
    boundary = report.get("privacy_boundary") if isinstance(report.get("privacy_boundary"), dict) else {}
    lines = [
        "# XinYu Persona Health Report",
        "",
        f"- generated_at: {report.get('generated_at', 'unknown')}",
        f"- root: {report.get('root', 'unknown')}",
        f"- mode: {report.get('mode', 'read_only_persona_preparation')}",
        "- stable_profile_write: blocked",
        "- owner_memory_write: blocked",
        "- private_owner_text: not_included",
        "",
        "## Persona State",
    ]
    for key in sorted(state):
        lines.append(f"- {key}: {state[key]}")
    lines.extend(["", "## Persona Assets"])
    for key in sorted(assets):
        value = assets[key]
        if isinstance(value, list):
            value = ", ".join(str(item) for item in value) or "none"
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Evidence Counts"])
    for key in sorted(evidence):
        lines.append(f"- {key}: {evidence[key]}")
    lines.extend(["", "## Risk Flags"])
    risk_flags = report.get("risk_flags") if isinstance(report.get("risk_flags"), list) else []
    if risk_flags:
        lines.extend(f"- {flag}" for flag in risk_flags)
    else:
        lines.append("- none")
    lines.extend(["", "## Privacy Boundary"])
    for key in sorted(boundary):
        lines.append(f"- {key}: {boundary[key]}")
    lines.extend(["", "## Refinement Proposals"])
    if proposals:
        for proposal in proposals:
            lines.append(
                "- "
                f"id={proposal.get('proposal_id')}; "
                f"type={proposal.get('type')}; "
                f"target={proposal.get('target')}; "
                f"auto_apply={str(proposal.get('auto_apply')).lower()}; "
                f"requires_owner_review={str(proposal.get('requires_owner_review')).lower()}; "
                f"suggestion={proposal.get('suggestion')}"
            )
    else:
        lines.append("- none")
    lines.extend(["", "## Recommendations"])
    for recommendation in report.get("recommendations", []):
        lines.append(f"- {recommendation}")
    return "\n".join(lines).rstrip() + "\n"


def write_persona_health_report(root: Path, report: dict[str, Any], proposals: list[dict[str, Any]]) -> Path:
    return write_persona_health_report_text(root, render_persona_health_report(report, proposals))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a read-only XinYu persona health report.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--write-report", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = build_persona_health_report(args.root)
    proposals = build_persona_refinement_proposals(report)
    payload = {**report, "refinement_proposals": proposals}
    if args.write_report:
        payload["report_path"] = str(write_persona_health_report(args.root, report, proposals))
    if args.json or not args.write_report:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

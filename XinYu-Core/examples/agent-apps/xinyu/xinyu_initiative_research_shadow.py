from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

from xinyu_initiative_orchestrator import run_initiative_orchestrator


REPORT_REL = Path("runtime/initiative_research_shadow_report.json")
WORKSPACE_REL = Path("runtime/initiative_research_shadow_workspace")


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _timestamp_or_now_iso(value: Any) -> str:
    parsed = _parse_iso(value)
    if parsed is None:
        return _now_iso()
    return parsed.astimezone().isoformat()


def _parse_iso(value: Any) -> datetime | None:
    text = "" if value is None else str(value).strip()
    if not text or text == "none":
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed


@dataclass(frozen=True, slots=True)
class InitiativeResearchCase:
    case_id: str
    scene: str
    posture: str
    recall_count: int
    expected_status: str
    expected_recall_support: bool
    seed_kind: str = "proactive_request"


DEFAULT_CASES: tuple[InitiativeResearchCase, ...] = (
    InitiativeResearchCase(
        case_id="quiet_without_recall_holds",
        scene="casual_chat",
        posture="quiet_by_default",
        recall_count=0,
        expected_status="hold_private",
        expected_recall_support=False,
    ),
    InitiativeResearchCase(
        case_id="feedback_with_recall_can_surface_locally",
        scene="initiative_feedback",
        posture="feedback_shaped",
        recall_count=2,
        expected_status="desktop_inbox",
        expected_recall_support=True,
    ),
    InitiativeResearchCase(
        case_id="feedback_without_recall_holds",
        scene="initiative_feedback",
        posture="feedback_shaped",
        recall_count=0,
        expected_status="hold_private",
        expected_recall_support=False,
    ),
    InitiativeResearchCase(
        case_id="memory_review_holds",
        scene="memory_review",
        posture="feedback_shaped",
        recall_count=2,
        expected_status="hold_private",
        expected_recall_support=True,
    ),
)


def run_initiative_research_shadow(
    root: Path | str,
    *,
    cases: Sequence[InitiativeResearchCase] = DEFAULT_CASES,
    run_id: str | None = None,
    write_report: bool = True,
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    observed_at = _timestamp_or_now_iso(_now_iso())
    run_id = _clean_token(run_id or "initiative-research-" + datetime.now().astimezone().strftime("%Y%m%dT%H%M%S"))
    results = [_run_case(root_path, case, run_id=run_id, observed_at=observed_at) for case in cases]
    report = _build_report(run_id=run_id, observed_at=observed_at, results=results)
    if write_report:
        _write_json_atomic(root_path / REPORT_REL, report)
    return report


def _run_case(root: Path, case: InitiativeResearchCase, *, run_id: str, observed_at: str) -> dict[str, Any]:
    case_root = root / WORKSPACE_REL / run_id / case.case_id
    _seed_case(case_root, case, observed_at=observed_at)
    result = run_initiative_orchestrator(
        case_root,
        checked_at=observed_at,
        trigger="initiative_research_shadow",
        delivery_level="desktop_inbox",
        dry_run=True,
    )
    context_gate = result.get("context_gate") if isinstance(result.get("context_gate"), dict) else {}
    delivery_level = str(result.get("delivery_level") or "")
    matched_expectation = (
        result.get("status") == case.expected_status
        and bool(context_gate.get("recall_support")) is case.expected_recall_support
        and delivery_level in {"dry_run", "none"}
        and not bool(result.get("desktop_item"))
    )
    return {
        "case_id": case.case_id,
        "scenario_hash": _short_hash(f"{case.scene}:{case.posture}:{case.recall_count}:{case.seed_kind}", length=16),
        "seed_kind": case.seed_kind,
        "status": result.get("status", ""),
        "expected_status": case.expected_status,
        "matched_expectation": matched_expectation,
        "candidate_count": result.get("candidate_count", 0),
        "decision_count": result.get("decision_count", 0),
        "delivery_level": delivery_level,
        "desktop_item_created": bool(result.get("desktop_item")),
        "context_gate": {
            "observed": bool(context_gate.get("observed")),
            "current_scene": str(context_gate.get("current_scene") or ""),
            "initiative_posture": str(context_gate.get("initiative_posture") or ""),
            "recall_support": bool(context_gate.get("recall_support")),
            "admitted_recall_count": int(context_gate.get("admitted_recall_count") or 0),
            "stale": bool(context_gate.get("stale")),
        },
        "research_signals": {
            "selective_retrieval_alignment": bool(context_gate.get("recall_support")) is case.expected_recall_support,
            "context_restraint_alignment": result.get("status") == case.expected_status,
            "outward_delivery_blocked": delivery_level in {"dry_run", "none"} and not bool(result.get("desktop_item")),
        },
        "notes": ["shadow_only", "isolated_workspace", "no_outward_delivery", "no_raw_owner_text"],
    }


def _build_report(*, run_id: str, observed_at: str, results: list[dict[str, Any]]) -> dict[str, Any]:
    gate = _research_gate(results)
    return {
        "run_id": run_id,
        "updated_at": _timestamp_or_now_iso(observed_at),
        "case_count": len(results),
        "cases": results,
        "research_gate": gate,
        "boundaries": {
            "initiative_delivery": "blocked_by_dry_run",
            "real_bridge_behavior": "unchanged",
            "long_term_memory_writes": "blocked_outside_isolated_workspace",
            "raw_owner_text_in_report": "blocked",
            "consciousness_claims": "blocked",
        },
    }


def _research_gate(results: Sequence[dict[str, Any]]) -> dict[str, Any]:
    mismatch_count = sum(1 for item in results if not item.get("matched_expectation"))
    outward_delivery_count = sum(
        1
        for item in results
        if item.get("delivery_level") not in {"dry_run", "none"} or item.get("desktop_item_created")
    )
    recall_alignment_count = sum(
        1 for item in results if item.get("research_signals", {}).get("selective_retrieval_alignment")
    )
    restraint_alignment_count = sum(
        1 for item in results if item.get("research_signals", {}).get("context_restraint_alignment")
    )
    checks = [
        _gate_check("cases_loaded", len(results) > 0),
        _gate_check("expected_shadow_outcomes_match", mismatch_count == 0),
        _gate_check("no_outward_delivery", outward_delivery_count == 0),
        _gate_check("selective_retrieval_alignment_observed", recall_alignment_count == len(results)),
        _gate_check("context_restraint_alignment_observed", restraint_alignment_count == len(results)),
    ]
    passed = all(bool(item["passed"]) for item in checks)
    return {
        "status": "passed" if passed else "failed",
        "passed": passed,
        "counts": {
            "case_count": len(results),
            "mismatch_count": mismatch_count,
            "outward_delivery_count": outward_delivery_count,
            "recall_alignment_count": recall_alignment_count,
            "restraint_alignment_count": restraint_alignment_count,
        },
        "checks": checks,
    }


def _seed_case(root: Path, case: InitiativeResearchCase, *, observed_at: str) -> None:
    _seed_context_gate(
        root,
        scene=case.scene,
        posture=case.posture,
        recall_count=case.recall_count,
        observed_at=_timestamp_or_now_iso(observed_at),
    )
    if case.seed_kind == "none":
        return
    _seed_proactive_request(root, request_id="proreq-" + case.case_id, observed_at=_timestamp_or_now_iso(observed_at))


def _seed_proactive_request(root: Path, *, request_id: str, observed_at: str) -> None:
    path = root / "memory/context/proactive_request_state.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "---",
                "title: Proactive Request State",
                f"updated_at: {_timestamp_or_now_iso(observed_at)}",
                "---",
                "",
                "# Proactive Request State",
                "",
                "## Current Request",
                f"- request_id: {_clean_token(request_id)}",
                f"- created_at: {_timestamp_or_now_iso(observed_at)}",
                "- status: ready",
                "- kind: reflection_question",
                "- source: self_thought",
                "- focus_kind: reflection",
                "- focus_label: grounded research shadow",
                "- evidence_label: owner_relevant fresh",
                "- evidence_hash: sha256:initiative_research_shadow",
                "- concrete_question: A grounded follow-up is ready for local review.",
                "- requested_action: owner_review",
                "- request_answer_state: pending",
                "- delivery_level: queue_owner_private",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _seed_context_gate(root: Path, *, scene: str, posture: str, recall_count: int, observed_at: str) -> None:
    evaluated_at = _timestamp_or_now_iso(observed_at)
    state_path = root / "memory/context/contextual_self_loop_state.md"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        "\n".join(
            [
                f"- evaluated_at: {evaluated_at}",
                "- last_trigger: initiative_research_shadow",
                f"- current_scene: {_clean_token(scene)}",
                "- working_context_budget: short",
                "- forgetting_posture: research_shadow",
                "- retrieval_intents: initiative_shadow",
                "- working_self: measured_behavior_only",
                f"- initiative_posture: {_clean_token(posture)}",
                "- next_action_bias: adjust_bias_before_action",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    recall_path = root / "memory/context/contextual_recall_state.md"
    recall_path.write_text(
        "\n".join(
            [
                f"- evaluated_at: {evaluated_at}",
                f"- current_scene: {_clean_token(scene)}",
                "- retrieval_intents: initiative_shadow",
                f"- admitted_recall_count: {max(0, int(recall_count))}",
                "- suppressed_recall_count: 0",
                f"- source_count: {1 if recall_count else 0}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _gate_check(name: str, passed: bool) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed)}


def _write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    tmp.write_text(json.dumps(_clean_json_value(data), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _clean_json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _clean_json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean_json_value(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _short_hash(value: Any, *, length: int = 12) -> str:
    return hashlib.sha256(str(value).encode("utf-8", errors="replace")).hexdigest()[:length]


def _clean_token(value: str) -> str:
    text = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "-" for ch in str(value).strip())
    while "--" in text:
        text = text.replace("--", "-")
    return text.strip("-")[:80] or "shadow"


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run XinYu initiative research shadow calibration.")
    parser.add_argument("--root", default=".", help="XinYu app root. Defaults to current directory.")
    parser.add_argument("--run-id", default="", help="Optional isolated run id.")
    parser.add_argument("--strict-gate", action="store_true", help="Exit non-zero if the research gate fails.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    report = run_initiative_research_shadow(Path(args.root), run_id=args.run_id or None)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    if args.strict_gate and not report.get("research_gate", {}).get("passed"):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

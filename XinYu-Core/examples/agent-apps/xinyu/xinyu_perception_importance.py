from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_perception_event_layer import build_perception_event_layer_report
from xinyu_state_io import read_text, write_text_atomic


STATE_REL = Path("memory/context/perception_importance_state.md")
TRACE_REL = Path("runtime/perception_importance_trace.jsonl")
REPORT_REL = Path("worklog/xinyu-perception-importance-latest.md")

NONE_VALUES = {"", "missing", "none", "unknown", "null"}


def build_perception_importance_report(
    root: Path,
    *,
    generated_at: str | None = None,
    perception_event_layer: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(root).resolve()
    generated_at = generated_at or _now_iso()
    event_layer = (
        perception_event_layer
        if isinstance(perception_event_layer, dict)
        else build_perception_event_layer_report(root, generated_at=generated_at)
    )
    events = event_layer.get("events") if isinstance(event_layer.get("events"), list) else []
    judgments = [_judge_event(event) for event in events if isinstance(event, dict)]
    metrics = _metrics(judgments, event_layer)
    status = _status(len(events), judgments, metrics)
    return {
        "ok": status in {"pass", "partial"},
        "status": status,
        "generated_at": generated_at,
        "root": str(root),
        "metrics": metrics,
        "judgments": [_public_judgment(judgment) for judgment in judgments[:16]],
        "privacy": {
            "raw_private_body_retained": False,
            "visible_reply_text_retained": False,
            "private_text_in_report": False,
            "stable_memory_write": "blocked",
        },
        "notes": _notes(status, metrics),
    }


def render_perception_importance_report(report: dict[str, Any]) -> str:
    metrics = report.get("metrics") if isinstance(report.get("metrics"), dict) else {}
    judgments = report.get("judgments") if isinstance(report.get("judgments"), list) else []
    privacy = report.get("privacy") if isinstance(report.get("privacy"), dict) else {}
    lines = [
        "# XinYu Perception Importance",
        "",
        f"- generated_at: {report.get('generated_at', 'unknown')}",
        f"- status: {report.get('status', 'unknown')}",
        f"- result: {'pass' if report.get('ok') else 'needs_check'}",
        "- claim_boundary: judges event pressure and internal gaps only; does not claim consciousness",
        "",
        "## Metrics",
    ]
    for key in (
        "event_count",
        "judged_event_count",
        "high_attention_count",
        "anomaly_judgment_count",
        "internal_gap_count",
        "owner_attention_count",
        "repair_gap_count",
        "boundary_gap_count",
        "action_residue_count",
        "maintenance_gap_count",
        "sensory_observation_count",
        "coverage_gap_count",
        "max_attention_weight",
        "latest_gap_type",
        "latest_future_effect",
        "latest_event_ref",
        "next_route_hint",
    ):
        lines.append(f"- {key}: {metrics.get(key, 'missing')}")
    lines.extend(["", "## Event Judgments"])
    if judgments:
        for judgment in judgments[:16]:
            lines.append(f"### {judgment.get('judgment_id', 'unknown')}")
            for key in (
                "event_id",
                "event_type",
                "source",
                "attention_class",
                "attention_weight",
                "gap_type",
                "anomaly_kind",
                "internal_pressure",
                "suggested_route",
                "future_effect",
                "evidence_ref",
            ):
                lines.append(f"- {key}: {judgment.get(key, 'missing')}")
    else:
        lines.append("- none")
    lines.extend(["", "## Privacy Boundary"])
    for key, value in privacy.items():
        lines.append(f"- {key}: {str(value).lower()}")
    lines.extend(["", "## Notes"])
    notes = report.get("notes") if isinstance(report.get("notes"), list) else []
    lines.extend(f"- {note}" for note in notes) if notes else lines.append("- none")
    return "\n".join(lines).rstrip() + "\n"


def write_perception_importance_report(
    root: Path,
    report: dict[str, Any],
    *,
    output: Path | None = None,
) -> dict[str, str]:
    root = Path(root).resolve()
    report_path = output if output is not None else root / REPORT_REL
    if not report_path.is_absolute():
        report_path = root / report_path
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_perception_importance_report(report), encoding="utf-8")
    _write_state(root, report, report_path=report_path)
    _append_trace(root, report)
    return {"report_path": str(report_path), "state_path": str(root / STATE_REL)}


def read_perception_importance_state(root: Path) -> dict[str, str]:
    text = read_text(Path(root) / STATE_REL)
    if not text:
        return {"status": "missing", "event_count": "0", "judged_event_count": "0"}
    return _parse_fields(text)


def perception_gap_signal(report: dict[str, Any]) -> dict[str, str]:
    metrics = report.get("metrics") if isinstance(report.get("metrics"), dict) else {}
    judgments = report.get("judgments") if isinstance(report.get("judgments"), list) else []
    selected = _prioritized_public_judgment(judgments)
    gap_type = _safe_token(selected.get("gap_type") if selected else metrics.get("latest_gap_type"), default="none")
    if gap_type in NONE_VALUES:
        gap_type = "none"
    route_hint = (
        _one_line(selected.get("suggested_route")) if selected else _one_line(metrics.get("next_route_hint"))
    ) or "none"
    future_effect = (
        _one_line(selected.get("future_effect")) if selected else _one_line(metrics.get("latest_future_effect"))
    ) or "none"
    evidence_ref = (
        _one_line(selected.get("evidence_ref")) if selected else _one_line(metrics.get("latest_event_ref"))
    ) or "none"
    return {
        "status": _safe_token(report.get("status"), default="missing"),
        "gap_type": gap_type,
        "route_hint": route_hint,
        "future_effect": future_effect,
        "attention_weight": str(_int(selected.get("attention_weight") if selected else metrics.get("max_attention_weight"))),
        "event_id": _one_line(selected.get("event_id") if selected else "") or "none",
        "evidence_ref": evidence_ref,
        "bias": perception_gap_bias(report),
    }


def perception_gap_bias(report: dict[str, Any]) -> str:
    gap_type = _safe_token(_prioritized_gap_type(report), default="none")
    return {
        "owner_attention": "owner_attention_current_turn_value:+6;require_short_term_anchor",
        "repair_gap": "perception_repair_gap_visible_risk:+8;proactive_future_block",
        "boundary_gap": "boundary_gap_external_or_group_risk:+8;proactive_future_block",
        "action_residue": "action_residue_requires_feedback_consumption",
        "maintenance_gap": "maintenance_gap_task_claim_risk:+6;verify_runtime_or_source_before_claim",
        "sensory_observation": "sensory_observation_confidence_boundary",
        "observation_gap": "observation_gap_keep_auditable_until_consumed",
    }.get(gap_type, "none")


def _judge_event(event: dict[str, Any]) -> dict[str, Any]:
    event_type = _safe_token(event.get("event_type"), default="unknown")
    source = _safe_token(event.get("source"), default="unknown")
    importance = _safe_token(event.get("importance"), default="normal")
    anomaly = bool(event.get("anomaly"))
    confidence = _safe_token(event.get("confidence"), default="medium")
    observed_at = _one_line(event.get("observed_at")) or "unknown"
    evidence_ref = _one_line(event.get("evidence_ref")) or "none"
    event_id = _one_line(event.get("event_id")) or _content_ref(f"{event_type}|{source}|{observed_at}|{evidence_ref}")

    if event_type == "owner_text_input":
        gap_type = "owner_attention"
        pressure = "current_turn_needs_attention_or_explained_hold"
        route = "attention_posture_and_intention_ecology"
        future = "raise_current_turn_attention_and_require_short_term_anchor"
        weight = 90
    elif event_type == "qq_drop":
        gap_type = "repair_gap"
        pressure = "visible_reply_order_or_delivery_needs_repair"
        route = "gate_repair_before_visible_send"
        future = "prefer_latest_input_and_retraction_before_any_visible_reply"
        weight = 95
    elif event_type == "qq_group_boundary":
        gap_type = "boundary_gap"
        pressure = "non_private_or_group_event_requires_boundary"
        route = "boundary_gate"
        future = "keep_group_or_non_owner_event_from_private_memory_and_unsanctioned_reply"
        weight = 60
    elif event_type == "desktop_ack":
        if anomaly:
            gap_type = "repair_gap"
            pressure = "desktop_delivery_or_adapter_state_needs_repair"
            route = "request_feedback_diagnostics"
            future = "check_desktop_delivery_before_repeating_request"
            weight = 85
        else:
            gap_type = "action_residue"
            pressure = "desktop_owner_response_or_request_state_should_update_strategy"
            route = "owner_response_feedback_and_intention_ecology"
            future = "route_desktop_request_state_into_next_request_strategy"
            weight = 70
    elif event_type in {"qq_ack", "qq_feedback"}:
        gap_type = "action_residue"
        pressure = "visible_action_result_should_update_transport_confidence"
        route = "action_feedback_surface"
        future = "confirm_or_adjust_visible_reply_transport_for_next_turn"
        weight = 45
    elif event_type == "tool_execution_result":
        gap_type = "repair_gap" if anomaly else "action_residue"
        pressure = "tool_result_should_change_task_strategy"
        route = "action_feedback_coverage"
        future = "adjust_next_tool_or_task_choice_from_result"
        weight = 80 if anomaly else 50
    elif event_type == "system_health_change":
        gap_type = "maintenance_gap"
        pressure = "runtime_health_should_bound_future_action"
        route = "runtime_presence_and_action_gate"
        future = "avoid_or_resume_actions_based_on_runtime_health"
        weight = 85 if anomaly else 50
    elif event_type == "file_change":
        gap_type = "maintenance_gap"
        pressure = "source_change_should_be_verified_before_claiming_loaded_behavior"
        route = "code_change_awareness"
        future = "verify_restart_need_before_next_runtime_claim"
        weight = 75
    elif event_type == "visual_observation_result":
        gap_type = "sensory_observation"
        pressure = "visual_observation_should_be_kept_as_observation_not_fact"
        route = "multimodal_perception_gate"
        future = "let_visual_observation_influence_candidates_with_confidence_boundary"
        weight = 75
    elif event_type == "voice_input_result":
        gap_type = "owner_attention"
        pressure = "voice_input_should_enter_current_turn_or_memory_review"
        route = "voice_to_text_input_gate"
        future = "treat_voice_transcript_as_input_with_confidence_boundary"
        weight = 85
    else:
        gap_type = "observation_gap"
        pressure = "event_should_remain_auditable_until_consumed"
        route = "attention_posture"
        future = "keep_event_available_for_next_state_update"
        weight = 40

    if importance == "high":
        weight = max(weight, 80)
    elif importance == "boundary":
        weight = max(weight, 60)
    elif importance == "low":
        weight = min(weight, 35)
    if anomaly:
        weight = max(weight, 85)
    if confidence == "low":
        weight = max(10, weight - 15)
    elif confidence == "high":
        weight = min(100, weight + 5)

    anomaly_kind = "none"
    if anomaly:
        anomaly_kind = {
            "qq_drop": "stale_or_dropped_visible_reply",
            "desktop_ack": "desktop_delivery_or_adapter_anomaly",
            "tool_execution_result": "tool_execution_anomaly",
            "system_health_change": "runtime_health_anomaly",
        }.get(event_type, "event_anomaly")

    judgment_id = "percimp-" + _hash(f"{event_id}|{gap_type}|{weight}|{future}")[:16]
    return {
        "judgment_id": judgment_id,
        "event_id": event_id,
        "event_type": event_type,
        "source": source,
        "observed_at": observed_at,
        "evidence_ref": evidence_ref,
        "attention_weight": max(0, min(100, int(weight))),
        "attention_class": _attention_class(weight),
        "gap_type": gap_type,
        "anomaly_kind": anomaly_kind,
        "internal_pressure": pressure,
        "suggested_route": route,
        "future_effect": future,
        "raw_private_body_retained": False,
        "visible_text_retained": False,
    }


def _metrics(judgments: list[dict[str, Any]], event_layer: dict[str, Any]) -> dict[str, Any]:
    event_metrics = event_layer.get("metrics") if isinstance(event_layer.get("metrics"), dict) else {}
    event_count = _int(event_metrics.get("event_count"), len(judgments))
    latest = _latest_judgment(judgments)
    coverage_gap_count = 0
    if _int(event_metrics.get("visual_event_count"), 0) <= 0:
        coverage_gap_count += 1
    if _int(event_metrics.get("voice_event_count"), 0) <= 0:
        coverage_gap_count += 1
    return {
        "event_count": event_count,
        "judged_event_count": len(judgments),
        "high_attention_count": sum(1 for item in judgments if _int(item.get("attention_weight")) >= 75),
        "anomaly_judgment_count": sum(1 for item in judgments if _safe_token(item.get("anomaly_kind"), default="none") != "none"),
        "internal_gap_count": len({str(item.get("gap_type", "")) for item in judgments if _present(item.get("gap_type"))}),
        "owner_attention_count": _gap_count(judgments, "owner_attention"),
        "repair_gap_count": _gap_count(judgments, "repair_gap"),
        "boundary_gap_count": _gap_count(judgments, "boundary_gap"),
        "action_residue_count": _gap_count(judgments, "action_residue"),
        "maintenance_gap_count": _gap_count(judgments, "maintenance_gap"),
        "sensory_observation_count": _gap_count(judgments, "sensory_observation"),
        "coverage_gap_count": coverage_gap_count,
        "max_attention_weight": max((_int(item.get("attention_weight")) for item in judgments), default=0),
        "latest_gap_type": latest.get("gap_type", "none"),
        "latest_future_effect": latest.get("future_effect", "none"),
        "latest_event_ref": latest.get("evidence_ref", "none"),
        "next_route_hint": _next_route_hint(judgments),
    }


def _status(event_count: int, judgments: list[dict[str, Any]], metrics: dict[str, Any]) -> str:
    if event_count <= 0:
        return "no_events"
    if len(judgments) < event_count:
        return "needs_check"
    if _int(metrics.get("internal_gap_count")) <= 0:
        return "needs_check"
    if _int(metrics.get("high_attention_count")) <= 0:
        return "partial"
    return "pass"


def _notes(status: str, metrics: dict[str, Any]) -> list[str]:
    notes: list[str] = []
    if status == "no_events":
        notes.append("no_events_available_for_importance_judgment")
    if _int(metrics.get("owner_attention_count")) > 0:
        notes.append("owner_input_creates_attention_pressure")
    if _int(metrics.get("repair_gap_count")) > 0:
        notes.append("repair_gap_visible_from_perception")
    if _int(metrics.get("boundary_gap_count")) > 0:
        notes.append("boundary_gap_visible_from_perception")
    if _int(metrics.get("action_residue_count")) > 0:
        notes.append("action_result_residue_ready_for_feedback_loop")
    if _int(metrics.get("maintenance_gap_count")) > 0:
        notes.append("maintenance_gap_visible_from_runtime_or_file_events")
    if _int(metrics.get("coverage_gap_count")) > 0:
        notes.append("visual_or_voice_sources_not_connected_yet")
    if status == "pass":
        notes.append("perception_events_have_importance_judgments_and_internal_gap_routes")
    return notes


def _write_state(root: Path, report: dict[str, Any], *, report_path: Path) -> None:
    metrics = report.get("metrics") if isinstance(report.get("metrics"), dict) else {}
    text = f"""---
title: Perception Importance State
memory_type: perception_importance_state
time_scope: rolling_runtime
subject_ids: [xinyu, owner]
protected: true
source: xinyu_perception_importance
updated_at: {report.get('generated_at', 'unknown')}
status: active
tags: [autonomy, perception, importance, internal-gap]
---

# Perception Importance State

## Current Judgment
- status: {report.get('status', 'unknown')}
- checked_at: {report.get('generated_at', 'unknown')}
- event_count: {metrics.get('event_count', 0)}
- judged_event_count: {metrics.get('judged_event_count', 0)}
- high_attention_count: {metrics.get('high_attention_count', 0)}
- anomaly_judgment_count: {metrics.get('anomaly_judgment_count', 0)}
- internal_gap_count: {metrics.get('internal_gap_count', 0)}
- owner_attention_count: {metrics.get('owner_attention_count', 0)}
- repair_gap_count: {metrics.get('repair_gap_count', 0)}
- boundary_gap_count: {metrics.get('boundary_gap_count', 0)}
- action_residue_count: {metrics.get('action_residue_count', 0)}
- maintenance_gap_count: {metrics.get('maintenance_gap_count', 0)}
- sensory_observation_count: {metrics.get('sensory_observation_count', 0)}
- coverage_gap_count: {metrics.get('coverage_gap_count', 0)}
- max_attention_weight: {metrics.get('max_attention_weight', 0)}
- latest_gap_type: {metrics.get('latest_gap_type', 'none')}
- latest_future_effect: {metrics.get('latest_future_effect', 'none')}
- latest_event_ref: {metrics.get('latest_event_ref', 'none')}
- next_route_hint: {metrics.get('next_route_hint', 'none')}

## Boundaries
- report_path: {report_path.as_posix()}
- raw_private_body_retained: false
- visible_reply_text_retained: false
- private_text_in_report: false
- stable_memory_write: blocked
"""
    write_text_atomic(root / STATE_REL, text)


def _append_trace(root: Path, report: dict[str, Any]) -> None:
    metrics = report.get("metrics") if isinstance(report.get("metrics"), dict) else {}
    judgments = report.get("judgments") if isinstance(report.get("judgments"), list) else []
    row = {
        "generated_at": report.get("generated_at", ""),
        "status": report.get("status", ""),
        "ok": bool(report.get("ok")),
        "metrics": metrics,
        "judgment_refs": [
            {
                "judgment_id": judgment.get("judgment_id"),
                "event_id": judgment.get("event_id"),
                "event_type": judgment.get("event_type"),
                "gap_type": judgment.get("gap_type"),
                "attention_weight": judgment.get("attention_weight"),
                "evidence_ref": judgment.get("evidence_ref"),
                "future_effect": judgment.get("future_effect"),
            }
            for judgment in judgments[:16]
            if isinstance(judgment, dict)
        ],
        "raw_private_body_retained": False,
        "visible_reply_text_retained": False,
    }
    path = root / TRACE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def _public_judgment(judgment: dict[str, Any]) -> dict[str, Any]:
    return {
        "judgment_id": _one_line(judgment.get("judgment_id")),
        "event_id": _one_line(judgment.get("event_id")),
        "event_type": _one_line(judgment.get("event_type")),
        "source": _one_line(judgment.get("source")),
        "observed_at": _one_line(judgment.get("observed_at")),
        "attention_class": _one_line(judgment.get("attention_class")),
        "attention_weight": _int(judgment.get("attention_weight")),
        "gap_type": _one_line(judgment.get("gap_type")),
        "anomaly_kind": _one_line(judgment.get("anomaly_kind")),
        "internal_pressure": _one_line(judgment.get("internal_pressure")),
        "suggested_route": _one_line(judgment.get("suggested_route")),
        "future_effect": _one_line(judgment.get("future_effect")),
        "evidence_ref": _one_line(judgment.get("evidence_ref")),
    }


def _latest_judgment(judgments: list[dict[str, Any]]) -> dict[str, Any]:
    if not judgments:
        return {}
    dated: list[tuple[float, dict[str, Any]]] = []
    for judgment in judgments:
        parsed = _parse_timestamp(judgment.get("observed_at"))
        if parsed is not None:
            dated.append((_time_sort_value(parsed.isoformat()), judgment))
    if dated:
        dated.sort(key=lambda item: item[0])
        return dated[-1][1]
    return judgments[-1]


def _next_route_hint(judgments: list[dict[str, Any]]) -> str:
    if not judgments:
        return "none"
    priorities = (
        "repair_gap",
        "owner_attention",
        "maintenance_gap",
        "boundary_gap",
        "action_residue",
        "sensory_observation",
        "observation_gap",
    )
    by_gap = {str(item.get("gap_type")): item for item in judgments}
    for gap_type in priorities:
        item = by_gap.get(gap_type)
        if item:
            return _one_line(item.get("suggested_route")) or "attention_posture"
    return "attention_posture"


def _prioritized_public_judgment(judgments: list[Any]) -> dict[str, Any]:
    if not judgments:
        return {}
    priorities = (
        "repair_gap",
        "owner_attention",
        "maintenance_gap",
        "boundary_gap",
        "action_residue",
        "sensory_observation",
        "observation_gap",
    )
    by_gap: dict[str, dict[str, Any]] = {}
    for item in judgments:
        if not isinstance(item, dict):
            continue
        gap_type = _safe_token(item.get("gap_type"), default="none")
        if gap_type not in by_gap:
            by_gap[gap_type] = item
    for gap_type in priorities:
        if gap_type in by_gap:
            return by_gap[gap_type]
    for item in reversed(judgments):
        if isinstance(item, dict):
            return item
    return {}


def _prioritized_gap_type(report: dict[str, Any]) -> str:
    judgments = report.get("judgments") if isinstance(report.get("judgments"), list) else []
    selected = _prioritized_public_judgment(judgments)
    if selected:
        return _safe_token(selected.get("gap_type"), default="none")
    metrics = report.get("metrics") if isinstance(report.get("metrics"), dict) else {}
    return _safe_token(metrics.get("latest_gap_type"), default="none")


def _gap_count(judgments: list[dict[str, Any]], gap_type: str) -> int:
    return sum(1 for item in judgments if item.get("gap_type") == gap_type)


def _parse_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- ") or ":" not in stripped:
            continue
        key, value = stripped[2:].split(":", 1)
        fields[key.strip()] = value.strip()
    return fields


def _parse_timestamp(value: Any) -> datetime | None:
    text = _one_line(value).replace("Z", "+00:00")
    if not text or text.lower() in NONE_VALUES:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _time_sort_value(value: Any) -> float:
    parsed = _parse_timestamp(value)
    if parsed is None:
        return 0.0
    if parsed.tzinfo is None:
        return parsed.timestamp()
    return parsed.timestamp()


def _attention_class(weight: int) -> str:
    value = int(weight)
    if value >= 75:
        return "high"
    if value >= 45:
        return "medium"
    return "low"


def _present(value: Any) -> bool:
    return _one_line(value).lower() not in NONE_VALUES


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_token(value: Any, *, default: str) -> str:
    text = _one_line(value).lower().replace(" ", "_")
    return text or default


def _one_line(value: Any, limit: int = 180) -> str:
    text = " ".join(str(value or "").split())
    if not text:
        return ""
    return text[: max(1, int(limit))]


def _content_ref(value: Any) -> str:
    text = _one_line(value)
    if not text:
        return "none"
    return "sha256:" + _hash(text)[:16]


def _hash(value: Any) -> str:
    return hashlib.sha256(str(value).encode("utf-8", errors="replace")).hexdigest()


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build XinYu perception importance and internal gap judgment.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = args.root.resolve()
    report = build_perception_importance_report(root)
    if args.write:
        report["written"] = write_perception_importance_report(root, report, output=args.output)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_perception_importance_report(report))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

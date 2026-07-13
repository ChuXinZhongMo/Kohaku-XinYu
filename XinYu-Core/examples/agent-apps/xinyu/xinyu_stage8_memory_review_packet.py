from __future__ import annotations


__all__ = (
    "PACKET_REL",
    "STATE_REL",
)

import argparse
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_dialogue_archive import list_memory_candidates
from xinyu_memory_candidate_analysis import candidate_review_context
from xinyu_memory_health_report import CANDIDATE_STATUSES, build_memory_health_report
from xinyu_stage8_memory_review_packet_store import stage8_memory_review_packet_path
from xinyu_stage8_memory_review_packet_store import write_stage8_memory_review_packet_state_text
from xinyu_stage8_memory_review_packet_store import write_stage8_memory_review_packet_text


from xinyu_stage8_duplicate_consolidation_packet_store import PACKET_REL

from xinyu_action_feedback_coverage import STATE_REL

PRIVATE_TEXT_MARKERS = (
    "owner_turn:",
    "visible_reply:",
    "user_turn:",
    "assistant_reply:",
)
CONTROLLED_TOPIC_HINTS = (
    (
        ("模板", "template", "机械", "生硬", "套话", "不像人", "gpt"),
        "reply_style_template_or_mechanical",
        "把相似的模板感、机械感回复降权，优先保留当前对话里的具体语境。",
    ),
    (
        ("嗯", "单字", "低信息", "敷衍"),
        "low_information_short_reply",
        "避免把低信息短回复当作合格回应；需要更明确地接住当前问题。",
    ),
    (
        ("不回", "没回", "卡住", "沉默", "间接性", "卡死"),
        "private_reply_missing_or_stalled",
        "把私聊未回复或卡住视为需要诊断的链路问题，而不是当成正常沉默。",
    ),
    (
        ("刚聊", "刚说", "不记得", "记忆", "忘", "检索", "哪一句"),
        "short_term_memory_or_recall_failure",
        "加强最近对话召回，避免刚发生的内容被当成未知问题。",
    ),
    (
        ("兜底", "为什么不回", "解决", "私聊"),
        "reply_fallback_or_no_reply_repair",
        "优先解释并修复不回复原因，而不是只给兜底话术。",
    ),
    (
        ("阶段", "大纲", "主线", "计划"),
        "roadmap_or_stage_alignment",
        "后续行动需要对齐长期大纲和当前阶段，不要偏离主线。",
    ),
)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        text = str(value)
    except Exception:
        return default
    return text if text else default


def _one_line(value: Any, *, limit: int = 180, default: str = "none") -> str:
    text = re.sub(r"\s+", " ", _safe_str(value)).strip()
    if not text:
        return default
    return text if len(text) <= limit else text[: max(0, limit - 3)].rstrip() + "..."


def _safe_list(value: Any, *, limit: int = 20) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_one_line(item, limit=120, default="") for item in value[: max(0, limit)] if _safe_str(item).strip()]


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _all_candidate_rows(root: Path, *, limit_per_status: int = 1000) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for status in CANDIDATE_STATUSES:
        for row in list_memory_candidates(root, status=status, limit=limit_per_status):
            candidate_id = _safe_str(row.get("candidate_id")).strip()
            if not candidate_id or candidate_id in seen:
                continue
            seen.add(candidate_id)
            rows.append(row)
    return rows


def _has_private_text_shape(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in PRIVATE_TEXT_MARKERS)


def _controlled_topic_hint(row: dict[str, Any]) -> tuple[str, str]:
    text = "\n".join(
        [
            _safe_str(row.get("candidate_text")),
            _safe_str(row.get("reason")),
            " ".join(_safe_list(row.get("risk_flags"))),
        ]
    ).lower()
    for markers, topic_key, readable_effect in CONTROLLED_TOPIC_HINTS:
        if any(marker.lower() in text for marker in markers):
            return topic_key, readable_effect
    candidate_type = _safe_str(row.get("candidate_type"))
    target = _safe_str(row.get("target_memory_layer")).replace("\\", "/")
    if candidate_type == "owner_preference" or target == "memory/people/owner.md":
        return (
            "owner_preference_boundary_unspecified",
            "记录 owner 对某类做法的偏好边界；后续只能作为降权/提醒信号，不能覆盖当前对话。",
        )
    if candidate_type == "relationship_signal" or target == "memory/relationships/index.md":
        return (
            "relationship_signal_unspecified",
            "记录关系姿态相关信号；后续只能作为观察线索，不能写成稳定关系事实。",
        )
    if candidate_type == "voice_correction":
        return (
            "voice_correction_unspecified",
            "记录表达风格修正信号；后续只用于降低相似表达风险。",
        )
    return (
        "review_topic_unspecified",
        "记录一条需要复核的候选信息；批准前仍不能当成稳定事实。",
    )


def _approval_question(row: dict[str, Any], review: dict[str, Any], topic_effect: str) -> str:
    candidate_type = _safe_str(row.get("candidate_type"), "memory_candidate")
    polarity = _safe_str(review.get("claim_polarity"), "unknown")
    if candidate_type == "owner_preference" and polarity == "negative":
        return f"是否允许把这条候选作为 owner 的负向偏好信号：{topic_effect}"
    if candidate_type == "owner_preference":
        return f"是否允许把这条候选作为 owner 偏好信号：{topic_effect}"
    if candidate_type == "voice_correction":
        return f"是否允许把这条候选作为表达修正信号：{topic_effect}"
    if candidate_type == "relationship_signal":
        return f"是否允许把这条候选作为关系观察信号：{topic_effect}"
    return f"是否允许保留这条候选用于后续受控记忆治理：{topic_effect}"


def _approval_impact(row: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    candidate_type = _safe_str(row.get("candidate_type"), "memory_candidate")
    target = _safe_str(row.get("target_memory_layer")).replace("\\", "/")
    conflict_count = _int(review.get("conflict_count"))
    return {
        "if_ok": (
            "候选状态可变为 approved，但仍不会直接写稳定记忆；后续稳定落地需要单独 owner apply。"
        ),
        "if_reject": "候选会被标记为 rejected，后续不应再作为记忆依据。",
        "approval_does_not_mean": [
            "不是确认原始私聊正文会进入公开报告",
            "不是确认这条内容已经是稳定事实",
            "不是允许绕过当前对话和 owner 后续纠正",
        ],
        "risk_note": (
            "存在冲突，必须先由 owner 解决冲突。"
            if conflict_count
            else f"{candidate_type} -> {target} 属于受控候选，当前仅允许审核状态变化。"
        ),
    }


def build_owner_review_brief(row: dict[str, Any], review: dict[str, Any]) -> dict[str, Any]:
    topic_key, topic_effect = _controlled_topic_hint(row)
    return {
        "review_topic_hint": topic_key,
        "approval_question": _approval_question(row, review, topic_effect),
        "approval_impact": _approval_impact(row, review),
        "private_text_shape_detected": _has_private_text_shape(_safe_str(row.get("candidate_text"))),
    }


def _owner_review_action_summary(row: dict[str, Any], review: dict[str, Any]) -> list[str]:
    actions = ["owner_decision_required", "do_not_write_stable_memory_from_packet"]
    candidate_type = _safe_str(row.get("candidate_type"))
    target = _safe_str(row.get("target_memory_layer")).replace("\\", "/")
    if _int(review.get("conflict_count")) > 0:
        actions.insert(1, "resolve_conflict_before_approval")
    if candidate_type in {"owner_preference", "relationship_signal", "voice_correction", "personality_change"}:
        actions.append("high_risk_candidate_requires_explicit_owner_approval")
    if target == "memory/reflection/growth_log.md":
        actions.append("approval_writes_preview_only_growth_log_apply_is_separate")
    else:
        actions.append("approval_records_candidate_only")
    return actions


def _owner_review_item(row: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    review = candidate_review_context(row, rows)
    brief = build_owner_review_brief(row, review)
    return {
        "candidate_id": _safe_str(row.get("candidate_id"), "unknown"),
        "status": _safe_str(row.get("status"), "unknown"),
        "candidate_type": _safe_str(row.get("candidate_type"), "unknown"),
        "target_memory_layer": _safe_str(row.get("target_memory_layer"), "unknown"),
        "target_gate": _safe_str(row.get("target_gate"), "unknown"),
        "risk_flags": _safe_list(row.get("risk_flags")),
        "claim_topic_key": _safe_str(review.get("claim_topic_key"), "unknown"),
        "claim_polarity": _safe_str(review.get("claim_polarity"), "unknown"),
        "evidence_count": _int(review.get("evidence_count"), 1),
        "distinct_source_turn_count": _int(review.get("distinct_source_turn_count")),
        "distinct_source_message_count": _int(review.get("distinct_source_message_count")),
        "conflict_count": _int(review.get("conflict_count")),
        "supporting_candidate_count": len(review.get("supporting_candidate_ids", []) or []),
        "conflicting_candidate_count": len(review.get("conflicting_candidate_ids", []) or []),
        "recommendation": _safe_str(review.get("recommendation"), "owner_review_required"),
        "review_topic_hint": brief["review_topic_hint"],
        "approval_question": brief["approval_question"],
        "approval_impact": brief["approval_impact"],
        "private_text_shape_detected": brief["private_text_shape_detected"],
        "candidate_text_preview": "hidden_owner_review_required",
        "owner_private_body": "hidden",
        "stable_memory_write": "blocked_until_explicit_owner_apply",
        "suggested_actions": _owner_review_action_summary(row, review),
    }


def _safe_duplicate_clusters(health: dict[str, Any], *, max_clusters: int) -> list[dict[str, Any]]:
    clusters = health.get("clusters") if isinstance(health.get("clusters"), list) else []
    safe: list[dict[str, Any]] = []
    for cluster in clusters:
        if not isinstance(cluster, dict) or _int(cluster.get("size")) <= 1:
            continue
        items = [item for item in cluster.get("items", []) if isinstance(item, dict)]
        item_ids = [_safe_str(item.get("candidate_id")) for item in items if _safe_str(item.get("candidate_id"))]
        private_count = sum(
            1
            for item in items
            if _safe_str(item.get("candidate_text_preview")).startswith("hidden_")
            or "scope:owner_private" in set(_safe_list(item.get("risk_flags")))
        )
        safe.append(
            {
                "claim_topic_key": _safe_str(cluster.get("claim_topic_key"), "unknown"),
                "size": _int(cluster.get("size")),
                "conflict_count": _int(cluster.get("conflict_count")),
                "recommendation": _safe_str(cluster.get("recommendation"), "observe_more"),
                "status_counts": dict(cluster.get("status_counts", {}) or {}),
                "candidate_type_counts": dict(cluster.get("candidate_type_counts", {}) or {}),
                "target_memory_layer_counts": dict(cluster.get("target_memory_layer_counts", {}) or {}),
                "sample_candidate_ids": item_ids[:8],
                "private_or_hidden_sample_count": private_count,
                "candidate_text_preview": "hidden_for_cluster_backlog",
                "suggested_actions": ["dedupe_or_merge_after_owner_review", "do_not_treat_duplicate_cluster_as_fact"],
            }
        )
        if len(safe) >= max(1, int(max_clusters)):
            break
    return safe


def _blocked_gates(stage8: dict[str, Any], duplicate_cluster_count: int) -> list[dict[str, Any]]:
    gates: list[dict[str, Any]] = []
    if not bool(stage8.get("stage7_ready_for_stage8", False)):
        gates.append({"gate": "stage7_feedback_closure", "status": "blocked", "reason": "stage7_not_ready"})
    if _int(stage8.get("owner_review_required_count")):
        gates.append(
            {
                "gate": "owner_review_required",
                "status": "blocked",
                "count": _int(stage8.get("owner_review_required_count")),
                "reason": "owner_private_or_high_risk_candidate_needs_owner_decision",
            }
        )
    if duplicate_cluster_count:
        gates.append(
            {
                "gate": "duplicate_candidate_clusters",
                "status": "blocked",
                "count": duplicate_cluster_count,
                "reason": "candidate_backlog_needs_consolidation_before_stable_write",
            }
        )
    if _safe_str(stage8.get("learning_trial_success_gate")) == "blocked":
        gates.append(
            {
                "gate": "learning_trial_success_gate",
                "status": "blocked",
                "reason": "same_trial_explicit_success_not_yet_satisfied",
            }
        )
    if _safe_str(stage8.get("status")) == "violation":
        gates.append({"gate": "stage8_boundary_violation", "status": "blocked", "reason": stage8.get("reason")})
    return gates


def _next_actions(stage8: dict[str, Any], owner_items: list[dict[str, Any]], clusters: list[dict[str, Any]]) -> list[str]:
    actions = ["keep_packet_read_only", "keep_raw_owner_text_hidden", "keep_stable_memory_write_blocked"]
    if owner_items:
        actions.append("owner_reviews_required_candidates_in_owner_channel_only")
        actions.append("record_owner_decision_without_auto_promoting_stable_memory")
    if clusters:
        actions.append("dedupe_candidate_clusters_after_owner_review_queue_is_clear")
    if _safe_str(stage8.get("learning_trial_success_gate")) == "blocked":
        actions.append("collect_same_trial_explicit_success_before_profile_or_habit_promotion")
    actions.append("rerun_stage8_memory_review_packet_after_decisions")
    return actions


def build_stage8_memory_review_packet(
    root: Path,
    *,
    limit_per_status: int = 1000,
    max_owner_items: int = 50,
    max_clusters: int = 24,
) -> dict[str, Any]:
    root = root.resolve()
    rows = _all_candidate_rows(root, limit_per_status=limit_per_status)
    health = build_memory_health_report(root, limit_per_status=limit_per_status, max_clusters=max_clusters)
    stage8 = health.get("stage8_memory_governance") if isinstance(health.get("stage8_memory_governance"), dict) else {}
    owner_rows = [row for row in rows if _safe_str(row.get("status")) == "owner_review_required"]
    owner_items = [_owner_review_item(row, rows) for row in owner_rows[: max(1, int(max_owner_items))]]
    clusters = _safe_duplicate_clusters(health, max_clusters=max_clusters)
    inventory = health.get("candidate_inventory") if isinstance(health.get("candidate_inventory"), dict) else {}
    status_counts = Counter(_safe_str(row.get("status"), "unknown") for row in rows)
    duplicate_cluster_count = _int(health.get("duplicate_cluster_count"))
    blocked = _blocked_gates(stage8, duplicate_cluster_count)
    packet_status = "ready_for_owner_review" if owner_items or clusters or blocked else "no_stage8_review_backlog"
    return {
        "ok": True,
        "generated_at": _now_iso(),
        "root": str(root),
        "packet_status": packet_status,
        "mode": "read_only_owner_review_packet",
        "stage": "stage8_memory_governance",
        "stage8_memory_governance": {
            "status": _safe_str(stage8.get("status"), "missing"),
            "ready_for_stage9": bool(stage8.get("ready_for_stage9", False)),
            "reason": _safe_str(stage8.get("reason"), "missing"),
            "next_step": _safe_str(stage8.get("next_step"), "missing"),
            "stage7_ready_for_stage8": bool(stage8.get("stage7_ready_for_stage8", False)),
            "learning_trial_success_gate": _safe_str(stage8.get("learning_trial_success_gate"), "missing"),
        },
        "candidate_inventory": {
            "total": _int(inventory.get("total"), len(rows)),
            "status_counts": dict(sorted(status_counts.items())),
            "owner_review_required_count": len(owner_items),
            "private_or_owner_scoped_count": _int(inventory.get("private_or_owner_scoped_count")),
            "duplicate_cluster_count": duplicate_cluster_count,
        },
        "owner_review_required": owner_items,
        "duplicate_cluster_backlog": clusters,
        "blocked_gates": blocked,
        "next_actions": _next_actions(stage8, owner_items, clusters),
        "boundaries": {
            "raw_owner_text_in_packet": False,
            "visible_reply_text_in_packet": False,
            "candidate_body_in_packet": False,
            "qq_message_enqueued": False,
            "candidate_status_changed": False,
            "stable_memory_write": "blocked",
            "stable_identity_profile_apply": "blocked",
            "consciousness_claim": False,
        },
    }


def render_stage8_memory_review_packet(packet: dict[str, Any]) -> str:
    inventory = packet.get("candidate_inventory") if isinstance(packet.get("candidate_inventory"), dict) else {}
    stage8 = packet.get("stage8_memory_governance") if isinstance(packet.get("stage8_memory_governance"), dict) else {}
    lines = [
        "# XinYu Stage 8 Memory Review Packet",
        "",
        f"- generated_at: {_one_line(packet.get('generated_at'))}",
        f"- packet_status: {_one_line(packet.get('packet_status'))}",
        f"- mode: {_one_line(packet.get('mode'))}",
        "- raw_owner_text: hidden",
        "- stable_memory_write: blocked",
        "- qq_message_enqueued: false",
        "",
        "## Stage 8 Gate",
        f"- status: {_one_line(stage8.get('status'))}",
        f"- ready_for_stage9: {str(bool(stage8.get('ready_for_stage9', False))).lower()}",
        f"- stage7_ready_for_stage8: {str(bool(stage8.get('stage7_ready_for_stage8', False))).lower()}",
        f"- learning_trial_success_gate: {_one_line(stage8.get('learning_trial_success_gate'))}",
        f"- reason: {_one_line(stage8.get('reason'), limit=220)}",
        f"- next_step: {_one_line(stage8.get('next_step'), limit=220)}",
        "",
        "## Inventory",
        f"- total: {_one_line(inventory.get('total'), default='0')}",
        f"- owner_review_required_count: {_one_line(inventory.get('owner_review_required_count'), default='0')}",
        f"- private_or_owner_scoped_count: {_one_line(inventory.get('private_or_owner_scoped_count'), default='0')}",
        f"- duplicate_cluster_count: {_one_line(inventory.get('duplicate_cluster_count'), default='0')}",
        "",
        "## Owner Review Required",
    ]
    owner_items = packet.get("owner_review_required") if isinstance(packet.get("owner_review_required"), list) else []
    if not owner_items:
        lines.append("- none")
    for item in owner_items:
        lines.append(
            "- "
            f"id={_one_line(item.get('candidate_id'), limit=90)}; "
            f"type={_one_line(item.get('candidate_type'), limit=80)}; "
            f"target={_one_line(item.get('target_memory_layer'), limit=140)}; "
            f"gate={_one_line(item.get('target_gate'), limit=100)}; "
            f"evidence={_one_line(item.get('evidence_count'), default='0')}; "
            f"conflicts={_one_line(item.get('conflict_count'), default='0')}; "
            f"recommendation={_one_line(item.get('recommendation'), limit=120)}; "
            f"topic_hint={_one_line(item.get('review_topic_hint'), limit=90)}; "
            "candidate_text_preview=hidden_owner_review_required"
        )
        lines.append(f"  approval_question: {_one_line(item.get('approval_question'), limit=260)}")
        impact = item.get("approval_impact") if isinstance(item.get("approval_impact"), dict) else {}
        lines.append(f"  if_ok: {_one_line(impact.get('if_ok'), limit=240)}")
        lines.append(f"  if_reject: {_one_line(impact.get('if_reject'), limit=220)}")
    lines.extend(["", "## Duplicate Cluster Backlog"])
    clusters = packet.get("duplicate_cluster_backlog") if isinstance(packet.get("duplicate_cluster_backlog"), list) else []
    if not clusters:
        lines.append("- none")
    for cluster in clusters:
        lines.append(
            "- "
            f"topic={_one_line(cluster.get('claim_topic_key'), limit=90)}; "
            f"size={_one_line(cluster.get('size'), default='0')}; "
            f"conflicts={_one_line(cluster.get('conflict_count'), default='0')}; "
            f"private_or_hidden_samples={_one_line(cluster.get('private_or_hidden_sample_count'), default='0')}; "
            f"recommendation={_one_line(cluster.get('recommendation'), limit=120)}; "
            f"statuses={json.dumps(cluster.get('status_counts', {}), ensure_ascii=False, sort_keys=True)}"
        )
    lines.extend(["", "## Blocked Gates"])
    blocked = packet.get("blocked_gates") if isinstance(packet.get("blocked_gates"), list) else []
    if not blocked:
        lines.append("- none")
    for gate in blocked:
        lines.append(
            "- "
            f"gate={_one_line(gate.get('gate'), limit=80)}; "
            f"status={_one_line(gate.get('status'), limit=80)}; "
            f"count={_one_line(gate.get('count'), default='0')}; "
            f"reason={_one_line(gate.get('reason'), limit=180)}"
        )
    lines.extend(["", "## Boundaries"])
    boundaries = packet.get("boundaries") if isinstance(packet.get("boundaries"), dict) else {}
    for key in sorted(boundaries):
        value = boundaries.get(key)
        lines.append(f"- {key}: {str(value).lower() if isinstance(value, bool) else _one_line(value)}")
    lines.extend(["", "## Next Actions"])
    for item in packet.get("next_actions", []) or []:
        lines.append(f"- {_one_line(item, limit=220)}")
    return "\n".join(lines).rstrip() + "\n"


def write_stage8_memory_review_packet(
    root: Path,
    packet: dict[str, Any],
    *,
    output: Path | None = None,
) -> Path:
    root = root.resolve()
    return write_stage8_memory_review_packet_text(root, render_stage8_memory_review_packet(packet), output=output)


def write_stage8_memory_review_packet_state(
    root: Path,
    packet: dict[str, Any],
    *,
    packet_path: Path | None = None,
) -> Path:
    root = root.resolve()
    inventory = packet.get("candidate_inventory") if isinstance(packet.get("candidate_inventory"), dict) else {}
    boundaries = packet.get("boundaries") if isinstance(packet.get("boundaries"), dict) else {}
    stage8 = packet.get("stage8_memory_governance") if isinstance(packet.get("stage8_memory_governance"), dict) else {}
    target_packet_path = packet_path or stage8_memory_review_packet_path(root)
    text = f"""---
title: Stage 8 Memory Review Packet State
memory_type: stage8_memory_review_packet_state
time_scope: rolling_runtime
subject_ids: [xinyu, owner]
protected: true
source: xinyu_stage8_memory_review_packet
updated_at: {packet.get('generated_at', 'unknown')}
status: active
tags: [autonomy, memory, governance, owner-review, stage8]
---

# Stage 8 Memory Review Packet State

## Latest
- packet_status: {packet.get('packet_status', 'missing')}
- stage8_memory_governance_status: {stage8.get('status', 'missing')}
- stage8_memory_ready_for_stage9: {str(bool(stage8.get('ready_for_stage9', False))).lower()}
- owner_review_required_count: {inventory.get('owner_review_required_count', 0)}
- duplicate_cluster_count: {inventory.get('duplicate_cluster_count', 0)}
- private_or_owner_scoped_count: {inventory.get('private_or_owner_scoped_count', 0)}
- learning_trial_success_gate: {stage8.get('learning_trial_success_gate', 'missing')}
- packet_path: {target_packet_path.as_posix()}

## Boundaries
- raw_owner_text_in_packet: {str(bool(boundaries.get('raw_owner_text_in_packet', False))).lower()}
- visible_reply_text_in_packet: {str(bool(boundaries.get('visible_reply_text_in_packet', False))).lower()}
- candidate_body_in_packet: {str(bool(boundaries.get('candidate_body_in_packet', False))).lower()}
- qq_message_enqueued: {str(bool(boundaries.get('qq_message_enqueued', False))).lower()}
- candidate_status_changed: {str(bool(boundaries.get('candidate_status_changed', False))).lower()}
- stable_memory_write: {boundaries.get('stable_memory_write', 'blocked')}
- stable_identity_profile_apply: {boundaries.get('stable_identity_profile_apply', 'blocked')}
- consciousness_claim: {str(bool(boundaries.get('consciousness_claim', False))).lower()}
"""
    return write_stage8_memory_review_packet_state_text(root, text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a redacted Stage 8 memory owner-review packet.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--max-owner-items", type=int, default=50)
    parser.add_argument("--max-clusters", type=int, default=24)
    args = parser.parse_args(argv)
    packet = build_stage8_memory_review_packet(
        args.root,
        max_owner_items=args.max_owner_items,
        max_clusters=args.max_clusters,
    )
    if args.write:
        path = write_stage8_memory_review_packet(args.root, packet, output=args.output)
        state_path = write_stage8_memory_review_packet_state(args.root, packet, packet_path=path)
        packet["packet_path"] = str(path)
        packet["state_path"] = str(state_path)
    if args.json:
        print(json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_stage8_memory_review_packet(packet))
    return 0 if packet.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

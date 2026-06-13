from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_dialogue_archive import list_memory_candidates, update_memory_candidate_status
from xinyu_memory_candidate_analysis import candidate_claim_metadata_from_row, candidate_review_context
from xinyu_memory_health_report import DUPLICATE_BACKLOG_STATUSES, build_memory_health_report
from xinyu_stage8_duplicate_consolidation_packet_store import APPLY_TRACE_REL
from xinyu_stage8_duplicate_consolidation_packet_store import PACKET_REL
from xinyu_stage8_duplicate_consolidation_packet_store import STATE_REL
from xinyu_stage8_duplicate_consolidation_packet_store import append_stage8_duplicate_consolidation_apply_trace_event
from xinyu_stage8_duplicate_consolidation_packet_store import write_stage8_duplicate_consolidation_packet_text
from xinyu_stage8_duplicate_consolidation_packet_store import write_stage8_duplicate_consolidation_state_text
ARCHIVED_DUPLICATE_STATUS = "archived_duplicate"
PROTECTED_NON_REPRESENTATIVE_STATUSES = {"approved"}
PRIVATE_TEXT_MARKERS = (
    "owner_turn:",
    "visible_reply:",
    "user_turn:",
    "assistant_reply:",
)
STATUS_PRIORITY = {
    "applied_growth_log": 90,
    "approved": 80,
    "owner_review_required": 70,
    "self_approved_recent_context": 60,
    "self_approved_voice_review": 55,
    "observe_more_owner_preference": 40,
    "observe_more_relationship_signal": 40,
    "observe_more_unknown": 30,
    "pending": 20,
    "rejected": 5,
}


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


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_list(value: Any, *, limit: int = 20) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_one_line(item, limit=120, default="") for item in value[: max(0, limit)] if _safe_str(item).strip()]


def _all_candidate_rows(root: Path, *, limit_per_status: int = 1000) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for status in DUPLICATE_BACKLOG_STATUSES:
        for row in list_memory_candidates(root, status=status, limit=limit_per_status):
            candidate_id = _safe_str(row.get("candidate_id")).strip()
            if not candidate_id or candidate_id in seen:
                continue
            seen.add(candidate_id)
            rows.append(row)
    return rows


def _has_private_text_shape(row: dict[str, Any]) -> bool:
    text = _safe_str(row.get("candidate_text")).lower()
    if any(marker in text for marker in PRIVATE_TEXT_MARKERS):
        return True
    target = _safe_str(row.get("target_memory_layer")).replace("\\", "/")
    flags = set(_safe_list(row.get("risk_flags")))
    return target in {
        "memory/people/owner.md",
        "memory/relationships/index.md",
        "memory/self/voice_calibration_log.md",
    } or "scope:owner_private" in flags


def _cluster_groups(rows: list[dict[str, Any]]) -> list[tuple[str, list[dict[str, Any]]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        meta = candidate_claim_metadata_from_row(row)
        topic = _safe_str(meta.get("claim_topic_key"), "unknown")
        grouped[topic].append(row)
    clusters = [(topic, items) for topic, items in grouped.items() if len(items) > 1]
    clusters.sort(key=lambda item: (len(item[1]), item[0]), reverse=True)
    return clusters


def _representative_candidate(items: list[dict[str, Any]]) -> dict[str, Any]:
    def rank(row: dict[str, Any]) -> tuple[int, int, str]:
        status = _safe_str(row.get("status"), "unknown")
        return (
            STATUS_PRIORITY.get(status, 0),
            _int(row.get("confidence_score")),
            _safe_str(row.get("created_at")),
        )

    return sorted(items, key=rank, reverse=True)[0]


def _dominant(counter: Counter[str], fallback: str = "unknown") -> str:
    if not counter:
        return fallback
    return counter.most_common(1)[0][0] or fallback


def _proposal_action(
    *,
    status_counts: Counter[str],
    target_counts: Counter[str],
    type_counts: Counter[str],
    conflict_count: int,
) -> tuple[str, str, str]:
    if conflict_count > 0:
        return (
            "hold_conflict_review",
            "blocked_by_conflict",
            "同 topic 内存在相反或冲突候选，必须先保留为冲突审查，不允许合并成事实。",
        )
    if status_counts.get("owner_review_required", 0) > 0:
        return (
            "owner_review_cluster_first",
            "blocked_by_owner_review",
            "同 topic 内还有主人审核项，先让 owner 明确处理，再谈合并。",
        )
    if _dominant(target_counts).replace("\\", "/") == "memory/reflection/growth_log.md":
        return (
            "prepare_growth_log_dedupe_preview",
            "review_ready",
            "可整理成一条成长日志候选预览，但仍需要单独 owner apply 才能写入。",
        )
    if _dominant(type_counts) in {"voice_correction", "owner_preference", "relationship_signal"}:
        return (
            "collapse_as_repeated_review_evidence",
            "review_ready",
            "可压缩成一条重复证据审查项，用作降权或观察信号，不能写成稳定事实。",
        )
    return (
        "consolidate_repeated_candidate_evidence",
        "review_ready",
        "可整理成一条重复证据审查项；合并包只改变审查视图，不改变候选状态。",
    )


def _build_proposal(topic: str, items: list[dict[str, Any]], rows: list[dict[str, Any]]) -> dict[str, Any]:
    representative = _representative_candidate(items)
    review = candidate_review_context(representative, rows)
    status_counts = Counter(_safe_str(item.get("status"), "unknown") for item in items)
    type_counts = Counter(_safe_str(item.get("candidate_type"), "unknown") for item in items)
    target_counts = Counter(_safe_str(item.get("target_memory_layer"), "unknown") for item in items)
    conflict_count = _int(review.get("conflict_count"))
    action, readiness, effect = _proposal_action(
        status_counts=status_counts,
        target_counts=target_counts,
        type_counts=type_counts,
        conflict_count=conflict_count,
    )
    candidate_ids = [_safe_str(item.get("candidate_id")) for item in items if _safe_str(item.get("candidate_id"))]
    private_count = sum(1 for item in items if _has_private_text_shape(item))
    return {
        "proposal_id": f"dedupe-{topic[:12]}",
        "claim_topic_key": topic,
        "size": len(items),
        "representative_candidate_id": _safe_str(representative.get("candidate_id"), "unknown"),
        "sample_candidate_ids": candidate_ids[:12],
        "status_counts": dict(sorted(status_counts.items())),
        "candidate_type_counts": dict(sorted(type_counts.items())),
        "target_memory_layer_counts": dict(sorted(target_counts.items())),
        "dominant_status": _dominant(status_counts),
        "dominant_candidate_type": _dominant(type_counts),
        "dominant_target_memory_layer": _dominant(target_counts),
        "conflict_count": conflict_count,
        "private_or_hidden_candidate_count": private_count,
        "recommendation": _safe_str(review.get("recommendation"), "review_duplicate_cluster"),
        "consolidation_action": action,
        "merge_readiness": readiness,
        "proposed_effect": effect,
        "candidate_text_preview": "hidden_duplicate_consolidation",
        "stable_memory_write": "blocked",
        "candidate_status_change": "none",
        "suggested_actions": [
            "keep_candidate_bodies_hidden",
            "review_cluster_before_any_stable_write",
            action,
        ],
    }


def build_stage8_duplicate_consolidation_packet(
    root: Path,
    *,
    limit_per_status: int = 1000,
    max_clusters: int = 24,
) -> dict[str, Any]:
    root = root.resolve()
    rows = _all_candidate_rows(root, limit_per_status=limit_per_status)
    health = build_memory_health_report(root, limit_per_status=limit_per_status, max_clusters=max_clusters)
    stage8 = health.get("stage8_memory_governance") if isinstance(health.get("stage8_memory_governance"), dict) else {}
    groups = _cluster_groups(rows)
    proposals = [_build_proposal(topic, items, rows) for topic, items in groups[: max(1, int(max_clusters))]]
    conflict_count = sum(1 for item in proposals if _int(item.get("conflict_count")) > 0)
    owner_review_count = sum(
        1
        for item in proposals
        if _int((item.get("status_counts") or {}).get("owner_review_required") if isinstance(item.get("status_counts"), dict) else 0)
        > 0
    )
    ready_count = sum(1 for item in proposals if item.get("merge_readiness") == "review_ready")
    packet_status = "ready_for_consolidation_review" if proposals else "no_duplicate_candidate_clusters"
    return {
        "ok": True,
        "generated_at": _now_iso(),
        "root": str(root),
        "packet_status": packet_status,
        "mode": "read_only_duplicate_consolidation_packet",
        "stage": "stage8_memory_governance",
        "stage8_memory_governance": {
            "status": _safe_str(stage8.get("status"), "missing"),
            "ready_for_stage9": bool(stage8.get("ready_for_stage9", False)),
            "reason": _safe_str(stage8.get("reason"), "missing"),
            "next_step": _safe_str(stage8.get("next_step"), "missing"),
        },
        "summary": {
            "duplicate_cluster_count": len(groups),
            "consolidation_item_count": len(proposals),
            "conflict_cluster_count": conflict_count,
            "owner_review_cluster_count": owner_review_count,
            "ready_cluster_count": ready_count,
        },
        "consolidation_proposals": proposals,
        "next_actions": [
            "keep_packet_read_only",
            "keep_candidate_bodies_hidden",
            "review_consolidation_proposals_before_stable_write",
            "do_not_change_candidate_status_from_consolidation_packet",
            "rerun_stage8_memory_health_after_owner_decisions",
        ],
        "boundaries": {
            "raw_owner_text_in_packet": False,
            "visible_reply_text_in_packet": False,
            "candidate_body_in_packet": False,
            "candidate_status_changed": False,
            "stable_memory_write": "blocked",
            "stable_identity_profile_apply": "blocked",
            "qq_message_enqueued": False,
            "consciousness_claim": False,
        },
    }


def render_stage8_duplicate_consolidation_packet(packet: dict[str, Any]) -> str:
    summary = packet.get("summary") if isinstance(packet.get("summary"), dict) else {}
    stage8 = packet.get("stage8_memory_governance") if isinstance(packet.get("stage8_memory_governance"), dict) else {}
    lines = [
        "# XinYu Stage 8 Duplicate Candidate Consolidation Packet",
        "",
        f"- generated_at: {_one_line(packet.get('generated_at'))}",
        f"- packet_status: {_one_line(packet.get('packet_status'))}",
        f"- mode: {_one_line(packet.get('mode'))}",
        "- raw_owner_text: hidden",
        "- stable_memory_write: blocked",
        "- candidate_status_changed: false",
        "",
        "## Stage 8 Gate",
        f"- status: {_one_line(stage8.get('status'))}",
        f"- ready_for_stage9: {str(bool(stage8.get('ready_for_stage9', False))).lower()}",
        f"- reason: {_one_line(stage8.get('reason'), limit=220)}",
        f"- next_step: {_one_line(stage8.get('next_step'), limit=220)}",
        "",
        "## Summary",
        f"- duplicate_cluster_count: {_one_line(summary.get('duplicate_cluster_count'), default='0')}",
        f"- consolidation_item_count: {_one_line(summary.get('consolidation_item_count'), default='0')}",
        f"- conflict_cluster_count: {_one_line(summary.get('conflict_cluster_count'), default='0')}",
        f"- owner_review_cluster_count: {_one_line(summary.get('owner_review_cluster_count'), default='0')}",
        f"- ready_cluster_count: {_one_line(summary.get('ready_cluster_count'), default='0')}",
        "",
    ]
    apply_result = packet.get("apply_result") if isinstance(packet.get("apply_result"), dict) else {}
    if apply_result:
        lines.extend(
            [
                "## Latest Apply",
                f"- ok: {str(bool(apply_result.get('ok', False))).lower()}",
                f"- applied_at: {_one_line(apply_result.get('applied_at'))}",
                f"- applied_cluster_count: {_one_line(apply_result.get('applied_cluster_count'), default='0')}",
                f"- archived_candidate_count: {_one_line(apply_result.get('archived_candidate_count'), default='0')}",
                f"- kept_representative_count: {_one_line(apply_result.get('kept_representative_count'), default='0')}",
                f"- skipped_cluster_count: {_one_line(apply_result.get('skipped_cluster_count'), default='0')}",
                f"- stable_memory_write: {_one_line(apply_result.get('stable_memory_write'))}",
                f"- candidate_status_changed: {str(bool(apply_result.get('candidate_status_changed', False))).lower()}",
                f"- candidate_body_changed: {str(bool(apply_result.get('candidate_body_changed', False))).lower()}",
                "",
            ]
        )
    lines.append("## Consolidation Proposals")
    proposals = packet.get("consolidation_proposals") if isinstance(packet.get("consolidation_proposals"), list) else []
    if not proposals:
        lines.append("- none")
    for item in proposals:
        status_counts = json.dumps(item.get("status_counts", {}), ensure_ascii=False, sort_keys=True)
        type_counts = json.dumps(item.get("candidate_type_counts", {}), ensure_ascii=False, sort_keys=True)
        target_counts = json.dumps(item.get("target_memory_layer_counts", {}), ensure_ascii=False, sort_keys=True)
        sample_ids = ",".join(_safe_list(item.get("sample_candidate_ids"), limit=12)) or "none"
        lines.append(
            "- "
            f"proposal={_one_line(item.get('proposal_id'), limit=80)}; "
            f"topic={_one_line(item.get('claim_topic_key'), limit=90)}; "
            f"size={_one_line(item.get('size'), default='0')}; "
            f"representative={_one_line(item.get('representative_candidate_id'), limit=90)}; "
            f"conflicts={_one_line(item.get('conflict_count'), default='0')}; "
            f"readiness={_one_line(item.get('merge_readiness'), limit=90)}; "
            f"action={_one_line(item.get('consolidation_action'), limit=120)}; "
            f"statuses={status_counts}"
        )
        lines.append(f"  candidate_type_counts: {type_counts}")
        lines.append(f"  target_memory_layer_counts: {target_counts}")
        lines.append(f"  sample_candidate_ids: {sample_ids}")
        lines.append(f"  proposed_effect: {_one_line(item.get('proposed_effect'), limit=260)}")
    lines.extend(["", "## Boundaries"])
    boundaries = packet.get("boundaries") if isinstance(packet.get("boundaries"), dict) else {}
    apply_result = packet.get("apply_result") if isinstance(packet.get("apply_result"), dict) else {}
    for key in sorted(boundaries):
        value = boundaries.get(key)
        lines.append(f"- {key}: {str(value).lower() if isinstance(value, bool) else _one_line(value)}")
    lines.extend(["", "## Next Actions"])
    for item in packet.get("next_actions", []) or []:
        lines.append(f"- {_one_line(item, limit=220)}")
    return "\n".join(lines).rstrip() + "\n"


def write_stage8_duplicate_consolidation_packet(
    root: Path,
    packet: dict[str, Any],
    *,
    output: Path | None = None,
) -> Path:
    root = root.resolve()
    return write_stage8_duplicate_consolidation_packet_text(
        root,
        render_stage8_duplicate_consolidation_packet(packet),
        output=output,
    )


def write_stage8_duplicate_consolidation_state(
    root: Path,
    packet: dict[str, Any],
    *,
    packet_path: Path | None = None,
) -> Path:
    root = root.resolve()
    summary = packet.get("summary") if isinstance(packet.get("summary"), dict) else {}
    boundaries = packet.get("boundaries") if isinstance(packet.get("boundaries"), dict) else {}
    apply_result = packet.get("apply_result") if isinstance(packet.get("apply_result"), dict) else {}
    target_packet_path = packet_path or (root / PACKET_REL)
    text = f"""---
title: Stage 8 Duplicate Consolidation State
memory_type: stage8_duplicate_consolidation_state
time_scope: rolling_runtime
subject_ids: [xinyu, owner]
protected: true
source: xinyu_stage8_duplicate_consolidation_packet
updated_at: {packet.get('generated_at', 'unknown')}
status: active
tags: [autonomy, memory, governance, duplicate-consolidation, stage8]
---

# Stage 8 Duplicate Consolidation State

## Latest
- packet_status: {packet.get('packet_status', 'missing')}
- duplicate_cluster_count: {summary.get('duplicate_cluster_count', 0)}
- consolidation_item_count: {summary.get('consolidation_item_count', 0)}
- conflict_cluster_count: {summary.get('conflict_cluster_count', 0)}
- owner_review_cluster_count: {summary.get('owner_review_cluster_count', 0)}
- ready_cluster_count: {summary.get('ready_cluster_count', 0)}
- packet_path: {target_packet_path.as_posix()}

## Latest Apply
- apply_ok: {str(bool(apply_result.get('ok', False))).lower()}
- applied_at: {apply_result.get('applied_at', 'none')}
- applied_cluster_count: {apply_result.get('applied_cluster_count', 0)}
- archived_candidate_count: {apply_result.get('archived_candidate_count', 0)}
- kept_representative_count: {apply_result.get('kept_representative_count', 0)}
- skipped_cluster_count: {apply_result.get('skipped_cluster_count', 0)}
- apply_candidate_status_changed: {str(bool(apply_result.get('candidate_status_changed', False))).lower()}
- apply_candidate_body_changed: {str(bool(apply_result.get('candidate_body_changed', False))).lower()}
- apply_stable_memory_write: {apply_result.get('stable_memory_write', 'blocked')}

## Boundaries
- raw_owner_text_in_packet: {str(bool(boundaries.get('raw_owner_text_in_packet', False))).lower()}
- visible_reply_text_in_packet: {str(bool(boundaries.get('visible_reply_text_in_packet', False))).lower()}
- candidate_body_in_packet: {str(bool(boundaries.get('candidate_body_in_packet', False))).lower()}
- candidate_status_changed: {str(bool(boundaries.get('candidate_status_changed', False))).lower()}
- stable_memory_write: {boundaries.get('stable_memory_write', 'blocked')}
- stable_identity_profile_apply: {boundaries.get('stable_identity_profile_apply', 'blocked')}
- qq_message_enqueued: {str(bool(boundaries.get('qq_message_enqueued', False))).lower()}
- consciousness_claim: {str(bool(boundaries.get('consciousness_claim', False))).lower()}
"""
    return write_stage8_duplicate_consolidation_state_text(root, text)


def _append_review_note(row: dict[str, Any], note: str) -> str:
    current = _safe_str(row.get("review_notes")).strip()
    if not current:
        return note
    return f"{current}; {note}"


def _append_apply_trace(root: Path, result: dict[str, Any]) -> None:
    payload = {
        "applied_at": result.get("applied_at"),
        "applied_cluster_count": result.get("applied_cluster_count"),
        "archived_candidate_count": result.get("archived_candidate_count"),
        "skipped_cluster_count": result.get("skipped_cluster_count"),
        "stable_memory_write": result.get("stable_memory_write"),
        "candidate_status_changed": result.get("candidate_status_changed"),
    }
    append_stage8_duplicate_consolidation_apply_trace_event(root, payload)


def apply_stage8_duplicate_consolidation(
    root: Path,
    *,
    owner_approved_consolidation: bool = False,
    limit_per_status: int = 1000,
    max_clusters: int = 1000,
    applied_at: str | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    if not owner_approved_consolidation:
        return {
            "ok": False,
            "error": "owner_approved_consolidation_required",
            "stable_memory_write": "blocked",
            "candidate_status_changed": False,
        }
    checked_at = applied_at or _now_iso()
    rows = _all_candidate_rows(root, limit_per_status=limit_per_status)
    groups = _cluster_groups(rows)[: max(1, int(max_clusters))]
    archived: list[dict[str, str]] = []
    representatives: list[str] = []
    skipped: list[dict[str, Any]] = []
    for topic, items in groups:
        proposal = _build_proposal(topic, items, rows)
        if proposal.get("merge_readiness") != "review_ready":
            skipped.append({"claim_topic_key": topic, "reason": proposal.get("merge_readiness", "not_review_ready")})
            continue
        if _int(proposal.get("conflict_count")) > 0:
            skipped.append({"claim_topic_key": topic, "reason": "conflict_cluster"})
            continue
        status_counts = proposal.get("status_counts") if isinstance(proposal.get("status_counts"), dict) else {}
        if _int(status_counts.get("owner_review_required")) > 0:
            skipped.append({"claim_topic_key": topic, "reason": "owner_review_required"})
            continue
        representative = _representative_candidate(items)
        representative_id = _safe_str(representative.get("candidate_id")).strip()
        if not representative_id:
            skipped.append({"claim_topic_key": topic, "reason": "missing_representative"})
            continue
        representatives.append(representative_id)
        for row in items:
            candidate_id = _safe_str(row.get("candidate_id")).strip()
            if not candidate_id or candidate_id == representative_id:
                continue
            status = _safe_str(row.get("status"))
            if status in PROTECTED_NON_REPRESENTATIVE_STATUSES:
                skipped.append(
                    {
                        "claim_topic_key": topic,
                        "candidate_id": candidate_id,
                        "reason": f"protected_non_representative_status:{status}",
                    }
                )
                continue
            note = _append_review_note(
                row,
                (
                    "stage8_duplicate_consolidation;"
                    f" representative={representative_id}; topic={topic}; archived_at={checked_at}"
                ),
            )
            if update_memory_candidate_status(
                root,
                candidate_id=candidate_id,
                status=ARCHIVED_DUPLICATE_STATUS,
                review_notes=note,
            ):
                archived.append(
                    {
                        "candidate_id": candidate_id,
                        "from": status,
                        "to": ARCHIVED_DUPLICATE_STATUS,
                        "representative_candidate_id": representative_id,
                        "claim_topic_key": topic,
                    }
                )
            else:
                skipped.append({"claim_topic_key": topic, "candidate_id": candidate_id, "reason": "status_update_failed"})
    result = {
        "ok": True,
        "applied_at": checked_at,
        "mode": "owner_approved_duplicate_candidate_status_consolidation",
        "applied_cluster_count": len(set(item["claim_topic_key"] for item in archived)),
        "kept_representative_count": len(set(representatives)),
        "archived_candidate_count": len(archived),
        "skipped_cluster_count": len({item.get("claim_topic_key", "") for item in skipped if item.get("claim_topic_key")}),
        "archived_items": archived[:80],
        "skipped_items": skipped[:80],
        "stable_memory_write": "blocked",
        "stable_identity_profile_apply": "blocked",
        "candidate_status_changed": bool(archived),
        "candidate_body_changed": False,
        "candidate_body_in_result": False,
        "qq_message_enqueued": False,
        "consciousness_claim": False,
        "notes": [
            "non_representative_duplicate_candidates_archived_only",
            "representative_candidates_remain_available_for_review",
            "stable_memory_not_modified",
        ],
    }
    _append_apply_trace(root, result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a redacted Stage 8 duplicate candidate consolidation packet.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--max-clusters", type=int, default=24)
    parser.add_argument("--apply-reviewed-consolidation", action="store_true")
    parser.add_argument("--owner-approved-consolidation", action="store_true")
    args = parser.parse_args(argv)
    packet = build_stage8_duplicate_consolidation_packet(args.root, max_clusters=args.max_clusters)
    if args.apply_reviewed_consolidation:
        apply_result = apply_stage8_duplicate_consolidation(
            args.root,
            owner_approved_consolidation=args.owner_approved_consolidation,
        )
        packet["apply_result"] = apply_result
        if apply_result.get("ok"):
            packet = build_stage8_duplicate_consolidation_packet(args.root, max_clusters=args.max_clusters)
            packet["apply_result"] = apply_result
    if args.write:
        path = write_stage8_duplicate_consolidation_packet(args.root, packet, output=args.output)
        state_path = write_stage8_duplicate_consolidation_state(args.root, packet, packet_path=path)
        packet["packet_path"] = str(path)
        packet["state_path"] = str(state_path)
    if args.json:
        print(json.dumps(packet, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_stage8_duplicate_consolidation_packet(packet))
    return 0 if packet.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())

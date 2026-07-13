"""Reviewable follow-up candidates from action-openended audit (proposal layer only)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from xinyu_action_openended_audit import run_audit


FOLLOWUP_INBOX_REL = Path("runtime/kernel_followup_review_inbox.jsonl")
STATE_REL = Path("memory/context/action_followup_proposals_state.md")

_BLOCKED_CHANGES = (
    "no new filesystem scope",
    "no stable personality rewrite",
    "no autonomous execution",
    "no direct memory promotion",
)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip() or default


def _proposal_id(seed: str) -> str:
    digest = hashlib.sha256(seed.encode("utf-8", errors="replace")).hexdigest()[:12]
    return f"followup-{digest}"


def _warning_rule(warning: str) -> dict[str, str] | None:
    text = _safe_str(warning)
    if text.startswith("low_salience_leak:"):
        return {
            "target_ecology": "metabolism",
            "candidate": "review low-salience action residue before dream or reflection promotion",
            "why_now": text,
        }
    if text.startswith("over_dreamized_action_residue:"):
        return {
            "target_ecology": "metabolism",
            "candidate": "hold new dream seeds from action residue until salience gate is healthy",
            "why_now": text,
        }
    if text.startswith("over_reflectionized_action_residue:"):
        return {
            "target_ecology": "metabolism",
            "candidate": "slow reflection intake from action residue until ratio returns to watch",
            "why_now": text,
        }
    if text.startswith("repeated_action_theme:"):
        theme = text.split(":", 1)[-1]
        return {
            "target_ecology": "maintenance",
            "candidate": f"inspect repeated action theme for safe variation: {theme[:120]}",
            "why_now": text,
        }
    if text.startswith("repeated_visible_phrase:"):
        phrase = text.split(":", 1)[-1]
        return {
            "target_ecology": "expression",
            "candidate": f"review repeated visible phrase motif before next outward reply: {phrase[:120]}",
            "why_now": text,
        }
    if text.startswith("residue_ratio_high:") or text.startswith("action_metabolism_ratio_high:"):
        return {
            "target_ecology": "metabolism",
            "candidate": "audit action-to-metabolism ratio and keep only high-salience residue",
            "why_now": text,
        }
    if text == "no_recent_action_experience":
        return {
            "target_ecology": "maintenance",
            "candidate": "confirm whether recent bounded actions are being recorded into action experience",
            "why_now": text,
        }
    return None


def build_followup_proposals_from_audit(audit: dict[str, Any]) -> list[dict[str, Any]]:
    """Turn audit warnings into reviewable follow-up candidates (no execution)."""
    proposals: list[dict[str, Any]] = []
    seen: set[str] = set()
    health = _safe_str(audit.get("health_status"), "unknown")
    if health in {"unhealthy", "watch"}:
        seed = f"health:{health}"
        if seed not in seen:
            seen.add(seed)
            proposals.append(
                _proposal_row(
                    seed=seed,
                    target_ecology="maintenance",
                    candidate="review action experience sedimentation health before expanding autonomy",
                    why_now=f"audit_health_status:{health}",
                )
            )
    for warning in audit.get("warnings") or []:
        rule = _warning_rule(_safe_str(warning))
        if rule is None:
            continue
        seed = f"warn:{warning}"
        if seed in seen:
            continue
        seen.add(seed)
        proposals.append(
            _proposal_row(
                seed=seed,
                target_ecology=rule["target_ecology"],
                candidate=rule["candidate"],
                why_now=rule["why_now"],
            )
        )
    for item in audit.get("top_repeated_action_themes") or []:
        if int(item.get("count") or 0) < 4:
            continue
        theme = _safe_str(item.get("theme"))
        seed = f"theme:{theme}"
        if seed in seen:
            continue
        seen.add(seed)
        proposals.append(
            _proposal_row(
                seed=seed,
                target_ecology="maintenance",
                candidate=f"compare last occurrences of repeated action theme: {theme[:120]}",
                why_now=f"repeated_action_theme_count:{item.get('count')}",
            )
        )
    return proposals[:12]


def _replicator_signal_rule(signal: str) -> dict[str, str] | None:
    text = _safe_str(signal)
    if text.startswith("visible_phrase_repeat:"):
        detail = text.split(":", 1)[-1]
        return {
            "target_ecology": "expression",
            "candidate": f"break visible phrase repetition cluster ({detail}) before next outward send",
            "why_now": f"replicator_signal:{text}",
        }
    if text.startswith("action_theme_repeat:"):
        detail = text.split(":", 1)[-1]
        return {
            "target_ecology": "maintenance",
            "candidate": f"vary repeated action theme ({detail}) before next bounded action",
            "why_now": f"replicator_signal:{text}",
        }
    if text == "top_phrase_cluster":
        return {
            "target_ecology": "expression",
            "candidate": "break up the top visible phrase cluster before next outward reply",
            "why_now": "replicator_signal:top_phrase_cluster",
        }
    if text == "top_theme_cluster":
        return {
            "target_ecology": "maintenance",
            "candidate": "vary the top repeated action theme before next maintenance pass",
            "why_now": "replicator_signal:top_theme_cluster",
        }
    if text.startswith("life_narrative_markers:"):
        detail = text.split(":", 1)[-1]
        return {
            "target_ecology": "expression",
            "candidate": "reduce life-narrative self-description motif in visible sends",
            "why_now": f"replicator_signal:life_narrative_markers:{detail}",
        }
    if text.startswith("tool_call_motif:"):
        detail = text.split(":", 1)[-1]
        return {
            "target_ecology": "maintenance",
            "candidate": f"reduce tool-call status motif repetition in visible sends ({detail})",
            "why_now": f"replicator_signal:{text}",
        }
    return None


def build_followup_proposals_from_replicator_pressure(
    pressure: dict[str, Any],
    *,
    audit: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Queue reviewable follow-ups when replicator pressure reaches alert (no execution)."""
    if _safe_str(pressure.get("level")) != "alert":
        return []

    proposals: list[dict[str, Any]] = []
    seen: set[str] = set()
    score = int(pressure.get("score") or 0)
    umbrella_seed = f"replicator:alert:score={score}"
    if umbrella_seed not in seen:
        seen.add(umbrella_seed)
        proposals.append(
            _proposal_row(
                seed=umbrella_seed,
                source="replicator_pressure_audit",
                target_ecology="expression",
                candidate="review replicator pressure cluster before next outward reply or autonomy expansion",
                why_now=f"replicator_pressure_alert:score={score}",
            )
        )

    for signal in pressure.get("signals") or []:
        rule = _replicator_signal_rule(_safe_str(signal))
        if rule is None:
            continue
        seed = f"replicator:signal:{signal}"
        if seed in seen:
            continue
        seen.add(seed)
        proposals.append(
            _proposal_row(
                seed=seed,
                source="replicator_pressure_audit",
                target_ecology=rule["target_ecology"],
                candidate=rule["candidate"],
                why_now=rule["why_now"],
            )
        )

    if audit and not (pressure.get("signals") or []):
        for warning in audit.get("warnings") or []:
            rule = _warning_rule(_safe_str(warning))
            if rule is None:
                continue
            seed = f"replicator:audit_warn:{warning}"
            if seed in seen:
                continue
            seen.add(seed)
            proposals.append(
                _proposal_row(
                    seed=seed,
                    source="replicator_pressure_audit",
                    target_ecology=rule["target_ecology"],
                    candidate=f"replicator alert follow-up: {rule['candidate'][:180]}",
                    why_now=f"replicator_pressure_alert:{rule['why_now'][:180]}",
                )
            )

    return proposals[:8]


def merge_followup_proposals(*proposal_lists: list[dict[str, Any]], limit: int = 16) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for proposals in proposal_lists:
        for proposal in proposals:
            item_id = _safe_str(proposal.get("item_id"))
            if not item_id or item_id in seen:
                continue
            seen.add(item_id)
            merged.append(proposal)
            if len(merged) >= limit:
                return merged
    return merged


def _proposal_row(
    *,
    seed: str,
    target_ecology: str,
    candidate: str,
    why_now: str,
    source: str = "action_openended_audit",
) -> dict[str, Any]:
    created_at = _now_iso()
    item_id = _proposal_id(seed)
    return {
        "item_id": item_id,
        "domain": "followup",
        "proposal_kind": "next_safe_challenge",
        "source": source,
        "target_ecology": target_ecology,
        "candidate": candidate[:220],
        "risk": "read_only",
        "requires_owner": True,
        "review_status": "pending",
        "why_now": why_now[:220],
        "blocked_changes": list(_BLOCKED_CHANGES),
        "content_preview": candidate[:120],
        "created_at": created_at,
    }


def load_followup_inbox(root: Path) -> list[dict[str, Any]]:
    path = root / FOLLOWUP_INBOX_REL
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _write_followup_state(
    root: Path,
    *,
    queued: int,
    pending: int,
    last_audit_health: str,
    last_replicator_level: str = "quiet",
) -> None:
    path = root / STATE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "---",
        "title: Action Follow-up Proposals State",
        "memory_type: action_followup_proposals_state",
        "time_scope: short_term",
        "protected: true",
        f"updated_at: {_now_iso()}",
        "---",
        "",
        "# Action Follow-up Proposals State",
        "",
        f"- last_audit_health: {last_audit_health}",
        f"- last_replicator_level: {last_replicator_level}",
        f"- last_queued_count: {queued}",
        f"- pending_followup_count: {pending}",
        "- execution_policy: review_only_no_auto_run",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def queue_followup_proposals(root: Path, proposals: list[dict[str, Any]]) -> dict[str, Any]:
    root = root.resolve()
    existing = load_followup_inbox(root)
    pending_ids = {
        _safe_str(row.get("item_id"))
        for row in existing
        if _safe_str(row.get("review_status"), "pending") == "pending"
    }
    inserted = 0
    path = root / FOLLOWUP_INBOX_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for proposal in proposals:
            item_id = _safe_str(proposal.get("item_id"))
            if not item_id or item_id in pending_ids:
                continue
            handle.write(json.dumps(proposal, ensure_ascii=False, sort_keys=True) + "\n")
            pending_ids.add(item_id)
            inserted += 1
    pending = sum(1 for row in load_followup_inbox(root) if _safe_str(row.get("review_status")) == "pending")
    _write_followup_state(root, queued=inserted, pending=pending, last_audit_health="unknown")
    return {
        "queued_count": inserted,
        "pending_count": pending,
        "proposal_ids": [p.get("item_id") for p in proposals[:inserted]],
        "notes": ["followup_proposals_queued"] if inserted else ["followup_proposals_none_new"],
    }


def update_followup_review_status(root: Path, item_id: str, *, action: str) -> dict[str, Any]:
    rows = load_followup_inbox(root)
    target = _safe_str(item_id)
    updated = False
    new_status = "approved" if action == "approve" else "rejected"
    for row in rows:
        if _safe_str(row.get("item_id")) != target:
            continue
        row["review_status"] = new_status
        row["reviewed_at"] = _now_iso()
        updated = True
        break
    if not updated:
        return {"updated": False, "item_id": target, "reason": "not_found"}
    path = root / FOLLOWUP_INBOX_REL
    text = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)
    path.write_text(text + ("\n" if text else ""), encoding="utf-8")
    return {"updated": True, "item_id": target, "review_status": new_status}


def run_audit_and_queue_followups(
    root: Path,
    *,
    low_salience_threshold: float = 0.6,
    include_replicator: bool = True,
) -> dict[str, Any]:
    from xinyu_replicator_pressure_audit import assess_replicator_pressure

    audit = run_audit(root, low_salience_threshold=low_salience_threshold)
    pressure: dict[str, Any] = {}
    if include_replicator:
        pressure = assess_replicator_pressure(root, audit_result=audit)
        audit["replicator_pressure"] = pressure
    audit_proposals = build_followup_proposals_from_audit(audit)
    replicator_proposals = build_followup_proposals_from_replicator_pressure(pressure, audit=audit)
    proposals = merge_followup_proposals(audit_proposals, replicator_proposals)
    queue = queue_followup_proposals(root, proposals)
    repl_level = _safe_str(pressure.get("level"), "quiet")
    _write_followup_state(
        root,
        queued=int(queue.get("queued_count") or 0),
        pending=int(queue.get("pending_count") or 0),
        last_audit_health=_safe_str(audit.get("health_status")),
        last_replicator_level=repl_level,
    )
    notes = list(queue.get("notes") or [])
    if repl_level == "alert" and replicator_proposals:
        notes.append(f"replicator_alert_followups:{len(replicator_proposals)}")
    return {
        **audit,
        "followup_proposals": proposals,
        "followup_proposal_count": len(proposals),
        "replicator_followup_proposals": replicator_proposals,
        "replicator_followup_count": len(replicator_proposals),
        "followup_queue": queue,
        "notes": notes,
    }
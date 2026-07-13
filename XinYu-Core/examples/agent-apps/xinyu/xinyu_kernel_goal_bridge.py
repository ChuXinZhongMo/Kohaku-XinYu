"""Bridge cognitive-kernel signals into self-chosen goal ecology candidates."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

KERNEL_SIGNALS_REL = Path("runtime/self_chosen_goal_ecology/kernel_signals.json")
CYCLE_EVENTS_REL = Path("memory/events/cognitive_cycle_events.jsonl")


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip() or default


def _read_cycle_tail(root: Path, *, limit: int = 8) -> list[dict[str, Any]]:
    path = root / CYCLE_EVENTS_REL
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
    return rows[-limit:]


def read_kernel_pressure_signals(root: Path) -> dict[str, Any]:
    root = root.resolve()
    signals: dict[str, Any] = {
        "available": False,
        "pending_review_count": 0,
        "structural_impact_recent": False,
        "slow_signal_count": 0,
        "reorg_recommendation": "none",
        "recent_cycle_count": 0,
        "kernel_pressure": False,
    }
    try:
        from kernel.bridge_access import query_kernel_state

        state = query_kernel_state(root)
        if not state.get("available"):
            return signals
        inbox = state.get("review_inbox") if isinstance(state.get("review_inbox"), dict) else {}
        meta = state.get("reorg_meta") if isinstance(state.get("reorg_meta"), dict) else {}
        ctx = state.get("kernel_context") if isinstance(state.get("kernel_context"), dict) else {}
        cycles = _read_cycle_tail(root)
        structural_recent = any(bool(row.get("structural_impact")) for row in cycles[-3:])
        pending = int(inbox.get("pending_count") or 0)
        slow = int(state.get("slow_signal_count") or 0)
        pending_reorg = int(ctx.get("pending_reorg_count") or 0)
        recommendation = _safe_str(meta.get("recommendation"), "none")
        pressure = pending >= 2 or structural_recent or slow >= 2 or pending_reorg >= 1
        signals.update(
            {
                "available": True,
                "pending_review_count": pending,
                "pending_reorg_count": pending_reorg,
                "structural_impact_recent": structural_recent,
                "slow_signal_count": slow,
                "reorg_recommendation": recommendation,
                "recent_cycle_count": len(cycles),
                "kernel_pressure": pressure,
                "checked_at": _now_iso(),
            }
        )
    except Exception:
        pass
    return signals


def sync_kernel_goal_signals(root: Path, *, cycle_result: dict[str, Any] | None = None) -> dict[str, Any]:
    """Persist kernel pressure snapshot for goal ecology selection."""
    root = root.resolve()
    signals = read_kernel_pressure_signals(root)
    if isinstance(cycle_result, dict):
        signals["last_cycle"] = {
            "source_event_id": cycle_result.get("source_event_id"),
            "reorg_mode": cycle_result.get("reorg_mode"),
            "structural_impact": bool(cycle_result.get("structural_impact")),
            "cycle_closed": bool(cycle_result.get("cycle_closed")),
        }
    path = root / KERNEL_SIGNALS_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(signals, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return signals


def kernel_goal_candidate_specs(signals: dict[str, Any]) -> list[dict[str, Any]]:
    if not signals.get("kernel_pressure"):
        return []
    specs: list[dict[str, Any]] = []
    if signals.get("structural_impact_recent") or int(signals.get("pending_reorg_count") or 0) >= 1:
        specs.append(
            {
                "goal_id": "kernel_reorg_review",
                "label": "kernel reorg review",
                "motive": "Recent cognitive cycle produced structural impact or pending reorg work.",
                "base_score": 0.24,
                "evidence_paths": ("memory/events/cognitive_cycle_events.jsonl", "runtime/self_chosen_goal_ecology/kernel_signals.json"),
                "next_safe_action": "surface kernel reorg/review items to owner inbox without auto-applying",
                "boundary": "state_only; kernel apply remains owner-gated",
            }
        )
    if int(signals.get("pending_review_count") or 0) >= 2:
        specs.append(
            {
                "goal_id": "kernel_belief_wm_review",
                "label": "kernel belief/world-model review",
                "motive": "Kernel review inbox has multiple pending belief or world-model candidates.",
                "base_score": 0.22,
                "evidence_paths": ("memory/kernel/owner_grants.json", "runtime/kernel_followup_review_inbox.jsonl"),
                "next_safe_action": "review pending kernel candidates before expanding outward initiative",
                "boundary": "state_only; no stable memory write",
            }
        )
    if int(signals.get("slow_signal_count") or 0) >= 2:
        specs.append(
            {
                "goal_id": "kernel_slow_signal_digest",
                "label": "kernel slow-signal digest",
                "motive": "Slow cognitive signals are accumulating and may need a bounded digest.",
                "base_score": 0.20,
                "evidence_paths": ("memory/kernel/reorg_meta.json", "runtime/self_chosen_goal_ecology/kernel_signals.json"),
                "next_safe_action": "prepare a read-only digest of slow signals for owner review",
                "boundary": "state_only; no automatic reorg execution",
            }
        )
    return specs
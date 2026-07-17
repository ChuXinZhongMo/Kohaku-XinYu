"""Joint priority queue for 24h autonomy ticks (E4 / Card 7).

device_gate + maintenance + proactive + scout share one control law:
- live private chat always wins
- high PE / concrete proactive next
- maintenance before heavy scout when resources tight
- independent timers alone cause thrash; this ranks concurrent candidates

Pure decision helper — does not start threads. Callers pass candidates and run winners.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence


# Lower number = higher priority (runs first / preferred under contention).
KIND_BASE_PRIORITY = {
    "live_chat": 0,
    "heartbeat": 1,
    "proactive": 20,
    "self_thought": 40,
    "maintenance": 50,
    "skill_curator": 55,
    "tech_scout": 70,
    "apply_batch": 80,
}

# Resource cost 0..1 — higher cost deferred when device is stressed.
KIND_COST = {
    "live_chat": 0.15,
    "heartbeat": 0.05,
    "proactive": 0.25,
    "self_thought": 0.2,
    "maintenance": 0.45,
    "skill_curator": 0.35,
    "tech_scout": 0.85,
    "apply_batch": 0.6,
}


@dataclass(frozen=True)
class TickCandidate:
    kind: str
    ready: bool = True
    pe_stress: float = 0.0
    predicted_deviation: float = 0.0
    has_finding: bool = False
    concrete: bool = False
    force: bool = False
    label: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "ready": self.ready,
            "pe_stress": self.pe_stress,
            "predicted_deviation": self.predicted_deviation,
            "has_finding": self.has_finding,
            "concrete": self.concrete,
            "force": self.force,
            "label": self.label,
            "meta": dict(self.meta),
        }


@dataclass(frozen=True)
class TickDecision:
    kind: str
    allow: bool
    score: float
    reason: str
    rank: int
    label: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "allow": self.allow,
            "score": self.score,
            "reason": self.reason,
            "rank": self.rank,
            "label": self.label,
        }


@dataclass(frozen=True)
class QueuePlan:
    ordered: tuple[TickDecision, ...]
    allowed: tuple[TickDecision, ...]
    deferred: tuple[TickDecision, ...]
    device_allowed: bool
    device_reason: str
    notes: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "ordered": [d.as_dict() for d in self.ordered],
            "allowed": [d.as_dict() for d in self.allowed],
            "deferred": [d.as_dict() for d in self.deferred],
            "device_allowed": self.device_allowed,
            "device_reason": self.device_reason,
            "notes": list(self.notes),
        }


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def score_candidate(
    candidate: TickCandidate,
    *,
    device_allowed: bool,
    resource_pressure: float = 0.0,
) -> TickDecision:
    kind = str(candidate.kind or "").strip().lower() or "unknown"
    base = float(KIND_BASE_PRIORITY.get(kind, 90))
    cost = float(KIND_COST.get(kind, 0.5))
    pe = _clamp01(candidate.pe_stress)
    pred = _clamp01(candidate.predicted_deviation)
    pressure = _clamp01(resource_pressure)

    # Effective rank score: lower is better.
    score = base
    # Opportunity: PE / deviation improves proactive/self_thought priority.
    if kind in {"proactive", "self_thought"}:
        score -= 12.0 * pe + 8.0 * pred
        if candidate.has_finding and candidate.concrete:
            score -= 15.0
        elif kind == "proactive" and not candidate.has_finding:
            score += 25.0  # deprioritize empty proactive hard
    if kind == "tech_scout":
        score += 20.0 * pressure  # push scout back under load
        if not device_allowed:
            return TickDecision(
                kind=kind,
                allow=False,
                score=score + 100.0,
                reason="device_blocked",
                rank=999,
                label=candidate.label,
            )
    if kind in {"maintenance", "skill_curator", "apply_batch"} and not device_allowed and not candidate.force:
        # Light maintenance may still run; heavy ones wait.
        if cost >= 0.4:
            return TickDecision(
                kind=kind,
                allow=False,
                score=score + 50.0,
                reason="device_blocked_heavy",
                rank=998,
                label=candidate.label,
            )

    if not candidate.ready and not candidate.force:
        return TickDecision(
            kind=kind,
            allow=False,
            score=score + 40.0,
            reason="not_ready",
            rank=997,
            label=candidate.label,
        )

    # Live chat never deferred by this queue.
    if kind == "live_chat":
        return TickDecision(
            kind=kind,
            allow=True,
            score=0.0,
            reason="live_preempts",
            rank=0,
            label=candidate.label,
        )

    # Cost under pressure.
    score += 18.0 * cost * pressure

    allow = True
    reason = "scheduled"
    if kind == "proactive" and not (candidate.has_finding and candidate.concrete):
        # Still rankable but not allowed to fire empty.
        if not candidate.concrete:
            allow = False
            reason = "proactive_no_concrete"
        elif not candidate.has_finding:
            allow = False
            reason = "proactive_no_finding"

    return TickDecision(
        kind=kind,
        allow=allow,
        score=score,
        reason=reason,
        rank=0,
        label=candidate.label,
    )


def plan_tick_queue(
    candidates: Sequence[TickCandidate] | Iterable[TickCandidate],
    *,
    device_allowed: bool = True,
    device_reason: str = "ok",
    resource_pressure: float = 0.0,
    max_allowed: int = 3,
) -> QueuePlan:
    """Order candidates; allow only top ready ones under device/pressure constraints."""
    items = list(candidates or [])
    decisions = [
        score_candidate(
            c,
            device_allowed=device_allowed,
            resource_pressure=resource_pressure,
        )
        for c in items
    ]
    # Sort by score ascending, stable by kind.
    decisions.sort(key=lambda d: (d.score, d.kind, d.label))
    ranked: list[TickDecision] = []
    for i, d in enumerate(decisions):
        ranked.append(
            TickDecision(
                kind=d.kind,
                allow=d.allow,
                score=d.score,
                reason=d.reason,
                rank=i,
                label=d.label,
            )
        )

    allowed: list[TickDecision] = []
    deferred: list[TickDecision] = []
    # Always allow live_chat if present and allowed.
    for d in ranked:
        if d.kind == "live_chat" and d.allow:
            allowed.append(d)
    for d in ranked:
        if d.kind == "live_chat":
            continue
        if d.allow and len(allowed) < max(1, int(max_allowed)):
            # Under hard device deny, only heartbeat/self_thought light work.
            if not device_allowed and d.kind in {"tech_scout", "apply_batch"}:
                deferred.append(
                    TickDecision(
                        kind=d.kind,
                        allow=False,
                        score=d.score,
                        reason="device_deferred",
                        rank=d.rank,
                        label=d.label,
                    )
                )
                continue
            allowed.append(d)
        else:
            deferred.append(
                TickDecision(
                    kind=d.kind,
                    allow=False,
                    score=d.score,
                    reason=d.reason if not d.allow else "queue_capacity",
                    rank=d.rank,
                    label=d.label,
                )
            )

    notes = []
    if not device_allowed:
        notes.append(f"device_not_allowed:{device_reason}")
    if resource_pressure >= 0.7:
        notes.append("high_resource_pressure")

    return QueuePlan(
        ordered=tuple(ranked),
        allowed=tuple(allowed),
        deferred=tuple(deferred),
        device_allowed=bool(device_allowed),
        device_reason=str(device_reason or ""),
        notes=tuple(notes),
    )


def resource_pressure_from_device_metrics(metrics: dict[str, Any] | None) -> float:
    """Map device gate metrics to 0..1 pressure for queue scoring."""
    m = dict(metrics or {})
    pressure = 0.0
    try:
        cpu = float(m.get("cpu_percent"))
        pressure = max(pressure, _clamp01((cpu - 50.0) / 50.0))
    except (TypeError, ValueError):
        pass
    try:
        ram = float(m.get("ram_free_gb"))
        # <3GB free starts pressure
        pressure = max(pressure, _clamp01((3.0 - ram) / 3.0))
    except (TypeError, ValueError):
        pass
    try:
        disk = float(m.get("disk_free_gb"))
        pressure = max(pressure, _clamp01((8.0 - disk) / 8.0))
    except (TypeError, ValueError):
        pass
    if m.get("tts_busy"):
        pressure = max(pressure, 0.55)
    return _clamp01(pressure)


def plan_from_device_gate(
    candidates: Sequence[TickCandidate] | Iterable[TickCandidate],
    device_decision: Any,
    *,
    max_allowed: int = 3,
) -> QueuePlan:
    """Convenience: accept DeviceGateDecision-like object or dict."""
    if device_decision is None:
        return plan_tick_queue(candidates, device_allowed=True, max_allowed=max_allowed)
    if hasattr(device_decision, "allowed"):
        allowed = bool(device_decision.allowed)
        reason = str(getattr(device_decision, "reason", "") or "")
        metrics = dict(getattr(device_decision, "metrics", {}) or {})
    elif isinstance(device_decision, dict):
        allowed = bool(device_decision.get("allowed", True))
        reason = str(device_decision.get("reason") or "")
        metrics = dict(device_decision.get("metrics") or {})
    else:
        allowed = True
        reason = "unknown_device"
        metrics = {}
    return plan_tick_queue(
        candidates,
        device_allowed=allowed,
        device_reason=reason,
        resource_pressure=resource_pressure_from_device_metrics(metrics),
        max_allowed=max_allowed,
    )


def should_run_kind(plan: QueuePlan, kind: str) -> bool:
    k = str(kind or "").strip().lower()
    return any(d.allow and d.kind == k for d in plan.allowed)

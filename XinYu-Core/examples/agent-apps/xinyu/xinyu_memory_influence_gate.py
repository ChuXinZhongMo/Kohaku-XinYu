"""Influence-governed memory gate (H2′ / Card 10).

Reliable long-lived companion memory governs *what may influence generation*
before prompt exposure: eligibility, status, boundary, supersession, abstention.

This is NOT dual-phase sleep consolidation (refuted in 2026-07-17 deep-research).
It is a small deterministic filter for recall/candidate items.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping

# Status values that must not enter live prompt influence.
BLOCKED_STATUSES = frozenset(
    {
        "archived",
        "disabled",
        "rejected",
        "stale",
        "superseded",
        "expired",
        "never",
        "ignore",
        "blocked",
        "quarantine",
        "quarantined",
    }
)

# Explicit write / store decisions that deny influence.
DENY_DECISIONS = frozenset({"never", "ignore", "reject", "drop", "block"})

# Boundary labels that keep content out of always-on prompt.
PRIVATE_BOUNDARIES = frozenset(
    {
        "owner_private_raw",
        "raw_qq",
        "secret",
        "credential",
        "prompt_forbidden",
        "no_prompt",
    }
)


@dataclass(frozen=True)
class InfluenceDecision:
    allow: bool
    reason: str
    status: str = ""
    boundary: str = ""
    superseded_by: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "allow": self.allow,
            "reason": self.reason,
            "status": self.status,
            "boundary": self.boundary,
            "superseded_by": self.superseded_by,
        }


def _norm(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "_")


def _item_get(item: Any, key: str, default: Any = "") -> Any:
    if item is None:
        return default
    if isinstance(item, Mapping):
        return item.get(key, default)
    return getattr(item, key, default)


def evaluate_memory_influence(item: Any) -> InfluenceDecision:
    """Decide whether a memory/candidate item may influence live generation."""
    status = _norm(_item_get(item, "status") or _item_get(item, "review_status"))
    boundary = _norm(_item_get(item, "boundary") or _item_get(item, "permission"))
    decision = _norm(_item_get(item, "store_decision") or _item_get(item, "write_decision"))
    superseded_by = str(
        _item_get(item, "superseded_by")
        or _item_get(item, "superseded_by_id")
        or ""
    ).strip()
    eligible = _item_get(item, "eligible", None)
    abstain = bool(_item_get(item, "abstain", False))

    if abstain:
        return InfluenceDecision(False, "abstain", status=status, boundary=boundary)

    if eligible is False or _norm(eligible) in {"0", "false", "no", "off"}:
        return InfluenceDecision(False, "not_eligible", status=status, boundary=boundary)

    if decision in DENY_DECISIONS:
        return InfluenceDecision(
            False, f"store_{decision}", status=status, boundary=boundary
        )

    if status in BLOCKED_STATUSES:
        return InfluenceDecision(
            False, f"status_{status}", status=status, boundary=boundary
        )

    if superseded_by:
        return InfluenceDecision(
            False,
            "superseded",
            status=status or "superseded",
            boundary=boundary,
            superseded_by=superseded_by,
        )

    if boundary in PRIVATE_BOUNDARIES:
        return InfluenceDecision(
            False, f"boundary_{boundary}", status=status, boundary=boundary
        )

    # review_only / approved / pending-with-self-approved paths may influence as hints.
    return InfluenceDecision(True, "eligible", status=status, boundary=boundary)


def filter_influence_items(items: Iterable[Any]) -> list[Any]:
    """Keep only items allowed to influence the live prompt."""
    kept: list[Any] = []
    for item in items or []:
        if evaluate_memory_influence(item).allow:
            kept.append(item)
    return kept


def influence_gate_stats(items: Iterable[Any]) -> dict[str, Any]:
    total = 0
    allowed = 0
    reasons: dict[str, int] = {}
    for item in items or []:
        total += 1
        decision = evaluate_memory_influence(item)
        if decision.allow:
            allowed += 1
        reasons[decision.reason] = reasons.get(decision.reason, 0) + 1
    return {
        "total": total,
        "allowed": allowed,
        "blocked": total - allowed,
        "reasons": reasons,
    }

"""Owner-controlled autonomy-expansion policy.

The self-action gateway and goal ecology are deliberately narrow: read-only probes,
one action per cycle, a fixed goal set. That keeps XinYu safe but also keeps it from
doing much on its own. This policy lets the owner widen the *inward, reversible*
autonomy envelope without touching the two hard boundaries that always stay human-gated
(outward messages, stable-memory / personality changes).

Everything here is OFF or set to the current behavior by default, so an absent or empty
policy file reproduces today's posture exactly. The owner opts into more autonomy by
writing the policy file; the expansion only ever covers contained, reversible work.

Levers:
  * productive_low_risk_enabled  (#1) — let goals emit a productive, reversible action
    (a scratch reflection note under runtime/self_scratch/) in addition to read probes.
  * max_low_risk_actions_per_cycle (#5) — execute up to N low-risk actions per cycle
    instead of exactly one.
  * productive_goals_enabled (#2) — add output-producing goals to the ecology.
  * reliability_budget_enabled (#4) — grow the trusted auto-approval window budget in
    proportion to a goal's proven success record.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

POLICY_REL = Path("memory/context/self_autonomy_expansion_policy.json")

SCRATCH_DIR_REL = Path("runtime/self_scratch")

# Goals that gain a productive (artifact-producing) low-risk action when #1 is enabled.
PRODUCTIVE_GOAL_IDS = frozenset(
    {
        "continue_bounded_work",
        "curate_failure_replay",
        "synthesize_knowledge",
        "draft_self_improvement",
    }
)


@dataclass(frozen=True, slots=True)
class AutonomyPolicy:
    productive_low_risk_enabled: bool = False
    max_low_risk_actions_per_cycle: int = 1
    productive_goals_enabled: bool = False
    reliability_budget_enabled: bool = False
    reliability_bonus_per_success: float = 0.5
    reliability_bonus_cap: int = 3


def default_policy() -> AutonomyPolicy:
    """The safe, no-change-from-today policy used when no owner file is present."""
    return AutonomyPolicy()


def load_policy(root: Path, *, reader: Callable[[Path], Any] | None = None) -> AutonomyPolicy:
    path = Path(root) / POLICY_REL
    raw = reader(path) if reader is not None else _read_json(path)
    if not isinstance(raw, dict):
        return default_policy()
    return AutonomyPolicy(
        productive_low_risk_enabled=bool(raw.get("productive_low_risk_enabled", False)),
        max_low_risk_actions_per_cycle=max(1, _safe_int(raw.get("max_low_risk_actions_per_cycle"), 1)),
        productive_goals_enabled=bool(raw.get("productive_goals_enabled", False)),
        reliability_budget_enabled=bool(raw.get("reliability_budget_enabled", False)),
        reliability_bonus_per_success=_safe_float(raw.get("reliability_bonus_per_success"), 0.5),
        reliability_bonus_cap=max(0, _safe_int(raw.get("reliability_bonus_cap"), 3)),
    )


def reliability_budget_bonus(success_count: int, policy: AutonomyPolicy) -> int:
    """Extra auto-approvals a goal earns from its proven success record (#4).

    Autonomy grows with demonstrated reliability: the more a goal type has succeeded,
    the larger its auto-approval window — capped so it can never run away.
    """
    if not policy.reliability_budget_enabled:
        return 0
    earned = int(max(0, success_count) * policy.reliability_bonus_per_success)
    return max(0, min(policy.reliability_bonus_cap, earned))


def write_example_policy(root: Path) -> Path:
    """Write a disabled, annotated example policy the owner can edit."""
    path = Path(root) / POLICY_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    example = {
        "_doc": "Owner-controlled autonomy expansion. All levers default to today's behavior. "
        "Expansion only ever covers inward, reversible work; outward messages and stable-memory "
        "changes always stay human-gated.",
        "productive_low_risk_enabled": False,
        "max_low_risk_actions_per_cycle": 1,
        "productive_goals_enabled": False,
        "reliability_budget_enabled": False,
        "reliability_bonus_per_success": 0.5,
        "reliability_bonus_cap": 3,
    }
    path.write_text(json.dumps(example, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

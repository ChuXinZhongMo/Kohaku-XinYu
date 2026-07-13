"""Owner-grant gated autonomy expansion (productive low-risk + reliability budget)."""

from __future__ import annotations

import re
from pathlib import Path

from xinyu_autonomy_policy import AutonomyPolicy, load_policy


GRANT_MARKER = "grant_autonomy_expansion: productive_low_risk_and_reliability_budget"
GRANTS_REL = Path("memory/context/owner_permission_grants.md")


def _read_grants(root: Path) -> str:
    path = root / GRANTS_REL
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return ""


def autonomy_expansion_granted(root: Path) -> bool:
    text = _read_grants(root)
    return GRANT_MARKER in text or bool(
        re.search(r"grant_autonomy_expansion\s*:\s*approved", text, re.I)
    )


def effective_autonomy_policy(root: Path) -> AutonomyPolicy:
    """Merge owner grant with on-disk policy; grant enables bounded expansion levers."""
    policy = load_policy(root)
    if not autonomy_expansion_granted(root):
        return policy
    return AutonomyPolicy(
        productive_low_risk_enabled=policy.productive_low_risk_enabled or True,
        max_low_risk_actions_per_cycle=max(policy.max_low_risk_actions_per_cycle, 2),
        productive_goals_enabled=policy.productive_goals_enabled,
        reliability_budget_enabled=policy.reliability_budget_enabled or True,
        reliability_bonus_per_success=policy.reliability_bonus_per_success,
        reliability_bonus_cap=max(policy.reliability_bonus_cap, 3),
    )


def expansion_canary_fields(root: Path) -> dict[str, str]:
    granted = autonomy_expansion_granted(root)
    policy = effective_autonomy_policy(root) if granted else load_policy(root)
    return {
        "autonomy_expansion_granted": "yes" if granted else "no",
        "productive_low_risk_enabled": "yes" if policy.productive_low_risk_enabled else "no",
        "reliability_budget_enabled": "yes" if policy.reliability_budget_enabled else "no",
        "max_low_risk_actions_per_cycle": str(policy.max_low_risk_actions_per_cycle),
    }
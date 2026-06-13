"""Trusted-scope auto-approval policy for the self-action gateway.

The self-action gateway queues every boundary-crossing action (code patch, outward
message, stable-memory change) for owner approval. That owner click is the single
real bottleneck on XinYu's autonomy. This module lets the owner delegate approval
for a *narrow, reversible* set of scopes — by default focused app-code patches and
replay fixture/test patches — so those flow through automatically while everything
risky still waits for a human.

Safety invariants (enforced here, not negotiable by config):
  * Outward messages and stable-memory / personality changes can NEVER be
    auto-approved, regardless of what the policy file says.
  * Auto-approval is OFF unless the owner writes an enabled policy file.
  * Auto-approval is rate-limited within a rolling window.
  * Auto-approval only removes the *approval* click; the patch executor's staged
    Codex run + watchdog snapshot remain the execution gate.

This module is pure policy: it parses the owner policy, decides eligibility, and
does the rolling-window ledger math. The gateway owns the wiring and the audit log.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable

POLICY_REL = Path("memory/context/self_action_trusted_autoapproval_policy.json")

# Hard exclusions: these can never be auto-approved even if a policy lists them.
NEVER_AUTO_APPROVE_ACTION_KINDS = frozenset(
    {
        "owner_message_draft_request",
        "stable_memory_change_request",
    }
)
NEVER_AUTO_APPROVE_SCOPES = frozenset(
    {
        "owner_private_message_draft",
        "stable_memory_or_voice_repair",
    }
)

DEFAULT_TRUSTED_SCOPES = frozenset({"focused_xinyu_app_patch", "replay_fixture_or_test_patch"})
DEFAULT_TRUSTED_ACTION_KINDS = frozenset({"self_code_patch_request"})
# Of the trusted scopes, only these may auto-run Codex unattended (#3). Fixture/test
# patches are the lowest-blast-radius slice; focused app patches stay human-launched.
DEFAULT_CODEX_ELIGIBLE_SCOPES = frozenset({"replay_fixture_or_test_patch"})


@dataclass(frozen=True, slots=True)
class TrustedAutoApprovalPolicy:
    enabled: bool = False
    trusted_scopes: frozenset[str] = DEFAULT_TRUSTED_SCOPES
    trusted_action_kinds: frozenset[str] = DEFAULT_TRUSTED_ACTION_KINDS
    max_auto_approvals_per_window: int = 3
    window_hours: float = 24.0
    auto_execute_handoff: bool = True
    auto_run_codex: bool = False
    codex_eligible_scopes: frozenset[str] = DEFAULT_CODEX_ELIGIBLE_SCOPES


def default_policy() -> TrustedAutoApprovalPolicy:
    """A safe, disabled policy used whenever no owner policy file is present."""
    return TrustedAutoApprovalPolicy()


def load_policy(
    root: Path,
    *,
    reader: Callable[[Path], Any] | None = None,
) -> TrustedAutoApprovalPolicy:
    """Load the owner policy file, falling back to the disabled default.

    `reader` lets the gateway inject its own boundary-aware JSON reader; tests and
    standalone use fall back to a plain UTF-8 JSON read.
    """
    path = Path(root) / POLICY_REL
    raw = reader(path) if reader is not None else _read_json(path)
    if not isinstance(raw, dict):
        return default_policy()
    return _policy_from_raw(raw)


def scope_is_auto_approvable(action_kind: str, scope: str, policy: TrustedAutoApprovalPolicy) -> bool:
    """True only when this action is inside the owner-trusted, never-excluded set."""
    if not policy.enabled:
        return False
    action_kind = (action_kind or "").strip()
    scope = (scope or "").strip()
    if action_kind in NEVER_AUTO_APPROVE_ACTION_KINDS or scope in NEVER_AUTO_APPROVE_SCOPES:
        return False
    if action_kind not in policy.trusted_action_kinds:
        return False
    return scope in policy.trusted_scopes


def scope_is_codex_auto_runnable(action_kind: str, scope: str, policy: TrustedAutoApprovalPolicy) -> bool:
    """True when an auto-approved action may also auto-run Codex unattended (#3).

    Strictly narrower than auto-approval: it must first be auto-approvable, the owner
    must have enabled ``auto_run_codex``, and the scope must be Codex-eligible.
    """
    if not policy.auto_run_codex:
        return False
    if not scope_is_auto_approvable(action_kind, scope, policy):
        return False
    return (scope or "").strip() in policy.codex_eligible_scopes


def prune_ledger(ledger: list[dict[str, Any]], *, now_iso: str, window_hours: float) -> list[dict[str, Any]]:
    """Drop ledger entries whose decision time is outside the rolling window."""
    now = _parse_iso(now_iso)
    if now is None or window_hours <= 0:
        return [entry for entry in ledger if isinstance(entry, dict)]
    cutoff = now - timedelta(hours=window_hours)
    kept: list[dict[str, Any]] = []
    for entry in ledger:
        if not isinstance(entry, dict):
            continue
        decided = _parse_iso(str(entry.get("decided_at", "")))
        if decided is None or decided >= cutoff:
            kept.append(entry)
    return kept


def remaining_budget(ledger: list[dict[str, Any]], policy: TrustedAutoApprovalPolicy) -> int:
    """How many more auto-approvals are allowed in the current window."""
    return max(0, policy.max_auto_approvals_per_window - len(ledger))


def write_example_policy(root: Path) -> Path:
    """Write a disabled, fully-annotated example policy the owner can edit."""
    path = Path(root) / POLICY_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    example = {
        "_doc": "Owner-controlled trusted-scope auto-approval. Set enabled=true to delegate "
        "approval for the listed code-patch scopes only. Outward messages and stable-memory "
        "changes can never be auto-approved.",
        "enabled": False,
        "trusted_scopes": sorted(DEFAULT_TRUSTED_SCOPES),
        "trusted_action_kinds": sorted(DEFAULT_TRUSTED_ACTION_KINDS),
        "max_auto_approvals_per_window": 3,
        "window_hours": 24,
        "auto_execute_handoff": True,
        "auto_run_codex": False,
        "codex_eligible_scopes": sorted(DEFAULT_CODEX_ELIGIBLE_SCOPES),
    }
    path.write_text(json.dumps(example, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _policy_from_raw(raw: dict[str, Any]) -> TrustedAutoApprovalPolicy:
    scopes = _clean_set(raw.get("trusted_scopes"), DEFAULT_TRUSTED_SCOPES) - NEVER_AUTO_APPROVE_SCOPES
    kinds = _clean_set(raw.get("trusted_action_kinds"), DEFAULT_TRUSTED_ACTION_KINDS) - NEVER_AUTO_APPROVE_ACTION_KINDS
    # Codex-eligible scopes can only ever be a subset of the (already cleaned) trusted scopes.
    codex_scopes = (_clean_set(raw.get("codex_eligible_scopes"), DEFAULT_CODEX_ELIGIBLE_SCOPES) & scopes) - NEVER_AUTO_APPROVE_SCOPES
    return TrustedAutoApprovalPolicy(
        enabled=bool(raw.get("enabled", False)),
        trusted_scopes=frozenset(scopes),
        trusted_action_kinds=frozenset(kinds),
        max_auto_approvals_per_window=_safe_int(raw.get("max_auto_approvals_per_window"), 3),
        window_hours=_safe_float(raw.get("window_hours"), 24.0),
        auto_execute_handoff=bool(raw.get("auto_execute_handoff", True)),
        auto_run_codex=bool(raw.get("auto_run_codex", False)),
        codex_eligible_scopes=frozenset(codex_scopes),
    )


def _clean_set(value: Any, default: frozenset[str]) -> set[str]:
    if not isinstance(value, list):
        return set(default)
    cleaned = {str(item).strip() for item in value if str(item).strip()}
    return cleaned or set(default)


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None


def _parse_iso(value: str) -> datetime | None:
    text = (value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
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

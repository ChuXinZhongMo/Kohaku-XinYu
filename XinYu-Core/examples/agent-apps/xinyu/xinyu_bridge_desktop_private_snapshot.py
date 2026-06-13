from __future__ import annotations

from pathlib import Path
from typing import Any, Callable


def desktop_private_ecosystem_snapshot(
    root: Path,
    *,
    build_private_ecosystem_snapshot_func: Callable[[Path], dict[str, Any]],
    build_browser_snapshot_func: Callable[[Path], dict[str, Any]],
    build_computer_snapshot_func: Callable[[Path], dict[str, Any]],
    safe_dict_func: Callable[[Any], dict[str, Any]],
    metric_int_func: Callable[[Any], int],
    safe_str_func: Callable[..., str],
) -> dict[str, Any]:
    """Sanitized first-screen view of XinYu's private ecosystem for the cockpit."""
    ecosystem = build_private_ecosystem_snapshot_func(root)
    browser = build_browser_snapshot_func(root)
    computer = build_computer_snapshot_func(root)
    counters = safe_dict_func(ecosystem.get("counters"))
    share = safe_dict_func(ecosystem.get("owner_private_share"))
    journal = safe_dict_func(ecosystem.get("journal"))
    boundaries = safe_dict_func(ecosystem.get("boundaries"))
    return {
        "observed": bool(ecosystem.get("observed")),
        "enabled": bool(ecosystem.get("enabled")),
        "rolloutState": safe_str_func(ecosystem.get("rollout_state")),
        "updatedAt": safe_str_func(ecosystem.get("updated_at")),
        "activeGoalId": safe_str_func(ecosystem.get("selected_goal_id")),
        "latestActionKind": safe_str_func(ecosystem.get("selected_action_kind")),
        "latestActionStatus": safe_str_func(ecosystem.get("last_action_status")),
        "counters": {
            "ticks": metric_int_func(counters.get("ticks")),
            "lowRiskExecuted": metric_int_func(counters.get("low_risk_executed")),
            "approvalQueued": metric_int_func(counters.get("approval_queued")),
            "memoryCandidates": metric_int_func(counters.get("memory_candidates")),
            "sharesPrepared": metric_int_func(counters.get("shares_prepared")),
            "sharesSent": metric_int_func(counters.get("shares_sent")),
            "sharesHeld": metric_int_func(counters.get("shares_held")),
            "blockedHighRisk": metric_int_func(counters.get("blocked_high_risk")),
        },
        "ownerPrivateShare": {
            "enabled": bool(share.get("enabled")),
            "paused": bool(share.get("paused")),
            "active": bool(share.get("active")),
            "deliveryLevel": safe_str_func(share.get("delivery_level")) or "none",
            "dailyRemaining": metric_int_func(share.get("daily_remaining")),
            "dailyLimit": metric_int_func(share.get("daily_limit")),
            "cooldownRemainingMinutes": metric_int_func(share.get("cooldown_remaining_minutes")),
            "quietHours": safe_str_func(share.get("quiet_hours")) or "00:00-06:00",
        },
        "journal": {
            "recentEvents": metric_int_func(journal.get("total_recent")),
            "latestEventKind": safe_str_func(journal.get("latest_event_kind")) or "none",
            "stableMemoryWriteCount": metric_int_func(journal.get("stable_memory_write_count")),
        },
        "browser": {
            "engine": safe_str_func(browser.get("engine")) or "unavailable",
            "lastActionKind": safe_str_func(browser.get("last_action_kind")) or "none",
            "lastResult": safe_str_func(browser.get("last_result")) or "none",
            "actionsTotal": metric_int_func(browser.get("actions_total")),
            "actionsBlocked": metric_int_func(browser.get("actions_blocked")),
            "artifactCount": metric_int_func(browser.get("artifact_count")),
            "screenshotCount": metric_int_func(browser.get("screenshot_count")),
            "usesOwnerProfile": bool(safe_dict_func(browser.get("boundaries")).get("uses_owner_browser_profile")),
        },
        "computer": {
            "backend": safe_str_func(computer.get("backend")) or "unavailable",
            "lastActionKind": safe_str_func(computer.get("last_action_kind")) or "none",
            "lastResult": safe_str_func(computer.get("last_result")) or "none",
            "observedCount": metric_int_func(computer.get("observed_count")),
            "proposedCount": metric_int_func(computer.get("proposed_count")),
            "blockedCount": metric_int_func(computer.get("blocked_count")),
            "multiStepArbitraryControl": safe_str_func(
                safe_dict_func(computer.get("boundaries")).get("multi_step_arbitrary_control")
            )
            or "disabled",
        },
        "killSwitch": {
            "sharePaused": bool(share.get("paused")),
            "shareEnabled": bool(share.get("enabled")),
        },
        "boundaries": {
            "stableMemoryWrite": safe_str_func(boundaries.get("stable_memory_write")) or "blocked",
            "qqMessageEnqueuedDirectly": bool(boundaries.get("qq_message_enqueued_directly")),
            "rawOwnerTextRetained": bool(boundaries.get("raw_owner_text_retained")),
            "secretOrLocalPathRetained": bool(boundaries.get("secret_or_local_path_retained")),
        },
        "paths": {
            "state": "memory/context/private_ecosystem_state.md",
            "grants": "memory/context/private_ecosystem_grants.json",
            "journal": "runtime/private_ecosystem/autonomy_journal.jsonl",
        },
    }

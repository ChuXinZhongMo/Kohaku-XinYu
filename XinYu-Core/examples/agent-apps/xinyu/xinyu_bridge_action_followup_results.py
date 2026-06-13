from __future__ import annotations

from typing import Any, Callable


def recent_action_row_note(row: dict[str, Any], safe_str_func: Callable[..., str]) -> str:
    if not row:
        return ""
    return f"recent_action_followup_result:{safe_str_func(row.get('result'), 'unknown')}"


def recent_action_payload(
    followup: dict[str, Any],
    row: dict[str, Any],
    safe_str_func: Callable[..., str],
) -> dict[str, str]:
    return {
        "mode": safe_str_func(followup.get("mode")),
        "tool": safe_str_func(row.get("tool")),
        "target_alias": safe_str_func(row.get("target_alias")),
        "result": safe_str_func(row.get("result")),
    }


def action_digest_row_note(row: dict[str, Any], safe_str_func: Callable[..., str]) -> str:
    if not row:
        return ""
    return f"action_digest_seed:{safe_str_func(row.get('seed_id'), 'none')}"


def action_digest_payload(
    followup: dict[str, Any],
    row: dict[str, Any],
    safe_str_func: Callable[..., str],
) -> dict[str, str]:
    return {
        "mode": safe_str_func(followup.get("mode")),
        "seed_id": safe_str_func(row.get("seed_id")),
        "reflection_item_id": safe_str_func(row.get("reflection_item_id")),
    }

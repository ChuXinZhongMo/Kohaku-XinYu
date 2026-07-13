from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from xinyu_bridge_stores import read_desktop_self_action_json_dict
from xinyu_bridge_stores import read_desktop_self_action_markdown_lines


def desktop_safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def desktop_safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def desktop_read_json_dict(path: Path) -> dict[str, Any]:
    return read_desktop_self_action_json_dict(path)


def desktop_read_markdown_fields(path: Path) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in read_desktop_self_action_markdown_lines(path):
        clean = line.strip()
        if not clean.startswith("- ") or ":" not in clean:
            continue
        key, value = clean[2:].split(":", 1)
        fields[key.strip()] = value.strip()
    return fields


def desktop_self_action_snapshot_payload(
    root: Path,
    *,
    gateway_state_rel: Path,
    approval_handoff_rel: Path,
    patch_state_rel: Path,
    patch_task_md_rel: Path,
    read_approval_queue_events_func: Callable[..., list[Any]],
    read_json_dict_func: Callable[[Path], dict[str, Any]] = desktop_read_json_dict,
    read_markdown_fields_func: Callable[[Path], dict[str, str]] = desktop_read_markdown_fields,
) -> dict[str, Any]:
    return {
        "gateway_state": read_json_dict_func(root / gateway_state_rel),
        "patch_state": read_json_dict_func(root / patch_state_rel),
        "approval_queue_events": read_approval_queue_events_func(root, limit=12),
        "handoff_fields": read_markdown_fields_func(root / approval_handoff_rel),
        "task_fields": read_markdown_fields_func(root / patch_task_md_rel),
    }


def desktop_self_action_snapshot_sources(
    payload: dict[str, Any],
    *,
    safe_dict_func: Callable[[Any], dict[str, Any]] = desktop_safe_dict,
    safe_list_func: Callable[[Any], list[Any]] = desktop_safe_list,
) -> dict[str, Any]:
    gateway_state = safe_dict_func(payload.get("gateway_state"))
    patch_state = safe_dict_func(payload.get("patch_state"))
    approval_queue_events = safe_list_func(payload.get("approval_queue_events"))
    handoff_fields = safe_dict_func(payload.get("handoff_fields"))
    task_fields = safe_dict_func(payload.get("task_fields"))
    patch_history = safe_list_func(patch_state.get("history"))

    return {
        "gateway_state": gateway_state,
        "patch_state": patch_state,
        "approval_queue_events": approval_queue_events,
        "handoff_fields": handoff_fields,
        "task_fields": task_fields,
        "last_run": safe_dict_func(gateway_state.get("last_run")),
        "approval_queue": safe_dict_func(gateway_state.get("approval_queue")),
        "latest_execution": safe_dict_func(gateway_state.get("latest_approval_execution")),
        "latest_event": approval_queue_events[-1] if approval_queue_events else {},
        "latest_patch_history": safe_dict_func(patch_history[-1]) if patch_history else {},
    }

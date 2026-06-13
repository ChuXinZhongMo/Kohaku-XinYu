from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import xinyu_bridge_desktop_self_action_snapshot_labels as _snapshot_labels
import xinyu_bridge_desktop_self_action_snapshot_payload as _snapshot_payload
import xinyu_bridge_desktop_self_action_snapshot_projection as _snapshot_projection


def desktop_safe_dict(value: Any) -> dict[str, Any]:
    return _snapshot_payload.desktop_safe_dict(value)


def desktop_safe_list(value: Any) -> list[Any]:
    return _snapshot_payload.desktop_safe_list(value)


def desktop_read_json_dict(path: Path) -> dict[str, Any]:
    return _snapshot_payload.desktop_read_json_dict(path)


def desktop_read_markdown_fields(path: Path) -> dict[str, str]:
    return _snapshot_payload.desktop_read_markdown_fields(path)


def desktop_public_candidate(candidate: Any, *, safe_str_func: Callable[..., str]) -> dict[str, Any]:
    return _snapshot_projection.desktop_public_candidate(
        candidate,
        safe_str_func=safe_str_func,
        safe_dict_func=desktop_safe_dict,
    )


def desktop_public_approval_event(event: Any, *, safe_str_func: Callable[..., str]) -> dict[str, Any]:
    return _snapshot_projection.desktop_public_approval_event(
        event,
        safe_str_func=safe_str_func,
        safe_dict_func=desktop_safe_dict,
    )


def desktop_self_action_snapshot(
    root: Path,
    *,
    gateway_state_rel: Path,
    approval_handoff_rel: Path,
    patch_state_rel: Path,
    patch_task_md_rel: Path,
    approval_queue_rel: Path,
    read_approval_queue_events_func: Callable[..., list[Any]],
    metric_int_func: Callable[[Any], int],
    safe_str_func: Callable[..., str],
) -> dict[str, Any]:
    payload = _snapshot_payload.desktop_self_action_snapshot_payload(
        root,
        gateway_state_rel=gateway_state_rel,
        approval_handoff_rel=approval_handoff_rel,
        patch_state_rel=patch_state_rel,
        patch_task_md_rel=patch_task_md_rel,
        read_approval_queue_events_func=read_approval_queue_events_func,
        read_json_dict_func=desktop_read_json_dict,
        read_markdown_fields_func=desktop_read_markdown_fields,
    )
    sources = _snapshot_payload.desktop_self_action_snapshot_sources(
        payload,
        safe_dict_func=desktop_safe_dict,
        safe_list_func=desktop_safe_list,
    )
    labels = _snapshot_labels.desktop_self_action_snapshot_labels(
        sources,
        metric_int_func=metric_int_func,
        safe_str_func=safe_str_func,
        safe_dict_func=desktop_safe_dict,
    )
    return _snapshot_projection.desktop_self_action_snapshot_projection(
        sources,
        labels,
        gateway_state_rel=gateway_state_rel,
        approval_handoff_rel=approval_handoff_rel,
        patch_state_rel=patch_state_rel,
        patch_task_md_rel=patch_task_md_rel,
        approval_queue_rel=approval_queue_rel,
        metric_int_func=metric_int_func,
        safe_str_func=safe_str_func,
        safe_dict_func=desktop_safe_dict,
        safe_list_func=desktop_safe_list,
        public_candidate_func=desktop_public_candidate,
        public_approval_event_func=desktop_public_approval_event,
    )

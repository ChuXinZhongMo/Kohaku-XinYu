from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from xinyu_bridge_desktop_private_snapshot import (
    desktop_private_ecosystem_snapshot as _runtime_desktop_private_ecosystem_snapshot,
)
from xinyu_bridge_desktop_self_action_snapshot import (
    desktop_safe_dict as _runtime_desktop_safe_dict,
    desktop_self_action_snapshot as _runtime_desktop_self_action_snapshot,
)


FacadeDeps = Mapping[str, Any]


def _dep(facade_deps: FacadeDeps, name: str) -> Any:
    return facade_deps[name]


def desktop_self_action_snapshot(root: Path, *, facade_deps: FacadeDeps) -> dict[str, Any]:
    return _runtime_desktop_self_action_snapshot(
        root,
        gateway_state_rel=_dep(facade_deps, "SELF_ACTION_GATEWAY_STATE_REL"),
        approval_handoff_rel=_dep(facade_deps, "SELF_ACTION_APPROVAL_HANDOFF_REL"),
        patch_state_rel=_dep(facade_deps, "SELF_ACTION_PATCH_STATE_REL"),
        patch_task_md_rel=_dep(facade_deps, "SELF_ACTION_PATCH_TASK_MD_REL"),
        approval_queue_rel=_dep(facade_deps, "SELF_ACTION_APPROVAL_QUEUE_REL"),
        read_approval_queue_events_func=_dep(facade_deps, "read_approval_queue_events"),
        metric_int_func=_dep(facade_deps, "desktop_metric_int"),
        safe_str_func=_dep(facade_deps, "safe_str"),
    )


def desktop_safe_dict(value: Any) -> dict[str, Any]:
    return _runtime_desktop_safe_dict(value)


def desktop_private_ecosystem_snapshot(root: Path, *, facade_deps: FacadeDeps) -> dict[str, Any]:
    return _runtime_desktop_private_ecosystem_snapshot(
        root,
        build_private_ecosystem_snapshot_func=_dep(facade_deps, "build_private_ecosystem_snapshot"),
        build_browser_snapshot_func=_dep(facade_deps, "build_browser_snapshot"),
        build_computer_snapshot_func=_dep(facade_deps, "build_computer_snapshot"),
        safe_dict_func=_dep(facade_deps, "_desktop_safe_dict"),
        metric_int_func=_dep(facade_deps, "desktop_metric_int"),
        safe_str_func=_dep(facade_deps, "safe_str"),
    )

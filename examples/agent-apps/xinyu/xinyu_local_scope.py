from __future__ import annotations

import os
from pathlib import Path


LOCAL_SCOPE_DIRNAME = "XinYu-Local-Scope"
DEFAULT_SUBDIRS = ("Inbox", "Outbox", "Workspace", "Requests")


class LocalScopeError(ValueError):
    pass


def default_local_scope_root(xinyu_dir: Path | None = None) -> Path:
    configured = os.environ.get("XINYU_LOCAL_SCOPE_DIR", "").strip()
    if configured:
        return Path(configured).expanduser()
    if xinyu_dir is not None:
        resolved = xinyu_dir.resolve()
        if len(resolved.parents) >= 4:
            return resolved.parents[3] / LOCAL_SCOPE_DIRNAME
    return Path.cwd() / LOCAL_SCOPE_DIRNAME


def ensure_local_scope(root: Path) -> Path:
    scope = root.resolve()
    scope.mkdir(parents=True, exist_ok=True)
    for name in DEFAULT_SUBDIRS:
        (scope / name).mkdir(exist_ok=True)
    return scope


def resolve_local_scope_path(root: Path, requested: str | Path) -> Path:
    scope = root.resolve()
    requested_path = Path(requested)
    if requested_path.is_absolute():
        target = requested_path.resolve()
    else:
        target = (scope / requested_path).resolve()

    if target != scope and scope not in target.parents:
        raise LocalScopeError(f"path outside local scope: {requested}")
    return target


def local_scope_status(xinyu_dir: Path | None = None) -> dict[str, str]:
    scope = ensure_local_scope(default_local_scope_root(xinyu_dir))
    return {
        "local_scope_root": str(scope),
        "inbox": str(scope / "Inbox"),
        "outbox": str(scope / "Outbox"),
        "workspace": str(scope / "Workspace"),
        "requests": str(scope / "Requests"),
        "write_policy": "allowed_inside_scope_only",
        "private_file_policy": "blocked_outside_scope_without_explicit_owner_approval",
    }

from __future__ import annotations

import os
from collections.abc import Iterable
from pathlib import Path


LOCAL_SCOPE_DIRNAME = "XinYu-Local-Scope"
DEFAULT_SUBDIRS = ("Inbox", "Outbox", "Workspace", "Requests")
READ_ONLY_DIRS_ENV = "XINYU_LOCAL_READ_DIRS"


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


def _is_inside(target: Path, root: Path) -> bool:
    return target == root or root in target.parents


def designated_read_roots() -> tuple[Path, ...]:
    configured = os.environ.get(READ_ONLY_DIRS_ENV, "").strip()
    if not configured:
        return ()
    roots: list[Path] = []
    seen: set[str] = set()
    for part in configured.split(os.pathsep):
        text = part.strip()
        if not text:
            continue
        root = Path(text).expanduser().resolve()
        key = os.path.normcase(str(root))
        if key in seen:
            continue
        seen.add(key)
        roots.append(root)
    return tuple(roots)


def resolve_local_scope_path(root: Path, requested: str | Path) -> Path:
    scope = root.resolve()
    requested_path = Path(requested)
    if requested_path.is_absolute():
        target = requested_path.resolve()
    else:
        target = (scope / requested_path).resolve()

    if not _is_inside(target, scope):
        raise LocalScopeError(f"path outside local scope: {requested}")
    return target


def resolve_read_only_scope_path(read_roots: Iterable[Path], requested: str | Path) -> Path:
    roots = tuple(root.resolve() for root in read_roots)
    if not roots:
        raise LocalScopeError("no owner-designated read-only directories configured")

    requested_path = Path(requested)
    if requested_path.is_absolute():
        target = requested_path.resolve()
        if any(_is_inside(target, root) for root in roots):
            return target
    else:
        for root in roots:
            target = (root / requested_path).resolve()
            if _is_inside(target, root):
                return target
    raise LocalScopeError(f"path outside owner-designated read-only directories: {requested}")


def local_scope_status(xinyu_dir: Path | None = None) -> dict[str, str]:
    scope = ensure_local_scope(default_local_scope_root(xinyu_dir))
    read_roots = designated_read_roots()
    return {
        "local_scope_root": str(scope),
        "inbox": str(scope / "Inbox"),
        "outbox": str(scope / "Outbox"),
        "workspace": str(scope / "Workspace"),
        "requests": str(scope / "Requests"),
        "extra_read_only_dirs": os.pathsep.join(str(root) for root in read_roots) or "none",
        "write_policy": "allowed_inside_scope_only",
        "read_only_policy": (
            "allowed_inside_explicit_owner_dirs_only"
            if read_roots
            else "not_configured"
        ),
        "private_file_policy": "blocked_outside_scope_without_explicit_owner_approval",
    }

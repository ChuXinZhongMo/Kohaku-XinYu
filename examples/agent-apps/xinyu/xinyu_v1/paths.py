"""Path resolution and local-scope enforcement for XinYu v1."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .errors import PathPolicyError


def find_xinyu_root(start: Path | None = None) -> Path:
    current = (start or Path.cwd()).resolve()
    candidates = [current, *current.parents]
    for path in candidates:
        if (path / "config.yaml").exists() and (path / "prompts").exists():
            return path
    return current


def _resolve(path: Path) -> Path:
    try:
        return path.resolve(strict=False)
    except OSError as exc:
        raise PathPolicyError(f"failed to resolve path: {path}", details={"path": str(path)}) from exc


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


@dataclass(frozen=True, slots=True)
class XinYuPaths:
    root: Path
    local_scope: Path
    memory_root: Path
    data_root: Path
    logs_root: Path
    runtime_root: Path
    vector_root: Path
    sqlite_path: Path

    @classmethod
    def discover(cls, start: Path | None = None, *, local_scope: Path | None = None) -> "XinYuPaths":
        root = find_xinyu_root(start)
        xin_yu_home = root.parents[3] if len(root.parents) >= 4 else root
        scope = local_scope or (xin_yu_home / "XinYu-Local-Scope")
        runtime_root = root / "runtime" / "v1"
        return cls(
            root=_resolve(root),
            local_scope=_resolve(scope),
            memory_root=_resolve(root / "memory"),
            data_root=_resolve(root / "data"),
            logs_root=_resolve(root / "logs"),
            runtime_root=_resolve(runtime_root),
            vector_root=_resolve(runtime_root / "vectors"),
            sqlite_path=_resolve(runtime_root / "xinyu_v1.sqlite3"),
        )

    def ensure_runtime_dirs(self) -> None:
        for path in (self.logs_root, self.runtime_root, self.vector_root, self.local_scope):
            path.mkdir(parents=True, exist_ok=True)

    def require_under_root(self, path: Path, *, label: str = "path") -> Path:
        resolved = _resolve(path)
        if not is_relative_to(resolved, self.root):
            raise PathPolicyError(
                f"{label} is outside XinYu root",
                details={"path": str(resolved), "root": str(self.root)},
            )
        return resolved

    def require_under_local_scope(self, path: Path, *, label: str = "path") -> Path:
        resolved = _resolve(path)
        if not is_relative_to(resolved, self.local_scope):
            raise PathPolicyError(
                f"{label} is outside approved local scope",
                details={"path": str(resolved), "local_scope": str(self.local_scope)},
            )
        return resolved

    def memory_path(self, *parts: str) -> Path:
        return self.require_under_root(self.memory_root.joinpath(*parts), label="memory_path")

    def runtime_path(self, *parts: str) -> Path:
        return self.require_under_root(self.runtime_root.joinpath(*parts), label="runtime_path")


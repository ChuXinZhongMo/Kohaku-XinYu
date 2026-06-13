from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from xinyu_tool_targets_store import (
    glob_tool_target_paths,
    read_tool_target_config_text,
    tool_target_config_exists,
    tool_target_path_exists,
    tool_target_path_is_dir,
    tool_target_path_is_file,
    tool_target_path_mtime,
)


CONFIG_REL = Path("config/tool_targets.json")
SENSITIVE_SEGMENTS = {
    ".ssh",
    ".gnupg",
    "appdata",
    "browser",
    "cookies",
    "credential",
    "credentials",
    "login data",
    "password",
    "secrets",
    "session",
    "token",
}


class TargetRegistryError(ValueError):
    pass


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _is_inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _has_sensitive_segment(path: Path) -> bool:
    lowered = [part.lower() for part in path.parts]
    return any(segment in lowered or any(segment in part for part in lowered) for segment in SENSITIVE_SEGMENTS)


@dataclass(frozen=True)
class TargetDefinition:
    alias: str
    kind: str
    read_roots: tuple[str, ...] = ()
    patterns: tuple[str, ...] = ()
    owner_setup_required: bool = False
    notes: tuple[str, ...] = ()

    @classmethod
    def from_config(cls, alias: str, value: dict[str, Any]) -> "TargetDefinition":
        return cls(
            alias=alias,
            kind=_safe_str(value.get("kind"), "unknown"),
            read_roots=tuple(_safe_str(item).strip() for item in value.get("read_roots", []) if _safe_str(item).strip()),
            patterns=tuple(_safe_str(item).strip() for item in value.get("patterns", []) if _safe_str(item).strip()),
            owner_setup_required=bool(value.get("owner_setup_required")),
            notes=tuple(_safe_str(item).strip() for item in value.get("notes", []) if _safe_str(item).strip()),
        )


@dataclass
class ResolvedTarget:
    definition: TargetDefinition
    roots: tuple[Path, ...] = field(default_factory=tuple)

    @property
    def alias(self) -> str:
        return self.definition.alias

    @property
    def kind(self) -> str:
        return self.definition.kind

    @property
    def patterns(self) -> tuple[str, ...]:
        return self.definition.patterns


class TargetRegistry:
    def __init__(self, root: Path, targets: dict[str, TargetDefinition] | None = None) -> None:
        self.root = root.resolve()
        self.targets = dict(targets or {})

    @classmethod
    def load(cls, root: Path, *, config_path: Path | None = None) -> "TargetRegistry":
        root = root.resolve()
        path = config_path or root / CONFIG_REL
        if not tool_target_config_exists(path):
            return cls(root, targets={})
        data = json.loads(read_tool_target_config_text(path))
        if not isinstance(data, dict):
            raise TargetRegistryError("tool target config must be a JSON object")
        raw_targets = data.get("targets")
        if not isinstance(raw_targets, dict):
            raise TargetRegistryError("tool target config missing targets object")
        targets: dict[str, TargetDefinition] = {}
        for alias, value in raw_targets.items():
            alias_text = _safe_str(alias).strip()
            if not alias_text or not isinstance(value, dict):
                continue
            targets[alias_text] = TargetDefinition.from_config(alias_text, value)
        return cls(root, targets=targets)

    def aliases(self) -> list[str]:
        return sorted(self.targets)

    def get(self, alias: str) -> TargetDefinition | None:
        return self.targets.get(_safe_str(alias).strip())

    def require(self, alias: str) -> TargetDefinition:
        target = self.get(alias)
        if target is None:
            raise TargetRegistryError(f"target alias is not registered: {alias}")
        return target

    def resolve_read_roots(self, alias: str) -> ResolvedTarget:
        target = self.require(alias)
        if target.owner_setup_required:
            raise TargetRegistryError(f"target alias requires owner setup before use: {alias}")
        if not target.read_roots:
            raise TargetRegistryError(f"target alias has no registered read roots: {alias}")

        roots: list[Path] = []
        for raw_root in target.read_roots:
            root_path = Path(raw_root)
            candidate = root_path if root_path.is_absolute() else self.root / root_path
            resolved = candidate.resolve()
            if _has_sensitive_segment(resolved):
                raise TargetRegistryError(f"target read root is blocked by private-path policy: {alias}")
            if not tool_target_path_exists(resolved) or not tool_target_path_is_dir(resolved):
                raise TargetRegistryError(f"target read root is not available: {alias}")
            roots.append(resolved)
        return ResolvedTarget(definition=target, roots=tuple(roots))

    def iter_log_files(self, alias: str, *, max_files: int = 8) -> list[Path]:
        resolved = self.resolve_read_roots(alias)
        if resolved.kind != "logs":
            raise TargetRegistryError(f"target is not a log target: {alias}")
        patterns = resolved.patterns or ("*.log",)
        files: dict[Path, float] = {}
        for root in resolved.roots:
            for pattern in patterns:
                safe_pattern = pattern.replace("\\", "/").lstrip("/")
                for path in glob_tool_target_paths(root, safe_pattern):
                    try:
                        file_path = path.resolve()
                    except OSError:
                        continue
                    if not _is_inside(file_path, root):
                        continue
                    if _has_sensitive_segment(file_path):
                        continue
                    if tool_target_path_is_file(file_path):
                        try:
                            files[file_path] = tool_target_path_mtime(file_path)
                        except OSError:
                            files[file_path] = 0.0
        ordered = sorted(files, key=lambda item: files[item], reverse=True)
        return ordered[: max(1, max_files)]

    def describe(self, alias: str) -> dict[str, Any]:
        target = self.require(alias)
        try:
            resolved = self.resolve_read_roots(alias)
            status = "ready"
            root_count = len(resolved.roots)
        except TargetRegistryError as exc:
            status = "blocked"
            root_count = 0
            return {
                "alias": alias,
                "kind": target.kind,
                "status": status,
                "root_count": root_count,
                "reason": str(exc),
                "owner_setup_required": target.owner_setup_required,
            }
        return {
            "alias": alias,
            "kind": target.kind,
            "status": status,
            "root_count": root_count,
            "patterns": list(target.patterns),
            "owner_setup_required": target.owner_setup_required,
        }

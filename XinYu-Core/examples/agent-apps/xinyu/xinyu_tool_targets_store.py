from __future__ import annotations

from pathlib import Path


def tool_target_config_exists(path: Path) -> bool:
    return Path(path).exists()


def read_tool_target_config_text(path: Path) -> str:
    return Path(path).read_text(encoding="utf-8-sig")


def tool_target_path_exists(path: Path) -> bool:
    return Path(path).exists()


def tool_target_path_is_dir(path: Path) -> bool:
    return Path(path).is_dir()


def glob_tool_target_paths(root: Path, pattern: str) -> list[Path]:
    return list(Path(root).glob(pattern))


def tool_target_path_is_file(path: Path) -> bool:
    return Path(path).is_file()


def tool_target_path_mtime(path: Path) -> float:
    return Path(path).stat().st_mtime

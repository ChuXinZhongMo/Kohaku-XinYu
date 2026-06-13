from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from state_service import atomic_write_text


PROMOTION_DRY_RUN_REL = Path("runtime/memory_promotion_dry_runs")


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    try:
        text = str(value)
    except Exception:
        return default
    return text if text else default


def safe_promotion_filename(value: Any, *, default: str = "item") -> str:
    text = re.sub(r"[^A-Za-z0-9_.-]+", "-", _safe_str(value).strip()).strip(".-")
    return text or default


def promotion_target_path(root: Path, target_rel: Path) -> Path:
    return Path(root) / Path(target_rel)


def promotion_dry_run_path(root: Path, candidate_id: Any) -> Path:
    filename = safe_promotion_filename(candidate_id, default="unknown")
    return Path(root) / PROMOTION_DRY_RUN_REL / f"{filename}.md"


def promotion_path_exists(path: Path) -> bool:
    return Path(path).exists()


def read_promotion_text(path: Path) -> str:
    path = Path(path)
    if not promotion_path_exists(path):
        return ""
    return path.read_text(encoding="utf-8-sig", errors="replace")


def write_promotion_text(path: Path, text: str) -> None:
    atomic_write_text(Path(path), text, final_newline=False)


def write_promotion_dry_run_text(root: Path, candidate_id: Any, text: str) -> Path:
    path = promotion_dry_run_path(root, candidate_id)
    write_promotion_text(path, text)
    return path

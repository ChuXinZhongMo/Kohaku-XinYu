from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CleanupTarget:
    path: Path
    kind: str
    size_bytes: int


def _size_bytes(path: Path) -> int:
    if path.is_file():
        try:
            return path.stat().st_size
        except OSError:
            return 0
    total = 0
    for item in path.rglob("*"):
        if not item.is_file():
            continue
        try:
            total += item.stat().st_size
        except OSError:
            continue
    return total


def _is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _iter_cache_targets(root: Path, *, include_venv_cache: bool) -> list[CleanupTarget]:
    targets: list[CleanupTarget] = []
    for path in root.rglob("*"):
        if not path.is_dir():
            continue
        if path.name not in {"__pycache__", ".pytest_cache"}:
            continue
        if not include_venv_cache and ".venv" in path.relative_to(root).parts:
            continue
        targets.append(CleanupTarget(path=path, kind=path.name, size_bytes=_size_bytes(path)))
    return targets


def _iter_runtime_readiness_log_targets(root: Path, *, retain: int) -> list[CleanupTarget]:
    logs = root / "logs"
    if not logs.exists():
        return []
    readiness_dirs = sorted(
        [path for path in logs.glob("runtime_readiness_*") if path.is_dir()],
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    return [
        CleanupTarget(path=path, kind="runtime_readiness_log", size_bytes=_size_bytes(path))
        for path in readiness_dirs[max(0, retain) :]
    ]


def collect_targets(
    root: Path,
    *,
    include_venv_cache: bool = True,
    retain_runtime_readiness: int = 5,
) -> list[CleanupTarget]:
    root = root.resolve()
    targets: list[CleanupTarget] = []
    targets.extend(_iter_cache_targets(root, include_venv_cache=include_venv_cache))
    targets.extend(_iter_runtime_readiness_log_targets(root, retain=retain_runtime_readiness))
    unique: dict[Path, CleanupTarget] = {}
    for target in targets:
        resolved = target.path.resolve()
        if _is_under(resolved, root):
            unique[resolved] = CleanupTarget(path=resolved, kind=target.kind, size_bytes=target.size_bytes)
    return sorted(unique.values(), key=lambda item: str(item.path))


def delete_targets(root: Path, targets: list[CleanupTarget]) -> dict[str, Any]:
    root = root.resolve()
    removed: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for target in targets:
        path = target.path.resolve()
        if not _is_under(path, root):
            skipped.append({"path": str(path), "kind": target.kind, "reason": "outside_root"})
            continue
        if target.kind not in {"__pycache__", ".pytest_cache", "runtime_readiness_log"}:
            skipped.append({"path": str(path), "kind": target.kind, "reason": "unexpected_kind"})
            continue
        try:
            shutil.rmtree(path)
            removed.append({"path": str(path), "kind": target.kind, "size_bytes": target.size_bytes})
        except OSError as exc:
            skipped.append({"path": str(path), "kind": target.kind, "reason": type(exc).__name__})
    return {"removed": removed, "skipped": skipped}


def _format_size(size_bytes: int) -> str:
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MiB"
    if size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KiB"
    return f"{size_bytes} B"


def main() -> int:
    parser = argparse.ArgumentParser(description="Low-risk XinYu housekeeping.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--execute", action="store_true", help="Actually delete selected cache/log targets.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable output.")
    parser.add_argument("--keep-venv-cache", action="store_true", help="Do not clean .venv __pycache__ directories.")
    parser.add_argument("--retain-runtime-readiness", type=int, default=5)
    args = parser.parse_args()

    root = args.root.resolve()
    targets = collect_targets(
        root,
        include_venv_cache=not args.keep_venv_cache,
        retain_runtime_readiness=args.retain_runtime_readiness,
    )
    total = sum(target.size_bytes for target in targets)
    result: dict[str, Any] = {
        "root": str(root),
        "mode": "execute" if args.execute else "dry_run",
        "target_count": len(targets),
        "target_bytes": total,
        "targets": [
            {"path": str(target.path), "kind": target.kind, "size_bytes": target.size_bytes}
            for target in targets
        ],
    }
    if args.execute:
        result.update(delete_targets(root, targets))

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        action = "would remove" if not args.execute else "removed"
        print(f"xinyu_housekeeping: {action} {len(targets)} target(s), {_format_size(total)}")
        if args.execute:
            print(f"removed: {len(result.get('removed', []))}")
            print(f"skipped: {len(result.get('skipped', []))}")
        else:
            print("dry run only; pass --execute to delete")
    return 0 if not result.get("skipped") else 1


if __name__ == "__main__":
    raise SystemExit(main())

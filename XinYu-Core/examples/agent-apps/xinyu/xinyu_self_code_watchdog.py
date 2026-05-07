from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


SNAPSHOT_ROOT_REL = Path("runtime/self_code_watchdog/snapshots")
STATE_REL = Path("memory/context/self_code_watchdog_state.md")
TRACE_REL = Path("runtime/self_code_watchdog_trace.jsonl")

SNAPSHOT_PATTERNS = (
    "*.py",
    "*.ps1",
    "*.yaml",
    "*.yml",
    "requirements*.txt",
    "custom/**/*.py",
    "xinyu_v1/**/*.py",
    "tests/**/*.py",
)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _stamp() -> str:
    return datetime.now().astimezone().strftime("%Y%m%dT%H%M%S")


def _safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _one_line(value: Any, *, limit: int = 240, default: str = "none") -> str:
    text = re.sub(r"\s+", " ", _safe_str(value)).strip()
    if not text:
        return default
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)].rstrip() + "..."


def _safe_token(value: str, *, default: str = "snapshot") -> str:
    token = re.sub(r"[^A-Za-z0-9_.-]+", "-", value or "").strip(".-")
    return token[:80] or default


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(tmp_path, path)
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            pass


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def _discover_snapshot_files(root: Path) -> list[Path]:
    files: set[Path] = set()
    for pattern in SNAPSHOT_PATTERNS:
        for path in root.glob(pattern):
            if not path.is_file():
                continue
            if any(part in {".venv", "__pycache__", "runtime", "logs", "learning"} for part in path.parts):
                continue
            if _is_relative_to(path, root):
                files.add(path.resolve())
    return sorted(files)


def _render_state(
    *,
    observed_at: str,
    status: str,
    snapshot_id: str,
    approval_id: str,
    manifest_path: str,
    file_count: int,
    reason: str,
    notes: list[str],
) -> str:
    note_lines = "\n".join(f"- {_one_line(note, limit=180)}" for note in notes) or "- none"
    return f"""---
title: Self Code Watchdog State
memory_type: self_code_watchdog_state
time_scope: short_term
subject_ids: [xinyu, owner]
protected: true
source: xinyu_self_code_watchdog
updated_at: {_one_line(observed_at)}
status: active
tags: [self-code, watchdog, rollback]
---

# Self Code Watchdog State

## Latest Snapshot
- observed_at: {_one_line(observed_at)}
- status: {_one_line(status)}
- snapshot_id: {_one_line(snapshot_id, limit=120)}
- approval_id: {_one_line(approval_id, limit=120)}
- manifest_path: {_one_line(manifest_path, limit=500)}
- file_count: {file_count}
- reason: {_one_line(reason, limit=220)}

## Rules
- health_gate_owner: start_xinyu_core_bridge.ps1
- rollback_scope: existing XinYu app code and startup files captured in the snapshot
- stable_memory_write: blocked
- delete_or_publish: blocked

## Notes
{note_lines}
"""


def _write_state(
    root: Path,
    *,
    status: str,
    snapshot_id: str,
    approval_id: str,
    manifest_path: str,
    file_count: int,
    reason: str,
    notes: list[str],
    observed_at: str | None = None,
) -> None:
    observed = observed_at or _now_iso()
    _atomic_write_text(
        root / STATE_REL,
        _render_state(
            observed_at=observed,
            status=status,
            snapshot_id=snapshot_id,
            approval_id=approval_id,
            manifest_path=manifest_path,
            file_count=file_count,
            reason=reason,
            notes=notes,
        ),
    )


def create_self_code_snapshot(
    root: Path,
    *,
    approval_id: str,
    reason: str = "owner_self_code_iteration",
    observed_at: str | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    observed = observed_at or _now_iso()
    snapshot_id = f"{_safe_token(approval_id, default='selfcode')}-{_stamp()}"
    snapshot_dir = root / SNAPSHOT_ROOT_REL / snapshot_id
    files_dir = snapshot_dir / "files"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    files_dir.mkdir(parents=True, exist_ok=True)

    entries: list[dict[str, Any]] = []
    for source in _discover_snapshot_files(root):
        rel = source.relative_to(root).as_posix()
        backup = files_dir / rel
        backup.parent.mkdir(parents=True, exist_ok=True)
        data = source.read_bytes()
        backup.write_bytes(data)
        entries.append(
            {
                "rel_path": rel,
                "source_path": str(source),
                "backup_path": str(backup),
                "sha256": _sha256_bytes(data),
                "size_bytes": len(data),
            }
        )

    manifest = {
        "version": 1,
        "snapshot_id": snapshot_id,
        "approval_id": approval_id,
        "created_at": observed,
        "root": str(root),
        "reason": reason,
        "status": "snapshot_created",
        "files": entries,
    }
    manifest_path = snapshot_dir / "manifest.json"
    _atomic_write_text(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    notes = ["snapshot_created", f"files:{len(entries)}"]
    _write_state(
        root,
        status="snapshot_created",
        snapshot_id=snapshot_id,
        approval_id=approval_id,
        manifest_path=str(manifest_path),
        file_count=len(entries),
        reason=reason,
        notes=notes,
        observed_at=observed,
    )
    _append_jsonl(
        root / TRACE_REL,
        {
            "event_kind": "snapshot_created",
            "observed_at": observed,
            "snapshot_id": snapshot_id,
            "approval_id": approval_id,
            "manifest_path": str(manifest_path),
            "file_count": len(entries),
            "reason": reason,
            "notes": notes,
        },
    )
    return {
        "ok": True,
        "snapshot_id": snapshot_id,
        "approval_id": approval_id,
        "manifest_path": str(manifest_path),
        "file_count": len(entries),
        "notes": notes,
    }


def _load_manifest(manifest_path: Path) -> dict[str, Any]:
    data = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("snapshot manifest must be a JSON object")
    files = data.get("files")
    if not isinstance(files, list):
        raise ValueError("snapshot manifest missing files list")
    return data


def restore_self_code_snapshot(
    manifest_path: Path,
    *,
    root: Path | None = None,
    observed_at: str | None = None,
    reason: str = "health_gate_failed",
) -> dict[str, Any]:
    manifest_path = manifest_path.resolve()
    manifest = _load_manifest(manifest_path)
    root_path = (root or Path(_safe_str(manifest.get("root")))).resolve()
    if not root_path.exists():
        raise FileNotFoundError(f"snapshot root missing: {root_path}")

    restored = 0
    skipped: list[str] = []
    for raw in manifest["files"]:
        if not isinstance(raw, dict):
            continue
        rel = _safe_str(raw.get("rel_path")).replace("\\", "/")
        if not rel or rel.startswith("../") or "/../" in rel:
            skipped.append(rel or "empty")
            continue
        target = (root_path / rel).resolve()
        backup = Path(_safe_str(raw.get("backup_path"))).resolve()
        if not _is_relative_to(target, root_path):
            skipped.append(rel)
            continue
        if not backup.exists():
            skipped.append(rel)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup, target)
        restored += 1

    observed = observed_at or _now_iso()
    snapshot_id = _safe_str(manifest.get("snapshot_id"), manifest_path.parent.name)
    approval_id = _safe_str(manifest.get("approval_id"), "unknown")
    notes = ["snapshot_restored", f"restored:{restored}"]
    if skipped:
        notes.append(f"skipped:{len(skipped)}")
    _write_state(
        root_path,
        status="restored",
        snapshot_id=snapshot_id,
        approval_id=approval_id,
        manifest_path=str(manifest_path),
        file_count=restored,
        reason=reason,
        notes=notes,
        observed_at=observed,
    )
    _append_jsonl(
        root_path / TRACE_REL,
        {
            "event_kind": "snapshot_restored",
            "observed_at": observed,
            "snapshot_id": snapshot_id,
            "approval_id": approval_id,
            "manifest_path": str(manifest_path),
            "restored": restored,
            "skipped": skipped[:20],
            "reason": reason,
            "notes": notes,
        },
    )
    return {
        "ok": True,
        "snapshot_id": snapshot_id,
        "approval_id": approval_id,
        "manifest_path": str(manifest_path),
        "restored": restored,
        "skipped": skipped,
        "notes": notes,
    }


def mark_self_code_watchdog_status(
    root: Path,
    *,
    snapshot_id: str,
    approval_id: str,
    manifest_path: str,
    status: str,
    reason: str,
    notes: list[str] | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    clean_notes = list(notes or [])
    _write_state(
        root,
        status=status,
        snapshot_id=snapshot_id,
        approval_id=approval_id,
        manifest_path=manifest_path,
        file_count=0,
        reason=reason,
        notes=clean_notes or [status],
    )
    _append_jsonl(
        root / TRACE_REL,
        {
            "event_kind": "watchdog_status",
            "observed_at": _now_iso(),
            "snapshot_id": snapshot_id,
            "approval_id": approval_id,
            "manifest_path": manifest_path,
            "status": status,
            "reason": reason,
            "notes": clean_notes,
        },
    )
    return {"ok": True, "status": status, "snapshot_id": snapshot_id, "notes": clean_notes}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create or restore XinYu self-code watchdog snapshots.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("snapshot")
    create.add_argument("--approval-id", required=True)
    create.add_argument("--reason", default="owner_self_code_iteration")

    restore = sub.add_parser("restore")
    restore.add_argument("--manifest", type=Path, required=True)
    restore.add_argument("--reason", default="health_gate_failed")
    restore.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "snapshot":
        result = create_self_code_snapshot(args.root, approval_id=args.approval_id, reason=args.reason)
    elif args.command == "restore":
        result = restore_self_code_snapshot(args.manifest, root=args.root, reason=args.reason)
    else:
        raise SystemExit(f"unknown command: {args.command}")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

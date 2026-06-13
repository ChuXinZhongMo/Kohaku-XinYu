from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from xinyu_code_awareness_store import append_source_change_trace
from xinyu_code_awareness_store import read_code_awareness_state_text
from xinyu_code_awareness_store import read_source_snapshot
from xinyu_code_awareness_store import write_code_awareness_state
from xinyu_code_awareness_store import write_source_snapshot
from xinyu_runtime_security import BRIDGE_RUNTIME_SOURCE_RELS, runtime_source_paths, source_files_digest


SNAPSHOT_REL = Path("runtime/code_awareness/source_snapshot.json")
TRACE_REL = Path("runtime/code_awareness/source_change_trace.jsonl")
STATE_REL = Path("memory/context/code_change_awareness_state.md")

SOURCE_PATTERNS = (
    "*.py",
    "*.ps1",
    "custom/**/*.py",
    "xinyu_v1/**/*.py",
    "prompts/*.md",
    "config/*.json",
)

RUNTIME_SOURCE_RELS = BRIDGE_RUNTIME_SOURCE_RELS

GATEWAY_SOURCE_PREFIXES = (
    "xinyu_qq_",
    "start_xinyu_qq_gateway.ps1",
    "stop_xinyu_qq_gateway.ps1",
)

MAX_CHANGED_FILES = 16


def record_code_awareness(
    root: Path,
    *,
    running_bridge_digest: str = "",
    running_runtime_digest: str = "",
) -> dict[str, Any]:
    root = Path(root)
    current = collect_source_snapshot(root)
    previous = read_source_snapshot(root / SNAPSHOT_REL)
    previous = previous if isinstance(previous, dict) else {}
    previous_exists = bool(previous.get("digest"))
    changes = _diff_snapshots(previous, current) if previous_exists else []
    current_bridge_digest = _file_digest(root / "xinyu_core_bridge.py")
    current_runtime_digest = source_files_digest(runtime_source_paths(root))
    bridge_restart_required = bool(
        running_bridge_digest
        and current_bridge_digest != "unknown"
        and running_bridge_digest != current_bridge_digest
    )
    runtime_restart_required = bool(
        running_runtime_digest
        and current_runtime_digest != "unknown"
        and running_runtime_digest != current_runtime_digest
    )
    changed_rels = [str(item.get("path", "")) for item in changes]
    gateway_restart_may_be_needed = any(_is_gateway_relevant(rel) for rel in changed_rels)

    status = "initialized" if not previous_exists else ("changed" if changes else "clean")
    observed_at = _timestamp_or_now_iso(_now_iso())
    summary = {
        "available": True,
        "updated_at": _timestamp_or_now_iso(observed_at),
        "status": status,
        "source_changed": bool(changes),
        "changed_count": len(changes),
        "changed_files": changes[:MAX_CHANGED_FILES],
        "current_project_digest": current.get("digest", "unknown"),
        "previous_project_digest": previous.get("digest", ""),
        "current_bridge_digest": current_bridge_digest,
        "running_bridge_digest": running_bridge_digest,
        "bridge_restart_required": bridge_restart_required,
        "current_runtime_digest": current_runtime_digest,
        "running_runtime_digest": running_runtime_digest,
        "runtime_restart_required": runtime_restart_required,
        "gateway_restart_may_be_needed": gateway_restart_may_be_needed,
        "snapshot_path": SNAPSHOT_REL.as_posix(),
        "trace_path": TRACE_REL.as_posix(),
        "state_path": STATE_REL.as_posix(),
        "scope": "source_whitelist_only_no_memory_runtime_logs_or_secrets",
        "memory_boundary": "runtime_state_only_not_identity_or_owner_relationship_memory",
    }

    if status in {"initialized", "changed"}:
        append_source_change_trace(
            root / TRACE_REL,
            {
                "observed_at": _timestamp_or_now_iso(observed_at),
                "event_kind": "source_snapshot_" + status,
                "changed_count": len(changes),
                "changed_files": changes[:MAX_CHANGED_FILES],
                "project_digest": current.get("digest", "unknown"),
                "bridge_restart_required": bridge_restart_required,
                "runtime_restart_required": runtime_restart_required,
                "gateway_restart_may_be_needed": gateway_restart_may_be_needed,
            },
        )
    write_source_snapshot(root / SNAPSHOT_REL, current)
    write_code_awareness_state(root / STATE_REL, render_code_awareness_state(summary))
    return summary


def read_code_awareness_summary(root: Path) -> dict[str, Any]:
    fields = _load_state_fields(Path(root) / STATE_REL)
    if not fields:
        return {"available": False, "observed": "false"}
    return {
        "available": True,
        "observed": "true",
        "updated_at": fields.get("updated_at", ""),
        "status": fields.get("status", "unknown"),
        "source_changed": fields.get("source_changed", "unknown"),
        "changed_count": fields.get("changed_count", "0"),
        "bridge_restart_required": fields.get("bridge_restart_required", "unknown"),
        "runtime_restart_required": fields.get("runtime_restart_required", "unknown"),
        "gateway_restart_may_be_needed": fields.get("gateway_restart_may_be_needed", "unknown"),
        "current_project_digest": fields.get("current_project_digest", "unknown"),
        "current_bridge_digest": fields.get("current_bridge_digest", "unknown"),
        "running_bridge_digest": fields.get("running_bridge_digest", "unknown"),
        "current_runtime_digest": fields.get("current_runtime_digest", "unknown"),
        "running_runtime_digest": fields.get("running_runtime_digest", "unknown"),
        "last_changed_files": fields.get("last_changed_files", "none"),
        "scope": fields.get("scope", "source_whitelist_only"),
    }


def collect_source_snapshot(root: Path) -> dict[str, Any]:
    root = Path(root)
    observed_at = _timestamp_or_now_iso(_now_iso())
    files: list[dict[str, Any]] = []
    for path in _iter_source_files(root):
        rel = _rel_path(root, path)
        digest = _file_digest(path)
        try:
            stat = path.stat()
        except OSError:
            continue
        files.append(
            {
                "path": rel,
                "sha256_16": digest,
                "size_bytes": stat.st_size,
                "mtime_ns": stat.st_mtime_ns,
            }
        )
    files.sort(key=lambda item: str(item["path"]).lower())
    return {
        "schema_version": 1,
        "generated_at": _timestamp_or_now_iso(observed_at),
        "scope": "source_whitelist_only",
        "file_count": len(files),
        "digest": _project_digest(files),
        "files": files,
    }


def render_code_awareness_state(summary: dict[str, Any]) -> str:
    changed_lines = _changed_file_lines(summary.get("changed_files"))
    return "\n".join(
        [
            "---",
            "title: Code Change Awareness State",
            "memory_type: code_change_awareness_state",
            "time_scope: immediate_runtime",
            "subject_ids: [xinyu]",
            "protected: true",
            "source: xinyu_code_awareness",
            f"updated_at: {_timestamp_or_now_iso(summary.get('updated_at'))}",
            "status: active",
            "tags: [runtime, code, awareness, sidecar]",
            "---",
            "",
            "# Code Change Awareness State",
            "",
            "## Boundary",
            f"- scope: {_safe(summary.get('scope'))}",
            f"- memory_boundary: {_safe(summary.get('memory_boundary'))}",
            "- direct_code_omniscience: false",
            "- needs_file_open_for_details: true",
            "",
            "## Source Snapshot",
            f"- status: {_safe(summary.get('status'))}",
            f"- source_changed: {_bool_text(summary.get('source_changed'))}",
            f"- changed_count: {_safe(summary.get('changed_count'), '0')}",
            f"- current_project_digest: {_safe(summary.get('current_project_digest'), 'unknown')}",
            f"- previous_project_digest: {_safe(summary.get('previous_project_digest'), 'unknown')}",
            f"- current_bridge_digest: {_safe(summary.get('current_bridge_digest'), 'unknown')}",
            f"- running_bridge_digest: {_safe(summary.get('running_bridge_digest'), 'unknown')}",
            f"- current_runtime_digest: {_safe(summary.get('current_runtime_digest'), 'unknown')}",
            f"- running_runtime_digest: {_safe(summary.get('running_runtime_digest'), 'unknown')}",
            "",
            "## Load Status",
            f"- bridge_restart_required: {_bool_text(summary.get('bridge_restart_required'))}",
            f"- runtime_restart_required: {_bool_text(summary.get('runtime_restart_required'))}",
            f"- gateway_restart_may_be_needed: {_bool_text(summary.get('gateway_restart_may_be_needed'))}",
            "",
            "## Last Changed Files",
            f"- last_changed_files: {', '.join(_changed_file_labels(summary.get('changed_files'))) or 'none'}",
            *changed_lines,
            "",
            "## Runtime Use",
            "- If owner asks whether a code change took effect, distinguish source_changed from restart_required.",
            "- Do not treat code changes as personality, relationship, or stable memory changes.",
            "- Gateway changes may require gateway restart; this state does not prove QQ/NapCat connectivity.",
            "",
        ]
    )


def _iter_source_files(root: Path) -> list[Path]:
    seen: dict[str, Path] = {}
    for pattern in SOURCE_PATTERNS:
        try:
            candidates = root.glob(pattern)
            for path in candidates:
                try:
                    if not path.is_file():
                        continue
                except OSError:
                    continue
                rel = _rel_path(root, path)
                if _is_excluded_rel(rel):
                    continue
                seen[rel.lower()] = path
        except OSError:
            continue
    return list(seen.values())


def _is_excluded_rel(rel: str) -> bool:
    lowered = rel.lower()
    return lowered.startswith(("runtime/", "memory/", "logs/", "learning/", ".venv/"))


def _diff_snapshots(previous: dict[str, Any], current: dict[str, Any]) -> list[dict[str, str]]:
    previous_files = _files_by_path(previous)
    current_files = _files_by_path(current)
    changes: list[dict[str, str]] = []
    for rel in sorted(set(previous_files) - set(current_files)):
        changes.append({"path": rel, "change": "deleted"})
    for rel in sorted(set(current_files) - set(previous_files)):
        changes.append({"path": rel, "change": "added"})
    for rel in sorted(set(previous_files) & set(current_files)):
        if previous_files[rel].get("sha256_16") != current_files[rel].get("sha256_16"):
            changes.append({"path": rel, "change": "modified"})
    return changes


def _files_by_path(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    files = snapshot.get("files")
    if not isinstance(files, list):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for item in files:
        if not isinstance(item, dict):
            continue
        rel = _safe(item.get("path")).strip()
        if rel:
            result[rel] = item
    return result


def _project_digest(files: Iterable[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for item in files:
        digest.update(_safe(item.get("path")).encode("utf-8", errors="replace"))
        digest.update(b"\0")
        digest.update(_safe(item.get("sha256_16")).encode("ascii", errors="replace"))
        digest.update(b"\0")
    return digest.hexdigest()[:16]


def _file_digest(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    except OSError:
        return "unknown"


def _changed_file_labels(items: Any) -> list[str]:
    if not isinstance(items, list):
        return []
    labels: list[str] = []
    for item in items[:MAX_CHANGED_FILES]:
        if not isinstance(item, dict):
            continue
        rel = _safe(item.get("path"))
        change = _safe(item.get("change"))
        if rel:
            labels.append(f"{change}:{rel}" if change else rel)
    return labels


def _changed_file_lines(items: Any) -> list[str]:
    labels = _changed_file_labels(items)
    if not labels:
        return ["- none"]
    return [f"- {label}" for label in labels]


def _load_state_fields(path: Path) -> dict[str, str]:
    text = read_code_awareness_state_text(path)
    if not text:
        return {}
    fields: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            stripped = stripped[2:].strip()
        if ":" not in stripped:
            continue
        key, _sep, value = stripped.partition(":")
        key = key.strip()
        if key:
            fields[key] = value.strip()
    return fields


def _rel_path(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.name


def _is_gateway_relevant(rel: str) -> bool:
    lowered = rel.lower()
    return any(lowered.startswith(prefix.lower()) or lowered == prefix.lower() for prefix in GATEWAY_SOURCE_PREFIXES)


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _timestamp_or_now_iso(value: Any) -> str:
    parsed = _parse_iso(value)
    if parsed is None:
        return _now_iso()
    return parsed.astimezone().isoformat(timespec="seconds")


def _parse_iso(value: Any) -> datetime | None:
    text = _safe(value).strip()
    if not text or text == "none":
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.astimezone()
    return parsed


def _safe(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value)
    return text if text else default


def _bool_text(value: Any) -> str:
    return "true" if bool(value) else "false"

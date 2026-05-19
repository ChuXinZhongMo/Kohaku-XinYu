from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    from ._validation_paths import ensure_validation_paths
except ImportError:  # pragma: no cover - direct script execution
    from _validation_paths import ensure_validation_paths


APP_ROOT = ensure_validation_paths()
DEFAULT_MANIFEST = APP_ROOT / "stores" / "queue_boundary_manifest.json"

REQUIRED_FIELDS: tuple[str, ...] = (
    "queue_id",
    "path",
    "owner_module",
    "owner_symbols",
    "projection_paths",
    "allowed_raw_readers",
    "privacy",
    "retention_policy",
    "body_policy",
    "stable_memory_policy",
    "status",
)

VALID_PRIVACY = {"private_runtime_queue"}
VALID_RETENTION = {"operational_queue", "bounded_rows"}
VALID_BODY_POLICY = {"no_body_migration"}
VALID_STATUS = {"compat_runtime_queue"}


@dataclass(frozen=True, slots=True)
class QueueBoundaryCheck:
    queue_id: str
    path: str
    owner_module: str
    privacy: str
    retention_policy: str
    status: str


@dataclass(frozen=True, slots=True)
class QueueBoundaryValidationResult:
    checks: tuple[QueueBoundaryCheck, ...]
    failures: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.failures


def load_manifest(path: Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def validate_manifest(path: Path = DEFAULT_MANIFEST) -> QueueBoundaryValidationResult:
    manifest = load_manifest(path)
    queues = manifest.get("queues")
    if not isinstance(queues, list):
        return QueueBoundaryValidationResult(
            checks=(),
            failures=("manifest queues must be a list",),
            warnings=(),
        )
    return validate_queues(queues)


def validate_queues(queues: list[Any]) -> QueueBoundaryValidationResult:
    checks: list[QueueBoundaryCheck] = []
    failures: list[str] = []
    warnings: list[str] = []
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()

    for index, raw in enumerate(queues, start=1):
        label = f"queue[{index}]"
        if not isinstance(raw, dict):
            failures.append(f"{label}: queue must be an object")
            continue
        queue = raw
        queue_id = _safe_str(queue.get("queue_id"))
        path_value = _safe_str(queue.get("path"))
        label = queue_id or path_value or label
        missing = [field for field in REQUIRED_FIELDS if field not in queue]
        if missing:
            failures.append(f"{label}: missing fields: {', '.join(missing)}")
            continue

        if queue_id in seen_ids:
            failures.append(f"{label}: duplicate queue_id")
        seen_ids.add(queue_id)
        if path_value in seen_paths:
            failures.append(f"{label}: duplicate path")
        seen_paths.add(path_value)

        owner_module = _safe_str(queue.get("owner_module"))
        owner_symbols = queue.get("owner_symbols")
        privacy = _safe_str(queue.get("privacy"))
        retention_policy = _safe_str(queue.get("retention_policy"))
        body_policy = _safe_str(queue.get("body_policy"))
        stable_memory_policy = _safe_str(queue.get("stable_memory_policy"))
        status = _safe_str(queue.get("status"))
        projection_paths = queue.get("projection_paths")
        allowed_raw_readers = queue.get("allowed_raw_readers")

        if not queue_id:
            failures.append(f"{label}: empty queue_id")
        if not _is_allowed_queue_path(path_value):
            failures.append(f"{label}: path must be a relative memory/*.json or runtime/*.json path")
        if Path(path_value).is_absolute() or ".." in Path(path_value).parts:
            failures.append(f"{label}: path must stay inside the app boundary")
        if not owner_module:
            failures.append(f"{label}: empty owner_module")
        if not isinstance(owner_symbols, list) or not owner_symbols or not all(_safe_str(item) for item in owner_symbols):
            failures.append(f"{label}: owner_symbols must be a non-empty list of strings")
        if privacy not in VALID_PRIVACY:
            failures.append(f"{label}: invalid privacy {privacy!r}")
        if retention_policy not in VALID_RETENTION:
            failures.append(f"{label}: invalid retention_policy {retention_policy!r}")
        if body_policy not in VALID_BODY_POLICY:
            failures.append(f"{label}: invalid body_policy {body_policy!r}")
        if not stable_memory_policy:
            failures.append(f"{label}: empty stable_memory_policy")
        if status not in VALID_STATUS:
            failures.append(f"{label}: invalid status {status!r}")
        if not isinstance(projection_paths, list) or not all(_is_relative_projection_path(item) for item in projection_paths):
            failures.append(f"{label}: projection_paths must be relative path strings")
        if not isinstance(allowed_raw_readers, list) or not allowed_raw_readers:
            failures.append(f"{label}: allowed_raw_readers must be a non-empty list")
        elif not all(_is_relative_source_path(item) for item in allowed_raw_readers):
            failures.append(f"{label}: allowed_raw_readers must be relative source file paths")

        resolved_owner = APP_ROOT / f"{owner_module}.py"
        if not resolved_owner.exists():
            warnings.append(f"{label}: owner module file is missing")
        if path_value:
            resolved_queue = APP_ROOT / path_value
            if not _is_relative_to(resolved_queue.resolve(), APP_ROOT.resolve()):
                failures.append(f"{label}: resolved queue path leaves app boundary")

        checks.append(
            QueueBoundaryCheck(
                queue_id=queue_id,
                path=path_value,
                owner_module=owner_module,
                privacy=privacy,
                retention_policy=retention_policy,
                status=status,
            )
        )

    return QueueBoundaryValidationResult(
        checks=tuple(checks),
        failures=tuple(failures),
        warnings=tuple(warnings),
    )


def _is_allowed_queue_path(value: str) -> bool:
    return (
        bool(value)
        and value.endswith(".json")
        and (value.startswith("memory/") or value.startswith("runtime/"))
    )


def _is_relative_projection_path(value: Any) -> bool:
    text = _safe_str(value)
    return bool(text) and not Path(text).is_absolute() and ".." not in Path(text).parts


def _is_relative_source_path(value: Any) -> bool:
    text = _safe_str(value)
    return bool(text) and not Path(text).is_absolute() and ".." not in Path(text).parts


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _result_payload(result: QueueBoundaryValidationResult) -> dict[str, Any]:
    return {
        "ok": result.ok,
        "failures": list(result.failures),
        "warnings": list(result.warnings),
        "checks": [
            {
                "queue_id": check.queue_id,
                "path": check.path,
                "owner_module": check.owner_module,
                "privacy": check.privacy,
                "retention_policy": check.retention_policy,
                "status": check.status,
            }
            for check in result.checks
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate XinYu runtime queue boundary manifest.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    result = validate_manifest(args.manifest)
    print(json.dumps(_result_payload(result), ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

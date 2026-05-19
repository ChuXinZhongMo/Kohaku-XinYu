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
DEFAULT_MANIFEST = APP_ROOT / "stores" / "event_boundary_manifest.json"

REQUIRED_FIELDS: tuple[str, ...] = (
    "stream_id",
    "path",
    "owner_module",
    "owner_symbol",
    "projection_paths",
    "allowed_raw_readers",
    "privacy",
    "retention_policy",
    "max_rows",
    "body_policy",
    "stable_memory_policy",
    "status",
)

VALID_PRIVACY = {
    "private_runtime_event_log",
    "private_relationship_event_log",
}
VALID_RETENTION = {"bounded_rows"}
VALID_BODY_POLICY = {"no_body_migration"}
VALID_STATUS = {"compat_event_stream"}


@dataclass(frozen=True, slots=True)
class EventBoundaryCheck:
    stream_id: str
    path: str
    owner_module: str
    privacy: str
    max_rows: int
    status: str


@dataclass(frozen=True, slots=True)
class EventBoundaryValidationResult:
    checks: tuple[EventBoundaryCheck, ...]
    failures: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.failures


def load_manifest(path: Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def validate_manifest(path: Path = DEFAULT_MANIFEST) -> EventBoundaryValidationResult:
    manifest = load_manifest(path)
    streams = manifest.get("streams")
    if not isinstance(streams, list):
        return EventBoundaryValidationResult(
            checks=(),
            failures=("manifest streams must be a list",),
            warnings=(),
        )
    return validate_streams(streams)


def validate_streams(streams: list[Any]) -> EventBoundaryValidationResult:
    checks: list[EventBoundaryCheck] = []
    failures: list[str] = []
    warnings: list[str] = []
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()

    for index, raw in enumerate(streams, start=1):
        label = f"stream[{index}]"
        if not isinstance(raw, dict):
            failures.append(f"{label}: stream must be an object")
            continue
        stream = raw
        stream_id = _safe_str(stream.get("stream_id"))
        path_value = _safe_str(stream.get("path"))
        label = stream_id or path_value or label
        missing = [field for field in REQUIRED_FIELDS if field not in stream]
        if missing:
            failures.append(f"{label}: missing fields: {', '.join(missing)}")
            continue

        if stream_id in seen_ids:
            failures.append(f"{label}: duplicate stream_id")
        seen_ids.add(stream_id)
        if path_value in seen_paths:
            failures.append(f"{label}: duplicate path")
        seen_paths.add(path_value)

        owner_module = _safe_str(stream.get("owner_module"))
        owner_symbol = _safe_str(stream.get("owner_symbol"))
        privacy = _safe_str(stream.get("privacy"))
        retention_policy = _safe_str(stream.get("retention_policy"))
        body_policy = _safe_str(stream.get("body_policy"))
        stable_memory_policy = _safe_str(stream.get("stable_memory_policy"))
        status = _safe_str(stream.get("status"))
        max_rows = _safe_int(stream.get("max_rows"), default=0)
        projection_paths = stream.get("projection_paths")
        allowed_raw_readers = stream.get("allowed_raw_readers")

        if not stream_id:
            failures.append(f"{label}: empty stream_id")
        if not path_value.startswith("memory/") or not path_value.endswith(".jsonl"):
            failures.append(f"{label}: path must be a relative memory/*.jsonl path")
        if Path(path_value).is_absolute() or ".." in Path(path_value).parts:
            failures.append(f"{label}: path must stay inside the app boundary")
        if not owner_module:
            failures.append(f"{label}: empty owner_module")
        if not owner_symbol:
            failures.append(f"{label}: empty owner_symbol")
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
        if max_rows <= 0:
            failures.append(f"{label}: max_rows must be positive")
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
            resolved_stream = APP_ROOT / path_value
            if not _is_relative_to(resolved_stream.resolve(), APP_ROOT.resolve()):
                failures.append(f"{label}: resolved stream path leaves app boundary")

        checks.append(
            EventBoundaryCheck(
                stream_id=stream_id,
                path=path_value,
                owner_module=owner_module,
                privacy=privacy,
                max_rows=max_rows,
                status=status,
            )
        )

    return EventBoundaryValidationResult(
        checks=tuple(checks),
        failures=tuple(failures),
        warnings=tuple(warnings),
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


def _safe_int(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _result_payload(result: EventBoundaryValidationResult) -> dict[str, Any]:
    return {
        "ok": result.ok,
        "failures": list(result.failures),
        "warnings": list(result.warnings),
        "checks": [
            {
                "stream_id": check.stream_id,
                "path": check.path,
                "owner_module": check.owner_module,
                "privacy": check.privacy,
                "max_rows": check.max_rows,
                "status": check.status,
            }
            for check in result.checks
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate XinYu event boundary manifest metadata without reading event bodies.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--json", action="store_true", help="Print redacted JSON result.")
    args = parser.parse_args(argv)

    result = validate_manifest(args.manifest)
    if args.json:
        print(json.dumps(_result_payload(result), ensure_ascii=False, indent=2, sort_keys=True))
    elif result.ok:
        print("Event boundary manifest validation passed")
        for check in result.checks:
            print(f"- {check.stream_id}: {check.path}, {check.privacy}, max_rows={check.max_rows}")
    else:
        print("Event boundary manifest validation failed")
        for failure in result.failures:
            print(f"- {failure}")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

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
DEFAULT_MANIFEST = APP_ROOT / "stores" / "runtime_trace_manifest.json"

REQUIRED_FIELDS: tuple[str, ...] = (
    "trace_id",
    "path",
    "owner_module",
    "owner_symbol",
    "projection_paths",
    "allowed_raw_readers",
    "privacy",
    "retention_policy",
    "body_policy",
    "stable_memory_policy",
    "status",
)

VALID_PRIVACY = {"internal_runtime_trace"}
VALID_RETENTION = {"append_only_pending_rotation", "bounded_rows"}
VALID_BODY_POLICY = {"no_body_migration"}
VALID_STATUS = {"compat_runtime_trace"}


@dataclass(frozen=True, slots=True)
class RuntimeTraceCheck:
    trace_id: str
    path: str
    owner_module: str
    privacy: str
    retention_policy: str
    status: str


@dataclass(frozen=True, slots=True)
class RuntimeTraceValidationResult:
    checks: tuple[RuntimeTraceCheck, ...]
    failures: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.failures


def load_manifest(path: Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def validate_manifest(path: Path = DEFAULT_MANIFEST) -> RuntimeTraceValidationResult:
    manifest = load_manifest(path)
    traces = manifest.get("traces")
    if not isinstance(traces, list):
        return RuntimeTraceValidationResult(
            checks=(),
            failures=("manifest traces must be a list",),
            warnings=(),
        )
    return validate_traces(traces)


def validate_traces(traces: list[Any]) -> RuntimeTraceValidationResult:
    checks: list[RuntimeTraceCheck] = []
    failures: list[str] = []
    warnings: list[str] = []
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()

    for index, raw in enumerate(traces, start=1):
        label = f"trace[{index}]"
        if not isinstance(raw, dict):
            failures.append(f"{label}: trace must be an object")
            continue
        trace = raw
        trace_id = _safe_str(trace.get("trace_id"))
        path_value = _safe_str(trace.get("path"))
        label = trace_id or path_value or label
        missing = [field for field in REQUIRED_FIELDS if field not in trace]
        if missing:
            failures.append(f"{label}: missing fields: {', '.join(missing)}")
            continue

        if trace_id in seen_ids:
            failures.append(f"{label}: duplicate trace_id")
        seen_ids.add(trace_id)
        if path_value in seen_paths:
            failures.append(f"{label}: duplicate path")
        seen_paths.add(path_value)

        owner_module = _safe_str(trace.get("owner_module"))
        owner_symbol = _safe_str(trace.get("owner_symbol"))
        privacy = _safe_str(trace.get("privacy"))
        retention_policy = _safe_str(trace.get("retention_policy"))
        body_policy = _safe_str(trace.get("body_policy"))
        stable_memory_policy = _safe_str(trace.get("stable_memory_policy"))
        status = _safe_str(trace.get("status"))
        projection_paths = trace.get("projection_paths")
        allowed_raw_readers = trace.get("allowed_raw_readers")

        if not trace_id:
            failures.append(f"{label}: empty trace_id")
        if not _is_allowed_trace_path(path_value):
            failures.append(f"{label}: path must be a relative memory/*.jsonl or runtime/*.jsonl path")
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
            resolved_trace = APP_ROOT / path_value
            if not _is_relative_to(resolved_trace.resolve(), APP_ROOT.resolve()):
                failures.append(f"{label}: resolved trace path leaves app boundary")

        checks.append(
            RuntimeTraceCheck(
                trace_id=trace_id,
                path=path_value,
                owner_module=owner_module,
                privacy=privacy,
                retention_policy=retention_policy,
                status=status,
            )
        )

    return RuntimeTraceValidationResult(
        checks=tuple(checks),
        failures=tuple(failures),
        warnings=tuple(warnings),
    )


def _is_allowed_trace_path(value: str) -> bool:
    return (
        bool(value)
        and value.endswith(".jsonl")
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


def _result_payload(result: RuntimeTraceValidationResult) -> dict[str, Any]:
    return {
        "ok": result.ok,
        "failures": list(result.failures),
        "warnings": list(result.warnings),
        "checks": [
            {
                "trace_id": check.trace_id,
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
    parser = argparse.ArgumentParser(description="Validate XinYu runtime trace boundary manifest.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    result = validate_manifest(args.manifest)
    print(json.dumps(_result_payload(result), ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

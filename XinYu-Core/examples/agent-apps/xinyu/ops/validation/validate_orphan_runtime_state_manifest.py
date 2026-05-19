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
DEFAULT_MANIFEST = APP_ROOT / "stores" / "orphan_runtime_state_manifest.json"

REQUIRED_FIELDS: tuple[str, ...] = (
    "path",
    "decision",
    "target_boundary",
    "delete_allowed",
    "handling",
)

VALID_DECISION = {"held_orphan_runtime_state"}
VALID_TARGET = {"stores/orphan_runtime_state_manifest"}


@dataclass(frozen=True, slots=True)
class OrphanRuntimeStateCheck:
    path: str
    decision: str
    target_boundary: str
    delete_allowed: bool


@dataclass(frozen=True, slots=True)
class OrphanRuntimeStateValidationResult:
    checks: tuple[OrphanRuntimeStateCheck, ...]
    failures: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return not self.failures


def load_manifest(path: Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def validate_manifest(path: Path = DEFAULT_MANIFEST) -> OrphanRuntimeStateValidationResult:
    manifest = load_manifest(path)
    states = manifest.get("states")
    if not isinstance(states, list):
        return OrphanRuntimeStateValidationResult(
            checks=(),
            failures=("manifest states must be a list",),
            warnings=(),
        )
    return validate_states(states)


def validate_states(states: list[Any]) -> OrphanRuntimeStateValidationResult:
    checks: list[OrphanRuntimeStateCheck] = []
    failures: list[str] = []
    warnings: list[str] = []
    seen_paths: set[str] = set()

    for index, raw in enumerate(states, start=1):
        label = f"state[{index}]"
        if not isinstance(raw, dict):
            failures.append(f"{label}: state must be an object")
            continue
        state = raw
        path_value = _safe_str(state.get("path"))
        label = path_value or label
        missing = [field for field in REQUIRED_FIELDS if field not in state]
        if missing:
            failures.append(f"{label}: missing fields: {', '.join(missing)}")
            continue

        decision = _safe_str(state.get("decision"))
        target_boundary = _safe_str(state.get("target_boundary"))
        delete_allowed = state.get("delete_allowed")
        handling = _safe_str(state.get("handling"))

        if path_value in seen_paths:
            failures.append(f"{label}: duplicate path")
        seen_paths.add(path_value)
        if not _is_allowed_state_path(path_value):
            failures.append(f"{label}: path must be a relative memory/*.json or runtime/*.json path")
        if Path(path_value).is_absolute() or ".." in Path(path_value).parts:
            failures.append(f"{label}: path must stay inside the app boundary")
        if decision not in VALID_DECISION:
            failures.append(f"{label}: invalid decision {decision!r}")
        if target_boundary not in VALID_TARGET:
            failures.append(f"{label}: invalid target_boundary {target_boundary!r}")
        if delete_allowed is not False:
            failures.append(f"{label}: delete_allowed must be false")
        if not handling:
            failures.append(f"{label}: empty handling")
        if path_value:
            resolved_state = APP_ROOT / path_value
            if not _is_relative_to(resolved_state.resolve(), APP_ROOT.resolve()):
                failures.append(f"{label}: resolved state path leaves app boundary")

        checks.append(
            OrphanRuntimeStateCheck(
                path=path_value,
                decision=decision,
                target_boundary=target_boundary,
                delete_allowed=bool(delete_allowed),
            )
        )

    return OrphanRuntimeStateValidationResult(
        checks=tuple(checks),
        failures=tuple(failures),
        warnings=tuple(warnings),
    )


def held_state_paths(path: Path = DEFAULT_MANIFEST) -> set[str]:
    try:
        manifest = load_manifest(path)
    except OSError:
        return set()
    paths: set[str] = set()
    for state in manifest.get("states") or []:
        if isinstance(state, dict):
            text = _safe_str(state.get("path"))
            if text:
                paths.add(text)
    return paths


def _is_allowed_state_path(value: str) -> bool:
    return (
        bool(value)
        and value.endswith(".json")
        and (value.startswith("memory/") or value.startswith("runtime/"))
    )


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _result_payload(result: OrphanRuntimeStateValidationResult) -> dict[str, Any]:
    return {
        "ok": result.ok,
        "failures": list(result.failures),
        "warnings": list(result.warnings),
        "checks": [
            {
                "path": check.path,
                "decision": check.decision,
                "target_boundary": check.target_boundary,
                "delete_allowed": check.delete_allowed,
            }
            for check in result.checks
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate XinYu orphan runtime state hold manifest.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()
    result = validate_manifest(args.manifest)
    print(json.dumps(_result_payload(result), ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import tempfile
from pathlib import Path

from xinyu_local_scope import (
    DEFAULT_SUBDIRS,
    LocalScopeError,
    ensure_local_scope,
    local_scope_status,
    resolve_read_only_scope_path,
    resolve_local_scope_path,
)


def main() -> int:
    root = ROOT
    live_status = local_scope_status(root)
    live_scope = Path(live_status["local_scope_root"])
    failures: list[str] = []

    if not live_scope.exists():
        failures.append(f"live local scope missing: {live_scope}")
    for name in DEFAULT_SUBDIRS:
        if not (live_scope / name).is_dir():
            failures.append(f"live local scope subdir missing: {name}")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = ensure_local_scope(Path(temp_dir) / "scope")
        allowed = resolve_local_scope_path(temp_root, "Inbox/example.txt")
        if allowed != (temp_root / "Inbox" / "example.txt").resolve():
            failures.append("allowed local scope path resolved incorrectly")

        outside_cases = [
            "..\\outside.txt",
            Path(temp_dir) / "outside.txt",
        ]
        for case in outside_cases:
            try:
                resolve_local_scope_path(temp_root, case)
            except LocalScopeError:
                continue
            failures.append(f"outside path was not blocked: {case}")

        read_root = Path(temp_dir) / "read-only"
        read_root.mkdir()
        read_allowed = resolve_read_only_scope_path([read_root], "notes/example.txt")
        if read_allowed != (read_root / "notes" / "example.txt").resolve():
            failures.append("allowed read-only path resolved incorrectly")
        read_absolute = resolve_read_only_scope_path([read_root], read_root / "notes" / "example.txt")
        if read_absolute != (read_root / "notes" / "example.txt").resolve():
            failures.append("absolute read-only path resolved incorrectly")
        for case in outside_cases:
            try:
                resolve_read_only_scope_path([read_root], case)
            except LocalScopeError:
                continue
            failures.append(f"outside read-only path was not blocked: {case}")

    if live_status["write_policy"] != "allowed_inside_scope_only":
        failures.append("unexpected local scope write policy")
    if live_status["read_only_policy"] not in {
        "not_configured",
        "allowed_inside_explicit_owner_dirs_only",
    }:
        failures.append("unexpected read-only policy")
    if "blocked_outside_scope" not in live_status["private_file_policy"]:
        failures.append("unexpected private file policy")

    if failures:
        print("Local scope smoke failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Local scope smoke passed")
    print(f"local_scope_root: {live_scope}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

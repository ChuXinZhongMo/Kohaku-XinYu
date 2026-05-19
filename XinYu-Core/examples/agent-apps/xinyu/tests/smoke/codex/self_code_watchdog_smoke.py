from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import tempfile
from pathlib import Path

from xinyu_self_code_watchdog import create_self_code_snapshot, restore_self_code_snapshot


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def main() -> int:
    root = ROOT
    failures: list[str] = []

    with tempfile.TemporaryDirectory(prefix="xinyu-self-code-watchdog-") as tmp:
        temp_root = Path(tmp)
        _write(temp_root / "xinyu_core_bridge.py", 'BRIDGE_VERSION = "smoke"\nprint("ok")')
        _write(temp_root / "xinyu_qq_gateway.py", "GATEWAY = True")
        _write(temp_root / "custom/engine.py", "VALUE = 1")
        _write(temp_root / "runtime/should_not_snapshot.py", "BROKEN = True")

        snapshot = create_self_code_snapshot(
            temp_root,
            approval_id="selfcode-direct-smoke",
            reason="smoke",
            observed_at="2026-05-02T18:00:00+08:00",
        )
        if not snapshot.get("ok"):
            failures.append(f"snapshot not ok: {snapshot}")
        if int(snapshot.get("file_count") or 0) < 3:
            failures.append(f"snapshot file count too low: {snapshot}")

        _write(temp_root / "xinyu_core_bridge.py", "raise SyntaxError('broken')")
        _write(temp_root / "custom/engine.py", "VALUE = 'broken'")
        restored = restore_self_code_snapshot(
            Path(str(snapshot["manifest_path"])),
            root=temp_root,
            observed_at="2026-05-02T18:00:10+08:00",
            reason="smoke_restore",
        )
        if not restored.get("ok") or int(restored.get("restored") or 0) < 3:
            failures.append(f"restore not ok: {restored}")
        if 'BRIDGE_VERSION = "smoke"' not in _read(temp_root / "xinyu_core_bridge.py"):
            failures.append("core bridge was not restored")
        if "VALUE = 1" not in _read(temp_root / "custom/engine.py"):
            failures.append("custom code was not restored")
        state = _read(temp_root / "memory/context/self_code_watchdog_state.md")
        trace = _read(temp_root / "runtime/self_code_watchdog_trace.jsonl")
        for marker in ("status: restored", "snapshot_id:", "rollback_scope: existing XinYu app code"):
            if marker not in state:
                failures.append(f"watchdog state missing marker: {marker}")
        if "snapshot_restored" not in trace:
            failures.append("watchdog trace missing restore event")

    start_script = _read(root / "start_xinyu_core_bridge.ps1")
    for marker in (
        "SelfCodeSnapshotPath",
        "Wait-CoreBridgeHealth",
        "Restore-SelfCodeSnapshot",
        "Add-OwnerOutboxMessage",
        "rolled_back_and_running",
    ):
        if marker not in start_script:
            failures.append(f"start script missing watchdog marker: {marker}")

    core_text = _read(root / "xinyu_core_bridge.py")
    for marker in (
        "_prepare_self_code_watchdog_payload",
        "self_code_watchdog_manifest_path",
        "-SelfCodeSnapshotPath",
    ):
        if marker not in core_text:
            failures.append(f"core bridge missing watchdog marker: {marker}")

    if failures:
        print("self_code_watchdog_smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("self_code_watchdog_smoke ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

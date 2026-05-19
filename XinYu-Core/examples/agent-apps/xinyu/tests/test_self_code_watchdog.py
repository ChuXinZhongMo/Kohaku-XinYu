from __future__ import annotations

from pathlib import Path

from xinyu_self_code_watchdog import create_self_code_snapshot, restore_self_code_snapshot


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def test_restore_skips_backup_when_manifest_sha_mismatch(tmp_path: Path) -> None:
    source = tmp_path / "xinyu_core_bridge.py"
    _write(source, 'BRIDGE_VERSION = "snapshot"\n')
    snapshot = create_self_code_snapshot(
        tmp_path,
        approval_id="selfcode-sha-test",
        reason="test",
        observed_at="2026-05-16T18:10:00+08:00",
    )

    manifest_path = Path(str(snapshot["manifest_path"]))
    backup_path = manifest_path.parent / "files" / "xinyu_core_bridge.py"
    _write(backup_path, 'BRIDGE_VERSION = "tampered"\n')
    _write(source, 'BRIDGE_VERSION = "current"\n')

    restored = restore_self_code_snapshot(
        manifest_path,
        root=tmp_path,
        observed_at="2026-05-16T18:11:00+08:00",
        reason="test_restore",
    )

    assert restored["restored"] == 0
    assert restored["skipped"] == ["xinyu_core_bridge.py"]
    assert source.read_text(encoding="utf-8") == 'BRIDGE_VERSION = "current"\n'

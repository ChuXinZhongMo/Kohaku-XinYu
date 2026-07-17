from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path

from xinyu_bridge_autonomous_maintenance_response import _plan_maintenance_ticks


def test_plan_maintenance_ticks_defers_heavy_when_device_blocked(tmp_path: Path, monkeypatch) -> None:
    runtime = SimpleNamespace(xinyu_dir=tmp_path, memory_root=tmp_path)

    class _Blocked:
        allowed = False
        reason = "cpu_high"
        metrics = {"cpu_percent": 99.0, "ram_free_gb": 0.5, "disk_free_gb": 2.0, "tts_busy": False}

        def as_dict(self):
            return {"allowed": False, "reason": self.reason, "metrics": self.metrics}

    monkeypatch.setattr(
        "xinyu_device_resource_gate.evaluate_device_resource_gate",
        lambda root=None: _Blocked(),
    )
    plan = _plan_maintenance_ticks(runtime)
    assert plan["run_maintenance_light"] is True
    assert plan["run_heavy"] is False
    assert "tick_queue" in plan["note"]


def test_plan_maintenance_ticks_allows_heavy_when_device_ok(tmp_path: Path, monkeypatch) -> None:
    runtime = SimpleNamespace(xinyu_dir=tmp_path)

    class _Ok:
        allowed = True
        reason = "ok"
        metrics = {"cpu_percent": 10.0, "ram_free_gb": 12.0, "disk_free_gb": 100.0}

        def as_dict(self):
            return {"allowed": True, "reason": "ok", "metrics": self.metrics}

    monkeypatch.setattr(
        "xinyu_device_resource_gate.evaluate_device_resource_gate",
        lambda root=None: _Ok(),
    )
    plan = _plan_maintenance_ticks(runtime)
    assert plan["run_heavy"] is True

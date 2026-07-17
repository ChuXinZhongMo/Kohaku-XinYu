from __future__ import annotations

from pathlib import Path

from xinyu_device_resource_gate import evaluate_device_resource_gate


def test_device_gate_allows_when_disabled(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XINYU_DEVICE_RESOURCE_GATE", "0")
    decision = evaluate_device_resource_gate(tmp_path)
    assert decision.allowed is True
    assert decision.reason == "gate_disabled"


def test_device_gate_returns_metrics(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XINYU_DEVICE_RESOURCE_GATE", "1")
    monkeypatch.setenv("XINYU_DEVICE_MIN_FREE_GB", "0.000001")
    monkeypatch.setenv("XINYU_DEVICE_MAX_CPU_PERCENT", "100")
    monkeypatch.setenv("XINYU_DEVICE_MIN_FREE_RAM_GB", "0")
    monkeypatch.setenv("XINYU_DEVICE_RESPECT_TTS_BUSY", "0")
    decision = evaluate_device_resource_gate(tmp_path)
    assert "metrics" in decision.as_dict()
    # On a normal dev machine this should allow; if not, reason is explicit.
    assert decision.reason in {"ok", "low_disk", "high_cpu", "low_ram", "tts_busy"}

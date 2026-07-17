"""Device resource gate for full-autonomy loops.

Keeps Agent-tech scout / search / self-iteration inside owner-machine limits:
CPU load, free RAM, free disk, and optional TTS-GPU courtesy pause.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ENV_ENABLED = "XINYU_DEVICE_RESOURCE_GATE"
ENV_MIN_FREE_GB = "XINYU_DEVICE_MIN_FREE_GB"
ENV_MAX_CPU = "XINYU_DEVICE_MAX_CPU_PERCENT"
ENV_MIN_FREE_RAM_GB = "XINYU_DEVICE_MIN_FREE_RAM_GB"
ENV_RESPECT_TTS = "XINYU_DEVICE_RESPECT_TTS_BUSY"

DEFAULT_MIN_FREE_GB = 5.0
DEFAULT_MAX_CPU = 90.0
DEFAULT_MIN_FREE_RAM_GB = 1.5


@dataclass(frozen=True)
class DeviceGateDecision:
    allowed: bool
    reason: str
    metrics: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "metrics": dict(self.metrics),
        }


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _gate_enabled() -> bool:
    raw = os.environ.get(ENV_ENABLED, "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _disk_free_gb(path: Path) -> float | None:
    try:
        usage = shutil.disk_usage(str(path))
        return float(usage.free) / (1024**3)
    except OSError:
        return None


def _cpu_percent() -> float | None:
    try:
        import psutil  # type: ignore

        return float(psutil.cpu_percent(interval=0.05))
    except Exception:
        # Fallback: load average on Unix; Windows without psutil → unknown.
        try:
            load1, _, _ = os.getloadavg()  # type: ignore[attr-defined]
            cpus = max(1, os.cpu_count() or 1)
            return min(100.0, 100.0 * float(load1) / float(cpus))
        except Exception:
            return None


def _ram_free_gb() -> float | None:
    try:
        import psutil  # type: ignore

        return float(psutil.virtual_memory().available) / (1024**3)
    except Exception:
        return None


def _tts_busy_hint(root: Path) -> bool:
    """Best-effort: if TTS lock/heartbeat looks active, avoid heavy scout."""
    candidates = [
        root / "runtime" / "tts_busy.lock",
        root / "runtime" / "higgs_busy.lock",
        root / "runtime" / "voice" / "busy.flag",
    ]
    for path in candidates:
        try:
            if path.exists():
                return True
        except OSError:
            continue
    return False


def evaluate_device_resource_gate(root: Path | str | None = None) -> DeviceGateDecision:
    root_path = Path(root or ".").resolve()
    metrics: dict[str, Any] = {}
    if not _gate_enabled():
        return DeviceGateDecision(True, "gate_disabled", metrics)

    min_disk = _env_float(ENV_MIN_FREE_GB, DEFAULT_MIN_FREE_GB)
    max_cpu = _env_float(ENV_MAX_CPU, DEFAULT_MAX_CPU)
    min_ram = _env_float(ENV_MIN_FREE_RAM_GB, DEFAULT_MIN_FREE_RAM_GB)
    respect_tts = os.environ.get(ENV_RESPECT_TTS, "1").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }

    free_disk = _disk_free_gb(root_path)
    cpu = _cpu_percent()
    free_ram = _ram_free_gb()
    tts_busy = _tts_busy_hint(root_path) if respect_tts else False

    metrics.update(
        {
            "free_disk_gb": free_disk,
            "cpu_percent": cpu,
            "free_ram_gb": free_ram,
            "tts_busy": tts_busy,
            "min_free_disk_gb": min_disk,
            "max_cpu_percent": max_cpu,
            "min_free_ram_gb": min_ram,
        }
    )

    if free_disk is not None and free_disk < min_disk:
        return DeviceGateDecision(False, "low_disk", metrics)
    if cpu is not None and cpu > max_cpu:
        return DeviceGateDecision(False, "high_cpu", metrics)
    if free_ram is not None and free_ram < min_ram:
        return DeviceGateDecision(False, "low_ram", metrics)
    if tts_busy:
        return DeviceGateDecision(False, "tts_busy", metrics)
    return DeviceGateDecision(True, "ok", metrics)

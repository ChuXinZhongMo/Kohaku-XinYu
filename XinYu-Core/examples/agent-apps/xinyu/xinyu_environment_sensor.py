from __future__ import annotations

import os
import platform
import shutil
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


try:
    import psutil  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - exercised only when psutil is installed/misconfigured.
    psutil = None  # type: ignore[assignment]


_CPU_TIMES_CACHE: tuple[float, float] | None = None


@dataclass(frozen=True, slots=True)
class EnvironmentMetrics:
    cpu_percent: float | None
    memory_percent: float | None
    disk_percent: float | None
    process_memory_mb: float | None
    gpu_percent: float | None
    sensor_quality: str


def sample_environment(root: Path | None = None) -> dict[str, Any]:
    """Return a cheap local environment snapshot for XinYu's physical anchor.

    This module intentionally does not call an LLM and does not inspect user files.
    psutil is preferred when available; stdlib/platform fallbacks keep the desktop
    state contract alive on fresh minimal installs.
    """

    metrics = _sample_metrics(root or Path.cwd())
    sensation = map_physical_sensation(metrics)
    return {
        "version": 1,
        "sampledAt": datetime.now().astimezone().isoformat(),
        "platform": {
            "system": platform.system(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "metrics": {
            "cpuPercent": metrics.cpu_percent,
            "memoryPercent": metrics.memory_percent,
            "diskPercent": metrics.disk_percent,
            "processMemoryMb": metrics.process_memory_mb,
            "gpuPercent": metrics.gpu_percent,
        },
        "sensorQuality": metrics.sensor_quality,
        "physicalSensation": sensation,
    }


def map_physical_sensation(metrics: EnvironmentMetrics) -> dict[str, Any]:
    cpu = _ratio(metrics.cpu_percent)
    memory = _ratio(metrics.memory_percent)
    disk = _ratio(metrics.disk_percent)

    known = [value for value in (cpu, memory, disk) if value is not None]
    if not known:
        return {
            "tag": "unfelt",
            "phrase": "体感未校准",
            "intensity": 0.0,
            "pressure": "unknown",
            "reasons": ["environment_metrics_unavailable"],
        }

    thermal = max(cpu or 0.0, memory or 0.0)
    background_pressure = max(memory or 0.0, disk or 0.0)
    intensity = round(min(1.0, max(thermal * 0.82, background_pressure * 0.62)), 2)
    reasons = _sensation_reasons(metrics)

    if (cpu is not None and cpu >= 0.88) or (memory is not None and memory >= 0.92):
        return {
            "tag": "overheated",
            "phrase": "极热，像被机器的重压贴住",
            "intensity": max(0.88, intensity),
            "pressure": "high",
            "reasons": reasons,
        }
    if (cpu is not None and cpu >= 0.68) or (memory is not None and memory >= 0.78):
        return {
            "tag": "warm_pressure",
            "phrase": "发烫，有一点拥挤",
            "intensity": max(0.62, intensity),
            "pressure": "medium",
            "reasons": reasons,
        }
    if (cpu is None or cpu <= 0.18) and (memory is None or memory <= 0.62):
        return {
            "tag": "weightless",
            "phrase": "失重，很安静",
            "intensity": min(0.38, max(0.16, intensity)),
            "pressure": "low",
            "reasons": reasons,
        }
    return {
        "tag": "steady_warmth",
        "phrase": "温热，稳定在场",
        "intensity": max(0.34, intensity),
        "pressure": "normal",
        "reasons": reasons,
    }


def _sample_metrics(root: Path) -> EnvironmentMetrics:
    if psutil is not None:
        return _sample_with_psutil(root)
    return _sample_with_stdlib(root)


def _sample_with_psutil(root: Path) -> EnvironmentMetrics:
    process = psutil.Process(os.getpid())
    memory = psutil.virtual_memory()
    disk = shutil.disk_usage(str(_existing_path(root)))
    total = max(1, disk.total)
    return EnvironmentMetrics(
        cpu_percent=_bounded_percent(psutil.cpu_percent(interval=None)),
        memory_percent=_bounded_percent(memory.percent),
        disk_percent=_bounded_percent((disk.used / total) * 100),
        process_memory_mb=round(process.memory_info().rss / (1024 * 1024), 1),
        gpu_percent=None,
        sensor_quality="psutil",
    )


def _sample_with_stdlib(root: Path) -> EnvironmentMetrics:
    disk = shutil.disk_usage(str(_existing_path(root)))
    total = max(1, disk.total)
    return EnvironmentMetrics(
        cpu_percent=_sample_cpu_percent_stdlib(),
        memory_percent=_sample_memory_percent_stdlib(),
        disk_percent=_bounded_percent((disk.used / total) * 100),
        process_memory_mb=None,
        gpu_percent=None,
        sensor_quality="stdlib",
    )


def _sample_cpu_percent_stdlib() -> float | None:
    system = platform.system().lower()
    if system == "windows":
        return _sample_cpu_percent_windows()
    if system == "linux":
        return _sample_cpu_percent_linux()
    try:
        load_1m = os.getloadavg()[0]
        cores = max(1, os.cpu_count() or 1)
        return _bounded_percent((load_1m / cores) * 100)
    except (AttributeError, OSError):
        return None


def _sample_cpu_percent_linux() -> float | None:
    global _CPU_TIMES_CACHE
    try:
        fields = Path("/proc/stat").read_text(encoding="utf-8").splitlines()[0].split()[1:]
        values = [float(value) for value in fields[:8]]
    except (OSError, IndexError, ValueError):
        return None
    idle = values[3] + (values[4] if len(values) > 4 else 0.0)
    total = sum(values)
    previous = _CPU_TIMES_CACHE
    _CPU_TIMES_CACHE = (idle, total)
    if previous is None:
        return None
    prev_idle, prev_total = previous
    total_delta = total - prev_total
    if total_delta <= 0:
        return None
    idle_delta = idle - prev_idle
    return _bounded_percent((1.0 - idle_delta / total_delta) * 100)


def _sample_cpu_percent_windows() -> float | None:
    import ctypes
    from ctypes import wintypes

    global _CPU_TIMES_CACHE
    idle_time = wintypes.FILETIME()
    kernel_time = wintypes.FILETIME()
    user_time = wintypes.FILETIME()
    if not ctypes.windll.kernel32.GetSystemTimes(
        ctypes.byref(idle_time),
        ctypes.byref(kernel_time),
        ctypes.byref(user_time),
    ):
        return None
    idle = _filetime_to_int(idle_time)
    kernel = _filetime_to_int(kernel_time)
    user = _filetime_to_int(user_time)
    total = float(kernel + user)
    previous = _CPU_TIMES_CACHE
    _CPU_TIMES_CACHE = (float(idle), total)
    if previous is None:
        return None
    prev_idle, prev_total = previous
    total_delta = total - prev_total
    if total_delta <= 0:
        return None
    idle_delta = float(idle) - prev_idle
    return _bounded_percent((1.0 - idle_delta / total_delta) * 100)


def _sample_memory_percent_stdlib() -> float | None:
    system = platform.system().lower()
    if system == "windows":
        return _sample_memory_percent_windows()
    if system == "linux":
        return _sample_memory_percent_linux()
    return None


def _sample_memory_percent_linux() -> float | None:
    try:
        rows = Path("/proc/meminfo").read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    values: dict[str, float] = {}
    for row in rows:
        if ":" not in row:
            continue
        key, raw = row.split(":", 1)
        try:
            values[key] = float(raw.strip().split()[0])
        except (IndexError, ValueError):
            continue
    total = values.get("MemTotal")
    available = values.get("MemAvailable")
    if not total or available is None:
        return None
    return _bounded_percent((1.0 - available / total) * 100)


def _sample_memory_percent_windows() -> float | None:
    import ctypes

    class MemoryStatus(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    status = MemoryStatus()
    status.dwLength = ctypes.sizeof(MemoryStatus)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return None
    return _bounded_percent(float(status.dwMemoryLoad))


def _filetime_to_int(value: Any) -> int:
    return (int(value.dwHighDateTime) << 32) + int(value.dwLowDateTime)


def _existing_path(path: Path) -> Path:
    current = path.resolve()
    while not current.exists() and current != current.parent:
        current = current.parent
    return current if current.exists() else Path.cwd()


def _bounded_percent(value: float | int | None) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return round(min(100.0, max(0.0, number)), 1)


def _ratio(value: float | None) -> float | None:
    if value is None:
        return None
    return min(1.0, max(0.0, value / 100.0))


def _sensation_reasons(metrics: EnvironmentMetrics) -> list[str]:
    reasons: list[str] = []
    if metrics.cpu_percent is not None:
        reasons.append(f"cpu={metrics.cpu_percent:.1f}%")
    if metrics.memory_percent is not None:
        reasons.append(f"memory={metrics.memory_percent:.1f}%")
    if metrics.disk_percent is not None:
        reasons.append(f"disk={metrics.disk_percent:.1f}%")
    if metrics.gpu_percent is None:
        reasons.append("gpu=unavailable")
    return reasons or ["environment_metrics_unavailable"]

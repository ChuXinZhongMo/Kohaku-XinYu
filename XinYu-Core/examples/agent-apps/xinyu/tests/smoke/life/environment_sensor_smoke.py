from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import sys

from xinyu_environment_sensor import EnvironmentMetrics, map_physical_sensation, sample_environment


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    failures: list[str] = []

    snapshot = sample_environment(ROOT)
    if snapshot.get("version") != 1:
        failures.append("environment snapshot version mismatch")
    if "physicalSensation" not in snapshot:
        failures.append("environment snapshot missing physicalSensation")
    sensation = snapshot.get("physicalSensation")
    if not isinstance(sensation, dict) or not sensation.get("phrase"):
        failures.append("physical sensation phrase missing")

    hot = map_physical_sensation(
        EnvironmentMetrics(
            cpu_percent=94.0,
            memory_percent=40.0,
            disk_percent=20.0,
            process_memory_mb=None,
            gpu_percent=None,
            sensor_quality="smoke",
        )
    )
    if hot.get("tag") != "overheated":
        failures.append(f"hot metrics should map to overheated: {hot}")

    quiet = map_physical_sensation(
        EnvironmentMetrics(
            cpu_percent=5.0,
            memory_percent=32.0,
            disk_percent=20.0,
            process_memory_mb=None,
            gpu_percent=None,
            sensor_quality="smoke",
        )
    )
    if quiet.get("tag") != "weightless":
        failures.append(f"quiet metrics should map to weightless: {quiet}")

    if failures:
        print("Environment sensor smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Environment sensor smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

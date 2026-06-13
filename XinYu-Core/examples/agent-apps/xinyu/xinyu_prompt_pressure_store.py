from __future__ import annotations

from pathlib import Path
from typing import Any

from state_service import atomic_write_json


def write_prompt_pressure_report_json(path: Path, report: dict[str, Any]) -> None:
    atomic_write_json(path, report)

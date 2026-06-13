from __future__ import annotations

import json

from xinyu_prompt_pressure_store import write_prompt_pressure_report_json


def test_write_prompt_pressure_report_json_uses_state_service_json_writer(tmp_path) -> None:
    path = tmp_path / "runtime/prompt_pressure/last_live_prompt_pressure.json"

    write_prompt_pressure_report_json(path, {"live_prompt_chars": 1234, "mode": "quiet"})

    assert json.loads(path.read_text(encoding="utf-8")) == {
        "live_prompt_chars": 1234,
        "mode": "quiet",
    }

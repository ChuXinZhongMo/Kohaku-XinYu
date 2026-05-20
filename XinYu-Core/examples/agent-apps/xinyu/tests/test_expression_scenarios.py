from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = ROOT / "expression-scenarios" / "scenarios.json"


def test_expression_scenario_set_covers_core_owner_private_cases() -> None:
    data = json.loads(SCENARIOS.read_text(encoding="utf-8"))
    ids = {item["id"] for item in data["scenarios"]}

    assert {
        "greeting",
        "acknowledgement",
        "fatigue",
        "anger_blame",
        "technical_request",
        "uncertainty_waiting",
        "proactive_response",
    }.issubset(ids)


def test_expression_scenarios_separate_intent_stance_surface_layers() -> None:
    data = json.loads(SCENARIOS.read_text(encoding="utf-8"))

    assert set(data["layers"]) == {"intent", "stance", "surface_expression"}
    for item in data["scenarios"]:
        assert item["intent"]
        assert item["surface_rule"]
        assert item["locale"] == "zh"

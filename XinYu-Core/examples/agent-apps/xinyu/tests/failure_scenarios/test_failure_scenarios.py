from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCENARIO_DIR = ROOT / "failure-scenarios" / "scenarios"
EXAMPLES_PATH = ROOT / "failure-scenarios" / "examples" / "sanitized_trace_examples.jsonl"

REQUIRED_KEYS = {
    "id",
    "title",
    "input_payload",
    "expected_trace_stages",
    "expected_health_state",
    "expected_visible_behavior",
    "expected_memory_impact",
    "recovery_action",
    "privacy_notes",
}
FORBIDDEN_PRIVATE_MARKERS = {
    "26921",
    "ChuXinZhongMo",
    "D:\\",
    "C:\\Users",
}


def _scenario_files() -> list[Path]:
    return sorted(SCENARIO_DIR.glob("*.json"))


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_failure_scenario_files_exist() -> None:
    ids = {path.stem for path in _scenario_files()}

    assert {
        "owner_private_greeting_fast_route",
        "stuck_before_route_decision",
        "pre_model_timeout_containment",
        "model_injection_timeout",
        "renderer_empty_reply_recovery",
        "stale_running_cancellation",
        "proactive_conflict_with_live_reply",
    }.issubset(ids)


def test_failure_scenarios_match_schema_and_privacy_boundary() -> None:
    for path in _scenario_files():
        data = _load(path)
        assert REQUIRED_KEYS.issubset(data), path.name
        assert data["id"] == path.stem
        assert isinstance(data["input_payload"], dict)
        assert isinstance(data["expected_trace_stages"], list) and data["expected_trace_stages"]
        assert isinstance(data["expected_health_state"], dict) and data["expected_health_state"]
        assert isinstance(data["expected_visible_behavior"], dict)
        assert isinstance(data["expected_memory_impact"], dict)
        assert isinstance(data["recovery_action"], dict)
        assert "operator_action" in data["recovery_action"]
        text = json.dumps(data, ensure_ascii=False)
        assert not any(marker in text for marker in FORBIDDEN_PRIVATE_MARKERS), path.name
        payload = data["input_payload"]
        assert payload.get("session_id", "").startswith(("scenario:", "owner_intervention"))
        assert payload.get("user_id") in {"scenario-owner", "owner"}


def test_failure_scenarios_assert_trace_health_visible_memory_and_recovery() -> None:
    for path in _scenario_files():
        data = _load(path)
        visible = data["expected_visible_behavior"]
        memory = data["expected_memory_impact"]
        recovery = data["recovery_action"]
        assert "accepted" in visible or "status" in visible
        assert "runtime_trace" in memory
        assert memory.get("approved_long_term_memory") == "forbidden"
        assert recovery.get("kind")
        assert recovery.get("operator_action")


def test_sanitized_trace_examples_reference_known_scenarios() -> None:
    scenario_ids = {path.stem for path in _scenario_files()}
    rows = [json.loads(line) for line in EXAMPLES_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]

    assert rows
    for row in rows:
        assert row["scenario_id"] in scenario_ids
        assert row["stage"]
        assert row["route"]
        assert row["status"]
        text = json.dumps(row, ensure_ascii=False)
        assert not any(marker in text for marker in FORBIDDEN_PRIVATE_MARKERS)

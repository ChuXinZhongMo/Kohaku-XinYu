from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "stores/cross_domain_synaesthesia_registry.json"
LEDGER = ROOT / "XINYU-CROSS-DOMAIN-SYNAESTHESIA.md"

REQUIRED_ENTRY_FIELDS = {
    "id",
    "domain",
    "source_anchor",
    "mechanism",
    "xinyu_problem",
    "xinyu_mapping",
    "risk_boundary",
    "candidate_module",
    "minimal_test",
    "owner_runtime_benefit",
    "integration_target",
    "status",
    "score",
}
SCORE_FIELDS = {
    "mechanism_clarity",
    "xinyu_fit",
    "testability",
    "risk_control",
    "reduction_value",
}
NO_OVERCLAIM_TEXT = (
    "biological consciousness",
    "biological sentience",
    "real human emotion",
    "has neurons",
    "has hormones",
    "has immunity",
)


def _load_registry() -> dict[str, Any]:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def test_cross_domain_registry_and_ledger_exist() -> None:
    assert LEDGER.exists()
    assert REGISTRY.exists()
    ledger = LEDGER.read_text(encoding="utf-8")

    assert "Runtime Spine" in ledger
    assert "canonical living memory recall" in ledger
    assert "It must not create a second memory recall algorithm." in ledger


def test_cross_domain_registry_schema_and_required_fields() -> None:
    data = _load_registry()

    assert data["schema_version"] == 1
    assert data["policy"]
    assert set(data["score_axes"]) == SCORE_FIELDS
    assert isinstance(data["entries"], list)
    assert len(data["entries"]) >= 10

    ids: set[str] = set()
    for entry in data["entries"]:
        missing = REQUIRED_ENTRY_FIELDS - set(entry)
        assert not missing, f"{entry.get('id', 'unknown')} missing {sorted(missing)}"
        assert entry["id"] not in ids
        ids.add(entry["id"])
        assert str(entry["source_anchor"]).startswith("http")
        assert str(entry["mechanism"]).strip()
        assert str(entry["xinyu_mapping"]).strip()
        assert str(entry["risk_boundary"]).strip()
        assert str(entry["minimal_test"]).strip()
        assert set(entry["score"]) == SCORE_FIELDS
        assert all(0 <= int(value) <= 3 for value in entry["score"].values())


def test_cross_domain_registry_prioritizes_executable_candidates() -> None:
    data = _load_registry()
    entries = {entry["id"]: entry for entry in data["entries"]}
    planned = [
        entry
        for entry in data["entries"]
        if entry["status"] in {"implemented_baseline", "planned_tier1", "candidate_tier2"}
    ]

    assert "neuro_memory_rules_baseline" in entries
    assert "medical_turn_triage" in entries
    assert "immune_memory_danger_gate" in entries
    assert len([entry for entry in data["entries"] if entry.get("tier") == 1]) >= 5
    for entry in planned:
        total = sum(int(value) for value in entry["score"].values())
        assert total >= 10, f"{entry['id']} score too low: {total}"


def test_cross_domain_registry_keeps_boundaries_and_no_overclaiming() -> None:
    data = _load_registry()
    all_text = json.dumps(data, ensure_ascii=False).lower()

    for phrase in NO_OVERCLAIM_TEXT:
        assert phrase not in all_text
    assert "direct stable-memory writes" in data["policy"]
    assert any("cannot create facts" in entry["risk_boundary"] for entry in data["entries"])
    assert any("no direct stable memory" in entry["risk_boundary"] for entry in data["entries"])

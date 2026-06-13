from __future__ import annotations

from dataclasses import dataclass

from xinyu_bridge_state_mapping import DataclassMappingState


@dataclass(eq=False)
class ExampleState(DataclassMappingState):
    name: str
    count: int


def test_dataclass_mapping_state_supports_legacy_mapping_access() -> None:
    state = ExampleState(name="xinyu", count=2)

    assert state["name"] == "xinyu"
    assert state.get("count") == 2
    assert state.get("missing", "fallback") == "fallback"
    assert state == {"name": "xinyu", "count": 2}
    assert state.as_dict() == {"name": "xinyu", "count": 2}
    assert state.keys() == ["name", "count"]
    assert state.items() == [("name", "xinyu"), ("count", 2)]
    assert state.values() == ["xinyu", 2]

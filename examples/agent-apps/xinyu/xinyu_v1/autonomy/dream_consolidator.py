"""Dream/consolidation idle job."""

from __future__ import annotations

from dataclasses import dataclass

from ..memory.consolidation import propose_consolidations
from ..memory.jsonl_store import JsonlMemoryStore
from ..types import JSONValue


@dataclass(frozen=True, slots=True)
class DreamConsolidationReport:
    candidates: int
    notes: tuple[str, ...]

    def to_json(self) -> dict[str, JSONValue]:
        return {"candidates": self.candidates, "notes": list(self.notes)}


def run_dream_consolidation(store: JsonlMemoryStore) -> DreamConsolidationReport:
    chunks = store.load_chunks()
    candidates = propose_consolidations(chunks)
    return DreamConsolidationReport(candidates=len(candidates), notes=("dry_run_consolidation",))


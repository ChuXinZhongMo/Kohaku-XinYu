"""Self data model for the Cognitive Kernel.

SelfModel represents the core identity and owned state of the persistent subject.
Extended for Self Model (K-002): stable Core Statements.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

from ..exceptions import OwnershipError

CoreStatementType = Literal[
    "identity",
    "core_value",
    "boundary",
    "long_term_orientation",
]


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class OwnedObject(BaseModel):
    """Record of an object claimed by this Self."""

    obj_id: str
    obj_type: str
    claimed_at: str = Field(default_factory=_utcnow_iso)


class CoreStatement(BaseModel):
    """A stable element of the Self Model.

    These are owned by Self and evolve very slowly via high-importance Experience.
    """
    statement_id: str
    statement_type: CoreStatementType
    content: str = Field(min_length=3, max_length=400)
    confidence: float = Field(ge=0.0, le=1.0, default=0.6)
    source_event_id: str | None = None
    created_at: str = Field(default_factory=_utcnow_iso)
    last_confirmed_at: str = Field(default_factory=_utcnow_iso)


class SelfModel(BaseModel):
    """Core data representation of a Self (the persistent owning subject)."""

    self_id: str = Field(
        default_factory=lambda: f"self_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}_{id(object())}"[:64],
        description="Unique identifier for this Self instance. Should be stable across restarts when persisted.",
    )
    owned_objects: list[OwnedObject] = Field(
        default_factory=list,
        description="General owned objects (memories, beliefs, etc.).",
    )
    core_statements: list[CoreStatement] = Field(
        default_factory=list,
        description="Stable Self Model components. Owned by this Self.",
    )
    created_at: str = Field(default_factory=_utcnow_iso)
    updated_at: str = Field(default_factory=_utcnow_iso)

    model_config = {"extra": "forbid"}

    def add_owned(self, obj_id: str, obj_type: str) -> None:
        if any(o.obj_id == obj_id for o in self.owned_objects):
            raise OwnershipError(f"Object already owned: {obj_id}")
        self.owned_objects.append(OwnedObject(obj_id=obj_id, obj_type=obj_type))
        self.updated_at = _utcnow_iso()

    def remove_owned(self, obj_id: str) -> bool:
        before = len(self.owned_objects)
        self.owned_objects = [o for o in self.owned_objects if o.obj_id != obj_id]
        if len(self.owned_objects) != before:
            self.updated_at = _utcnow_iso()
            return True
        return False

    def has_owned(self, obj_id: str) -> bool:
        return any(o.obj_id == obj_id for o in self.owned_objects)

    def add_core_statement(self, stmt: CoreStatement) -> None:
        if any(s.statement_id == stmt.statement_id for s in self.core_statements):
            raise OwnershipError(f"Core statement already exists: {stmt.statement_id}")
        self.core_statements.append(stmt)
        self.updated_at = _utcnow_iso()

    def replace_core_statement(self, stmt: CoreStatement) -> bool:
        for i, existing in enumerate(self.core_statements):
            if existing.statement_id == stmt.statement_id:
                self.core_statements[i] = stmt
                self.updated_at = _utcnow_iso()
                return True
        self.add_core_statement(stmt)
        return True

    def get_core_statements(self, stmt_type: CoreStatementType | None = None) -> list[CoreStatement]:
        if stmt_type:
            return [s for s in self.core_statements if s.statement_type == stmt_type]
        return list(self.core_statements)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SelfModel:
        return cls.model_validate(data)

"""Pydantic models for Experience Processor.

These models define the input/output structures for turning raw events
into importance scores and belief update proposals. They are intentionally
minimal and designed to be easy to serialize into the existing event log.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class EventInput(BaseModel):
    """Normalized input for experience processing.

    This is intentionally loose to accept dicts from different sources
    (chat_input, action, learning, etc.).
    """
    event_id: str | None = None
    timestamp: str | None = None
    source_channel: str = "unknown"
    actor_scope: str = "unknown"  # "owner", "non_owner", "group_member" ...
    raw_text: str = ""
    turn_mode: str = "unknown"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("raw_text")
    @classmethod
    def normalize_text(cls, v: str) -> str:
        if v is None:
            return ""
        return str(v).strip()


class BeliefProposal(BaseModel):
    """A single proposed belief update derived from experience.

    This is *not* a committed belief. It is a proposal that a future
    Belief system can consider.
    """
    proposal_type: Literal[
        "preference",
        "fact",
        "boundary",
        "relationship",
        "self_observation",
        "other",
    ] = "other"
    content: str = Field(min_length=1, max_length=500)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    evidence_span: str | None = Field(
        default=None,
        description="Short excerpt from the original text that supports this proposal"
    )


class ExperienceResult(BaseModel):
    """Output of ExperienceProcessor.

    importance_score: 0-100, higher means more worth retaining / reflecting on.
    belief_update_proposals: list of candidate updates. Can be empty.
    notes: free-form observations from the processor (for debugging / tracing).
    """
    importance_score: int = Field(ge=0, le=100, default=30)
    belief_update_proposals: list[BeliefProposal] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convenience for logging into existing event structures."""
        return self.model_dump(mode="json")


class ExperienceEnrichment(BaseModel):
    """Optional structure that can be merged into structured_events or claims."""
    salience: int | None = None  # maps to existing "salience" field
    experience_importance: int
    belief_proposals: list[dict[str, Any]]
    processor_notes: list[str]

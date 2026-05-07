"""Shared question/exploration manifest for Xinyu."""

from __future__ import annotations

QUESTION_PIPELINE_SOURCES: list[dict[str, object]] = [
    {
        "name": "active_questions",
        "path": "memory/context/active_questions.md",
        "role": "source of unresolved inward questions",
    },
    {
        "name": "question_states",
        "path": "memory/context/question_states.md",
        "role": "tracks current processing state",
    },
    {
        "name": "exploration_queue",
        "path": "memory/context/exploration_queue.md",
        "role": "holds candidates for future outward exploration",
    },
    {
        "name": "source_notes",
        "path": "memory/knowledge/source_notes.md",
        "role": "records what should be checked before external knowledge is trusted",
    },
]

QUESTION_PIPELINE_TARGETS: list[str] = [
    "memory/context/question_pipeline_state.md",
    "memory/context/question_states.md",
    "memory/context/exploration_queue.md",
    "memory/knowledge/source_notes.md",
]

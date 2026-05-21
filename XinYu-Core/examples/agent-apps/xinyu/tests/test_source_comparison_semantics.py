from __future__ import annotations

import sys
from pathlib import Path


CUSTOM_DIR = Path(__file__).resolve().parents[1] / "custom"
if str(CUSTOM_DIR) not in sys.path:
    sys.path.insert(0, str(CUSTOM_DIR))

from source_comparison_engine import semantic_overlap, support_tokens_for_claim  # noqa: E402


def test_relationship_source_overlap_normalizes_safe_word_forms() -> None:
    existing_claim = (
        "Closeness, distance, and memory Relationship memory can preserve "
        "closeness, distance, boundary, return context, and earlier caution together."
    )
    followup_claim = (
        "Setting Boundaries: Connection, Not Distance. Healthy boundaries "
        "strengthen connection, not distance."
    )

    overlap, shared = semantic_overlap(followup_claim, existing_claim)

    assert {"boundary", "distance"}.issubset(shared)
    assert overlap >= 0.06


def test_relationship_source_overlap_keeps_generic_relationship_words_out() -> None:
    tokens = support_tokens_for_claim("Relationships and relationship advice can mention people.")

    assert "relationship" not in tokens
    assert "people" not in tokens

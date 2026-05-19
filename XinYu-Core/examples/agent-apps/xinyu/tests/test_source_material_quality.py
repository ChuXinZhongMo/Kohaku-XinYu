from __future__ import annotations

import sys
from pathlib import Path

CUSTOM_DIR = Path(__file__).resolve().parents[1] / "custom"
if str(CUSTOM_DIR) not in sys.path:
    sys.path.insert(0, str(CUSTOM_DIR))

from source_material_quality import claim_is_placeholder, claim_is_too_thin, claim_looks_garbled


def test_source_material_quality_rejects_placeholder_and_thin_claims() -> None:
    assert claim_is_placeholder("downloaded https://example.test/item")
    assert claim_is_too_thin("tiny note")


def test_source_material_quality_accepts_substantive_plain_claim() -> None:
    claim = (
        "Public source comparison should keep source materials staged until "
        "corroboration, reliability, and learning quality checks all pass."
    )

    assert not claim_looks_garbled(claim)
    assert not claim_is_placeholder(claim)
    assert not claim_is_too_thin(claim)

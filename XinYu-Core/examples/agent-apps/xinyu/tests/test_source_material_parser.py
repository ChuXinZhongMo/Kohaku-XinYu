from __future__ import annotations

import sys
from pathlib import Path

CUSTOM_DIR = Path(__file__).resolve().parents[1] / "custom"
if str(CUSTOM_DIR) not in sys.path:
    sys.path.insert(0, str(CUSTOM_DIR))

from learner_integration_engine import split_materials as split_learner_materials  # noqa: E402
from source_comparison_engine import split_material_blocks  # noqa: E402
from source_integration_gate_engine import split_materials as split_gate_materials  # noqa: E402
from source_material_parser import (  # noqa: E402
    integrated_source_material_ids,
    split_material_field_maps,
    split_material_sections,
)


def test_split_material_sections_preserves_preface_body_and_fields() -> None:
    text = """# Source Materials

intro

## material-local-alpha
- question_id: q-001
- reliability: verified

body tail
"""

    preface, materials = split_material_sections(text, allow_named_ids=True, rstrip_body=True)

    assert preface == "# Source Materials\n\nintro"
    assert materials[0]["material_id"] == "material-local-alpha"
    assert materials[0]["fields"]["question_id"] == "q-001"
    assert materials[0]["body"].endswith("body tail")


def test_legacy_source_comparison_parser_keeps_named_material_ids() -> None:
    text = """preface

## material-local-alpha
- status: ready
- reliability: curated
"""

    preface, materials = split_material_blocks(text)

    assert preface == "preface"
    assert materials[0]["material_id"] == "material-local-alpha"
    assert materials[0]["fields"]["status"] == "ready"


def test_legacy_learner_and_gate_material_shapes_stay_distinct() -> None:
    text = """## material-2026-05-18-001
- question_id: q-006
- url: https://example.test/source
- source_type: paper
- reliability: verified
- integration_scope: knowledge_only
- status: ready
- comparison_status: curated
- evidence_hosts: 2
- claim: A concrete claim with enough source detail for integration.
"""

    learner = split_learner_materials(text)[0]
    gate = split_gate_materials(text)[0]

    assert learner["url"] == "https://example.test/source"
    assert learner["source_type"] == "paper"
    assert learner["extraction_status"] == "unknown"
    assert "url" not in gate
    assert gate["comparison_status"] == "curated"


def test_shared_field_map_defaults_and_integrated_ids() -> None:
    text = """## material-2026-05-18-001
- status: ready

## material-local-ignore
- status: ready
"""

    materials = split_material_field_maps(
        text,
        fields=("status", "claim"),
        defaults={"status": "hold", "claim": "none"},
    )

    assert materials == [{"material_id": "material-2026-05-18-001", "status": "ready", "claim": "none"}]
    assert integrated_source_material_ids("- source_material: material-2026-05-18-001\n") == {
        "material-2026-05-18-001"
    }

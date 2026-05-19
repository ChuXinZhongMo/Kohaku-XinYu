from __future__ import annotations

from pathlib import Path

from stores.persona_runtime_overlay import (
    BOUNDARY_ID,
    COMPATIBILITY_NOTE,
    OVERLAY_REL,
    goldmark_overlay_path,
    read_goldmark_overlay,
    write_goldmark_overlay,
)
from xinyu_goldmark import OVERLAY_REL as GOLDMARK_OVERLAY_REL
from xinyu_goldmark import PERSONA_RUNTIME_OVERLAY_BOUNDARY
from xinyu_runtime_context import GOLDMARK_OVERLAY_REL as RUNTIME_GOLDMARK_OVERLAY_REL


def test_persona_runtime_overlay_store_keeps_legacy_path_as_compatibility_boundary(tmp_path: Path) -> None:
    assert BOUNDARY_ID == "stores/persona_runtime_overlay"
    assert PERSONA_RUNTIME_OVERLAY_BOUNDARY == BOUNDARY_ID
    assert "legacy memory/self" in COMPATIBILITY_NOTE
    assert OVERLAY_REL == GOLDMARK_OVERLAY_REL
    assert OVERLAY_REL == RUNTIME_GOLDMARK_OVERLAY_REL

    write_goldmark_overlay(
        tmp_path,
        [
            {
                "mark_id": "gm-test",
                "dehydration_status": "done",
                "vibe_features": {"tone_tags": ["warm"], "structural_pattern": "short and concrete"},
            }
        ],
    )

    assert goldmark_overlay_path(tmp_path) == tmp_path / "memory/self/goldmark_positive_overlay.json"
    assert read_goldmark_overlay(tmp_path)[0]["mark_id"] == "gm-test"


def test_persona_runtime_overlay_store_accepts_legacy_entries_wrapper(tmp_path: Path) -> None:
    path = goldmark_overlay_path(tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('{"entries":[{"mark_id":"gm-wrapper"}]}\n', encoding="utf-8")

    assert read_goldmark_overlay(tmp_path) == [{"mark_id": "gm-wrapper"}]

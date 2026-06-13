from __future__ import annotations

import json
from pathlib import Path

from xinyu_action_openended_audit import ACTION_RESIDUE_REL as MODULE_ACTION_RESIDUE_REL
from xinyu_action_openended_audit import DREAM_SEEDS_REL as MODULE_DREAM_SEEDS_REL
from xinyu_action_openended_audit import RECENT_ACTION_REL as MODULE_RECENT_ACTION_REL
from xinyu_action_openended_audit import REFLECTION_QUEUE_REL as MODULE_REFLECTION_QUEUE_REL
from xinyu_action_openended_audit_store import ACTION_RESIDUE_REL
from xinyu_action_openended_audit_store import DREAM_SEEDS_REL
from xinyu_action_openended_audit_store import RECENT_ACTION_REL
from xinyu_action_openended_audit_store import REFLECTION_QUEUE_REL
from xinyu_action_openended_audit_store import read_action_openended_audit_jsonl
from xinyu_action_openended_audit_store import read_action_openended_audit_text


def test_action_openended_audit_store_exports_legacy_paths() -> None:
    assert RECENT_ACTION_REL == MODULE_RECENT_ACTION_REL
    assert ACTION_RESIDUE_REL == MODULE_ACTION_RESIDUE_REL
    assert DREAM_SEEDS_REL == MODULE_DREAM_SEEDS_REL
    assert REFLECTION_QUEUE_REL == MODULE_REFLECTION_QUEUE_REL
    assert RECENT_ACTION_REL == Path("runtime/life_kernel/recent_action_experience.jsonl")
    assert ACTION_RESIDUE_REL == Path("runtime/life_kernel/action_experience_residue.jsonl")


def test_action_openended_audit_store_reads_text(tmp_path: Path) -> None:
    path = tmp_path / "memory/dreams/dream_seeds.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# Dream Seeds\n", encoding="utf-8-sig")

    text, warnings = read_action_openended_audit_text(path)

    assert text == "# Dream Seeds\n"
    assert warnings == []


def test_action_openended_audit_store_reports_missing_input(tmp_path: Path) -> None:
    path = tmp_path / "runtime/life_kernel/recent_action_experience.jsonl"

    text, warnings = read_action_openended_audit_text(path)

    assert text == ""
    assert warnings == [f"missing_input:{path.as_posix()}"]


def test_action_openended_audit_store_reads_jsonl_and_reports_invalid_rows(tmp_path: Path) -> None:
    path = tmp_path / RECENT_ACTION_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    valid = {"experience_id": "exp-1", "salience": 0.7}
    path.write_text(
        "\ufeff"
        + "\n".join(
            (
                json.dumps(valid, ensure_ascii=False, separators=(",", ":")),
                "[\"not\", \"dict\"]",
                "{bad",
                "",
            )
        )
        + "\n",
        encoding="utf-8",
    )

    rows, warnings = read_action_openended_audit_jsonl(path)

    assert rows == [valid]
    assert warnings == [f"invalid_jsonl_lines:{path.as_posix()}:2"]


def test_action_openended_audit_store_jsonl_reuses_missing_input_warning(tmp_path: Path) -> None:
    path = tmp_path / ACTION_RESIDUE_REL

    rows, warnings = read_action_openended_audit_jsonl(path)

    assert rows == []
    assert warnings == [f"missing_input:{path.as_posix()}"]

from __future__ import annotations

import json
from pathlib import Path

from xinyu_action_openended_audit import ACTION_RESIDUE_REL
from xinyu_action_openended_audit import DREAM_SEEDS_REL
from xinyu_action_openended_audit import RECENT_ACTION_REL
from xinyu_action_openended_audit import REFLECTION_QUEUE_REL
from xinyu_action_openended_audit import run_audit


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def test_action_openended_audit_detects_low_salience_action_residue(tmp_path: Path) -> None:
    _write_jsonl(
        tmp_path / RECENT_ACTION_REL,
        [
            {
                "experience_id": "exp-low-salience",
                "tool": "browser",
                "target_alias": "search",
                "result": "ok",
                "salience": 0.2,
                "summary": "opened a low salience action",
            }
        ],
    )
    _write_jsonl(
        tmp_path / ACTION_RESIDUE_REL,
        [
            {
                "experience_id": "exp-low-salience",
                "tool": "browser",
                "target_alias": "search",
                "result": "ok",
                "salience": 0.2,
                "summary": "low salience action residue",
            }
        ],
    )
    (tmp_path / DREAM_SEEDS_REL).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / DREAM_SEEDS_REL).write_text(
        "## seed-1\n"
        "- source_event: action_experience / exp-low-salience\n"
        "- theme: low salience action residue\n",
        encoding="utf-8",
    )
    (tmp_path / REFLECTION_QUEUE_REL).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / REFLECTION_QUEUE_REL).write_text(
        "## reflection-1\n"
        "- source: action_experience_residue / exp-low-salience\n"
        "- topic: low salience action residue\n",
        encoding="utf-8",
    )

    result = run_audit(tmp_path, low_salience_threshold=0.6)

    assert result["health_status"] == "unhealthy"
    assert result["recent_action_count"] == 1
    assert result["residue_count"] == 1
    assert result["dream_seed_from_action_count"] == 1
    assert result["reflection_from_action_count"] == 1
    assert result["low_salience_leaked_count"] == 3
    assert any(str(warning).startswith("low_salience_leak:count=3") for warning in result["warnings"])

from __future__ import annotations

from pathlib import Path

from xinyu_skill_library import (
    build_skill_recall_block,
    list_skills,
    record_skill_outcome,
    write_skill,
)


def test_rpe_promote_and_harmful_archive(tmp_path: Path) -> None:
    write_skill(
        tmp_path,
        {
            "skill_id": "quiet-share",
            "title": "有 finding 再分享",
            "status": "review_only",
            "situation": "想主动分享技术见闻",
            "routine": "先确认有具体 finding 再开口",
            "trigger_keys": ["分享", "finding"],
            "confidence": "1",
        },
    )
    updated = record_skill_outcome(
        tmp_path, "quiet-share", helpful=True, better_than_predicted=True
    )
    assert updated.get("status") == "active"
    assert int(updated.get("use_count") or 0) >= 1

    record_skill_outcome(tmp_path, "quiet-share", harmful=True)
    record_skill_outcome(tmp_path, "quiet-share", harmful=True)
    skills = {s["skill_id"]: s for s in list_skills(tmp_path)}
    assert skills["quiet-share"].get("status") == "archived"

    block = build_skill_recall_block(tmp_path, query_text="分享 finding")
    assert block == "" or "quiet-share" not in block

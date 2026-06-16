from __future__ import annotations

from pathlib import Path

from xinyu_skill_library import (
    SKILL_MEMORY_TYPE,
    build_skill_recall_block,
    list_skills,
    parse_skill_frontmatter,
    read_skill,
    render_skill_markdown,
    write_skill,
)


def _skill(**over) -> dict:
    base = {
        "skill_id": "voice-correction-abc123",
        "title": "说话风格·语气",
        "situation": "主人对语气给出反馈时（关键词：语气、接待腔）。",
        "routine": "按主人纠正过的风格说话；避免机械接待腔。",
        "evidence": "corroborated by 2 candidate(s): c1, c2",
        "trigger_keys": ["语气", "接待腔", "ai味"],
        "evidence_candidate_ids": ["c1", "c2"],
        "evidence_count": 2,
        "confidence": 2,
        "tags": ["voice_correction"],
        "status": "review_only",
    }
    base.update(over)
    return base


def test_write_and_read_roundtrip(tmp_path: Path) -> None:
    path = write_skill(tmp_path, _skill())
    assert path.exists()
    loaded = read_skill(tmp_path, "voice-correction-abc123")
    assert loaded["title"] == "说话风格·语气"
    assert loaded["memory_type"] == SKILL_MEMORY_TYPE
    assert loaded["permission"] == "review_only"
    assert "语气" in loaded["trigger_keys"]
    assert "机械接待腔" in loaded["routine"]
    assert loaded["created_at"]


def test_frontmatter_parses_lists() -> None:
    md = render_skill_markdown(_skill())
    fields = parse_skill_frontmatter(md)
    assert fields["trigger_keys"] == ["语气", "接待腔", "ai味"]
    assert fields["evidence_candidate_ids"] == ["c1", "c2"]


def test_index_lists_skill(tmp_path: Path) -> None:
    write_skill(tmp_path, _skill())
    skills = list_skills(tmp_path)
    assert len(skills) == 1
    assert skills[0]["skill_id"] == "voice-correction-abc123"


def test_recall_block_matches_on_trigger(tmp_path: Path) -> None:
    write_skill(tmp_path, _skill())
    block = build_skill_recall_block(tmp_path, query_text="主人说我语气太机械了")
    assert "## Learned Skills" in block
    assert "voice-correction-abc123" in block
    assert "situational_hint_not_stable_identity" in block


def test_recall_block_empty_when_no_match(tmp_path: Path) -> None:
    write_skill(tmp_path, _skill())
    block = build_skill_recall_block(tmp_path, query_text="完全无关的天气话题 weather forecast")
    assert block == ""


def test_recall_block_empty_when_no_skills(tmp_path: Path) -> None:
    assert build_skill_recall_block(tmp_path, query_text="anything") == ""


def test_update_preserves_created_at(tmp_path: Path) -> None:
    write_skill(tmp_path, _skill())
    first = read_skill(tmp_path, "voice-correction-abc123")["created_at"]
    write_skill(tmp_path, _skill(title="说话风格·更新"))
    second = read_skill(tmp_path, "voice-correction-abc123")
    assert second["created_at"] == first
    assert second["title"] == "说话风格·更新"

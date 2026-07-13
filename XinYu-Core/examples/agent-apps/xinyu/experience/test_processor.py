"""Basic tests for ExperienceProcessor.

Run with:
    python -m pytest experience/test_processor.py -q
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make local package importable when running the test file directly
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from experience.processor import ExperienceProcessor


def test_empty_event_gives_low_score():
    proc = ExperienceProcessor()
    res = proc.process({"raw_text": ""})
    assert res.importance_score == 0
    assert "empty_text" in res.notes


def test_owner_long_message_gets_high_score():
    proc = ExperienceProcessor()
    text = "Remember this is very important: I want you to always do X when I say Y. Never forget."
    res = proc.process({
        "raw_text": text,
        "actor_scope": "owner",
        "source_channel": "qq_private",
        "turn_mode": "live_user_turn",
    })
    assert res.importance_score >= 70
    assert res.belief_update_proposals  # should extract at least preference/boundary


def test_group_message_downweighted(monkeypatch):
    monkeypatch.setenv("XINYU_GROUP_FULL_MEMORY_PIPELINE", "0")
    proc = ExperienceProcessor()
    text = "hello everyone this is a long group message with some content here and there"
    res = proc.process({
        "raw_text": text,
        "actor_scope": "group_member",
        "source_channel": "qq_group",
    })
    owner_res = proc.process({
        "raw_text": text,
        "actor_scope": "owner",
        "source_channel": "qq_private",
    })
    assert res.importance_score < owner_res.importance_score


def test_group_owner_not_downweighted_when_pipeline_enabled(monkeypatch):
    monkeypatch.setenv("XINYU_GROUP_FULL_MEMORY_PIPELINE", "1")
    proc = ExperienceProcessor()
    text = "hello everyone this is a long group message with some content here and there"
    member_res = proc.process({
        "raw_text": text,
        "actor_scope": "group_member",
        "source_channel": "qq_group",
    })
    owner_group_res = proc.process({
        "raw_text": text,
        "actor_scope": "owner",
        "source_channel": "qq_group",
    })
    assert owner_group_res.importance_score >= member_res.importance_score


def test_rule_based_proposals_owner_preference():
    proc = ExperienceProcessor()
    res = proc.process({
        "raw_text": "我喜欢你这样回复，不要用太正式的语气",
        "actor_scope": "owner",
    })
    types = {p.proposal_type for p in res.belief_update_proposals}
    assert "preference" in types or "boundary" in types


def test_to_enrichment_compatible():
    proc = ExperienceProcessor()
    res = proc.process({"raw_text": "This is important.", "actor_scope": "owner"})
    enrich = proc.to_enrichment(res, base_salience=60)
    assert enrich.experience_importance == res.importance_score
    assert "salience" in enrich.model_dump()


def test_llm_judge_optional_and_safe(monkeypatch):
    def bad_judge(text, **kw):
        raise RuntimeError("LLM down")

    proc = ExperienceProcessor(llm_judge=bad_judge)
    res = proc.process({"raw_text": "something", "actor_scope": "owner"})
    # Should not crash, just record the error
    assert any("llm_judge_error" in n for n in res.notes)


if __name__ == "__main__":
    # Allow direct execution for quick smoke
    pytest.main([__file__, "-q"])

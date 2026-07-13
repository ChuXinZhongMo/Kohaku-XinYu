"""Tests for Higher Goal 1 (self-story) and owner grants."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from kernel.self import Self
from kernel.narrative_builder import build_self_story, maybe_update_self_story, write_self_story
from kernel.owner_grants import grant_owner_scope, is_scope_granted, load_owner_grants
from kernel.bridge_governance import get_kernel_review_inbox


def test_build_and_write_self_story():
    s = Self(self_id="story-test")
    s.propose_goal("Stay honest and direct.", priority=0.8, source_event_id="g1")
    s.propose_belief("Trust grows through consistency.", confidence=0.8, source_event_id="b1")
    s.update_world_model(from_error={"error_magnitude": 0.6, "source_event_id": "w1"})
    s.cognitive_cycle_state.cycle_count = 5

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        event_dir = root / "memory" / "events"
        event_dir.mkdir(parents=True)
        (event_dir / "cognitive_cycle_events.jsonl").write_text(
            json.dumps({
                "event_kind": "cognitive_cycle",
                "source_event_id": "e1",
                "structural_impact": True,
                "reorg_mode": "fast",
                "importance": 75,
                "error_magnitude": 0.7,
            }) + "\n",
            encoding="utf-8",
        )

        story = build_self_story(s, root)
        assert "Current Orientation" in story["body"]
        assert story["cycle_count"] == 5

        result = write_self_story(root, story)
        assert result["written"] is True
        assert (root / "memory" / "kernel" / "self_story.md").exists()


def test_maybe_update_self_story_on_structural_impact():
    s = Self(self_id="story-rate")
    s.cognitive_cycle_state.cycle_count = 2

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        res = maybe_update_self_story(s, root, structural_impact=True)
        assert res["updated"] is True

        res2 = maybe_update_self_story(s, root, structural_impact=False)
        assert res2["updated"] is False


def test_owner_grants_and_inbox():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        grant_owner_scope(root, "world_model", note="owner approved WM updates")
        assert is_scope_granted(root, "world_model") is True

        data = load_owner_grants(root)
        assert len(data["grants"]) == 1

        s = Self(self_id="grant-test")
        s.world_model.add_fact("Identity shift.", confidence=0.85, review_status="review_only")
        inbox = get_kernel_review_inbox(s, root)
        wm_items = [i for i in inbox["items"] if i["domain"] == "world_model"]
        if wm_items:
            assert wm_items[0]["review_status"] == "candidate"
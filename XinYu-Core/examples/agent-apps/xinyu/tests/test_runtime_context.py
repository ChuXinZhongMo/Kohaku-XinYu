from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from xinyu_runtime_context import (  # noqa: E402
    build_goldmark_auth_prompt_block,
    build_renderer_memory_context,
    read_limited,
    refresh_runtime_context,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def test_runtime_context_refreshes_shared_snapshots(tmp_path: Path) -> None:
    _write(tmp_path / "prompts/live_voice_card.md", "voice card")
    _write(
        tmp_path / "memory/self/core.md",
        """---
title: Core
importance_score: 100
impact_score: 100
confidence_score: 100
status: active
---

# Core
XinYu stable identity.
""",
    )
    _write(
        tmp_path / "memory/self/personality_profile.md",
        """---
title: Profile
importance_score: 84
impact_score: 84
confidence_score: 88
status: active
---

# Profile
stable tendency seed.
""",
    )

    snapshot = refresh_runtime_context(
        tmp_path,
        user_text="今天广州很热",
        evaluated_at="2026-04-29T21:40:00+08:00",
    )
    context = build_renderer_memory_context(tmp_path, user_text="今天广州很热")

    assert snapshot.life_month_context == ""
    assert snapshot.personality_evolution_state == ""
    assert snapshot.private_thought_state == ""
    assert snapshot.self_model_state == ""
    assert snapshot.memory_weight_state == ""
    assert snapshot.thought_seeds == ""
    assert "[prompts/live_voice_card.md]" in context
    assert "[memory/self/core.md]" in context
    assert "[memory/self/personality_profile.md]" in context
    assert "[memory/self/private_thought_state.md]" not in context
    assert "[memory/self/self_model_state.md]" not in context
    assert "[memory/context/thought_seeds.md]" not in context
    assert "[layer: concept_seed]" in context
    assert "[layer: xinyu_concept]" in context
    assert "[runtime/scene_frame]" in context
    assert "[layer: scene_frame]" in context
    assert "[memory/context/contextual_self_loop]" in context
    assert "[layer: context_horizon]" in context
    assert "[layer: self_narrative]" not in context
    assert not (tmp_path / "memory/context/current_life_month_context.md").exists()
    assert not (tmp_path / "memory/context/memory_weight_state.md").exists()
    assert not (tmp_path / "memory/context/thought_seeds.md").exists()
    assert not (tmp_path / "memory/self/private_thought_state.md").exists()
    assert not (tmp_path / "memory/self/self_model_state.md").exists()


def test_runtime_context_includes_initiative_lifecycle_state(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory/context/initiative_lifecycle_state.md",
        """
        # Initiative Lifecycle State

        - checked_at: 2026-05-13T02:00:00+08:00
        - selected_candidate_id: procand-test
        - selected_decision: desktop_inbox
        - delivery_level: desktop_inbox
        - interruption_posture: owner_visible_local
        - next_step: wait for owner ack before changing future initiative bias
        """,
    )
    _write(
        tmp_path / "memory/context/initiative_feedback_state.md",
        """
        # Initiative Feedback State

        - last_feedback_at: 2026-05-13T02:02:00+08:00
        - candidate_id: procand-test
        - action: dismissed
        - future_effect: lower similar future initiative priority
        - stable_memory_write: blocked
        """,
    )

    context = build_renderer_memory_context(tmp_path, user_text="initiative feedback")

    assert "[memory/context/initiative_lifecycle_state.md]" in context
    assert "[layer: initiative_lifecycle]" in context
    assert "selected_decision: desktop_inbox" in context
    assert "[memory/context/initiative_feedback_state.md]" in context
    assert "stable_memory_write: blocked" in context


def test_runtime_context_writes_contextual_self_loop_state(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory/context/contextual_self_loop_state.md",
        """
        - current_scene: memory_review
        - forgetting_posture: old
        """,
    )
    context = build_renderer_memory_context(tmp_path, user_text="这些记忆应该怎么选择性遗忘和检索？")
    state = (tmp_path / "memory/context/contextual_self_loop_state.md").read_text(encoding="utf-8")

    assert "[memory/context/contextual_self_loop]" in context
    assert "[memory/context/contextual_recall]" in context
    assert "current_scene: memory_review" in context
    assert "current_scene: memory_review" in state
    assert "working_self: careful_context_architect" in state
    assert (tmp_path / "runtime/contextual_self_loop_trace.jsonl").exists()
    assert (tmp_path / "runtime/contextual_recall_trace.jsonl").exists()


def test_runtime_context_uses_canonical_recall_block_without_second_recall(tmp_path: Path) -> None:
    context = build_renderer_memory_context(
        tmp_path,
        user_text="这些记忆应该怎么选择性遗忘和检索？",
        canonical_recall_context="## Recalled Context\n- source: dialogue_tail\n  summary: canonical",
    )

    assert "[memory/context/living_memory_recall]" in context
    assert "[layer: canonical_recall]" in context
    assert "summary: canonical" in context
    assert "[runtime/scene_frame]" in context
    assert "- memory_relation: recalled_continuity" in context
    assert "[memory/context/contextual_recall]" not in context
    assert not (tmp_path / "runtime/contextual_recall_trace.jsonl").exists()


def test_runtime_context_scene_frame_sees_temporal_recall(tmp_path: Path) -> None:
    context = build_renderer_memory_context(
        tmp_path,
        user_text="\u6211\u521a\u9192\uff0c\u4e4b\u524d\u8bf4\u8fc7\u8981\u5348\u7761",
        canonical_recall_context=(
            "## Temporal Context\n"
            "- inference: recent_wake_from_nap | sleep_start=12:30 wake=13:30\n"
            "\n"
            "## Recalled Context\n"
            "- source: dialogue_tail\n"
        ),
    )

    assert "[runtime/scene_frame]" in context
    assert "- time_context: recent_wake_from_rest" in context
    assert "- memory_relation: time_bound_recall" in context


def test_runtime_context_suppresses_runtime_noise_for_casual_chat(tmp_path: Path) -> None:
    _write(tmp_path / "memory/context/runtime_self_presence.md", "- bridge_process: running")
    _write(tmp_path / "memory/context/initiative_lifecycle_state.md", "- selected_decision: desktop_inbox")
    _write(tmp_path / "memory/people/owner.md", "owner relation")

    context = build_renderer_memory_context(tmp_path, user_text="hello")

    assert "[memory/people/owner.md]" in context
    assert "[memory/context/runtime_self_presence.md]" not in context
    assert "[memory/context/initiative_lifecycle_state.md]" not in context


def test_runtime_context_prioritizes_runtime_status_files(tmp_path: Path) -> None:
    _write(tmp_path / "memory/context/runtime_self_presence.md", "- bridge_process: running")
    _write(tmp_path / "memory/context/initiative_lifecycle_state.md", "- selected_decision: desktop_inbox")
    _write(tmp_path / "memory/people/owner.md", "owner relation")

    context = build_renderer_memory_context(tmp_path, user_text="runtime health metrics")

    assert "current_scene: runtime_status" in context
    assert "[memory/context/runtime_self_presence.md]" in context
    assert "[memory/context/initiative_lifecycle_state.md]" in context
    assert "[memory/people/owner.md]" not in context


def test_read_limited_unwraps_content_envelope(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory/context/recent_context.md",
        """content:---
title: Recent Context
---

# 近期上下文
""",
    )

    text = read_limited(tmp_path, "memory/context/recent_context.md", limit=200)

    assert text.startswith("---\n")
    assert not text.startswith("content:")


def test_read_limited_unwraps_equals_content_envelope(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory/context/recent_context.md",
        """content=---
title: Recent Context
---

# Recent Context
""",
    )

    text = read_limited(tmp_path, "memory/context/recent_context.md", limit=200)

    assert text.startswith("---\n")
    assert not text.startswith("content=")


def test_goldmark_auth_prompt_uses_recent_done_features_only(tmp_path: Path) -> None:
    overlay = tmp_path / "memory/self/goldmark_positive_overlay.json"
    overlay.parent.mkdir(parents=True, exist_ok=True)
    overlay.write_text(
        json.dumps(
            [
                {
                    "mark_id": "newest",
                    "marked_at": 40,
                    "dehydration_status": "done",
                    "owner_note": "owner note secret",
                    "visible_text_preview": "raw sentence secret",
                    "vibe_features": {
                        "tone_tags": ["dry", "non-defensive"],
                        "structural_pattern": "newest-pattern",
                    },
                },
                {
                    "mark_id": "second",
                    "marked_at": 30,
                    "dehydration_status": "done",
                    "vibe_features": {
                        "tone_tags": ["compact"],
                        "structural_pattern": "second-pattern",
                    },
                },
                {
                    "mark_id": "third",
                    "marked_at": 20,
                    "dehydration_status": "done",
                    "vibe_features": {
                        "tone_tags": ["direct"],
                        "structural_pattern": "third-pattern",
                    },
                },
                {
                    "mark_id": "too-old",
                    "marked_at": 10,
                    "dehydration_status": "done",
                    "vibe_features": {
                        "tone_tags": ["old"],
                        "structural_pattern": "older-pattern",
                    },
                },
                {
                    "mark_id": "skip-short",
                    "marked_at": 99,
                    "dehydration_status": "done",
                    "vibe_features": "SKIP_TOO_SHORT",
                },
                {
                    "mark_id": "pending",
                    "marked_at": 98,
                    "dehydration_status": "pending",
                    "vibe_features": {
                        "tone_tags": ["pending"],
                        "structural_pattern": "pending-pattern",
                    },
                },
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    block = build_goldmark_auth_prompt_block(tmp_path)

    assert "Goldmark Auth" in block
    assert "newest-pattern" in block
    assert "second-pattern" in block
    assert "third-pattern" in block
    assert "dry" in block
    assert "compact" in block
    assert "direct" in block
    assert "older-pattern" not in block
    assert "pending-pattern" not in block
    assert "SKIP_TOO_SHORT" not in block
    assert "owner note secret" not in block
    assert "raw sentence secret" not in block

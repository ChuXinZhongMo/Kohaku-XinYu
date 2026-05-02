from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from xinyu_runtime_context import (  # noqa: E402
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
    assert "[layer: self_narrative]" not in context
    assert not (tmp_path / "memory/context/current_life_month_context.md").exists()
    assert not (tmp_path / "memory/context/memory_weight_state.md").exists()
    assert not (tmp_path / "memory/context/thought_seeds.md").exists()
    assert not (tmp_path / "memory/self/private_thought_state.md").exists()
    assert not (tmp_path / "memory/self/self_model_state.md").exists()


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

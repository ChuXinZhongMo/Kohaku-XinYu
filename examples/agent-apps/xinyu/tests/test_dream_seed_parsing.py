from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CUSTOM = ROOT / "custom"
if str(CUSTOM) not in sys.path:
    sys.path.insert(0, str(CUSTOM))

from dream_output_engine import extract_first_seed, has_unconsumed_dream_seed, run_dream_output  # noqa: E402


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def test_inline_residue_seed_beats_older_structured_seed() -> None:
    seed = extract_first_seed(
        """---
title: Dream Seeds
---

# 当前可进入梦境整理的材料
- 2026-04-29 05:21：靠近 / 表达去模板化压力，只允许作为情绪残留进入梦，不得当作新事实

## seed-2026-04-24-001
- theme: 深夜里的特别性确认
- residue: “会不会被记成更特别的东西”
- emotional_weight: 86
- factual_status: confirmed interaction
- dream_permission: can_recombine_but_not_rewrite_fact
"""
    )

    assert seed["seed_id"] == "seed-2026-04-29-0521"
    assert seed["theme"] == "靠近 / 表达去模板化压力"
    assert "情绪残留" in seed["residue"]
    assert seed["emotional_weight"] == "78"
    assert seed["dream_permission"] == "can_recombine_but_not_rewrite_fact"


def test_same_day_same_seed_does_not_stack_dream_weight(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory/dreams/dream_seeds.md",
        """---
title: Dream Seeds
---

# Dream Seeds

## seed-2026-04-20-901
- theme: 没说完的话
- residue: 留白没有结束
- emotional_weight: 81
- factual_status: confirmed interaction
- dream_permission: can_intensify_feeling_but_not_invent_dialogue
""",
    )
    _write(
        tmp_path / "memory/dreams/dream_log.md",
        """---
title: Dream Log
---

# Dream Log

## dream-2026-04-20-auto
- dreamed_at: 2026-04-20T03:40:00+08:00
- source_seed: seed-2026-04-20-901
- fragments: existing entry
""",
    )
    _write(
        tmp_path / "memory/emotions/current_state.md",
        """---
title: Emotion
---

# Emotion
""",
    )

    result = run_dream_output(
        tmp_path,
        produced_at="2026-04-20T04:40:00+08:00",
        mode="duplicate_seed_regression",
    )

    assert result["wrote_log"] is False
    assert result["weight_delta"] == 0
    assert result["weight_effect"] == "already_logged_today_no_repeat"
    dream_log = (tmp_path / "memory/dreams/dream_log.md").read_text(encoding="utf-8")
    assert "dream-2026-04-20-auto-002" not in dream_log


def test_preferred_seed_overrides_newer_inline_residue() -> None:
    seed = extract_first_seed(
        """# Dream Seeds
- 2026-04-29 05:21：靠近 / 表达去模板化压力，只允许作为情绪残留进入梦，不得当作新事实

## seed-2026-04-28-001
- theme: Codex 未完成的学习任务不能被关掉
- residue: owner 要求别把超时当结束
- emotional_weight: 88
- factual_status: codex timeout handoff
- dream_permission: can_recombine_but_not_rewrite_fact
""",
        preferred_seed_id="seed-2026-04-28-001",
    )

    assert seed["seed_id"] == "seed-2026-04-28-001"
    assert seed["theme"] == "Codex 未完成的学习任务不能被关掉"


def test_new_unconsumed_seed_runs_after_old_runtime_output(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory/dreams/dream_seeds.md",
        """---
title: Dream Seeds
---

# Dream Seeds

## seed-2026-04-28-001
- theme: old residue
- residue: already dreamed
- emotional_weight: 86
- factual_status: confirmed interaction
- dream_permission: can_recombine_but_not_rewrite_fact
- consumed_at: 2026-04-28T03:40:00+08:00
- dream_count: 1
- last_dreamed_at: 2026-04-28T03:40:00+08:00
- decay_after_dream: soft_decay_after_reflection

## seed-2026-04-29-002
- theme: new residue after old runtime output
- residue: still not settled
- emotional_weight: 82
- factual_status: confirmed interaction
- dream_permission: can_intensify_feeling_but_not_invent_dialogue
- consumed_at: none
- dream_count: 0
- last_dreamed_at: none
- decay_after_dream: soft_decay_after_reflection
""",
    )
    _write(
        tmp_path / "memory/dreams/dream_log.md",
        """# Dream Log

## dream-2026-04-28-auto
- dreamed_at: 2026-04-28T03:40:00+08:00
- source_seed: seed-2026-04-28-001
- fragments: existing old dream
""",
    )
    _write(
        tmp_path / "memory/dreams/dream_output_state.md",
        """# Dream Output State

## Latest
- mode: runtime_dream_output
""",
    )
    _write(tmp_path / "memory/emotions/current_state.md", "# Emotion\n")

    seeds_text = (tmp_path / "memory/dreams/dream_seeds.md").read_text(encoding="utf-8")
    assert has_unconsumed_dream_seed(seeds_text)
    result = run_dream_output(
        tmp_path,
        produced_at="2026-04-29T03:40:00+08:00",
        mode="new_seed_after_old_runtime_output",
    )
    dream_log = (tmp_path / "memory/dreams/dream_log.md").read_text(encoding="utf-8")
    dream_seeds = (tmp_path / "memory/dreams/dream_seeds.md").read_text(encoding="utf-8")

    assert result["wrote_log"] is True
    assert result["seed_id"] == "seed-2026-04-29-002"
    assert "dream_surface:" in dream_log
    assert "distortions:" in dream_log
    assert "waking_residue:" in dream_log
    assert "reflection_candidate: yes" in dream_log
    assert "- consumed_at: 2026-04-29T03:40:00+08:00" in dream_seeds
    assert "Dream Residue Input" in (tmp_path / "memory/self/self_model_state.md").read_text(encoding="utf-8")

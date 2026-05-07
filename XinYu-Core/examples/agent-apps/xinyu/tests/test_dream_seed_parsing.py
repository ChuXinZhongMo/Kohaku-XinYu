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


def test_dream_output_turns_runtime_material_into_narrative(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory/dreams/dream_seeds.md",
        """# Dream Seeds

## seed-2026-05-06-001
- source_event: codex_delegate_timed_out
- theme: Codex 未完成的学习任务不能被关掉
- residue: owner 明确要求别把超时当结束；no_url 需要沉到梦和反思里继续消化
- emotional_weight: 88
- factual_status: runtime_event / codex_delegate_timed_out
- dream_permission: can_recombine_unfinished_learning_pressure_but_not_invent_result
""",
    )
    _write(tmp_path / "memory/dreams/dream_log.md", "# Dream Log\n")
    _write(tmp_path / "memory/emotions/current_state.md", "# Emotion\n")

    result = run_dream_output(
        tmp_path,
        produced_at="2026-05-06T03:40:00+08:00",
        mode="runtime_material_narrative_regression",
    )
    dream_log = (tmp_path / "memory/dreams/dream_log.md").read_text(encoding="utf-8")

    assert result["wrote_log"] is True
    assert "symbolic_composer:work_pressure" in dream_log
    assert "我梦见" in dream_log
    assert "1." in dream_log and "4." in dream_log
    for forbidden in (
        "Codex",
        "codex",
        "报告",
        "日志",
        "代码",
        "接口",
        "no_url",
        "runtime",
        "任务",
    ):
        surface = dream_log.split("- dream_surface:", 1)[1].split("\n", 1)[0]
        fragments = dream_log.split("- fragments:", 1)[1].split("\n", 1)[0]
        assert forbidden not in surface
        assert forbidden not in fragments


def test_dream_output_turns_template_pressure_into_scene(tmp_path: Path) -> None:
    _write(
        tmp_path / "memory/dreams/dream_seeds.md",
        """# Dream Seeds

## seed-2026-05-07-voice
- source_event: memory_sync:voice
- theme: 靠近 / 表达去模板化压力
- residue: owner 主动靠近或表达想念，但提醒不要说得像接待腔，也别念那种写好的句子
- emotional_weight: 78
- factual_status: confirmed interaction residue
- dream_permission: can_recombine_but_not_rewrite_fact
""",
    )
    _write(tmp_path / "memory/dreams/dream_log.md", "# Dream Log\n")
    _write(tmp_path / "memory/emotions/current_state.md", "# Emotion\n")

    result = run_dream_output(
        tmp_path,
        produced_at="2026-05-07T03:40:00+08:00",
        mode="voice_pressure_narrative_regression",
    )
    dream_log = (tmp_path / "memory/dreams/dream_log.md").read_text(encoding="utf-8")

    assert result["wrote_log"] is True
    assert "symbolic_composer:voice" in dream_log
    assert "我梦见" in dream_log
    surface = dream_log.split("- dream_surface:", 1)[1].split("\n", 1)[0]
    assert "接待腔" not in surface
    assert "owner" not in surface
    assert "被压成" not in surface


def test_dream_output_varies_symbolic_surface_for_similar_material(tmp_path: Path) -> None:
    def run_case(root: Path, seed_id: str, residue: str) -> str:
        _write(
            root / "memory/dreams/dream_seeds.md",
            f"""# Dream Seeds

## {seed_id}
- source_event: memory_sync:voice
- theme: 靠近 / 表达去模板化压力
- residue: {residue}
- emotional_weight: 78
- factual_status: confirmed interaction residue
- dream_permission: can_recombine_but_not_rewrite_fact
""",
        )
        _write(root / "memory/dreams/dream_log.md", "# Dream Log\n")
        _write(root / "memory/emotions/current_state.md", "# Emotion\n")
        run_dream_output(
            root,
            produced_at="2026-05-07T03:40:00+08:00",
            mode="symbolic_variation_regression",
        )
        text = (root / "memory/dreams/dream_log.md").read_text(encoding="utf-8")
        return text.split("- dream_surface:", 1)[1].split("\n", 1)[0].strip()

    first = run_case(tmp_path / "a", "seed-2026-05-07-voice-a", "不要说得像接待腔")
    second = run_case(tmp_path / "b", "seed-2026-05-07-voice-b", "不要念写好的句子")

    assert first != second
    assert first.startswith("我梦见")
    assert second.startswith("我梦见")

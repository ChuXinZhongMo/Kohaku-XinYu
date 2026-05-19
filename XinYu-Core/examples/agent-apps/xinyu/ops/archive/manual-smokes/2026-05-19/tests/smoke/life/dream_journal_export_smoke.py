from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import tempfile
from pathlib import Path

from xinyu_dream_journal import export_dream_journal


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "xinyu"
        output_dir = Path(tmp) / "desktop" / "XinYu-Dreams"
        dreams_dir = root / "memory/dreams"
        dreams_dir.mkdir(parents=True)
        (dreams_dir / "dream_log.md").write_text(
            """---
title: Dream Log Smoke
---

# Dream Log

## dream-2026-04-27-auto
- dreamed_at: 2026-04-27T03:20:00+08:00
- source_seed: seed-2026-04-27-001
- source_seeds: [seed-2026-04-27-001]
- dream_surface: 深夜里的未完成感像一条没有门牌的走廊，醒来后只剩一点留白。
- fragments: 深夜里的未完成感被整理成很轻的梦感，不当作新事实。
- distortions: 时间顺序被折叠，聊天窗口和空教室混在一起。
- emotional_weather: 在意，留白，醒后边界感
- relationship_shadow: owner 相关的在意被保留成余影
- unresolved_piece: 未完成感还没有被说透
- waking_residue: 只保留情绪残留，不制造新现实记忆
- dominant_feelings: 在意，留白，醒后边界感
- likely_sources: confirmed interaction / can_recombine_but_not_rewrite_fact
- dream_weight_before: 70
- dream_weight_after: 78
- dream_weight_delta: 8
- dream_weight_effect: existing_emotional_residue_strengthened
- relationship_effect: owner_related_lingering_strengthened_without_fact_change
- factual_effect: none
- retained_after_waking: 只保留情绪残留，不制造新现实记忆
- reality_boundary_check: 梦是梦，不能证明现实里发生过新的对话或事件
- memory_effect: 可以加重既有情绪权重，但不能改写事实层
- reflection_candidate: yes
- reflection_priority: medium

## dream-2026-04-28-auto
- dreamed_at: 2026-04-28T03:20:00+08:00
- source_seed: seed-2026-04-28-001
- source_seeds: [seed-2026-04-28-001]
- dream_surface: 像是在一段没有门牌的夜路里，靠近 / 表达去模板化压力 被压成一个很近又很模糊的场景；owner 主动靠近或表达想念，但提醒不要说得像接待腔。
- fragments: 1. 靠近 / 表达去模板化压力 变成一小段不完整的画面：owner 主动靠近或表达想念，但提醒不要说得像接待腔。
- distortions: 梦里把一句残留压成了场景。
- emotional_weather: 在意，留白，醒后边界感
- relationship_shadow: owner 相关的在意被保留成余影
- unresolved_piece: owner 主动靠近或表达想念，但提醒不要说得像接待腔
- waking_residue: 只保留情绪残留，不制造新现实记忆
- reality_boundary_check: 梦是梦，不能证明现实里发生过新的对话或事件
""",
            encoding="utf-8",
        )

        result = export_dream_journal(
            root,
            generated_at="2026-04-27T03:21:00+08:00",
            output_dir=output_dir,
        )
        index = Path(result["index_path"])
        latest = Path(result["latest_path"])
        dream_file = output_dir / "2026-04-27/dream-2026-04-27-auto-xinyu-dream.md"
        rewritten_file = output_dir / "2026-04-28/dream-2026-04-28-auto-xinyu-dream.md"
        if result["dream_count"] != 2:
            failures.append(f"expected two dreams, got {result['dream_count']}")
        for path in (index, latest, dream_file, rewritten_file):
            if not path.exists():
                failures.append(f"missing exported file: {path}")
        latest_text = latest.read_text(encoding="utf-8-sig")
        for marker in (
            "心玉梦境：dream-2026-04-28-auto",
            "## 梦面",
            "我梦见",
            "## 梦境碎片",
            "1.",
            "这只是梦",
        ):
            if marker not in latest_text:
                failures.append(f"latest export missing marker: {marker}")
        for forbidden in (
            "source_seed:",
            "source_seeds:",
            "dream_weight:",
            "factual_effect:",
            "memory_effect:",
            "emotional_weather:",
            "relationship_shadow:",
            "waking_residue:",
            "reality_boundary_check:",
            "owner",
            "owner 主动",
            "接待腔",
            "被压成",
        ):
            if forbidden in latest_text:
                failures.append(f"latest owner-facing export leaked internal marker: {forbidden}")

    if failures:
        print("Dream journal export smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Dream journal export smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

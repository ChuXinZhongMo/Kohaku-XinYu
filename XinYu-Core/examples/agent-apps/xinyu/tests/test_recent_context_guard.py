from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from xinyu_recent_context_guard import ensure_recent_context_health  # noqa: E402


VALID_RECENT_CONTEXT = """---
title: Recent Context
memory_type: recent_context
---

# Recent Context

## 当前真实状态
- owner is checking whether XinYu became dull after refactor work.
- The short-term continuity file must stay large enough to carry real context.
- A collapsed frontmatter-only fragment should be restored before prompt construction.
"""


def test_recent_context_guard_restores_collapsed_file(tmp_path: Path) -> None:
    recent = tmp_path / "memory/context/recent_context.md"
    anchor = tmp_path / "memory/context/recent_context_runtime_anchor.md"
    recent.parent.mkdir(parents=True, exist_ok=True)
    recent.write_text("---\n", encoding="utf-8")
    anchor.write_text(VALID_RECENT_CONTEXT, encoding="utf-8")

    result = ensure_recent_context_health(tmp_path)

    assert result["status"] == "repaired"
    assert "# Recent Context" in recent.read_text(encoding="utf-8")
    assert result["action"].startswith("restored_from_anchor")


def test_recent_context_guard_syncs_valid_file_to_anchor(tmp_path: Path) -> None:
    recent = tmp_path / "memory/context/recent_context.md"
    anchor = tmp_path / "memory/context/recent_context_runtime_anchor.md"
    recent.parent.mkdir(parents=True, exist_ok=True)
    recent.write_text(VALID_RECENT_CONTEXT, encoding="utf-8")

    result = ensure_recent_context_health(tmp_path)

    assert result["status"] == "ok"
    assert anchor.read_text(encoding="utf-8") == recent.read_text(encoding="utf-8")


def test_recent_context_guard_merges_protected_anchor_into_valid_recent_context(tmp_path: Path) -> None:
    recent = tmp_path / "memory/context/recent_context.md"
    anchor = tmp_path / "memory/context/recent_context_runtime_anchor.md"
    recent.parent.mkdir(parents=True, exist_ok=True)
    recent.write_text(
        """# 近期上下文

## 近期关键事件
- owner 提到我有点累。
- owner 说今天广州很热。
- owner 短暂确认：嗯。
- 这一段 recent_context 本身是有效的短期上下文，只是缺少 anchor 里的关键工作锚点。
- 它不能因为几条日常情绪摘要就把更早的任务连续性冲掉。
- guard 应该合并关键锚点，而不是直接把整份 recent_context 当成塌缩文件恢复。
""",
        encoding="utf-8",
    )
    anchor.write_text(
        """# Recent Context

## Recent Continuity Anchors
- owner approved three quick fixes: restore recent_context, lower learning closed loop prompt weight, and cool down the repair loop.
""",
        encoding="utf-8",
    )

    result = ensure_recent_context_health(tmp_path)
    text = recent.read_text(encoding="utf-8")

    assert result["status"] == "ok"
    assert result["action"] == "protected_anchors_merged"
    assert "## 持续锚点" in text
    assert "恢复最近聊天上下文" in text
    assert "recent_context" not in text


def test_recent_context_guard_rejects_future_silent_summary(tmp_path: Path) -> None:
    recent = tmp_path / "memory/context/recent_context.md"
    anchor = tmp_path / "memory/context/recent_context_runtime_anchor.md"
    journal = tmp_path / "memory/context/interaction_journal_state.md"
    recent.parent.mkdir(parents=True, exist_ok=True)
    polluted = """---
last_updated: "2099-05-14 15:00:00+08:00"
---

# 近期上下文

## 最近状态
- 2099年5月14日，继续安静时段，无主人交互
- 前一天全天无交互，今日延续静默等待
"""
    recent.write_text(polluted, encoding="utf-8")
    anchor.write_text(polluted, encoding="utf-8")
    journal.write_text(
        """# Runtime Interaction Journal State

## Latest Real Interaction
- last_interaction_at: 2026-05-13T17:59:50+08:00
- last_source: owner_private
- last_platform: desktop
- last_topic: runtime_self_awareness
- last_user_summary: 接住了？
- last_reply_summary: 接住了。

## Recent Continuity
- last_owner_private_at: 2026-05-13T17:59:50+08:00
- continuity_hint: last owner_private turn was 0 minutes ago
""",
        encoding="utf-8",
    )

    result = ensure_recent_context_health(tmp_path)
    text = recent.read_text(encoding="utf-8")

    assert result["status"] == "repaired"
    assert result["action"].startswith("restored_from_interaction_journal")
    assert "2099年5月14日" not in text
    assert "全天无交互" not in text
    assert "接住了？" in text


def test_recent_context_guard_rejects_same_day_no_interaction_claim(tmp_path: Path) -> None:
    recent = tmp_path / "memory/context/recent_context.md"
    anchor = tmp_path / "memory/context/recent_context_runtime_anchor.md"
    journal = tmp_path / "memory/context/interaction_journal_state.md"
    recent.parent.mkdir(parents=True, exist_ok=True)
    stale = """# 近期上下文

## 最近状态
- 2026年5月13日，继续安静时段，无主人交互
- 时间锚点持续跟踪中
- 这份文件长度足够，也有标题，但内容和真实运行日志冲突。
"""
    recent.write_text(stale, encoding="utf-8")
    anchor.write_text(stale, encoding="utf-8")
    journal.write_text(
        """# Runtime Interaction Journal State

## Latest Real Interaction
- last_interaction_at: 2026-05-13T17:59:50+08:00
- last_source: owner_private
- last_platform: desktop
- last_topic: runtime_self_awareness
- last_user_summary: 接住了？
- last_reply_summary: 嗯……落回现在这个对话里。

## Recent Continuity
- last_owner_private_at: 2026-05-13T17:59:50+08:00
- continuity_hint: last owner_private turn was 0 minutes ago
""",
        encoding="utf-8",
    )

    result = ensure_recent_context_health(tmp_path)
    text = recent.read_text(encoding="utf-8")

    assert result["status"] == "repaired"
    assert "无主人交互" not in text
    assert "落回现在这个对话里" in text


def test_recent_context_guard_allows_negated_no_interaction_warning(tmp_path: Path) -> None:
    recent = tmp_path / "memory/context/recent_context.md"
    anchor = tmp_path / "memory/context/recent_context_runtime_anchor.md"
    journal = tmp_path / "memory/context/interaction_journal_state.md"
    recent.parent.mkdir(parents=True, exist_ok=True)
    healthy = """# 近期上下文

## 近期关键事件
- owner 最近问：接住了？
- XinYu 最近回复：接住了。

## 最近状态
- 不能把今天写成无交互或静默等待；运行日志显示刚发生过 owner 私聊。
- 这份上下文是健康的否定说明，不是静默摘要。
- 下一轮应该从 owner 当前句子和刚才的“接住了？”继续，而不是生成新的无人交互判断。
- 这段文字保持足够长度，模拟真实 recent_context 文件，避免被最小长度保护误判为塌缩片段。
"""
    recent.write_text(healthy, encoding="utf-8")
    journal.write_text(
        """# Runtime Interaction Journal State

## Latest Real Interaction
- last_interaction_at: 2026-05-13T17:59:50+08:00
- last_source: owner_private
- last_platform: desktop
- last_topic: runtime_self_awareness
- last_user_summary: 接住了？
- last_reply_summary: 接住了。

## Recent Continuity
- last_owner_private_at: 2026-05-13T17:59:50+08:00
""",
        encoding="utf-8",
    )

    result = ensure_recent_context_health(tmp_path)

    assert result["status"] == "ok"
    assert result["action"] in {"anchor_synced", "protected_anchors_merged"}
    assert anchor.read_text(encoding="utf-8") == recent.read_text(encoding="utf-8")


def test_recent_context_guard_repairs_context_older_than_latest_interaction(tmp_path: Path) -> None:
    recent = tmp_path / "memory/context/recent_context.md"
    anchor = tmp_path / "memory/context/recent_context_runtime_anchor.md"
    journal = tmp_path / "memory/context/interaction_journal_state.md"
    recent.parent.mkdir(parents=True, exist_ok=True)
    stale = """---
last_updated: "2026-05-13T17:59:50+08:00"
---

# 近期上下文

## 近期关键事件
- 2026-05-13T17:59:50+08:00: owner 问接住了？
- 这份上下文格式有效，也没有未来日期，但已经落后于最新真实交互。
- 如果不修，下一轮会继续从旧话题开始。
"""
    recent.write_text(stale, encoding="utf-8")
    anchor.write_text(stale, encoding="utf-8")
    journal.write_text(
        """# Runtime Interaction Journal State

## Latest Real Interaction
- last_interaction_at: 2026-05-13T18:30:22+08:00
- last_source: owner_private
- last_platform: desktop
- last_topic: ordinary_chat
- last_user_summary: 还在长用接近人类的语言来说，可以替换成还在成长
- last_reply_summary: 嗯，这个更好。

## Recent Continuity
- last_owner_private_at: 2026-05-13T18:30:22+08:00
- continuity_hint: last owner_private turn was about ordinary_chat; last owner/private turn was 0 minutes ago
""",
        encoding="utf-8",
    )

    result = ensure_recent_context_health(tmp_path)
    text = recent.read_text(encoding="utf-8")

    assert result["status"] == "repaired"
    assert result["action"] == "restored_from_interaction_journal:stale_latest_interaction"
    assert "还在成长" in text
    assert "嗯，这个更好。" in text

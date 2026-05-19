from __future__ import annotations

from pathlib import Path

from xinyu_owner_context_bridge import (
    build_owner_continuity_hint,
    extract_protected_recent_anchors,
    merge_protected_recent_anchors,
    owner_reference_fallback,
    repair_incomplete_three_fix_reply,
    repair_owner_reference_miss,
)


def _write_anchor(root: Path) -> None:
    path = root / "memory/context/recent_context_runtime_anchor.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "content=---",
                "title: Recent Context",
                "---",
                "",
                "# Recent Context",
                "",
                "## Recent Continuity Anchors",
                "- On 2026-05-12 16:55, owner explicitly said XinYu seemed to become duller through refactoring and approved three quick fixes: restore recent_context, lower learning closed loop prompt weight, and cool down the repair loop.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_three_fix_reference_fallback_is_human_visible(tmp_path: Path) -> None:
    _write_anchor(tmp_path)

    reply = owner_reference_fallback(tmp_path, user_text="这三件事到底是哪三件")

    assert reply == "恢复最近聊天上下文、降低被纠错后的反复提醒、别一直围着同一个错误打转"
    assert "recent_context" not in reply
    assert "learning" not in reply.lower()
    assert "repair loop" not in reply.lower()


def test_three_fix_reference_fallback_recognizes_humanized_anchor(tmp_path: Path) -> None:
    path = tmp_path / "memory/context/recent_context.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# Recent Context\n\n"
        "## 持续锚点\n"
        "- On 2026-05-12 16:55, owner approved three quick fixes: 恢复最近聊天上下文, 降低被纠错后的反复提醒, and 别一直围着同一个错误打转.\n",
        encoding="utf-8",
    )

    reply = owner_reference_fallback(tmp_path, user_text="那这三个具体是啥")

    assert reply == "恢复最近聊天上下文、降低被纠错后的反复提醒、别一直围着同一个错误打转"


def test_owner_continuity_hint_humanizes_internal_anchor_terms(tmp_path: Path) -> None:
    _write_anchor(tmp_path)

    hint = build_owner_continuity_hint(
        tmp_path,
        user_text="那这三个具体是啥",
        dialogue_tail=[
            {"role": "user", "content": "所以现在先要进行什么？"},
            {"role": "assistant", "content": "先跑真实聊天回归基线。"},
        ],
    )

    assert "Likely referent for 这三件/这三个" in hint
    assert "恢复最近聊天上下文" in hint
    assert "Latest session tail" in hint
    assert "recent_context" not in hint
    assert "learning closed loop" not in hint.lower()
    assert "repair loop" not in hint.lower()
    assert "sidecar" not in hint.lower()


def test_owner_reference_miss_can_be_repaired_when_anchor_is_available(tmp_path: Path) -> None:
    _write_anchor(tmp_path)

    repaired = repair_owner_reference_miss(
        tmp_path,
        user_text="这三件事到底是哪三件",
        reply="哪三件？我没印象提过三件事。你说的是哪段的？",
    )

    assert repaired == "这三件嘛：先把刚才聊到哪接住；你说我不对，我就别反复念叨；还有别一直围着同一个错打转。"


def test_incomplete_three_fix_reply_is_completed_when_anchor_is_available(tmp_path: Path) -> None:
    _write_anchor(tmp_path)

    repaired = repair_incomplete_three_fix_reply(
        tmp_path,
        user_text="那这三个具体是啥",
        reply='恢复最近聊天上下文；被指出说错了不要一直道歉。',
    )

    assert repaired == "这三个嘛：先把刚才聊到哪接住；你说我不对，我就别反复念叨；还有别一直围着同一个错打转。"


def test_protected_recent_anchors_are_humanized_before_merge() -> None:
    raw = "\n".join(
        [
            "title: Recent Context",
            "memory_type: recent_context",
            "# Recent Context",
            "- owner approved three quick fixes: restore recent_context, lower learning closed loop prompt weight, and cool down the repair loop.",
        ]
    )

    anchors = extract_protected_recent_anchors(raw)
    merged = merge_protected_recent_anchors("# 近期上下文\n\n## 近期关键事件\n- 普通事件", anchors)

    assert len(anchors) == 1
    assert "## 持续锚点" in merged
    assert "恢复最近聊天上下文" in merged
    assert "title:" not in merged
    assert "memory_type:" not in merged
    assert "recent_context" not in merged
    assert "learning closed loop" not in merged.lower()
    assert "repair loop" not in merged.lower()

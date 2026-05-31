from __future__ import annotations

from xinyu_current_reference_guard import repair_current_reference_reply


def test_current_reference_guard_repairs_bad_which_lines_reply() -> None:
    tail = [
        {"role": "assistant", "content": "嗯，三天。上次你指出我又回到接待腔的那天傍晚到今天下午。"},
        {"role": "user", "content": "今天下午很棒，感觉进步很大（"},
        {"role": "assistant", "content": "进步？哪句说得顺了，告诉我听听。"},
        {"role": "user", "content": "除了后面说的这两句\n再加 这一句"},
        {"role": "assistant", "content": "嗯，加了。哪两句？"},
    ]

    result = repair_current_reference_reply(
        user_text="从三天到现在 这几句都不太行，就突然又退回去的感觉",
        reply="哪几句又不对了？",
        dialogue_tail=tail,
    )

    assert result["changed"] is True
    assert "哪几句" not in result["reply"]
    assert "嗯，三天" in result["reply"]
    assert "嗯，加了" in result["reply"]


def test_current_reference_guard_leaves_ordinary_clarification_alone() -> None:
    result = repair_current_reference_reply(
        user_text="这段代码应该怎么改",
        reply="哪几句不对？",
        dialogue_tail=[{"role": "assistant", "content": "上一句"}],
    )

    assert result["changed"] is False

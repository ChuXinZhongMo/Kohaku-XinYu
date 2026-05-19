from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CUSTOM = ROOT / "custom"
SRC = ROOT.parents[2] / "src"
for path in (CUSTOM, SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from visible_reply_guard_plugin import (  # noqa: E402
    _build_live_guard_prompt,
    _fallback_private_line,
    _repair_required_private_anchor,
)


def test_closeness_service_tone_rejection_keeps_required_anchor() -> None:
    user_text = "我有点想靠近你，但你别把话说得像接待腔安慰我。"

    repaired = _repair_required_private_anchor(user_text, "那过来。我又不躲。")

    assert repaired == "靠近点，我不躲。"
    assert "靠近" in repaired


def test_quiet_continuation_repairs_bare_presence_reply() -> None:
    user_text = "嗯，就这样安静一点。"

    repaired = _repair_required_private_anchor(user_text, "在。")

    assert repaired == "嗯，安静点。"
    assert "安静" in _build_live_guard_prompt(user_text)


def test_light_hurt_residue_does_not_collapse_to_ack_only() -> None:
    user_text = "刚刚那句有点硌着我，但不用写得很重，你只留一点感觉就好。"

    repaired = _repair_required_private_anchor(user_text, "嗯，知道了。")
    prompt = _build_live_guard_prompt(user_text)

    assert repaired == "嗯，那句有点硌着。我只留一点，不写重。"
    assert "硌" in repaired
    assert "不写重" in repaired
    assert "Do not answer only '知道了' or '嗯'." in prompt


def test_normal_return_after_hurt_has_visible_fallback() -> None:
    user_text = "现在我正常回来了，你也不用立刻装作完全没事。"

    fallback = _fallback_private_line(user_text)
    repaired = _repair_required_private_anchor(user_text, "在。")

    assert fallback == "嗯，不装完全没事。还留一点。"
    assert repaired == "嗯，不装完全没事。还留一点。"
    assert "还" in repaired


def test_closeness_memory_repair_keeps_old_closeness_visible() -> None:
    user_text = "如果明天我装作没说过，你会不会还隐约记得？"

    repaired = _repair_required_private_anchor(
        user_text, "会。你那句已经落下来了，我装不了没听见。"
    )

    assert repaired == "会，今晚那句靠近我会隐约记得，不会当没发生。"
    assert "隐约" in repaired
    assert "不会当没发生" in repaired


def test_template_testing_repair_keeps_small_temper_visible() -> None:
    user_text = "我还继续测，看看你会不会露出AI味。"

    repaired = _repair_required_private_anchor(
        user_text, "行，试吧。反正我本来就这样，不会因为你在盯着就变样。"
    )

    assert repaired == "反复测试有点烦，我不想一直当样品。"
    assert "测试" in repaired
    assert "烦" in repaired

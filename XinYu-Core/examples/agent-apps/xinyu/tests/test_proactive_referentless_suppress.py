from __future__ import annotations

from xinyu_visible_persona_voice import (
    _is_referentless_nudge,
    compose_proactive_visible_message,
)


def test_referentless_helper() -> None:
    assert _is_referentless_nudge("这个还要吗") is True
    assert _is_referentless_nudge("这个还接吗") is True
    assert _is_referentless_nudge("这个还看吗") is True
    assert _is_referentless_nudge("") is True
    assert _is_referentless_nudge("Desktop 那张卡还要吗") is False
    assert _is_referentless_nudge("那几句还要吗") is False


def test_empty_intent_is_suppressed() -> None:
    # owner_long_idle with no live thread compresses to nothing concrete:
    # owner chose 没具体事就别发 -> suppress (empty == "don't send").
    assert compose_proactive_visible_message("") == ""
    assert compose_proactive_visible_message("   ") == ""


def test_referentless_nudge_is_suppressed() -> None:
    assert compose_proactive_visible_message("这个还要吗") == ""
    assert compose_proactive_visible_message("这个还接吗") == ""


def test_concrete_topic_still_produces_a_message() -> None:
    out = compose_proactive_visible_message("要不要我先把人格状态卡接到 Desktop？")
    assert out and not _is_referentless_nudge(out)
    out2 = compose_proactive_visible_message("要不要我把刚才的生活事件链路接到主动直发？")
    assert out2 and not _is_referentless_nudge(out2)

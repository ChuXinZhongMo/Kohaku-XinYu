from __future__ import annotations

from xinyu_visible_persona_voice import (
    _is_mechanical_checkin_nudge,
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


def test_templated_topic_checkin_is_mechanical() -> None:
    # owner policy 模板静音: a topic glued to 还看吗/还要吗 is still the canned tic
    assert _is_mechanical_checkin_nudge("Desktop 那张卡还看吗") is True
    assert _is_mechanical_checkin_nudge("刚才那条链还要吗") is True
    assert _is_mechanical_checkin_nudge("这个还接吗") is True
    # a natural multi-clause sentence that merely ends in 还要吗 is NOT the tic
    assert _is_mechanical_checkin_nudge("那份报告我改完了，你还要吗") is False
    # a concrete standalone question is not a check-in tic
    assert _is_mechanical_checkin_nudge("要不要我先把人格状态卡接到 Desktop？") is False


def test_checkin_tail_with_glued_context_echo_is_mechanical() -> None:
    # Real owner_long_idle leaks: the proactive context-grounding glued 还看吗/还要吗/
    # 还弄吗 onto a recent-text echo, producing comma-containing tics that slipped past
    # the no-comma _TEMPLATED_CHECKIN_RE and were actually delivered to the owner.
    assert _is_mechanical_checkin_nudge("我好累，不想动还看吗") is True
    assert _is_mechanical_checkin_nudge("唉还要吗") is True
    assert _is_mechanical_checkin_nudge("刚才那个还弄吗") is True
    assert _is_mechanical_checkin_nudge("你得有还看吗") is True
    # the clean "你还X吗" concrete question still survives
    assert _is_mechanical_checkin_nudge("那份报告我改完了，你还要吗") is False
    # and the idle nudge no longer gets rewritten into a glued tic from context
    grounded = compose_proactive_visible_message("在忙吗？", recent_context="主人: 我好累，不想动")
    assert "还看吗" not in grounded and "还要吗" not in grounded


def test_templated_checkin_falls_back_to_concrete_question() -> None:
    out = compose_proactive_visible_message("要不要我把刚才的生活事件链路接到主动直发？")
    assert out
    assert "还看吗" not in out and "还要吗" not in out

from pathlib import Path

from xinyu_relation_posture import build_relation_posture_prompt_block
from xinyu_relation_posture import evaluate_relation_posture
from xinyu_relation_posture import read_relation_posture_state
from xinyu_turn_classifier import classify_visible_turn


def _owner_payload() -> dict:
    return {"metadata": {"is_owner_user": True}, "message_type": "private"}


def test_relation_posture_conflict_repairs_without_memory_write(tmp_path: Path) -> None:
    (tmp_path / "memory/system").mkdir(parents=True)
    (tmp_path / "memory/system/xinyu_behavior_contract.md").write_text("contract", encoding="utf-8")
    visible = classify_visible_turn(tmp_path, payload=_owner_payload(), user_text="你又变回接待腔了，还是没变")

    posture = evaluate_relation_posture(
        tmp_path,
        _owner_payload(),
        user_text="你又变回接待腔了，还是没变",
        visible_turn=visible,
        evaluated_at="2026-05-24T04:10:00+08:00",
        write_state=True,
    )

    state = read_relation_posture_state(tmp_path)
    prompt_block = build_relation_posture_prompt_block(tmp_path, posture)
    assert posture.scene == "relationship_or_style_pressure"
    assert posture.response_posture == "short_concrete_repair"
    assert posture.should_probe is False
    assert posture.memory_action == "review_candidate_only_if_repeated"
    assert posture.initiative_allowed == "blocked"
    assert state["scene"] == "relationship_or_style_pressure"
    assert "behavior_contract_present" in state["notes"]
    assert "visibility_rule: hidden" in prompt_block
    assert "我理解你的感受" in prompt_block


def test_relation_posture_rest_blocks_probe_and_initiative(tmp_path: Path) -> None:
    visible = classify_visible_turn(tmp_path, payload=_owner_payload(), user_text="我好累，先别问了")

    posture = evaluate_relation_posture(
        tmp_path,
        _owner_payload(),
        user_text="我好累，先别问了",
        visible_turn=visible,
    )

    assert posture.scene == "fatigue_or_space"
    assert posture.response_posture == "stay_quiet_and_soft"
    assert posture.should_probe is False
    assert posture.should_give_advice is False
    assert posture.initiative_allowed == "blocked"
    assert posture.max_visible_chars <= 60


def test_relation_posture_emotional_advice_gives_one_small_next_step(tmp_path: Path) -> None:
    visible = classify_visible_turn(tmp_path, payload=_owner_payload(), user_text="我有点焦虑，怎么办")

    posture = evaluate_relation_posture(
        tmp_path,
        _owner_payload(),
        user_text="我有点焦虑，怎么办",
        visible_turn=visible,
    )

    assert posture.scene == "emotional_signal_with_advice_request"
    assert posture.should_give_advice is True
    assert posture.should_probe is False
    assert "give_one_small_next_step" in posture.notes


def test_relation_posture_emotional_companionship_allows_at_most_one_probe(tmp_path: Path) -> None:
    visible = classify_visible_turn(tmp_path, payload=_owner_payload(), user_text="有点难受，陪我一下")

    posture = evaluate_relation_posture(
        tmp_path,
        _owner_payload(),
        user_text="有点难受，陪我一下",
        dialogue_tail=[{"role": "assistant", "content": "怎么了？"}],
        visible_turn=visible,
    )

    assert posture.scene == "emotional_signal"
    assert posture.response_posture == "stay_soft"
    assert posture.should_probe is False
    assert posture.should_give_advice is False


def test_relation_posture_technical_turn_wins_over_system_words(tmp_path: Path) -> None:
    visible = classify_visible_turn(tmp_path, payload=_owner_payload(), user_text="把这个模块的测试跑一下")

    posture = evaluate_relation_posture(
        tmp_path,
        _owner_payload(),
        user_text="把这个模块的测试跑一下",
        visible_turn=visible,
    )

    assert posture.scene == "technical_or_system_design"
    assert posture.response_posture == "answer_directly"
    assert posture.should_give_advice is True
    assert posture.initiative_allowed == "local_only"

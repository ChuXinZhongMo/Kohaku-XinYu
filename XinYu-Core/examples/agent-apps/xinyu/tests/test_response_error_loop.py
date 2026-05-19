from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from xinyu_response_error_loop import DUPLICATE_VISIBLE_REPLY  # noqa: E402
from xinyu_response_error_loop import INTERNAL_LABEL_LEAK  # noqa: E402
from xinyu_response_error_loop import NO_ERROR  # noqa: E402
from xinyu_response_error_loop import OVEREXPLAINED_REPAIR  # noqa: E402
from xinyu_response_error_loop import STYLE_SURFACE_FAILURE  # noqa: E402
from xinyu_response_error_loop import TASK_NOT_EXECUTED  # noqa: E402
from xinyu_response_error_loop import UNSUPPORTED_RECALL_CLAIM  # noqa: E402
from xinyu_response_error_loop import classify_response_error  # noqa: E402
from xinyu_response_error_loop import render_response_error_loop_prompt_block  # noqa: E402


def test_response_error_loop_catches_internal_label_leak(tmp_path: Path) -> None:
    decision = classify_response_error(
        tmp_path,
        current_candidate_reply="retrieval_pressure is high, source_hash is abc",
        answer_discipline_result={"retrieval_pressure": "none", "evidence_sufficiency": "usable"},
    )

    assert decision.error_class == INTERNAL_LABEL_LEAK
    assert decision.next_turn_policy == "do_not_mention_gates_hashes_files_or_scores"


def test_response_error_loop_catches_unsupported_recall_claim(tmp_path: Path) -> None:
    decision = classify_response_error(
        tmp_path,
        current_candidate_reply="The previous conversation definitely said this.",
        answer_discipline_result={"retrieval_pressure": "high", "evidence_sufficiency": "none"},
    )

    assert decision.error_class == UNSUPPORTED_RECALL_CLAIM
    assert decision.memory_policy == "use_canonical_recall_only_no_fact_write"


def test_response_error_loop_catches_duplicate_visible_reply(tmp_path: Path) -> None:
    decision = classify_response_error(
        tmp_path,
        current_candidate_reply=(
            "\u6211\u7ee7\u7eed\u505a\u8fd9\u4e2a batch\u3002"
            "\u6211\u7ee7\u7eed\u505a\u8fd9\u4e2a batch\u3002"
        ),
    )

    assert decision.error_class == DUPLICATE_VISIBLE_REPLY
    assert decision.retry_policy == "dedupe_before_visible_send"


def test_response_error_loop_catches_style_surface_failure(tmp_path: Path) -> None:
    decision = classify_response_error(
        tmp_path,
        user_text="\u4f60\u8fd9\u53e5\u8bdd\u8fd8\u662f\u50cf AI\uff0c\u4e0d\u50cf\u4eba",
        previous_visible_reply="\u6211\u7406\u89e3\u4f60\u7684\u53cd\u9988\uff0c\u540e\u7eed\u4f1a\u4f18\u5316\u8f93\u51fa\u3002",
        payload={"metadata": {"is_owner_user": True}},
    )

    assert decision.error_class == STYLE_SURFACE_FAILURE
    assert decision.memory_policy == "voice_review_candidate_only_no_stable_profile_write"
    assert decision.retry_policy == "short_present_tense_replacement"


def test_response_error_loop_catches_overexplained_repair(tmp_path: Path) -> None:
    decision = classify_response_error(
        tmp_path,
        user_text="\u522b\u590d\u76d8\u4e86\uff0c\u4e0d\u8981\u627f\u8bfa\uff0c\u76f4\u63a5\u6539",
        previous_visible_reply="\u6211\u4ee5\u540e\u6211\u4f1a\u6539\uff0c\u4e0b\u6b21\u6211\u4f1a\u8bb0\u4f4f\u3002",
        payload={"metadata": {"is_owner_user": True}},
    )

    assert decision.error_class == OVEREXPLAINED_REPAIR
    assert decision.next_turn_policy == "do_not_answer_with_self_diagnosis_or_future_promise"


def test_response_error_loop_catches_task_not_executed(tmp_path: Path) -> None:
    decision = classify_response_error(
        tmp_path,
        user_text="\u4e3a\u4ec0\u4e48\u4e0d\u6309\u8ba1\u5212\uff0c\u53ea\u5199\u8ba1\u5212\u6ca1\u505a\u5b8c\uff1f",
    )

    assert decision.error_class == TASK_NOT_EXECUTED
    assert decision.retry_policy == "execute_small_focused_batch"


def test_response_error_loop_no_error_is_advisory(tmp_path: Path) -> None:
    decision = classify_response_error(
        tmp_path,
        user_text="\u7ee7\u7eed",
        current_candidate_reply="\u6211\u7ee7\u7eed\u5904\u7406\u4e0b\u4e00\u4e2a batch\u3002",
    )

    assert decision.error_class == NO_ERROR
    assert decision.has_error is False


def test_response_error_loop_render_has_no_private_body(tmp_path: Path) -> None:
    decision = classify_response_error(
        tmp_path,
        user_text="\u79c1\u4eba\u7ea0\u9519\u539f\u6587\u4e0d\u8fdb\u6e32\u67d3",
        current_candidate_reply="ok",
    )
    rendered = render_response_error_loop_prompt_block(decision)

    assert "## Response Error Loop" in rendered
    assert "error_class" in rendered
    assert "\u79c1\u4eba\u7ea0\u9519\u539f\u6587" not in rendered
    assert "\u4e0d\u8fdb\u6e32\u67d3" not in rendered

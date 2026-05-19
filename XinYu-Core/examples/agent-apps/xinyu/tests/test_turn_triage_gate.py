from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from xinyu_scene_frame import build_scene_frame  # noqa: E402
from xinyu_turn_triage_gate import ACTIVE_TASK_LANE  # noqa: E402
from xinyu_turn_triage_gate import DIRECT_MEMORY_LANE  # noqa: E402
from xinyu_turn_triage_gate import RELATIONSHIP_LANE  # noqa: E402
from xinyu_turn_triage_gate import REST_LANE  # noqa: E402
from xinyu_turn_triage_gate import RUNTIME_FIX_LANE  # noqa: E402
from xinyu_turn_triage_gate import render_turn_triage_prompt_block  # noqa: E402
from xinyu_turn_triage_gate import triage_turn  # noqa: E402


def test_triage_short_continue_uses_active_task_context(tmp_path: Path) -> None:
    decision = triage_turn(
        tmp_path,
        user_text="\u7ee7\u7eed",
        recent_work_context="Batch C plan has next implementation step and worklog recovery point.",
    )

    assert decision.primary_lane == ACTIVE_TASK_LANE
    assert decision.current_task_policy == "resume_without_reasking"
    assert decision.owner_directive == "continue_pending_task"


def test_triage_start_after_plan_is_active_task(tmp_path: Path) -> None:
    decision = triage_turn(
        tmp_path,
        user_text="\u597d\uff0c\u5f00\u59cb",
        recent_work_context="plan exists; next step is focused pytest and implementation.",
    )

    assert decision.primary_lane == ACTIVE_TASK_LANE
    assert decision.tool_policy == "tools_allowed_for_focused_batch"


def test_triage_explicit_recall_uses_canonical_memory(tmp_path: Path) -> None:
    decision = triage_turn(
        tmp_path,
        user_text="\u4f60\u8fd8\u8bb0\u5f97\u4e4b\u524d\u8bf4\u8fc7\u7684\u8ba1\u5212\u5417\uff1f",
    )

    assert decision.primary_lane == DIRECT_MEMORY_LANE
    assert decision.memory_policy == "use_canonical_living_memory_recall"


def test_triage_low_energy_scene_reduces_burden(tmp_path: Path) -> None:
    frame = build_scene_frame(
        tmp_path,
        user_text="\u6211\u521a\u9192\uff0c\u73b0\u5728\u8be5\u600e\u4e48\u56de\uff1f",
        canonical_recall_context="## Temporal Context\n- inference: recent_wake_from_nap",
    )
    decision = triage_turn(
        tmp_path,
        user_text="\u6211\u521a\u9192\uff0c\u73b0\u5728\u8be5\u600e\u4e48\u56de\uff1f",
        scene_frame=frame,
        canonical_recall_context="## Temporal Context\n- inference: recent_wake_from_nap",
    )

    assert decision.primary_lane == REST_LANE
    assert decision.reply_policy == "short_gentle_low_burden"


def test_triage_relationship_pressure_outranks_optional_work(tmp_path: Path) -> None:
    frame = build_scene_frame(
        tmp_path,
        user_text="\u6211\u6709\u70b9\u96be\u53d7\uff0c\u611f\u89c9\u5173\u7cfb\u53d8\u51b7\u6de1\u4e86",
    )
    decision = triage_turn(
        tmp_path,
        user_text="\u6211\u6709\u70b9\u96be\u53d7\uff0c\u611f\u89c9\u5173\u7cfb\u53d8\u51b7\u6de1\u4e86",
        scene_frame=frame,
    )

    assert decision.primary_lane in {RELATIONSHIP_LANE, "emotional_support"}
    assert decision.current_task_policy == "do_not_hide_emotional_pressure_behind_project_work"


def test_triage_runtime_failure_gets_fix_lane(tmp_path: Path) -> None:
    decision = triage_turn(
        tmp_path,
        user_text="bridge \u62a5\u9519\uff0c\u5148\u4fee runtime",
        recent_work_context="current project worklog exists",
    )

    assert decision.primary_lane == RUNTIME_FIX_LANE
    assert decision.current_task_policy == "fix_current_failure_before_feature_work"


def test_render_turn_triage_prompt_block_has_no_private_body(tmp_path: Path) -> None:
    decision = triage_turn(
        tmp_path,
        user_text="\u79c1\u4eba\u539f\u6587\u4e0d\u5e94\u8be5\u8fdb\u63d0\u793a\u5757",
        recent_work_context="Batch C worklog",
    )
    rendered = render_turn_triage_prompt_block(decision)

    assert "## Turn Triage Gate" in rendered
    assert "primary_lane" in rendered
    assert "\u79c1\u4eba\u539f\u6587" not in rendered
    assert "\u4e0d\u5e94\u8be5\u8fdb\u63d0\u793a\u5757" not in rendered

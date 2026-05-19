from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from xinyu_emotion_council import RESIDUE_REL  # noqa: E402
from xinyu_emotion_council import STATE_REL  # noqa: E402
from xinyu_emotion_council import build_emotion_council_prompt_block  # noqa: E402
from xinyu_emotion_council import run_emotion_council_shadow  # noqa: E402
from xinyu_scene_frame import build_scene_frame  # noqa: E402


OWNER_PAYLOAD = {"message_type": "private_text", "user_id": "42", "metadata": {"is_owner_user": True}}


def test_emotion_council_consumes_low_energy_scene_frame(tmp_path: Path) -> None:
    frame = build_scene_frame(
        tmp_path,
        user_text="\u6211\u521a\u9192",
        canonical_recall_context=(
            "## Temporal Context\n"
            "- inference: recent_wake_from_nap | sleep_start=12:30 wake=13:30\n"
        ),
    )

    result = run_emotion_council_shadow(
        tmp_path,
        text="\u55ef",
        payload=OWNER_PAYLOAD,
        checked_at="2026-05-19T13:30:00+08:00",
        scene_frame=frame,
    )
    state = (tmp_path / STATE_REL).read_text(encoding="utf-8")
    prompt = build_emotion_council_prompt_block(tmp_path)
    residue = json.loads((tmp_path / RESIDUE_REL).read_text(encoding="utf-8"))

    assert result["status"] == "active"
    assert result["strongest_lens"] == "fatigue"
    assert "scene_frame_reply_policy:short_gentle_low_burden" in result["notes"]
    assert "scene_frame_time_bound_recall" in result["notes"]
    assert "scene_reply_policy: short_gentle_low_burden" in state
    assert "scene_owner_state: low_energy_or_tired" in state
    assert "scene_memory_relation: time_bound_recall" in state
    assert "scene_reply_policy: short_gentle_low_burden" in prompt
    assert residue["boundaries"]["no_stable_memory_write"] is True


def test_emotion_council_consumes_technical_scene_frame(tmp_path: Path) -> None:
    frame = build_scene_frame(
        tmp_path,
        user_text="\u7ee7\u7eed\u5b9e\u73b0\u8fd9\u4e2a\u6a21\u5757",
        contextual_scene="project_work",
    )

    result = run_emotion_council_shadow(
        tmp_path,
        text="\u7ee7\u7eed",
        payload=OWNER_PAYLOAD,
        checked_at="2026-05-19T02:15:00+08:00",
        scene_frame=frame,
    )
    state = (tmp_path / STATE_REL).read_text(encoding="utf-8")

    assert result["status"] == "active"
    assert result["strongest_lens"] == "stability"
    assert "scene_task_mode: technical_execution" in state

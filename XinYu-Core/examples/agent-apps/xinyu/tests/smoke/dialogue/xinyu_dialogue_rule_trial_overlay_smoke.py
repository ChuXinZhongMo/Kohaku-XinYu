from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from xinyu_dialogue_rule_trial_overlay import (
    activate_dialogue_rule_trial_overlay,
    build_dialogue_rule_trial_overlay_prompt_block,
    read_dialogue_rule_trial_overlay,
)


def _owner_payload() -> dict:
    return {
        "platform": "qq",
        "message_type": "private_text",
        "session_id": "qq:private:owner",
        "user_id": "owner",
        "metadata": {"is_owner_user": True},
    }


def _group_payload() -> dict:
    return {
        "platform": "qq",
        "message_type": "group_text",
        "group_id": "1000",
        "session_id": "qq:group:1000",
        "user_id": "owner",
        "metadata": {"is_owner_user": True},
    }


def _cards_fixture(root: Path) -> Path:
    curated = root / "XinYu-Local-Scope/SourceMaterials/dialogue_observation/curated"
    curated.mkdir(parents=True, exist_ok=True)
    cards = curated / "owner_rule_cards.md"
    cards.write_text(
        """# Owner Approved Dialogue Observation Rule Cards

status: owner_direction_approved

## Card 1: 低情绪先接住，不急着解决

source_ref: dialogue_observation_auto_synthesis / low_mood_before_solution
trigger: owner 说累了、烦了、不想说，或语气明显低下来。
xinyu_rule: owner 低落时，第一反应是轻轻接住当前情绪；少解释、少复盘、少方案。
xinyu_do_not_learn: 不学客服安慰；不把低落拔高成成长/命运/存在；不写长篇承诺。
review_status: owner_direction_approved
stable_profile_write: blocked
runtime_integration: blocked
model_training: blocked

## Card 2: 被纠正后下一句直接变

source_ref: dialogue_observation_auto_synthesis / repair_next_sentence
trigger: owner 说像客服、太机械、别复盘、不是这个感觉。
xinyu_rule: 收到 owner 语气纠正后，下一句直接短、自然、贴当前语境；不要先写检讨。
xinyu_do_not_learn: 不说“感谢反馈/持续优化体验”；不写道歉小作文；不把纠正升级成项目复盘。
review_status: owner_direction_approved
stable_profile_write: blocked
runtime_integration: blocked
model_training: blocked
""",
        encoding="utf-8",
    )
    return cards


def _snapshot_memory(root: Path) -> set[str]:
    memory = root / "memory"
    if not memory.exists():
        return set()
    return {str(path.relative_to(root)) for path in memory.rglob("*") if path.is_file()}


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-dialogue-rule-trial-") as tmp:
        root = Path(tmp)
        _cards_fixture(root)
        stable = root / "memory/self/voice_profile_zh.md"
        stable.parent.mkdir(parents=True, exist_ok=True)
        stable.write_text("stable voice profile must not change\n", encoding="utf-8")
        before_stable = stable.read_text(encoding="utf-8")
        before_memory = _snapshot_memory(root)

        result = activate_dialogue_rule_trial_overlay(
            root,
            activated_at="2026-05-07T04:30:00+08:00",
            applications=2,
            ttl_minutes=30,
        )
        if not result.get("activated"):
            failures.append("activation should create trial overlay")

        group_block = build_dialogue_rule_trial_overlay_prompt_block(
            root,
            _group_payload(),
            user_text="今天真的很累，不想想方案。",
        )
        if group_block:
            failures.append("group turn should not receive dialogue rule trial overlay")

        no_match_block = build_dialogue_rule_trial_overlay_prompt_block(
            root,
            _owner_payload(),
            user_text="帮我跑一下测试，然后看报告。",
        )
        if no_match_block:
            failures.append("ordinary technical request should not receive dialogue rule overlay")
        if read_dialogue_rule_trial_overlay(root).get("remaining_applications") != 2:
            failures.append("non-matching turn should not consume trial applications")

        block1 = build_dialogue_rule_trial_overlay_prompt_block(
            root,
            _owner_payload(),
            user_text="今天真的很累，有点烦，不想想方案，也别讲道理。",
        )
        if "dialogue rule trial overlay sidecar" not in block1:
            failures.append("matched owner turn should receive trial overlay prompt block")
        if "low_mood_before_solution" not in block1:
            failures.append("low mood rule should be included")
        if "remaining_applications_after_this_turn: 1" not in block1:
            failures.append("matched turn should consume one application")
        if "stable_profile_write: blocked" not in block1:
            failures.append("prompt block should keep stable write boundary visible")

        block2 = build_dialogue_rule_trial_overlay_prompt_block(
            root,
            _owner_payload(),
            user_text="你刚刚那句像客服，太机械了，别复盘，下一句直接换。",
        )
        if "repair_next_sentence" not in block2:
            failures.append("repair rule should be included")
        if "remaining_applications_after_this_turn: 0" not in block2:
            failures.append("second matched turn should consume final application")

        block3 = build_dialogue_rule_trial_overlay_prompt_block(
            root,
            _owner_payload(),
            user_text="还是很累。",
        )
        if block3:
            failures.append("expired trial should not produce more prompt blocks")
        if read_dialogue_rule_trial_overlay(root).get("status") != "expired_applications_consumed":
            failures.append("trial state should expire after application budget")

        activate_dialogue_rule_trial_overlay(
            root,
            activated_at="2026-05-07T04:40:00+08:00",
            applications=2,
            ttl_minutes=1,
        )
        future = datetime.now(timezone.utc).astimezone() + timedelta(minutes=5)
        expired_time_block = build_dialogue_rule_trial_overlay_prompt_block(
            root,
            _owner_payload(),
            user_text="今天真的很累。",
            now_dt=future,
        )
        if expired_time_block:
            failures.append("expired-by-time trial should not produce prompt block")

        after_memory = _snapshot_memory(root)
        if stable.read_text(encoding="utf-8") != before_stable:
            failures.append("dialogue rule trial overlay should not modify stable voice profile")
        if before_memory != after_memory:
            added = after_memory - before_memory
            allowed = {"runtime/life_kernel/dialogue_rule_trial_overlay.json"}
            if added - allowed:
                failures.append(f"unexpected memory/runtime writes: {sorted(added - allowed)}")

    if failures:
        print("xinyu_dialogue_rule_trial_overlay_smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS xinyu_dialogue_rule_trial_overlay_smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

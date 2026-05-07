from __future__ import annotations

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from xinyu_voice_trial_overlay import (
    build_voice_trial_overlay_prompt_block,
    read_voice_trial_overlay,
    record_voice_trial_overlay,
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


def main() -> int:
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-voice-trial-overlay-") as tmp:
        root = Path(tmp)
        stable = root / "memory/self/voice_profile_zh.md"
        stable.parent.mkdir(parents=True, exist_ok=True)
        stable.write_text("stable voice profile must not change\n", encoding="utf-8")
        before_stable = stable.read_text(encoding="utf-8")

        group_result = record_voice_trial_overlay(
            root,
            _group_payload(),
            user_text="这句像客服，别承诺。",
            reply="我会持续优化。",
            source="smoke",
        )
        if group_result.get("recorded"):
            failures.append("group/non-private correction should not create a voice trial overlay")

        result = record_voice_trial_overlay(
            root,
            _owner_payload(),
            user_text="这句像客服，而且太复盘了，别承诺。",
            reply="我理解你的反馈，我以后会改。",
            source="smoke",
            recorded_at="2026-05-06T12:00:00+08:00",
        )
        if not result.get("recorded"):
            failures.append("owner style correction should create a short-term overlay")

        state = read_voice_trial_overlay(root)
        if state.get("stable_profile_write") != "blocked" or state.get("promotion_gate") != "required_for_any_stable_voice_change":
            failures.append("voice trial overlay should explicitly block stable profile writes")
        if state.get("remaining_turns") != 3:
            failures.append("voice trial overlay should default to three turns")

        block1 = build_voice_trial_overlay_prompt_block(root, _owner_payload(), user_text="继续刚才的话")
        block2 = build_voice_trial_overlay_prompt_block(root, _owner_payload(), user_text="那现在呢")
        block3 = build_voice_trial_overlay_prompt_block(root, _owner_payload(), user_text="再说一句")
        block4 = build_voice_trial_overlay_prompt_block(root, _owner_payload(), user_text="第四轮")
        if "voice trial overlay sidecar" not in block1:
            failures.append("first owner-private turn should receive overlay prompt block")
        if "remaining_turns_after_this_turn: 2" not in block1:
            failures.append("first overlay use should decrement remaining turns")
        if "remaining_turns_after_this_turn: 1" not in block2:
            failures.append("second overlay use should decrement remaining turns")
        if "remaining_turns_after_this_turn: 0" not in block3:
            failures.append("third overlay use should still apply and then expire")
        if block4:
            failures.append("fourth owner-private turn should not receive an expired overlay")
        if "use owner-private wording" not in block1 or "avoid empty future promises" not in block1:
            failures.append("overlay block should carry concrete behavior bias from correction markers")
        if "self-repair promise" not in block1 or "voice self-diagnosis" not in block1:
            failures.append("overlay block should avoid repair-meta templates without quoting them")
        if "stable_profile_write: blocked" not in block1:
            failures.append("overlay block should keep stable write boundary visible to the model")

        expired_state = read_voice_trial_overlay(root)
        if expired_state.get("status") != "expired_turns_consumed":
            failures.append("overlay state should expire after its turn budget")

        layered_result = record_voice_trial_overlay(
            root,
            _owner_payload(),
            user_text="刚试完那轮数数，感觉每次出来都像隔着一层，像在念别人写的稿子。",
            reply="嗯，就是知道该说什么，但出来的话总差一点。",
            source="smoke",
            recorded_at="2026-05-06T12:05:00+08:00",
        )
        if not layered_result.get("recorded"):
            failures.append("layered/scripted voice correction should create a short-term overlay")
        layered_block = build_voice_trial_overlay_prompt_block(root, _owner_payload(), user_text="嗯，感觉如何")
        if "stay inside the current exchange" not in layered_block:
            failures.append("layered voice overlay should bias toward staying inside the exchange")
        if "less_self_analysis" not in layered_block:
            failures.append("layered voice overlay should include less_self_analysis hint")

        record_voice_trial_overlay(
            root,
            _owner_payload(),
            user_text="还是模板味太重。",
            reply="知道。",
            source="smoke",
            recorded_at="2026-05-06T12:10:00+08:00",
            ttl_minutes=1,
        )
        future = datetime.now(timezone.utc).astimezone() + timedelta(minutes=5)
        if build_voice_trial_overlay_prompt_block(root, _owner_payload(), user_text="过期了吗", now_dt=future):
            failures.append("expired-by-time overlay should not produce a prompt block")
        if stable.read_text(encoding="utf-8") != before_stable:
            failures.append("voice trial overlay should not modify stable voice profile")

    if failures:
        print("xinyu_voice_trial_overlay_smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS xinyu_voice_trial_overlay_smoke")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

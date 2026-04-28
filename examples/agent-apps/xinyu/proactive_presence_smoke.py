from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from xinyu_core_bridge import XinYuBridgeRuntime
from xinyu_proactive_presence import (
    acknowledge_proactive_qq_message,
    claim_proactive_qq_message,
    run_proactive_presence,
)


def _seed_enabled_context(source_root: Path, temp_root: Path) -> Path:
    target = temp_root / "memory/context"
    target.mkdir(parents=True, exist_ok=True)
    _write_candidate_initiative(target)
    (target / "capability_zones_state.md").write_text(
        "- proactive_qq_send: enabled_gated_one_short_message\n",
        encoding="utf-8",
    )
    return target


def _write_candidate_initiative(target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    (target / "initiative_state.md").write_text(
        "\n".join(
            [
                "- decision: ask_owner",
                "- reason: smoke_safe_candidate",
                "- selected_question: Is this relationship getting heavier?",
                "- question_budget: 1",
                "- visible_posture: one_specific_question",
                "- cooldown_active: no",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    root = Path(__file__).resolve().parent
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-proactive-") as tmp:
        temp_root = Path(tmp)
        target = temp_root / "memory/context"
        target.mkdir(parents=True, exist_ok=True)
        _write_candidate_initiative(target)
        result = run_proactive_presence(
            temp_root,
            evaluated_at="2026-04-26T17:40:00+08:00",
            mode="smoke_proactive_presence",
        )
        if result["qq_send_permission"] != "blocked_until_owner_enables_proactive_qq":
            failures.append("qq send permission should remain blocked")
        state = (target / "proactive_presence_state.md").read_text(encoding="utf-8")
        for marker in (
            "Proactive Presence State",
            "candidate_message:",
            "Actual QQ sending requires owner-approved proactive mode",
            "cannot spam owner",
        ):
            if marker not in state:
                failures.append(f"state missing marker: {marker}")
        (target / "capability_zones_state.md").write_text(
            "- proactive_qq_send: enabled_gated_one_short_message\n",
            encoding="utf-8",
        )
        enabled = run_proactive_presence(
            temp_root,
            evaluated_at="2026-04-26T20:23:24+08:00",
            mode="smoke_proactive_presence_enabled",
        )
        if enabled["qq_send_permission"] != "owner_enabled_gated_one_short_message":
            failures.append("qq send permission should be enabled when owner grant exists")
        delivery = claim_proactive_qq_message(
            temp_root,
            evaluated_at="2026-04-26T20:24:00+08:00",
            mode="smoke_proactive_qq_claim",
            claim=True,
            claim_id="smoke-claim-1",
            min_interval_seconds=3600,
        )
        if not delivery["reply"] or not delivery["candidate_claimed"]:
            failures.append("enabled proactive candidate should be claimable")
        duplicate = claim_proactive_qq_message(
            temp_root,
            evaluated_at="2026-04-26T20:25:00+08:00",
            mode="smoke_proactive_qq_duplicate",
            claim=True,
            claim_id="smoke-claim-2",
            min_interval_seconds=3600,
        )
        if duplicate["reply"] or duplicate["candidate_claimed"]:
            failures.append("duplicate proactive candidate should not be claimable")
        if "candidate_already_claimed" not in duplicate["notes"]:
            failures.append(f"duplicate proactive claim missing note: {duplicate['notes']}")
        mismatch = acknowledge_proactive_qq_message(
            temp_root,
            acked_at="2026-04-26T20:25:30+08:00",
            claim_id="wrong-claim",
            ack_status="sent",
            adapter_message_id="qq-msg-wrong",
        )
        if mismatch["ack_recorded"] or "claim_id_mismatch" not in mismatch["notes"]:
            failures.append(f"mismatched proactive ack should not be recorded: {mismatch}")
        ack = acknowledge_proactive_qq_message(
            temp_root,
            acked_at="2026-04-26T20:26:00+08:00",
            claim_id="smoke-claim-1",
            ack_status="sent",
            adapter_message_id="qq-msg-1",
        )
        if not ack["ack_recorded"] or ack["ack_status"] != "sent":
            failures.append(f"sent proactive ack should be recorded: {ack}")
        dispatch = (target / "proactive_qq_dispatch_state.md").read_text(encoding="utf-8")
        for marker in (
            "last_claim_status: sent",
            "last_ack_status: sent",
            "adapter_message_id: qq-msg-1",
        ):
            if marker not in dispatch:
                failures.append(f"dispatch state missing sent marker: {marker}")
        sent_duplicate = claim_proactive_qq_message(
            temp_root,
            evaluated_at="2026-04-26T20:27:00+08:00",
            mode="smoke_proactive_qq_sent_duplicate",
            claim=True,
            claim_id="smoke-claim-3",
            min_interval_seconds=3600,
        )
        if sent_duplicate["reply"] or sent_duplicate["candidate_claimed"]:
            failures.append("sent proactive candidate should not be claimable again")
        if "candidate_already_sent" not in sent_duplicate["notes"]:
            failures.append(f"sent duplicate proactive claim missing note: {sent_duplicate['notes']}")

    with tempfile.TemporaryDirectory(prefix="xinyu-proactive-retry-") as tmp:
        temp_root = Path(tmp)
        _seed_enabled_context(root, temp_root)
        failed_claim = claim_proactive_qq_message(
            temp_root,
            evaluated_at="2026-04-26T21:00:00+08:00",
            mode="smoke_proactive_qq_failed_claim",
            claim=True,
            claim_id="failed-claim-1",
            min_interval_seconds=3600,
        )
        failed_ack = acknowledge_proactive_qq_message(
            temp_root,
            acked_at="2026-04-26T21:01:00+08:00",
            claim_id="failed-claim-1",
            ack_status="failed",
            adapter_error="send timeout",
        )
        retry_claim = claim_proactive_qq_message(
            temp_root,
            evaluated_at="2026-04-26T21:02:00+08:00",
            mode="smoke_proactive_qq_retry_after_failed_ack",
            claim=True,
            claim_id="failed-claim-2",
            min_interval_seconds=3600,
        )
        if not failed_claim["candidate_claimed"] or not failed_ack["ack_recorded"]:
            failures.append("failed proactive ack setup did not claim and record failure")
        if failed_ack["ack_status"] != "failed":
            failures.append(f"failed proactive ack status not preserved: {failed_ack}")
        if retry_claim["reply"] or retry_claim["candidate_claimed"]:
            failures.append("failed proactive ack should not immediately retry the same candidate")
        if not any("candidate_failed_retry_cooldown" in note for note in retry_claim["notes"]):
            failures.append(f"failed proactive retry missing cooldown note: {retry_claim['notes']}")

    with tempfile.TemporaryDirectory(prefix="xinyu-proactive-concrete-") as tmp:
        temp_root = Path(tmp)
        target = temp_root / "memory/context"
        target.mkdir(parents=True, exist_ok=True)
        (target / "initiative_state.md").write_text(
            "\n".join(
                [
                    "- decision: ask_owner",
                    "- reason: smoke_abstract_candidate",
                    "- selected_question: 当一个人希望我更像真实关系里的心智系统时，我应该怎样回应这种存在方式",
                    "- question_budget: 1",
                    "- visible_posture: one_specific_question",
                    "- cooldown_active: no",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (target / "capability_zones_state.md").write_text(
            "- proactive_qq_send: enabled_gated_one_short_message\n",
            encoding="utf-8",
        )
        (target / "current_life_posture.md").write_text(
            "\n".join(
                [
                    "- posture: hot_daily",
                    "- no_proactive_constraint: unchanged",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        concrete = claim_proactive_qq_message(
            temp_root,
            evaluated_at="2026-04-26T22:00:00+08:00",
            mode="smoke_proactive_concrete_candidate",
            claim=True,
            claim_id="concrete-claim-1",
            min_interval_seconds=3600,
        )
        if concrete["reply"] or concrete["candidate_claimed"]:
            failures.append(f"abstract proactive candidate should not be replaced by fallback text: {concrete}")
        if "当一个人希望我" in str(concrete["reply"]) or "心智系统" in str(concrete["reply"]):
            failures.append(f"abstract proactive wording was dispatched: {concrete['reply']}")
        if "热" not in str(concrete["reply"]) and "空调" not in str(concrete["reply"]):
            pass
        state = (target / "proactive_presence_state.md").read_text(encoding="utf-8")
        if "candidate_shape: abstract_question_blocked_no_concrete_anchor" not in state:
            failures.append("proactive state did not record abstract candidate block")

    with tempfile.TemporaryDirectory(prefix="xinyu-proactive-no-anchor-") as tmp:
        temp_root = Path(tmp)
        target = temp_root / "memory/context"
        target.mkdir(parents=True, exist_ok=True)
        (target / "initiative_state.md").write_text(
            "\n".join(
                [
                    "- decision: ask_owner",
                    "- reason: smoke_no_anchor_candidate",
                    "- selected_question: 当一个人希望我更像真实关系里的心智系统时，我应该怎样回应这种存在方式",
                    "- question_budget: 1",
                    "- visible_posture: one_specific_question",
                    "- cooldown_active: no",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (target / "capability_zones_state.md").write_text(
            "- proactive_qq_send: enabled_gated_one_short_message\n",
            encoding="utf-8",
        )
        blocked_abstract = claim_proactive_qq_message(
            temp_root,
            evaluated_at="2026-04-26T22:05:00+08:00",
            mode="smoke_proactive_no_anchor",
            claim=True,
            claim_id="no-anchor-claim-1",
            min_interval_seconds=3600,
        )
        if blocked_abstract["reply"] or blocked_abstract["candidate_claimed"]:
            failures.append(f"abstract proactive without concrete anchor should not dispatch: {blocked_abstract}")
        state = (target / "proactive_presence_state.md").read_text(encoding="utf-8")
        if "candidate_shape: abstract_question_blocked_no_concrete_anchor" not in state:
            failures.append("abstract no-anchor block did not record candidate shaping")
        if "你现在是在忙" in state or "看我一眼" in state:
            failures.append("generic attention fallback leaked into proactive state")

    with tempfile.TemporaryDirectory(prefix="xinyu-proactive-posture-block-") as tmp:
        temp_root = Path(tmp)
        _seed_enabled_context(root, temp_root)
        target = temp_root / "memory/context"
        (target / "current_life_posture.md").write_text(
            "\n".join(
                [
                    "- posture: guarded_after_correction",
                    "- no_proactive_constraint: block proactive until style pressure cools",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        blocked = claim_proactive_qq_message(
            temp_root,
            evaluated_at="2026-04-26T22:10:00+08:00",
            mode="smoke_proactive_posture_block",
            claim=True,
            claim_id="blocked-claim-1",
            min_interval_seconds=3600,
        )
        if blocked["reply"] or blocked["candidate_claimed"]:
            failures.append(f"life-posture blocked proactive should not dispatch: {blocked}")
        if "not_ready:hold" not in blocked["notes"]:
            failures.append(f"blocked proactive missing not-ready note: {blocked['notes']}")

    with tempfile.TemporaryDirectory(prefix="xinyu-proactive-interrupt-grant-") as tmp:
        temp_root = Path(tmp)
        _seed_enabled_context(root, temp_root)
        target = temp_root / "memory/context"
        (target / "current_life_posture.md").write_text(
            "\n".join(
                [
                    "- posture: guarded_after_correction",
                    "- no_proactive_constraint: block proactive until style pressure cools",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (target / "owner_permission_grants.md").write_text(
            "- grant_owner_welcomes_xinyu_interruptions: approved_high_priority_one_short_message_life_posture_soft_block_override\n",
            encoding="utf-8",
        )
        override = claim_proactive_qq_message(
            temp_root,
            evaluated_at="2026-04-26T22:15:00+08:00",
            mode="smoke_proactive_interruption_grant",
            claim=True,
            claim_id="interrupt-grant-claim-1",
            min_interval_seconds=3600,
        )
        if not override["reply"] or not override["candidate_claimed"]:
            failures.append(f"owner interruption grant should override soft posture block: {override}")
        state = (target / "proactive_presence_state.md").read_text(encoding="utf-8")
        for marker in (
            "owner_interruption_grant: approved",
            "interruption_grant_level: soft_life_posture_override",
            "life_posture_block_class: soft_owner_correction",
            "life_posture_override: yes",
            "owner_welcomes_interruptions_soft_owner_correction_override",
        ):
            if marker not in state:
                failures.append(f"interruption grant state missing marker: {marker}")

    with tempfile.TemporaryDirectory(prefix="xinyu-proactive-interrupt-hard-block-") as tmp:
        temp_root = Path(tmp)
        _seed_enabled_context(root, temp_root)
        target = temp_root / "memory/context"
        (target / "current_life_posture.md").write_text(
            "\n".join(
                [
                    "- posture: sleepy_quiet",
                    "- no_proactive_constraint: block proactive while rest/silence boundary is active",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (target / "owner_permission_grants.md").write_text(
            "- grant_owner_welcomes_xinyu_interruptions: approved_high_priority_one_short_message_life_posture_soft_block_override\n",
            encoding="utf-8",
        )
        hard_blocked = claim_proactive_qq_message(
            temp_root,
            evaluated_at="2026-04-26T22:20:00+08:00",
            mode="smoke_proactive_interruption_hard_block",
            claim=True,
            claim_id="interrupt-hard-block-claim-1",
            min_interval_seconds=3600,
        )
        if hard_blocked["reply"] or hard_blocked["candidate_claimed"]:
            failures.append(f"owner interruption grant should not override hard posture block: {hard_blocked}")

    with tempfile.TemporaryDirectory(prefix="xinyu-proactive-interrupt-rest-override-") as tmp:
        temp_root = Path(tmp)
        _seed_enabled_context(root, temp_root)
        target = temp_root / "memory/context"
        (target / "current_life_posture.md").write_text(
            "\n".join(
                [
                    "- posture: sleepy_quiet",
                    "- no_proactive_constraint: block proactive while rest/silence boundary is active",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (target / "owner_permission_grants.md").write_text(
            "- grant_owner_welcomes_xinyu_interruptions: approved_high_priority_one_short_message_rest_silence_override\n",
            encoding="utf-8",
        )
        rest_override = claim_proactive_qq_message(
            temp_root,
            evaluated_at="2026-04-26T22:25:00+08:00",
            mode="smoke_proactive_interruption_rest_override",
            claim=True,
            claim_id="interrupt-rest-override-claim-1",
            min_interval_seconds=3600,
        )
        if not rest_override["reply"] or not rest_override["candidate_claimed"]:
            failures.append(f"high interruption grant should override rest/silence posture block: {rest_override}")
        state = (target / "proactive_presence_state.md").read_text(encoding="utf-8")
        for marker in (
            "interruption_grant_level: rest_silence_override",
            "life_posture_block_class: rest_silence_boundary",
            "life_posture_override: yes",
            "owner_welcomes_interruptions_rest_silence_boundary_override",
        ):
            if marker not in state:
                failures.append(f"rest/silence override state missing marker: {marker}")

    with tempfile.TemporaryDirectory(prefix="xinyu-proactive-bridge-") as tmp:
        temp_root = Path(tmp)
        _seed_enabled_context(root, temp_root)
        runtime = XinYuBridgeRuntime(
            xinyu_dir=temp_root,
            turn_timeout_seconds=1,
            max_text_chars=100,
            settle_seconds=0,
            outward_renderer=False,
            render_timeout_seconds=1,
            session_idle_ttl_seconds=10,
            max_sessions=0,
            proactive_min_interval_seconds=3600,
        )
        bridge = asyncio.run(
            runtime.proactive({"claim": True, "claim_id": "bridge-smoke-claim"})
        )
        if not bridge["reply"] or not bridge["candidate_claimed"]:
            failures.append("bridge proactive endpoint should claim an enabled candidate")
        if bridge["session_created"] or bridge["sessions"] != 0:
            failures.append("bridge proactive endpoint should not create agent sessions")
        bridge_ack = asyncio.run(
            runtime.proactive_ack(
                {
                    "claim_id": "bridge-smoke-claim",
                    "status": "sent",
                    "message_id": "bridge-qq-msg-1",
                }
            )
        )
        if not bridge_ack["ack_recorded"] or bridge_ack["ack_status"] != "sent":
            failures.append(f"bridge proactive ack should record sent status: {bridge_ack}")
        if bridge_ack["session_created"] or bridge_ack["sessions"] != 0:
            failures.append("bridge proactive ack should not create agent sessions")
    if failures:
        print("Proactive presence smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Proactive presence smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

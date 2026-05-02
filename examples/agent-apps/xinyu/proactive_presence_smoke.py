from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

from xinyu_core_bridge import XinYuBridgeRuntime
from xinyu_dialogue_working_memory import load_dialogue_tail
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


def _write_request_preview(
    target: Path,
    question: str = "Should I continue the current plan?",
    *,
    request_id: str = "proreq-preview-smoke",
    kind: str = "clarify",
    requested_action: str = "owner_answer",
    status: str = "candidate_only",
    delivery_level: str = "state_only",
) -> None:
    target.mkdir(parents=True, exist_ok=True)
    (target / "proactive_request_state.md").write_text(
        "\n".join(
            [
                "---",
                "title: Proactive Request State",
                "memory_type: proactive_request_state",
                "source: xinyu_proactive_request_loop",
                "status: active",
                "---",
                "",
                "# Proactive Request State",
                "",
                "## Current Request",
                f"- request_id: {request_id}",
                "- created_at: 2026-05-01T11:00:00+08:00",
                f"- status: {status}",
                f"- kind: {kind}",
                "- source: self_thought",
                "- request_family: self_thought:active_question",
                "- evidence_label: active question marked proactive_ok",
                "- evidence_hash: sha256:abcdef1234567890",
                f"- concrete_question: {question}",
                f"- requested_action: {requested_action}",
                "- why_now: active question marked proactive_ok",
                "- after_owner_replies: continue the current thread",
                "- dedupe_key: proreq:self_thought:active_question:sha256:abcdef1234567890",
                "",
                "## Gates",
                "- has_concrete_question: true",
                "- has_requested_action: true",
                "- source_allowed: true",
                "",
                "## Delivery",
                f"- delivery_level: {delivery_level}",
                "",
                "## Boundaries",
                "- no_qq_enqueue: true",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    root = Path(__file__).resolve().parent
    failures: list[str] = []
    with tempfile.TemporaryDirectory(prefix="xinyu-proactive-request-preview-") as tmp:
        temp_root = Path(tmp)
        target = temp_root / "memory/context"
        target.mkdir(parents=True, exist_ok=True)
        (target / "initiative_state.md").write_text(
            "- decision: defer\n- cooldown_active: no\n",
            encoding="utf-8",
        )
        _write_request_preview(target)
        preview = run_proactive_presence(
            temp_root,
            evaluated_at="2026-05-01T11:10:00+08:00",
            mode="smoke_proactive_request_preview",
        )
        if preview["proactive_decision"] != "request_preview_only":
            failures.append(f"proactive request should become preview only: {preview}")
        if preview["qq_send_permission"] != "preview_only_no_qq_claim":
            failures.append(f"request preview should not allow QQ claim: {preview}")
        if preview["candidate_message"] != "Should I continue the current plan?":
            failures.append(f"request preview candidate mismatch: {preview}")
        claim_attempt = claim_proactive_qq_message(
            temp_root,
            evaluated_at="2026-05-01T11:11:00+08:00",
            mode="smoke_proactive_request_preview_claim",
            claim=True,
            claim_id="request-preview-claim",
            min_interval_seconds=3600,
        )
        if claim_attempt["reply"] or claim_attempt["candidate_claimed"]:
            failures.append(f"request preview should not be claimable: {claim_attempt}")
        if claim_attempt.get("preview_reply") != "Should I continue the current plan?":
            failures.append(f"request preview should return preview_reply: {claim_attempt}")
        if (target / "proactive_qq_dispatch_state.md").exists():
            failures.append("request preview claim wrote proactive QQ dispatch state")
        state = (target / "proactive_presence_state.md").read_text(encoding="utf-8")
        for marker in (
            "proactive_decision: request_preview_only",
            "candidate_shape: proactive_request_preview",
            "proactive_request_status: candidate_only",
            "proactive_request_delivery_level: state_only",
        ):
            if marker not in state:
                failures.append(f"request preview state missing marker: {marker}")

    with tempfile.TemporaryDirectory(prefix="xinyu-proactive-request-dream-preview-") as tmp:
        temp_root = Path(tmp)
        target = temp_root / "memory/context"
        target.mkdir(parents=True, exist_ok=True)
        (target / "initiative_state.md").write_text(
            "- decision: defer\n- cooldown_active: no\n",
            encoding="utf-8",
        )
        dream_message = "I had a dream about a classroom. It is only a dream, not a new real event."
        _write_request_preview(
            target,
            dream_message,
            kind="dream_share",
            requested_action="owner_response_optional",
        )
        preview = run_proactive_presence(
            temp_root,
            evaluated_at="2026-05-01T11:20:00+08:00",
            mode="smoke_proactive_request_dream_preview",
        )
        if preview["candidate_message"] != dream_message:
            failures.append(f"dream share preview should remain a statement: {preview}")
        if preview["proactive_decision"] != "request_preview_only":
            failures.append(f"dream share request should become preview only: {preview}")

    with tempfile.TemporaryDirectory(prefix="xinyu-proactive-request-ready-claim-") as tmp:
        temp_root = Path(tmp)
        target = temp_root / "memory/context"
        target.mkdir(parents=True, exist_ok=True)
        (target / "initiative_state.md").write_text(
            "- decision: defer\n- cooldown_active: no\n",
            encoding="utf-8",
        )
        (target / "capability_zones_state.md").write_text(
            "- proactive_qq_send: enabled_gated_one_short_message\n",
            encoding="utf-8",
        )
        ready_message = "Should I continue the current plan?"
        _write_request_preview(
            target,
            ready_message,
            status="ready",
            delivery_level="queue_owner_private",
        )
        ready = run_proactive_presence(
            temp_root,
            evaluated_at="2026-05-01T11:30:00+08:00",
            mode="smoke_proactive_request_ready",
        )
        if ready["proactive_decision"] != "candidate_ready_owner_enabled":
            failures.append(f"ready proactive request should become claimable: {ready}")
        claim = claim_proactive_qq_message(
            temp_root,
            evaluated_at="2026-05-01T11:31:00+08:00",
            mode="smoke_proactive_request_ready_claim",
            claim=True,
            claim_id="request-ready-claim",
            min_interval_seconds=0,
        )
        if not claim["candidate_claimed"] or claim["reply"] != ready_message:
            failures.append(f"ready proactive request should be claimable: {claim}")
        if not (target / "proactive_qq_dispatch_state.md").exists():
            failures.append("ready proactive request did not write dispatch claim state")
        dispatch_after_claim = (target / "proactive_qq_dispatch_state.md").read_text(encoding="utf-8")
        if "proactive_request_id: proreq-preview-smoke" not in dispatch_after_claim:
            failures.append("proactive dispatch state did not remember request id")
        request_after_claim = (target / "proactive_request_state.md").read_text(encoding="utf-8")
        if "status: claimed" not in request_after_claim or "last_ack_status: pending" not in request_after_claim:
            failures.append("ready proactive request was not marked claimed/pending after claim")
        ack_ready = acknowledge_proactive_qq_message(
            temp_root,
            acked_at="2026-05-01T11:32:00+08:00",
            claim_id="request-ready-claim",
            ack_status="sent",
            adapter_message_id="qq-request-ready-1",
        )
        if not ack_ready["ack_recorded"] or ack_ready["ack_status"] != "sent":
            failures.append(f"ready proactive request ack should be recorded: {ack_ready}")
        _write_request_preview(
            target,
            ready_message,
            request_id="proreq-preview-smoke-next",
            status="ready",
            delivery_level="queue_owner_private",
        )
        next_claim = claim_proactive_qq_message(
            temp_root,
            evaluated_at="2026-05-01T11:33:00+08:00",
            mode="smoke_proactive_request_next_same_text",
            claim=True,
            claim_id="request-ready-next-claim",
            min_interval_seconds=0,
        )
        if not next_claim["candidate_claimed"] or next_claim["reply"] != ready_message:
            failures.append(f"same message from a new request id should be claimable after cooldown is open: {next_claim}")

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
            "bounded owner-private thread",
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

    with tempfile.TemporaryDirectory(prefix="xinyu-proactive-outbox-bridge-") as tmp:
        temp_root = Path(tmp)
        target = temp_root / "memory/context"
        target.mkdir(parents=True, exist_ok=True)
        (target / "initiative_state.md").write_text(
            "- decision: defer\n- cooldown_active: no\n",
            encoding="utf-8",
        )
        (target / "capability_zones_state.md").write_text(
            "- proactive_qq_send: enabled_gated_one_short_message\n",
            encoding="utf-8",
        )
        _write_request_preview(
            target,
            "I had a dream about a classroom. It is only a dream, not a new real event.",
            kind="dream_share",
            requested_action="owner_response_optional",
            status="ready",
            delivery_level="queue_owner_private",
        )
        previous_owner_ids = os.environ.get("XINYU_OWNER_USER_IDS")
        os.environ["XINYU_OWNER_USER_IDS"] = "42"
        try:
            runtime = XinYuBridgeRuntime(
                xinyu_dir=temp_root,
                turn_timeout_seconds=1,
                max_text_chars=100,
                settle_seconds=0,
                outward_renderer=False,
                render_timeout_seconds=1,
                session_idle_ttl_seconds=10,
                max_sessions=0,
                proactive_min_interval_seconds=0,
            )
            outbox_claim = asyncio.run(
                runtime.qq_outbox_claim({"claim_id": "bridge-outbox-proactive-claim", "min_interval_seconds": 0})
            )
            if not outbox_claim.get("message_claimed") or outbox_claim.get("source") != "proactive_request":
                failures.append(f"qq outbox claim should surface ready proactive request: {outbox_claim}")
            if outbox_claim.get("target", {}).get("user_id") != "42":
                failures.append(f"proactive outbox claim should target owner private QQ: {outbox_claim}")
            outbox_ack = asyncio.run(
                runtime.qq_outbox_ack(
                    {
                        "message_id": outbox_claim.get("message_id"),
                        "claim_id": outbox_claim.get("claim_id"),
                        "ack_status": "sent",
                        "adapter_message_id": "qq-proactive-msg-1",
                    }
                )
            )
            if not outbox_ack.get("ack_recorded") or outbox_ack.get("ack_status") != "sent":
                failures.append(f"proactive outbox ack should route to proactive ack: {outbox_ack}")
            request_after_ack = (target / "proactive_request_state.md").read_text(encoding="utf-8")
            if "status: sent" not in request_after_ack or "last_ack_status: sent" not in request_after_ack:
                failures.append("proactive request delivery state was not marked sent after ack")
            tail = load_dialogue_tail(temp_root, "qq:private:42", max_entries=4)
            if not any(
                item.get("role") == "assistant"
                and "I had a dream about a classroom" in item.get("content", "")
                for item in tail
            ):
                failures.append(f"sent proactive request should be written to dialogue tail: {tail}")
            after_sent = asyncio.run(
                runtime.qq_outbox_claim({"claim_id": "bridge-outbox-proactive-after-sent", "min_interval_seconds": 0})
            )
            if after_sent.get("message_claimed"):
                failures.append(f"sent proactive request should not be reclaimed by outbox: {after_sent}")
        finally:
            if previous_owner_ids is None:
                os.environ.pop("XINYU_OWNER_USER_IDS", None)
            else:
                os.environ["XINYU_OWNER_USER_IDS"] = previous_owner_ids

    with tempfile.TemporaryDirectory(prefix="xinyu-proactive-outbox-fast-") as tmp:
        temp_root = Path(tmp)
        target = temp_root / "memory/context"
        target.mkdir(parents=True, exist_ok=True)
        (target / "initiative_state.md").write_text("- decision: defer\n- cooldown_active: no\n", encoding="utf-8")
        (target / "capability_zones_state.md").write_text(
            "- proactive_qq_send: enabled_gated_one_short_message\n",
            encoding="utf-8",
        )
        _write_request_preview(
            target,
            "I had a dream about a hallway. It is only a dream, not a new real event.",
            kind="dream_share",
            requested_action="owner_response_optional",
            status="ready",
            delivery_level="queue_owner_private",
        )
        previous_owner_ids = os.environ.get("XINYU_OWNER_USER_IDS")
        os.environ["XINYU_OWNER_USER_IDS"] = "42"
        try:
            runtime = XinYuBridgeRuntime(
                xinyu_dir=temp_root,
                turn_timeout_seconds=1,
                max_text_chars=100,
                settle_seconds=0,
                outward_renderer=False,
                render_timeout_seconds=1,
                session_idle_ttl_seconds=10,
                max_sessions=0,
                proactive_min_interval_seconds=0,
            )
            fast_claim = runtime.qq_outbox_claim_fast({"claim_id": "bridge-outbox-fast-claim", "min_interval_seconds": 0})
            if not fast_claim.get("message_claimed") or fast_claim.get("source") != "proactive_request":
                failures.append(f"fast qq outbox claim should surface proactive request: {fast_claim}")
            fast_ack = runtime.qq_outbox_ack_fast(
                {
                    "message_id": fast_claim.get("message_id"),
                    "claim_id": fast_claim.get("claim_id"),
                    "ack_status": "sent",
                    "adapter_message_id": "qq-fast-proactive-msg-1",
                }
            )
            if not fast_ack.get("ack_recorded") or fast_ack.get("ack_status") != "sent":
                failures.append(f"fast proactive outbox ack should record sent status: {fast_ack}")
            tail = load_dialogue_tail(temp_root, "qq:private:42", max_entries=4)
            if not any("I had a dream about a hallway" in item.get("content", "") for item in tail):
                failures.append(f"fast proactive ack should write dialogue tail: {tail}")
        finally:
            if previous_owner_ids is None:
                os.environ.pop("XINYU_OWNER_USER_IDS", None)
            else:
                os.environ["XINYU_OWNER_USER_IDS"] = previous_owner_ids
    if failures:
        print("Proactive presence smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Proactive presence smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

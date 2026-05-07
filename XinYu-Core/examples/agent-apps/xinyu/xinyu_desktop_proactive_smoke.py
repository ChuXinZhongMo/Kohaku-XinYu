from __future__ import annotations

import argparse
import asyncio
import os
import tempfile
from pathlib import Path

from xinyu_core_bridge import XinYuBridgeRuntime
from xinyu_desktop_events import DesktopEventBus, event_types


def _write_request_state(
    root: Path,
    *,
    status: str,
    delivery_level: str = "preview_only",
    claim_id: str = "none",
    ack_status: str = "none",
    question: str = "proactive smoke question?",
    why_now: str = "smoke wants to surface a pending thought",
) -> None:
    path = root / "memory/context/proactive_request_state.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"""---
title: Proactive Request State
memory_type: proactive_request_state
updated_at: 2026-01-01T00:00:00+00:00
status: active
---

# Proactive Request State

## Current Request
- request_id: proreq-smoke
- created_at: 2026-01-01T00:00:00+00:00
- status: {status}
- kind: reflection_share
- source: self_thought
- focus_kind: reflection_queue
- focus_label: smoke reflection
- priority: low
- request_family: self_thought:reflection_queue
- thread_id: prothread:smoke
- evidence_label: smoke evidence
- evidence_hash: sha256:abcdef1234567890
- concrete_question: {question}
- requested_action: owner_response_optional
- why_now: {why_now}
- dedupe_key: proreq:smoke
- expires_at: 2099-01-01T00:00:00+00:00
- request_answer_state: pending

## Delivery
- delivery_level: {delivery_level}
- last_claim_id: {claim_id}
- last_ack_status: {ack_status}
- adapter_message_id: adapter-smoke
- adapter_error: none
""",
        encoding="utf-8",
    )


async def _smoke() -> list[str]:
    failures: list[str] = []
    loop = asyncio.get_running_loop()
    with tempfile.TemporaryDirectory(prefix="xinyu-desktop-proactive-") as tmp:
        xinyu_dir = Path(tmp)
        (xinyu_dir / "memory").mkdir(parents=True, exist_ok=True)
        runtime = XinYuBridgeRuntime(
            xinyu_dir=xinyu_dir,
            turn_timeout_seconds=1,
            max_text_chars=2000,
            settle_seconds=0.0,
            outward_renderer=False,
            renderer_mode="off",
            render_timeout_seconds=1,
            session_idle_ttl_seconds=60,
            max_sessions=2,
            proactive_min_interval_seconds=60,
            autonomous_maintenance_enabled=False,
        )
        bus = DesktopEventBus(loop=loop, max_events=10)
        runtime.desktop_event_bus = bus

        _write_request_state(xinyu_dir, status="ready")
        ready = await runtime._desktop_publish_proactive_candidate_ready_from_state(notes=["smoke_ready"])
        if ready.get("type") != "proactive.candidate.ready":
            failures.append("candidate ready event was not published")

        inbox = await runtime.desktop_proactive_inbox({})
        items = inbox.get("items", [])
        if [item.get("candidateId") for item in items] != ["proreq-smoke"]:
            failures.append("ready candidate did not hydrate into proactive inbox")

        _write_request_state(
            xinyu_dir,
            status="ready",
            question="刚才梦里 local action pressure after codex_delegate:none 被压成一段路，要不要看？",
            why_now="reflection queue strong topic: action residue after local action pressure after codex_delegate:none",
        )
        scrubbed = (await runtime.desktop_proactive_inbox({})).get("items", [])
        scrubbed_preview = str(scrubbed[-1].get("candidatePreview") if scrubbed else "")
        scrubbed_reason = str(scrubbed[-1].get("whyNowPreview") if scrubbed else "")
        if "codex_delegate" in scrubbed_preview or "local action pressure" in scrubbed_preview:
            failures.append(f"desktop proactive preview leaked action internals: {scrubbed_preview}")
        if "Codex 委派" not in scrubbed_preview:
            failures.append(f"desktop proactive preview lost humanized action marker: {scrubbed_preview}")
        if any(marker in scrubbed_reason for marker in ("reflection queue", "action residue", "local action pressure", "codex_delegate")):
            failures.append(f"desktop proactive reason leaked action internals: {scrubbed_reason}")
        if "反思队列" not in scrubbed_reason or "Codex 委派" not in scrubbed_reason:
            failures.append(f"desktop proactive reason lost humanized action marker: {scrubbed_reason}")

        _write_request_state(xinyu_dir, status="ready")
        read_local = await runtime.desktop_proactive_ack(
            {"candidateId": "proreq-smoke", "action": "read_locally"}
        )
        if not read_local.get("ack_recorded") or read_local.get("status") != "read_locally":
            failures.append(f"desktop read-local ack was not recorded: {read_local}")
        inbox = await runtime.desktop_proactive_inbox({})
        if inbox.get("items") != []:
            failures.append("read-local proactive ack should remove candidate from inbox")

        _write_request_state(xinyu_dir, status="candidate_only", delivery_level="preview_only")
        reply_ack = await runtime.desktop_proactive_ack(
            {"candidateId": "proreq-smoke", "action": "reply"}
        )
        if not reply_ack.get("ack_recorded") or reply_ack.get("status") != "answered":
            failures.append(f"desktop reply ack should mark proactive answered: {reply_ack}")
        reply_state = (xinyu_dir / "memory/context/proactive_request_state.md").read_text(encoding="utf-8")
        if "request_answer_state: owner_replied" not in reply_state or "last_ack_status: replied" not in reply_state:
            failures.append("desktop reply ack did not preserve owner-replied state")
        inbox = await runtime.desktop_proactive_inbox({})
        if inbox.get("items") != []:
            failures.append("reply proactive ack should remove candidate from inbox")

        _write_request_state(xinyu_dir, status="claimed", delivery_level="queue_owner_private", claim_id="claim-smoke")
        claimed = await runtime._desktop_publish_proactive_delivery_from_state(
            status_override="claimed",
            notes=["smoke_claimed"],
        )
        if claimed.get("type") != "proactive.delivery.updated":
            failures.append("claimed delivery update was not published")
        inbox = await runtime.desktop_proactive_inbox({})
        items = inbox.get("items", [])
        if not items or items[-1].get("status") != "claimed":
            failures.append("claimed candidate did not stay in proactive inbox")

        _write_request_state(xinyu_dir, status="sent", delivery_level="queue_owner_private", claim_id="claim-smoke", ack_status="sent")
        sent = await runtime._desktop_publish_proactive_delivery_from_state(
            status_override="sent",
            notes=["smoke_sent"],
        )
        if sent.get("type") != "proactive.delivery.updated":
            failures.append("sent delivery update was not published")
        inbox = await runtime.desktop_proactive_inbox({})
        if inbox.get("items") != []:
            failures.append("sent candidate should be removed from proactive inbox")

        _write_request_state(xinyu_dir, status="ready", delivery_level="queue_owner_private")
        previous_owner_ids = os.environ.get("XINYU_OWNER_USER_IDS")
        os.environ["XINYU_OWNER_USER_IDS"] = "42"
        try:
            approve_qq = await runtime.desktop_proactive_ack(
                {"candidateId": "proreq-smoke", "action": "approve_qq"}
            )
        finally:
            if previous_owner_ids is None:
                os.environ.pop("XINYU_OWNER_USER_IDS", None)
            else:
                os.environ["XINYU_OWNER_USER_IDS"] = previous_owner_ids
        if not approve_qq.get("ack_recorded") or approve_qq.get("status") != "queued_qq":
            failures.append(f"desktop approve-qq ack should enqueue QQ outbox: {approve_qq}")
        inbox = await runtime.desktop_proactive_inbox({})
        if inbox.get("items") != []:
            failures.append("approve-qq proactive ack should remove candidate from inbox")
        queue_text = (xinyu_dir / "memory/context/qq_outbox_queue.json").read_text(encoding="utf-8")
        if "proactive smoke question?" not in queue_text or "desktop_proactive_ack" not in queue_text:
            failures.append("approve-qq proactive ack did not enqueue the candidate message")
        dispatch_text = (xinyu_dir / "memory/context/proactive_qq_dispatch_state.md").read_text(encoding="utf-8")
        if "last_claim_status: claimed" not in dispatch_text or "proactive smoke question?" not in dispatch_text:
            failures.append("approve-qq proactive ack did not preserve proactive dispatch continuity")

        events = await bus.recent(limit=10)
        if event_types(events) != [
            "proactive.candidate.ready",
            "proactive.delivery.updated",
            "proactive.delivery.updated",
            "proactive.delivery.updated",
            "proactive.delivery.updated",
            "proactive.delivery.updated",
        ]:
            failures.append(f"unexpected proactive event sequence: {event_types(events)}")

        await runtime.shutdown()
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate XinYu desktop proactive telemetry.")
    parser.parse_args()
    failures = asyncio.run(_smoke())
    if failures:
        print("XinYu desktop proactive smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu desktop proactive smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

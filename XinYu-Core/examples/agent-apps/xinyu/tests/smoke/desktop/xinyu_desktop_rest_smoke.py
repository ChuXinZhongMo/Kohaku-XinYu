from __future__ import annotations

from _bootstrap import ensure_project_root_on_path

ROOT = ensure_project_root_on_path()

import asyncio
import json
import tempfile
import threading
import urllib.error
import urllib.request
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from xinyu_bridge_http import XinYuBridgeHTTPServer, XinYuBridgeRequestHandler
from xinyu_core_bridge import XinYuBridgeRuntime
from xinyu_action_experience_digest import digest_action_experience_residue
from xinyu_desktop_events import DesktopEventBus


NO_PROXY_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def _start_loop() -> tuple[asyncio.AbstractEventLoop, threading.Thread]:
    loop = asyncio.new_event_loop()

    def runner() -> None:
        asyncio.set_event_loop(loop)
        loop.run_forever()

    thread = threading.Thread(target=runner, name="xinyu-desktop-rest-loop", daemon=True)
    thread.start()
    return loop, thread


def _request_json(url: str, *, token: str | None = None) -> tuple[int, dict[str, Any]]:
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with NO_PROXY_OPENER.open(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def _post_json(url: str, payload: dict[str, Any], *, token: str | None = None) -> tuple[int, dict[str, Any]]:
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, headers=headers, data=body, method="POST")
    try:
        with NO_PROXY_OPENER.open(request, timeout=5) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def _seed_action_digest(root: Path) -> None:
    path = root / "runtime/life_kernel/action_experience_residue.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "experience_id": "exp-desktop-rest-action-digest",
        "created_at": "2026-01-01T00:00:10+00:00",
        "tool": "log_scan",
        "target_alias": "xinyu_logs",
        "result": "failure",
        "pressure": {"score": 0.61, "band": "medium", "reasons": ["desktop_rest_smoke"]},
        "salience": 0.72,
        "memory_candidates": ["desktop smoke action experience should reach the desktop snapshot"],
        "outcome_summary": ["found smoke warning in xinyu_logs"],
        "notes": ["desktop_snapshot_action_digest_smoke"],
    }
    path.write_text(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    digest_action_experience_residue(root, produced_at="2026-01-01T00:00:20+00:00", salience_threshold=0.6)


async def _seed_desktop_state(runtime: XinYuBridgeRuntime, bus: DesktopEventBus) -> dict[str, Any]:
    service_event = await bus.publish("service.status.changed", {"service": "core", "status": "ready"})
    proactive_state = runtime.xinyu_dir / "memory/context/proactive_request_state.md"
    proactive_state.parent.mkdir(parents=True, exist_ok=True)
    proactive_state.write_text(
        """---
title: Proactive Request State
memory_type: proactive_request_state
updated_at: 2026-01-01T00:00:00+00:00
status: active
---

# Proactive Request State

## Current Request
- request_id: proreq-smoke
- created_at: 2026-01-01T00:00:00+00:00
- status: ready
- kind: reflection_share
- source: self_thought
- focus_kind: reflection_queue
- focus_label: smoke reflection
- priority: low
- request_family: self_thought:reflection_queue
- thread_id: prothread:smoke
- evidence_label: smoke evidence
- evidence_hash: sha256:abcdef1234567890
- concrete_question: proactive smoke question?
- requested_action: owner_response_optional
- why_now: smoke wants to surface a pending thought
- dedupe_key: proreq:smoke
- expires_at: 2099-01-01T00:00:00+00:00
- request_answer_state: pending

## Delivery
- delivery_level: preview_only
- last_claim_id: none
- last_ack_status: none
- adapter_message_id: none
- adapter_error: none
""",
        encoding="utf-8",
    )
    proactive_event = await runtime._desktop_publish_proactive_candidate_ready_from_state(notes=["desktop_smoke"])
    payload = {
        "platform": "qq",
        "source": "desktop_rest_smoke",
        "message_type": "private",
        "session_id": "session-smoke",
        "user_id": "owner-smoke",
        "message_id": "message-smoke",
        "command_id": "desktop-command-smoke",
        "metadata": {"is_owner_user": True, "desktop_command_id": "desktop-command-smoke"},
    }
    await runtime._desktop_publish_chat_started(
        payload,
        text="hello from smoke",
        session_key="session-smoke",
        turn_id="turn-smoke",
        started_at="2026-01-01T00:00:00+00:00",
        active_sessions=0,
    )
    recall_result = SimpleNamespace(
        turn_id="recall-turn-smoke",
        query_text="hello from smoke\nprevious context",
        notes=("recalled_context_active",),
        route_plan=SimpleNamespace(
            selected_experts=("recent_dialogue", "project_task"),
            allowed_sources=("dialogue_tail", "dialogue_archive", "stable_memory"),
            allowed_memory_refs=("memory/context/recent_context.md", "memory/self/personality_profile.md"),
            current_turn_facts=("visible_turn_current",),
            notes=("sparse_memory_router_v1", "memory_experts:recent_dialogue,project_task"),
            decisions=(
                SimpleNamespace(expert="recent_dialogue", score=3.4, selected=True, reasons=("direct_recall",)),
                SimpleNamespace(expert="project_task", score=2.1, selected=True, reasons=("technical_work",)),
                SimpleNamespace(expert="emotion_residue", score=0.0, selected=False, reasons=()),
            ),
        ),
        items=(
            SimpleNamespace(
                recall_id="mem-smoke",
                source="stable_memory",
                scope="stable",
                time="stable memory file",
                speaker="memory",
                summary="smoke memory summary",
                relevance="selected stable memory reference",
                confidence="high",
                score=9.5,
                message_id=None,
                memory_ref="memory/self/personality_profile.md",
            ),
        ),
    )
    recall_event = await runtime._desktop_publish_memory_recall(
        payload,
        recall_result,
        session_key="session-smoke",
        turn_id="turn-smoke",
    )
    await runtime._desktop_publish_chat_finished(
        payload,
        text="hello from smoke",
        reply="reply from smoke",
        session_key="session-smoke",
        turn_id="turn-smoke",
        started_at="2026-01-01T00:00:00+00:00",
        elapsed_ms=42,
        status="ok",
        notes=["desktop_chat_smoke"],
        memory_changed=True,
        archive_message_ids=[101, 102],
        reply_hash="hash-smoke",
        recall_event_id=recall_event["id"],
        recall_count=1,
        top_recall_sources=["stable_memory"],
    )
    events = await bus.recent(limit=10)
    return {
        "serviceEventId": service_event["id"],
        "proactiveEventId": proactive_event["id"],
        "recallEventId": recall_event["id"],
        "latestEventId": events[-1]["id"],
        "eventTypes": [event.get("type") for event in events],
    }


def main() -> int:
    failures: list[str] = []
    token = "desktop-rest-smoke-token"
    loop, loop_thread = _start_loop()

    with tempfile.TemporaryDirectory(prefix="xinyu-desktop-rest-") as tmp:
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
        _seed_action_digest(xinyu_dir)
        seeded = asyncio.run_coroutine_threadsafe(_seed_desktop_state(runtime, bus), loop).result(timeout=5)

        server = XinYuBridgeHTTPServer(
            ("127.0.0.1", 0),
            XinYuBridgeRequestHandler,
            runtime=runtime,
            loop=loop,
            bridge_token=token,
            max_body_bytes=1024 * 1024,
            request_timeout_seconds=2,
        )
        server_thread = threading.Thread(target=server.serve_forever, name="xinyu-desktop-rest-http", daemon=True)
        server_thread.start()
        base_url = f"http://127.0.0.1:{server.server_address[1]}"

        try:
            status, body = _request_json(f"{base_url}/desktop/snapshot")
            if status != 401 or body.get("error") != "unauthorized":
                failures.append(f"unauthorized desktop snapshot returned {status}: {body}")

            status, snapshot = _request_json(f"{base_url}/desktop/snapshot", token=token)
            if status != 200:
                failures.append(f"desktop snapshot returned {status}: {snapshot}")
            if snapshot.get("lastEventId") != seeded["latestEventId"]:
                failures.append("desktop snapshot did not expose latest event id")
            if not snapshot.get("eventBus", {}).get("available"):
                failures.append("desktop snapshot did not report event bus availability")
            if not isinstance(snapshot.get("services"), list) or not snapshot["services"]:
                failures.append("desktop snapshot did not include services")
            if "health" not in snapshot:
                failures.append("desktop snapshot did not include health")
            action_digest = snapshot.get("actionDigestState")
            if not isinstance(action_digest, dict):
                failures.append("desktop snapshot did not include actionDigestState")
            else:
                if int(action_digest.get("digested_count") or 0) < 1:
                    failures.append("desktop snapshot actionDigestState did not expose digested count")
                recent_digest = action_digest.get("recent")
                if not isinstance(recent_digest, list) or not recent_digest:
                    failures.append("desktop snapshot actionDigestState did not expose recent digest rows")
                elif recent_digest[-1].get("experience_id") != "exp-desktop-rest-action-digest":
                    failures.append("desktop snapshot actionDigestState did not expose the seeded action experience")

            recent_turns = snapshot.get("recentTurns")
            if not isinstance(recent_turns, list) or not recent_turns or recent_turns[-1].get("turnId") != "turn-smoke":
                failures.append("desktop snapshot did not include recent chat turns")
            elif recent_turns[-1].get("recallEventId") != seeded["recallEventId"]:
                failures.append("desktop snapshot chat turn did not link the recall event")
            elif recent_turns[-1].get("commandId") != "desktop-command-smoke":
                failures.append("desktop snapshot chat turn did not expose commandId")
            recent_memory_events = snapshot.get("recentMemoryEvents")
            if (
                not isinstance(recent_memory_events, list)
                or not recent_memory_events
                or recent_memory_events[-1].get("eventId") != seeded["recallEventId"]
            ):
                failures.append("desktop snapshot did not include recent memory recall events")
            elif recent_memory_events[-1].get("selectedExperts") != ["recent_dialogue", "project_task"]:
                failures.append("desktop snapshot did not expose sparse memory selected experts")
            else:
                route = recent_memory_events[-1].get("route")
                if not isinstance(route, dict) or route.get("currentTurnFacts") != ["visible_turn_current"]:
                    failures.append("desktop snapshot did not expose sparse memory route current-turn facts")
            xinyu_state = snapshot.get("xinyuState")
            if not isinstance(xinyu_state, dict):
                failures.append("desktop snapshot did not include xinyuState")
            elif xinyu_state.get("latest_memory_route_experts") != ["recent_dialogue", "project_task"]:
                failures.append("desktop xinyuState did not expose latest memory route experts")
            proactive_inbox = snapshot.get("proactiveInbox")
            if (
                not isinstance(proactive_inbox, list)
                or not proactive_inbox
                or proactive_inbox[-1].get("candidateId") != "proreq-smoke"
            ):
                failures.append("desktop snapshot did not include the proactive inbox candidate")

            status, recent = _request_json(f"{base_url}/desktop/events/recent?limit=3", token=token)
            if status != 200:
                failures.append(f"desktop events recent returned {status}: {recent}")
            if [event.get("type") for event in recent.get("items", [])] != seeded["eventTypes"][-3:]:
                failures.append("desktop events recent did not return the seeded desktop event sequence")

            status, chat_recent = _request_json(f"{base_url}/desktop/chat/recent?limit=3", token=token)
            if status != 200:
                failures.append(f"desktop chat recent returned {status}: {chat_recent}")
            elif [item.get("turnId") for item in chat_recent.get("items", [])] != ["turn-smoke"]:
                failures.append("desktop chat recent did not return the runtime turn buffer")
            elif chat_recent.get("items", [])[-1].get("commandId") != "desktop-command-smoke":
                failures.append("desktop chat recent did not expose commandId")

            status, memory_recent = _request_json(f"{base_url}/desktop/memory/recent?limit=3", token=token)
            if status != 200:
                failures.append(f"desktop memory recent returned {status}: {memory_recent}")
            elif [item.get("eventId") for item in memory_recent.get("items", [])] != [seeded["recallEventId"]]:
                failures.append("desktop memory recent did not return the runtime memory event buffer")
            elif memory_recent.get("items", [])[-1].get("route", {}).get("selectedExperts") != ["recent_dialogue", "project_task"]:
                failures.append("desktop memory recent did not return sparse memory route details")

            status, proactive = _request_json(f"{base_url}/desktop/proactive/inbox", token=token)
            if status != 200:
                failures.append(f"desktop proactive inbox returned {status}: {proactive}")
            elif [item.get("candidateId") for item in proactive.get("items", [])] != ["proreq-smoke"]:
                failures.append("desktop proactive inbox did not return the runtime candidate")

            status, private_desktop_start = _post_json(
                f"{base_url}/desktop/private-desktop/start",
                {},
                token=token,
            )
            if status != 403 or private_desktop_start.get("error") != "owner_private_context_required":
                failures.append(
                    "desktop private desktop start did not dispatch to the owner-private route: "
                    f"{status}: {private_desktop_start}"
                )

            status, proactive_ack = _post_json(
                f"{base_url}/desktop/proactive/ack",
                {"candidateId": "proreq-smoke", "action": "read_locally"},
                token=token,
            )
            if status != 200:
                failures.append(f"desktop proactive ack returned {status}: {proactive_ack}")
            elif proactive_ack.get("status") != "read_locally" or not proactive_ack.get("ack_recorded"):
                failures.append(f"desktop proactive ack did not record read-local action: {proactive_ack}")
            status, proactive_after_ack = _request_json(f"{base_url}/desktop/proactive/inbox", token=token)
            if status != 200:
                failures.append(f"desktop proactive inbox after ack returned {status}: {proactive_after_ack}")
            elif proactive_after_ack.get("items") != []:
                failures.append("desktop proactive inbox should be empty after read-local ack")
        finally:
            server.shutdown()
            server.server_close()
            server_thread.join(timeout=5)
            asyncio.run_coroutine_threadsafe(runtime.shutdown(), loop).result(timeout=5)
            loop.call_soon_threadsafe(loop.stop)
            loop_thread.join(timeout=5)

    if failures:
        print("XinYu desktop REST smoke failed")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("XinYu desktop REST smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

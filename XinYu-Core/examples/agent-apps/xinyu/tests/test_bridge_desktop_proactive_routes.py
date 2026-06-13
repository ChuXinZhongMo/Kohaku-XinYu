from __future__ import annotations

import asyncio
import json
import threading
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import xinyu_bridge_desktop_proactive_routes as desktop_proactive_routes


def _write_proactive_state(root: Path, lines: list[str]) -> None:
    path = root / "memory/context/proactive_request_state.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def _state_runtime(root: Path) -> SimpleNamespace:
    return SimpleNamespace(
        xinyu_dir=root,
        _desktop_proactive_expired=lambda expires_at: expires_at == "past",
        _desktop_recent_owner_private_turns=lambda *, limit: ["recent owner turn"],
    )


def test_desktop_proactive_delivery_payload_projects_status_adapter_and_notes() -> None:
    item = {
        "candidateId": "candidate-1",
        "status": "ready",
        "claimId": 123,
        "ackStatus": None,
        "adapterMessageId": "adapter-message-1",
        "adapterError": " ".join(["adapter-error"] * 40),
        "notes": ["existing", "duplicate", "duplicate"],
    }

    payload = desktop_proactive_routes.desktop_proactive_delivery_payload(
        item,
        status_override="failed",
        notes=["duplicate", "new", *[f"extra-{index}" for index in range(12)]],
    )

    assert payload["candidateId"] == "candidate-1"
    assert payload["status"] == "failed"
    assert datetime.fromisoformat(payload["updatedAt"])
    assert payload["claimId"] == "123"
    assert payload["ackStatus"] == ""
    assert payload["adapterMessageHash"].startswith("sha256:")
    assert len(payload["adapterErrorPreview"]) <= 180
    assert payload["notes"] == [
        "existing",
        "duplicate",
        "new",
        "extra-0",
        "extra-1",
        "extra-2",
        "extra-3",
        "extra-4",
        "extra-5",
        "extra-6",
    ]


def test_desktop_apply_proactive_delivery_routes_final_and_active_statuses() -> None:
    calls: list[tuple[str, object]] = []
    runtime = SimpleNamespace(
        _desktop_remember_proactive_history=lambda payload: calls.append(("history", payload["candidateId"])),
        _desktop_remove_proactive_inbox=lambda candidate_id: calls.append(("remove", candidate_id)),
        _desktop_upsert_proactive_inbox=lambda payload: calls.append(("upsert", payload["candidateId"])),
    )

    desktop_proactive_routes.desktop_apply_proactive_delivery(
        runtime,
        {"candidateId": "candidate-final", "status": "answered"},
    )
    desktop_proactive_routes.desktop_apply_proactive_delivery(
        runtime,
        {"candidateId": "candidate-active", "status": "claimed"},
    )
    desktop_proactive_routes.desktop_apply_proactive_delivery(runtime, {"status": "answered"})

    assert calls == [
        ("history", "candidate-final"),
        ("remove", "candidate-final"),
        ("upsert", "candidate-active"),
    ]


def test_desktop_publish_proactive_candidate_ready_from_state_publishes_and_stores_event_id() -> None:
    calls: list[tuple[str, object]] = []
    item = {"candidateId": "candidate-1", "candidatePreview": "preview", "notes": ["existing"]}

    async def _publish(event_type, payload, **kwargs):
        calls.append(("publish", (event_type, payload, kwargs)))
        return {"id": "event-1"}

    runtime = SimpleNamespace(
        _desktop_proactive_item_from_state=lambda *, include_final: item,
        _desktop_proactive_existing=lambda candidate_id: {},
        _desktop_upsert_proactive_inbox=lambda received_item: calls.append(("upsert", dict(received_item))),
        _desktop_publish_event=_publish,
    )

    result = asyncio.run(
        desktop_proactive_routes.desktop_publish_proactive_candidate_ready_from_state(
            runtime,
            notes=["new", "new"],
        )
    )

    assert result == {"id": "event-1"}
    assert calls == [
        ("upsert", {"candidateId": "candidate-1", "candidatePreview": "preview", "notes": ["existing"]}),
        (
            "publish",
            (
                "proactive.candidate.ready",
                {
                    "candidateId": "candidate-1",
                    "candidatePreview": "preview",
                    "notes": ["existing", "new"],
                },
                {"privacy": "owner_private"},
            ),
        ),
        (
            "upsert",
            {
                "candidateId": "candidate-1",
                "candidatePreview": "preview",
                "notes": ["existing"],
                "readyEventId": "event-1",
            },
        ),
    ]


def test_desktop_publish_proactive_candidate_ready_from_state_reuses_existing_event() -> None:
    calls: list[tuple[str, object]] = []
    item = {"candidateId": "candidate-1", "candidatePreview": "preview"}
    runtime = SimpleNamespace(
        _desktop_proactive_item_from_state=lambda *, include_final: item,
        _desktop_proactive_existing=lambda candidate_id: {
            "readyEventId": "event-existing",
            "candidatePreview": "preview",
        },
        _desktop_upsert_proactive_inbox=lambda received_item: calls.append(("upsert", dict(received_item))),
        _desktop_publish_event=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not publish")),
    )

    result = asyncio.run(desktop_proactive_routes.desktop_publish_proactive_candidate_ready_from_state(runtime))

    assert result == {"id": "event-existing"}
    assert calls == [("upsert", item)]


def test_desktop_publish_proactive_candidate_ready_from_state_returns_empty_without_item() -> None:
    runtime = SimpleNamespace(
        _desktop_proactive_item_from_state=lambda *, include_final: {},
        _desktop_proactive_existing=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not read")),
    )

    assert asyncio.run(desktop_proactive_routes.desktop_publish_proactive_candidate_ready_from_state(runtime)) == {}


def test_desktop_schedule_proactive_candidate_ready_from_state_requires_bus_and_loop() -> None:
    assert (
        desktop_proactive_routes.desktop_schedule_proactive_candidate_ready_from_state(
            SimpleNamespace(desktop_event_bus=None)
        )
        is False
    )
    assert (
        desktop_proactive_routes.desktop_schedule_proactive_candidate_ready_from_state(
            SimpleNamespace(desktop_event_bus=object())
        )
        is False
    )


def test_desktop_schedule_proactive_candidate_ready_from_state_creates_task() -> None:
    calls: list[list[str]] = []

    async def run() -> bool:
        async def _publish(*, notes):
            calls.append(list(notes or []))
            return {"id": "event-1"}

        runtime = SimpleNamespace(
            desktop_event_bus=object(),
            _desktop_publish_proactive_candidate_ready_from_state=_publish,
        )
        scheduled = desktop_proactive_routes.desktop_schedule_proactive_candidate_ready_from_state(
            runtime,
            notes=["note-1"],
        )
        await asyncio.sleep(0)
        return scheduled

    assert asyncio.run(run()) is True
    assert calls == [["note-1"]]


def test_desktop_publish_initiative_candidate_threadsafe_builds_safe_item_and_publishes() -> None:
    calls: list[tuple[str, object]] = []
    runtime = SimpleNamespace(
        _desktop_proactive_existing=lambda candidate_id: {},
        _desktop_upsert_proactive_inbox=lambda item: calls.append(("upsert", dict(item))),
        _desktop_publish_event_threadsafe=lambda event_type, payload, **kwargs: calls.append(
            ("publish", (event_type, payload, kwargs))
        ),
    )

    result = desktop_proactive_routes.desktop_publish_initiative_candidate_threadsafe(
        runtime,
        {
            "candidateId": "candidate-1",
            "candidatePreview": "preview",
            "deliveryLevel": "",
            "claimable": True,
            "requiresOwnerAck": False,
            "notes": ["existing"],
        },
        notes=["new", "new"],
    )

    safe_item = {
        "candidateId": "candidate-1",
        "candidatePreview": "preview",
        "deliveryLevel": "state_only",
        "claimable": False,
        "requiresOwnerAck": True,
        "notes": ["existing", "new"],
    }
    assert result is True
    assert calls == [
        ("upsert", safe_item),
        ("publish", ("proactive.candidate.ready", safe_item, {"privacy": "owner_private"})),
    ]


def test_desktop_publish_initiative_candidate_threadsafe_suppresses_duplicates() -> None:
    calls: list[tuple[str, object]] = []
    runtime = SimpleNamespace(
        _desktop_proactive_existing=lambda candidate_id: {
            "source": "initiative_orchestrator",
            "candidatePreview": "preview",
        },
        _desktop_upsert_proactive_inbox=lambda item: calls.append(("upsert", dict(item))),
        _desktop_publish_event_threadsafe=lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("should not publish duplicate")
        ),
    )

    result = desktop_proactive_routes.desktop_publish_initiative_candidate_threadsafe(
        runtime,
        {"candidateId": "candidate-1", "candidatePreview": "preview", "source": "initiative_orchestrator"},
    )

    assert result is True
    assert calls == [
        (
            "upsert",
            {
                "candidateId": "candidate-1",
                "candidatePreview": "preview",
                "source": "initiative_orchestrator",
                "claimable": False,
                "deliveryLevel": "state_only",
                "requiresOwnerAck": True,
                "notes": [],
            },
        )
    ]


def test_desktop_publish_initiative_candidate_threadsafe_rejects_missing_candidate_id() -> None:
    assert desktop_proactive_routes.desktop_publish_initiative_candidate_threadsafe(SimpleNamespace(), {}) is False


def test_desktop_publish_proactive_delivery_item_applies_and_publishes_payload() -> None:
    calls: list[tuple[str, object]] = []

    async def _publish(event_type, payload, **kwargs):
        calls.append(("publish", event_type, payload, kwargs))
        return {"id": "event-1"}

    runtime = SimpleNamespace(
        _desktop_proactive_delivery_payload=lambda item, **kwargs: {
            **item,
            "status": kwargs["status_override"] or item["status"],
            "notes": list(kwargs["notes"] or []),
        },
        _desktop_apply_proactive_delivery=lambda payload: calls.append(("apply", payload)),
        _desktop_publish_event=_publish,
    )

    result = asyncio.run(
        desktop_proactive_routes.desktop_publish_proactive_delivery_item(
            runtime,
            {"candidateId": "candidate-1", "status": "ready"},
            status_override="failed",
            notes=["delivery_failed"],
        )
    )

    payload = {"candidateId": "candidate-1", "status": "failed", "notes": ["delivery_failed"]}
    assert result == {"id": "event-1"}
    assert calls == [
        ("apply", payload),
        (
            "publish",
            "proactive.delivery.updated",
            payload,
            {"privacy": "owner_private", "severity": "error"},
        ),
    ]


def test_desktop_publish_proactive_delivery_item_respects_explicit_severity() -> None:
    calls: list[dict[str, object]] = []

    async def _publish(event_type, payload, **kwargs):
        calls.append(kwargs)
        return {"id": "event-2"}

    runtime = SimpleNamespace(
        _desktop_proactive_delivery_payload=lambda item, **kwargs: {**item, "status": "failed"},
        _desktop_apply_proactive_delivery=lambda payload: None,
        _desktop_publish_event=_publish,
    )

    asyncio.run(
        desktop_proactive_routes.desktop_publish_proactive_delivery_item(
            runtime,
            {"candidateId": "candidate-1", "status": "failed"},
            severity="warn",
        )
    )

    assert calls == [{"privacy": "owner_private", "severity": "warn"}]


def test_desktop_publish_proactive_delivery_from_state_delegates_when_item_exists() -> None:
    calls: list[tuple[dict[str, object], dict[str, object]]] = []
    item = {"candidateId": "candidate-1", "status": "sent"}

    async def _publish(received_item, **kwargs):
        calls.append((received_item, kwargs))
        return {"id": "event-1"}

    runtime = SimpleNamespace(
        _desktop_proactive_item_from_state=lambda *, include_final: item if include_final else {},
        _desktop_publish_proactive_delivery_item=_publish,
    )

    result = asyncio.run(
        desktop_proactive_routes.desktop_publish_proactive_delivery_from_state(
            runtime,
            status_override="answered",
            notes=["owner_answered"],
            severity="warn",
        )
    )

    assert result == {"id": "event-1"}
    assert calls == [
        (
            item,
            {"status_override": "answered", "notes": ["owner_answered"], "severity": "warn"},
        )
    ]


def test_desktop_publish_proactive_delivery_from_state_returns_empty_without_item() -> None:
    runtime = SimpleNamespace(
        _desktop_proactive_item_from_state=lambda *, include_final: {},
        _desktop_publish_proactive_delivery_item=lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("should not publish")
        ),
    )

    assert asyncio.run(desktop_proactive_routes.desktop_publish_proactive_delivery_from_state(runtime)) == {}


def test_desktop_publish_proactive_delivery_from_state_threadsafe_applies_and_publishes() -> None:
    calls: list[tuple[str, object]] = []
    item = {"candidateId": "candidate-1", "status": "ready"}
    payload = {"candidateId": "candidate-1", "status": "failed", "notes": ["delivery_failed"]}
    runtime = SimpleNamespace(
        _desktop_proactive_item_from_state=lambda *, include_final: item if include_final else {},
        _desktop_proactive_delivery_payload=lambda received_item, **kwargs: payload,
        _desktop_apply_proactive_delivery=lambda received_payload: calls.append(("apply", received_payload)),
        _desktop_publish_event_threadsafe=lambda event_type, received_payload, **kwargs: calls.append(
            ("publish", (event_type, received_payload, kwargs))
        ),
    )

    desktop_proactive_routes.desktop_publish_proactive_delivery_from_state_threadsafe(runtime)

    assert calls == [
        ("apply", payload),
        (
            "publish",
            (
                "proactive.delivery.updated",
                payload,
                {"privacy": "owner_private", "severity": "error"},
            ),
        ),
    ]


def test_desktop_publish_proactive_delivery_from_state_threadsafe_returns_without_item() -> None:
    runtime = SimpleNamespace(
        _desktop_proactive_item_from_state=lambda *, include_final: {},
        _desktop_proactive_delivery_payload=lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("should not build payload")
        ),
    )

    desktop_proactive_routes.desktop_publish_proactive_delivery_from_state_threadsafe(runtime)


def test_desktop_proactive_inbox_primitives_manage_runtime_buffer() -> None:
    runtime = SimpleNamespace(
        _desktop_proactive_inbox={},
        _desktop_proactive_lock=threading.Lock(),
        _desktop_proactive_expired=lambda expires_at: expires_at == "past",
    )

    desktop_proactive_routes.desktop_upsert_proactive_inbox(
        runtime,
        {"candidateId": "candidate-1", "status": "ready", "source": "state"},
    )
    desktop_proactive_routes.desktop_upsert_proactive_inbox(
        runtime,
        {"candidateId": "candidate-1", "deliveryLevel": "preview_only"},
    )
    existing = desktop_proactive_routes.desktop_proactive_existing(runtime, "candidate-1")
    existing["status"] = "mutated-copy"

    assert runtime._desktop_proactive_inbox["candidate-1"] == {
        "candidateId": "candidate-1",
        "status": "ready",
        "source": "state",
        "deliveryLevel": "preview_only",
    }

    desktop_proactive_routes.desktop_upsert_proactive_inbox(
        runtime,
        {"candidateId": "initiative", "status": "ready", "source": "initiative_orchestrator"},
    )
    desktop_proactive_routes.desktop_remove_proactive_state_items(runtime)
    assert set(runtime._desktop_proactive_inbox) == {"initiative"}

    runtime._desktop_proactive_inbox.update(
        {
            "final": {"candidateId": "final", "status": "answered"},
            "expired": {"candidateId": "expired", "status": "ready", "expiresAt": "past"},
            "active": {"candidateId": "active", "status": "claimed", "expiresAt": "future"},
        }
    )
    desktop_proactive_routes.desktop_prune_proactive_inbox(runtime)
    assert set(runtime._desktop_proactive_inbox) == {"initiative", "active"}

    desktop_proactive_routes.desktop_remove_proactive_inbox(runtime, "active")
    assert set(runtime._desktop_proactive_inbox) == {"initiative"}
    desktop_proactive_routes.desktop_clear_proactive_inbox(runtime)
    assert runtime._desktop_proactive_inbox == {}


def test_desktop_proactive_item_from_state_projects_ready_claimable_item(tmp_path) -> None:
    _write_proactive_state(
        tmp_path,
        [
            "- status: ready",
            "- request_id: candidate-1",
            "- concrete_question: should this go out?",
            "- delivery_level: queue_owner_private",
            "- created_at: 2026-06-05T01:00:00+08:00",
            "- expires_at: future",
            "- kind: dream_share",
            "- source: proactive_request_loop",
            "- focus_kind: memory",
            "- focus_label: focus label",
            "- priority: high",
            "- request_family: proactive",
            "- thread_id: thread-1",
            "- requested_action: ask_owner",
            "- evidence_hash: evidence-1",
            "- dedupe_key: dedupe-1",
            "- why_now: because now matters",
            "- request_answer_state: pending",
            "- last_claim_id: claim-1",
            "- last_ack_status: queued",
            "- adapter_message_id: adapter-1",
            "- adapter_error: adapter error",
        ],
    )

    item = desktop_proactive_routes.desktop_proactive_item_from_state(_state_runtime(tmp_path))

    assert item["candidateId"] == "candidate-1"
    assert item["requestId"] == "candidate-1"
    assert item["status"] == "ready"
    assert item["deliveryLevel"] == "queue_owner_private"
    assert item["claimable"] is True
    assert item["requiresOwnerAck"] is False
    assert item["dedupeHash"] == desktop_proactive_routes.desktop_hash("dedupe-1")
    assert item["candidatePreview"]
    assert item["whyNowPreview"] == "because now matters"
    assert item["claimId"] == "claim-1"
    assert item["ackStatus"] == "queued"
    assert item["adapterMessageId"] == "adapter-1"
    assert item["adapterError"] == "adapter error"


def test_desktop_proactive_item_from_state_marks_owner_ack_only_items(tmp_path) -> None:
    cases = [
        ("candidate_only", "queue_owner_private"),
        ("ready", "preview_only"),
        ("ready", "state_only"),
    ]
    for status, delivery_level in cases:
        _write_proactive_state(
            tmp_path,
            [
                f"- status: {status}",
                f"- request_id: {status}-{delivery_level}",
                "- concrete_question: should this stay local?",
                f"- delivery_level: {delivery_level}",
            ],
        )

        item = desktop_proactive_routes.desktop_proactive_item_from_state(_state_runtime(tmp_path))

        assert item["claimable"] is False
        assert item["requiresOwnerAck"] is True


def test_desktop_proactive_item_from_state_handles_expired_and_unknown_status(tmp_path) -> None:
    _write_proactive_state(
        tmp_path,
        [
            "- status: ready",
            "- request_id: expired-1",
            "- concrete_question: expired question?",
            "- delivery_level: queue_owner_private",
            "- expires_at: past",
        ],
    )

    runtime = _state_runtime(tmp_path)
    assert desktop_proactive_routes.desktop_proactive_item_from_state(runtime) == {}
    expired = desktop_proactive_routes.desktop_proactive_item_from_state(runtime, include_final=True)
    assert expired["candidateId"] == "expired-1"
    assert expired["status"] == "expired"

    _write_proactive_state(
        tmp_path,
        [
            "- status: unknown",
            "- request_id: unknown-1",
            "- concrete_question: unknown question?",
        ],
    )
    assert desktop_proactive_routes.desktop_proactive_item_from_state(runtime, include_final=True) == {}


def test_desktop_proactive_item_from_state_falls_back_to_question_hash_for_missing_request_id(tmp_path) -> None:
    question = "fallback question?"
    _write_proactive_state(
        tmp_path,
        [
            "- status: ready",
            "- request_id: none",
            f"- concrete_question: {question}",
            "- delivery_level: claim_ack",
        ],
    )

    item = desktop_proactive_routes.desktop_proactive_item_from_state(_state_runtime(tmp_path))

    assert item["candidateId"] == desktop_proactive_routes.desktop_hash(question)
    assert item["requestId"] == "none"
    assert item["claimable"] is True


def test_desktop_current_proactive_question_requires_matching_request_id(tmp_path) -> None:
    path = tmp_path / "memory/context/proactive_request_state.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "- request_id: candidate-1",
                "- concrete_question: proactive smoke question?",
            ]
        ),
        encoding="utf-8",
    )
    runtime = SimpleNamespace(xinyu_dir=tmp_path)

    assert (
        desktop_proactive_routes.desktop_current_proactive_question(
            runtime,
            {"candidateId": "candidate-1", "requestId": "candidate-1"},
        )
        == "proactive smoke question?"
    )
    assert (
        desktop_proactive_routes.desktop_current_proactive_question(
            runtime,
            {"candidateId": "candidate-2", "requestId": "candidate-2"},
        )
        == ""
    )


def test_desktop_compact_proactive_history_dedupes_sorts_and_limits() -> None:
    rows = [
        {"candidateId": "old", "updatedAt": "2026-06-05T00:00:00+08:00", "value": "drop-duplicate"},
        {"candidateId": "old", "updatedAt": "2026-06-05T00:01:00+08:00", "value": "keep-duplicate"},
        {"candidateId": "", "updatedAt": "2026-06-05T00:02:00+08:00"},
        *[
            {
                "candidateId": f"candidate-{index:02d}",
                "createdAt": f"2026-06-05T00:{index + 2:02d}:00+08:00",
            }
            for index in range(22)
        ],
    ]

    compacted = desktop_proactive_routes.desktop_compact_proactive_history(rows)

    assert len(compacted) == desktop_proactive_routes.DESKTOP_PROACTIVE_HISTORY_MAX
    assert all(item.get("candidateId") for item in compacted)
    assert "drop-duplicate" not in {item.get("value") for item in compacted}
    assert compacted[0]["candidateId"] == "candidate-02"
    assert compacted[-1]["candidateId"] == "candidate-21"


def test_desktop_proactive_history_write_and_load_use_jsonl_buffer(tmp_path) -> None:
    traces: list[str] = []
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        _desktop_proactive_history=[],
        _desktop_proactive_lock=threading.Lock(),
        _trace_autonomous=traces.append,
    )

    desktop_proactive_routes.desktop_remember_proactive_history(
        runtime,
        {
            "candidateId": "candidate-1",
            "status": "answered",
            "updatedAt": "2026-06-05T01:00:00+08:00",
        },
    )

    path = tmp_path / desktop_proactive_routes.DESKTOP_PROACTIVE_HISTORY_REL
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert rows == [
        {
            "candidateId": "candidate-1",
            "status": "answered",
            "updatedAt": "2026-06-05T01:00:00+08:00",
            "handledAt": "2026-06-05T01:00:00+08:00",
            "event_time": "2026-06-05T01:00:00+08:00",
        }
    ]
    assert runtime._desktop_proactive_history == rows
    assert traces == []

    path.write_text(
        path.read_text(encoding="utf-8") + "\nnot-json\n" + json.dumps(
            {
                "candidateId": "candidate-2",
                "status": "dismissed",
                "updatedAt": "2026-06-05T01:01:00+08:00",
            }
        ),
        encoding="utf-8",
    )
    runtime._desktop_proactive_history = []
    desktop_proactive_routes.desktop_load_proactive_history(runtime)

    assert [item["candidateId"] for item in runtime._desktop_proactive_history] == ["candidate-1", "candidate-2"]

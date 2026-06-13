from __future__ import annotations

import asyncio
from types import SimpleNamespace

import xinyu_bridge_desktop_snapshot


def test_desktop_latest_memory_route_prefers_nested_route() -> None:
    route = xinyu_bridge_desktop_snapshot.desktop_latest_memory_route(
        [
            {"selectedExperts": ["older"]},
            {
                "route": {
                    "selectedExperts": ["recent_dialogue", "project_task", ""],
                    "currentTurnFacts": ["fact A", ""],
                }
            },
        ]
    )

    assert route == {
        "summary": "recent_dialogue + project_task",
        "selectedExperts": ["recent_dialogue", "project_task"],
        "currentTurnFacts": ["fact A"],
    }


def test_desktop_latest_memory_route_falls_back_to_flat_fields_and_empty() -> None:
    route = xinyu_bridge_desktop_snapshot.desktop_latest_memory_route(
        [
            "ignored",
            {"selectedExperts": ["flat", ""], "currentTurnFacts": ["flat fact", ""]},
        ]
    )

    assert route == {
        "summary": "flat",
        "selectedExperts": ["flat"],
        "currentTurnFacts": ["flat fact"],
    }
    assert xinyu_bridge_desktop_snapshot.desktop_latest_memory_route([]) == {
        "summary": "",
        "selectedExperts": [],
        "currentTurnFacts": [],
    }


def test_desktop_creative_writing_state_reads_markdown_fields(tmp_path) -> None:
    path = tmp_path / xinyu_bridge_desktop_snapshot.CREATIVE_WRITING_STATE_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "- status: drafting",
                "- creative_writing_mode: serial",
                "- current_project: River",
                "- today_chapters_written: 2",
                "- daily_target_chapters: 3",
                "- min_platform_chars: 800",
                "- target_platform_chars: 1200",
                "- total_chapters: 10",
                "- publish_ready_chapters: 4",
                "- publish_pending_chapters: 1",
                "- latest_chapter_path: chapters/010.md",
                "- publication_latest_chapter_path: publish/009.md",
                "- publication_log_path: logs/publish.md",
                "- next_action: revise chapter",
                "- reference_collection_status: active",
                "- reference_sources_collected: 7",
                "- reference_downloaded_sources: 5",
                "- reference_digest_path: refs/digest.md",
                "- reference_local_files: 6",
                "- reference_local_index_path: refs/index.json",
            ]
        ),
        encoding="utf-8",
    )

    state = xinyu_bridge_desktop_snapshot.desktop_creative_writing_state(tmp_path)

    assert state == {
        "creative_writing_status": "drafting",
        "creative_writing_mode": "serial",
        "creative_writing_project": "River",
        "creative_writing_today_chapters": 2,
        "creative_writing_daily_target": 3,
        "creative_writing_min_platform_chars": 800,
        "creative_writing_target_platform_chars": 1200,
        "creative_writing_total_chapters": 10,
        "creative_writing_publish_ready_chapters": 4,
        "creative_writing_publish_pending_chapters": 1,
        "creative_writing_latest_chapter": "chapters/010.md",
        "creative_writing_publication_latest_chapter": "publish/009.md",
        "creative_writing_publication_log": "logs/publish.md",
        "creative_writing_next_action": "revise chapter",
        "creative_writing_reference_status": "active",
        "creative_writing_reference_sources": 7,
        "creative_writing_reference_downloads": 5,
        "creative_writing_reference_digest": "refs/digest.md",
        "creative_writing_reference_local_files": 6,
        "creative_writing_reference_local_index": "refs/index.json",
    }


def test_desktop_creative_writing_state_uses_defaults(tmp_path) -> None:
    state = xinyu_bridge_desktop_snapshot.desktop_creative_writing_state(tmp_path)

    assert state["creative_writing_status"] == "unknown"
    assert state["creative_writing_mode"] == "novel_mode"
    assert state["creative_writing_today_chapters"] == 0
    assert state["creative_writing_reference_local_index"] == ""


def test_desktop_xinyu_state_projects_life_action_and_metrics(tmp_path) -> None:
    runtime = SimpleNamespace(xinyu_dir=tmp_path)

    state = xinyu_bridge_desktop_snapshot.desktop_xinyu_state(
        runtime,
        environment={
            "sensorQuality": "sampled",
            "physicalSensation": {"phrase": "warm", "pressure": "high", "tag": "active"},
        },
        entropy_state={
            "entropy_level": 0.42,
            "entropy_band": "clear",
            "resource_request": {"reason": "organize context"},
        },
        active_desires=[],
        proactive_items=[],
        recent_turns=[{"textPreview": "turn text"}],
        recent_memory_events=[
            {
                "route": {
                    "selectedExperts": ["recent_dialogue", "project_task"],
                    "currentTurnFacts": ["fact A"],
                }
            }
        ],
        action_digest={
            "digested_count": "3",
            "recent": [
                {
                    "seed_id": "seed-1",
                    "reflection_item_id": "reflection-1",
                    "pressure": "high",
                    "result": "success",
                    "seed_detail": {
                        "theme": "desktop cleanup",
                        "consumed_at": "2026-06-06T01:00:00+08:00",
                    },
                }
            ],
        },
        initiative_metrics={
            "observed": True,
            "event_count_24h": "2",
            "desktop_shown_count_24h": "1",
        },
    )

    assert state["version"] == 1
    assert state["mood_tag"] == "行动残留未散"
    assert state["action_experience_count"] == 3
    assert state["action_residue_route"] == "已进梦境和反思"
    assert state["action_residue_seed_id"] == "seed-1"
    assert state["latest_memory_route_summary"] == "recent_dialogue + project_task"
    assert state["latest_memory_current_turn_facts"] == ["fact A"]
    assert state["initiative_metrics"]["observed"] is True
    assert state["initiative_metrics"]["eventCount24h"] == 2
    assert state["creative_writing_status"] == "unknown"


def test_desktop_event_state_delegates_to_runtime_event_bus() -> None:
    class _EventBus:
        async def snapshot(self) -> dict[str, object]:
            return {
                "version": 1,
                "max_events": 200,
                "buffer_size": 3,
                "latest_event_id": "event-1",
                "subscriber_count": 2,
            }

    result = asyncio.run(
        xinyu_bridge_desktop_snapshot.desktop_event_state(SimpleNamespace(desktop_event_bus=_EventBus()))
    )

    assert result == {
        "version": 1,
        "available": True,
        "max_events": 200,
        "buffer_size": 3,
        "latest_event_id": "event-1",
        "subscriber_count": 2,
    }


def test_desktop_services_projects_runtime_service_status(tmp_path) -> None:
    runtime = SimpleNamespace(
        desktop_ws_server=SimpleNamespace(server=object(), bound_port=17891),
        _closed=False,
        memory_root=tmp_path,
    )

    services = xinyu_bridge_desktop_snapshot.desktop_services(runtime)

    assert services[0]["service"] == "core"
    assert services[0]["status"] == "ready"
    assert services[1] == {
        "service": "desktop_events",
        "status": "ready",
        "port": 17891,
        "message": "desktop event stream dark launch",
    }
    assert services[2] == {
        "service": "memory",
        "status": "ready",
        "message": "local memory root",
    }


def test_desktop_memory_route_payload_handles_empty_route_plan() -> None:
    assert xinyu_bridge_desktop_snapshot.desktop_memory_route_payload(None) == {
        "version": 1,
        "selectedExperts": [],
        "allowedSources": [],
        "allowedMemoryRefs": [],
        "currentTurnFacts": [],
        "decisions": [],
        "notes": [],
    }


def test_desktop_memory_route_payload_projects_route_plan_fields() -> None:
    route_plan = SimpleNamespace(
        selected_experts=["recent_dialogue", "", "project_task"],
        allowed_sources=["memory", "runtime"],
        allowed_memory_refs=[f"ref-{index}" for index in range(14)],
        current_turn_facts=["fact A", "", "fact B"],
        decisions=[
            SimpleNamespace(
                expert="recent_dialogue",
                score=0.98765,
                selected=True,
                reasons=["matched current turn", ""],
            )
        ],
        notes=["note A", ""],
    )

    payload = xinyu_bridge_desktop_snapshot.desktop_memory_route_payload(route_plan)

    assert payload == {
        "version": 1,
        "selectedExperts": ["recent_dialogue", "project_task"],
        "allowedSources": ["memory", "runtime"],
        "allowedMemoryRefs": [f"ref-{index}" for index in range(12)],
        "currentTurnFacts": ["fact A", "fact B"],
        "decisions": [
            {
                "expert": "recent_dialogue",
                "score": 0.988,
                "selected": True,
                "reasons": ["matched current turn"],
            }
        ],
        "notes": ["note A"],
    }


def test_desktop_recall_item_projects_memory_recall_fields() -> None:
    item = SimpleNamespace(
        recall_id="recall-1",
        source="dialogue",
        scope="owner_private",
        time="2026-06-05T12:00:00+08:00",
        speaker="owner",
        summary=" ".join(["summary"] * 60),
        relevance=" ".join(["relevance"] * 40),
        confidence="high",
        score=0.87654,
        message_id=123,
        memory_ref="memory/ref/" + ("x" * 260),
    )

    payload = xinyu_bridge_desktop_snapshot.desktop_recall_item(item)

    assert payload["recallId"] == "recall-1"
    assert payload["source"] == "dialogue"
    assert payload["scope"] == "owner_private"
    assert payload["speaker"] == "owner"
    assert payload["confidence"] == "high"
    assert payload["score"] == 0.877
    assert payload["messageId"] == 123
    assert len(payload["summaryPreview"]) <= 220
    assert len(payload["relevancePreview"]) <= 180
    assert len(payload["memoryRef"]) == 240
    assert payload["memoryRefHash"].startswith("sha256:")


def test_desktop_session_label_projects_session_kind_and_contact() -> None:
    class _Runtime:
        def _desktop_text_preview(self, text: str, *, limit: int) -> str:
            return text[:limit]

        def _desktop_hash(self, value: object, *, length: int = 16) -> str:
            return f"hash{length}:{value}" if value else ""

    runtime = _Runtime()

    assert (
        xinyu_bridge_desktop_snapshot.desktop_session_label(
            runtime,
            {},
            session_kind="desktop_private",
            metadata={},
        )
        == "桌面主人"
    )
    assert (
        xinyu_bridge_desktop_snapshot.desktop_session_label(
            runtime,
            {"sender_name": "Alice", "group_id": "20002"},
            session_kind="qq_group",
            metadata={},
        )
        == "QQ群聊 / Alice"
    )
    assert (
        xinyu_bridge_desktop_snapshot.desktop_session_label(
            runtime,
            {"group_id": "20002"},
            session_kind="qq_group",
            metadata={},
        )
        == "QQ群聊 / 群#hash8:20002"
    )
    assert (
        xinyu_bridge_desktop_snapshot.desktop_session_label(
            runtime,
            {"sender_name": "Owner", "user_id": "10001"},
            session_kind="qq_private",
            metadata={"is_owner_user": "true"},
        )
        == "主人QQ / Owner"
    )
    assert (
        xinyu_bridge_desktop_snapshot.desktop_session_label(
            runtime,
            {"user_id": "10002"},
            session_kind="qq_private",
            metadata={"is_trusted_user": True},
        )
        == "可信QQ / #hash8:10002"
    )
    assert (
        xinyu_bridge_desktop_snapshot.desktop_session_label(
            runtime,
            {},
            session_kind="qq_private",
            metadata={},
        )
        == "外部QQ / 未知联系人"
    )
    assert (
        xinyu_bridge_desktop_snapshot.desktop_session_label(
            runtime,
            {},
            session_kind="system",
            metadata={},
        )
        == "系统窗口"
    )


def test_desktop_account_label_projects_account_identity() -> None:
    assert (
        xinyu_bridge_desktop_snapshot.desktop_account_label(
            None,
            {},
            session_kind="desktop_private",
            metadata={},
            user_display_id="",
            group_display_id="",
        )
        == "桌面 owner"
    )
    assert (
        xinyu_bridge_desktop_snapshot.desktop_account_label(
            None,
            {},
            session_kind="qq_group",
            metadata={},
            user_display_id="10001",
            group_display_id="20002",
        )
        == "群 20002 / QQ 10001"
    )
    assert (
        xinyu_bridge_desktop_snapshot.desktop_account_label(
            None,
            {},
            session_kind="qq_group",
            metadata={},
            user_display_id="",
            group_display_id="",
        )
        == "QQ群聊"
    )
    assert (
        xinyu_bridge_desktop_snapshot.desktop_account_label(
            None,
            {},
            session_kind="qq_private",
            metadata={"is_owner_user": True},
            user_display_id="10001",
            group_display_id="",
        )
        == "主人QQ 10001"
    )
    assert (
        xinyu_bridge_desktop_snapshot.desktop_account_label(
            None,
            {},
            session_kind="qq_private",
            metadata={"is_trusted_user": "true"},
            user_display_id="",
            group_display_id="",
        )
        == "可信QQ"
    )
    assert (
        xinyu_bridge_desktop_snapshot.desktop_account_label(
            None,
            {},
            session_kind="qq_private",
            metadata={},
            user_display_id="10003",
            group_display_id="",
        )
        == "外部QQ 10003"
    )
    assert (
        xinyu_bridge_desktop_snapshot.desktop_account_label(
            None,
            {"platform": "bridge"},
            session_kind="system",
            metadata={},
            user_display_id="",
            group_display_id="",
        )
        == "bridge"
    )


def test_desktop_active_desires_returns_empty_when_life_kernel_has_no_desire(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_evaluate_life_kernel(**kwargs):
        calls.append(kwargs)
        return None

    monkeypatch.setattr(xinyu_bridge_desktop_snapshot, "evaluate_life_kernel", fake_evaluate_life_kernel)
    runtime = SimpleNamespace()

    result = asyncio.run(
        xinyu_bridge_desktop_snapshot.desktop_active_desires(
            runtime,
            environment={"sensorQuality": "ok"},
            entropy_state={"entropy": 0.1},
            proactive_items=[{"candidateId": "p1"}],
            recent_turns=[{"turnId": "t1"}],
            recent_memory_events=[{"eventId": "m1"}],
            self_choice_state={"affect": "warm"},
        )
    )

    assert result == []
    assert calls == [
        {
            "environment": {"sensorQuality": "ok"},
            "entropy_state": {"entropy": 0.1},
            "proactive_items": [{"candidateId": "p1"}],
            "recent_turns": [{"turnId": "t1"}],
            "recent_memory_events": [{"eventId": "m1"}],
            "self_choice_state": {"affect": "warm"},
        }
    ]


def test_desktop_active_desires_records_non_metabolism_life_choice(monkeypatch) -> None:
    class _Desire:
        chosen_action = "leave_note_on_desk"

        def model_dump(self, *, mode: str) -> dict[str, object]:
            assert mode == "json"
            return {"chosen_action": self.chosen_action, "visible_trace": "trace"}

    class _SelfChoiceStore:
        def __init__(self) -> None:
            self.recorded: list[str] = []

        async def record_life_choice(self, choice: str) -> None:
            self.recorded.append(choice)

    monkeypatch.setattr(xinyu_bridge_desktop_snapshot, "evaluate_life_kernel", lambda **kwargs: _Desire())
    store = _SelfChoiceStore()
    runtime = SimpleNamespace(self_choice_store=store)

    result = asyncio.run(
        xinyu_bridge_desktop_snapshot.desktop_active_desires(
            runtime,
            environment={},
            entropy_state={},
            proactive_items=[],
            recent_turns=[],
            recent_memory_events=[],
        )
    )

    assert store.recorded == ["leave_note_on_desk"]
    assert result == [{"chosen_action": "leave_note_on_desk", "visible_trace": "trace"}]


def test_desktop_active_desires_creates_metabolism_ticket_when_missing(monkeypatch, tmp_path) -> None:
    create_calls: list[tuple[object, dict[str, object]]] = []

    class _Desire:
        chosen_action = "request_metabolism_window"

        def model_dump(self, *, mode: str) -> dict[str, object]:
            assert mode == "json"
            return {
                "chosen_action": self.chosen_action,
                "entropy": {"resource_request": {"seconds": 120}},
            }

    class _Entropy:
        def model_dump(self, *, mode: str) -> dict[str, object]:
            assert mode == "json"
            return {"entropy_level": 0.9}

    class _SelfChoiceStore:
        def __init__(self) -> None:
            self.recorded: list[str] = []

        async def record_life_choice(self, choice: str) -> None:
            self.recorded.append(choice)

        async def dream_bias_snapshot(self) -> dict[str, object]:
            return {"dream": "bias"}

    def fake_create_ticket(root, **kwargs):
        create_calls.append((root, kwargs))
        return {"ticket": {"ticket_id": "ticket-1", "status": "requested"}}

    monkeypatch.setattr(xinyu_bridge_desktop_snapshot, "evaluate_life_kernel", lambda **kwargs: _Desire())
    monkeypatch.setattr(xinyu_bridge_desktop_snapshot, "create_metabolism_ticket", fake_create_ticket)
    store = _SelfChoiceStore()
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        self_choice_store=store,
        _desktop_open_metabolism_ticket=lambda: {},
        _metabolism_input_window=lambda **kwargs: {"window": kwargs},
    )

    result = asyncio.run(
        xinyu_bridge_desktop_snapshot.desktop_active_desires(
            runtime,
            environment={},
            entropy_state=_Entropy(),
            proactive_items=[{"candidateId": "p1"}],
            recent_turns=[{"turnId": "t1"}],
            recent_memory_events=[{"eventId": "m1"}],
        )
    )

    assert store.recorded == ["request_metabolism_window"]
    assert result[0]["metabolism_ticket_id"] == "ticket-1"
    assert result[0]["metabolism_ticket_status"] == "requested"
    assert result[0]["metabolism_ticket"] == {"ticket_id": "ticket-1", "status": "requested"}
    assert create_calls == [
        (
            tmp_path,
            {
                "entropy_state": {"entropy_level": 0.9},
                "resource_request": {"seconds": 120},
                "active_desire": {
                    "chosen_action": "request_metabolism_window",
                    "entropy": {"resource_request": {"seconds": 120}},
                    "metabolism_ticket_id": "ticket-1",
                    "metabolism_ticket_status": "requested",
                    "metabolism_ticket": {"ticket_id": "ticket-1", "status": "requested"},
                },
                "input_window": {
                    "window": {
                        "proactive_items": [{"candidateId": "p1"}],
                        "recent_turns": [{"turnId": "t1"}],
                        "recent_memory_events": [{"eventId": "m1"}],
                        "self_choice_dream_bias": {"dream": "bias"},
                    }
                },
            },
        )
    ]


def test_desktop_turn_base_projects_common_event_fields() -> None:
    calls: dict[str, object] = {}

    class _Runtime:
        def _desktop_session_kind(self, payload: dict[str, object]) -> str:
            calls["session_kind_payload"] = payload
            return "qq_private"

        def _desktop_display_id(self, value: object) -> str:
            return f"display:{value}" if value else ""

        def _desktop_hash(self, value: object, *, length: int = 16) -> str:
            return f"hash{length}:{value}"

        def _desktop_session_label(
            self,
            payload: dict[str, object],
            *,
            session_kind: str,
            metadata: dict[str, object],
        ) -> str:
            calls["session_label"] = (payload, session_kind, metadata)
            return "session-label"

        def _desktop_account_label(
            self,
            payload: dict[str, object],
            *,
            session_kind: str,
            metadata: dict[str, object],
            user_display_id: str,
            group_display_id: str,
        ) -> str:
            calls["account_label"] = (payload, session_kind, metadata, user_display_id, group_display_id)
            return "account-label"

        def _desktop_avatar_url(
            self,
            payload: dict[str, object],
            *,
            session_kind: str,
            user_display_id: str,
        ) -> str:
            calls["avatar"] = (payload, session_kind, user_display_id)
            return "avatar-url"

        def _desktop_group_avatar_url(self, group_display_id: str) -> str:
            return f"group-avatar:{group_display_id}"

        def _desktop_text_preview(self, text: str, *, limit: int) -> str:
            return f"{limit}:{text}"

    payload = {
        "source": "",
        "adapter": "onebot",
        "platform": "qq",
        "message_type": "private",
        "sender_name": "sender",
        "user_id": "10001",
        "group_id": "20002",
        "message_id": "30003",
        "command_id": "command-fallback",
        "metadata": {
            "desktop_command_id": "command-1",
            "is_owner_user": "true",
            "is_trusted_user": True,
            "user_trust_level": "owner",
        },
    }

    result = xinyu_bridge_desktop_snapshot.desktop_turn_base(
        _Runtime(),
        payload,
        session_key="session-1",
        turn_id="turn-1",
    )

    assert result == {
        "turnId": "turn-1",
        "commandId": "command-1",
        "sessionHash": "hash16:session-1",
        "sessionKind": "qq_private",
        "sessionLabel": "session-label",
        "accountLabel": "account-label",
        "avatarUrl": "avatar-url",
        "groupAvatarUrl": "group-avatar:display:20002",
        "platform": "qq",
        "source": "onebot",
        "messageType": "private",
        "isOwner": True,
        "isTrusted": True,
        "trustLevel": "owner",
        "senderName": "80:sender",
        "userDisplayId": "display:10001",
        "groupDisplayId": "display:20002",
        "userHash": "hash16:10001",
        "groupHash": "hash16:20002",
        "messageHash": "hash16:30003",
    }
    assert calls["session_kind_payload"] is payload
    assert calls["session_label"] == (payload, "qq_private", payload["metadata"])
    assert calls["account_label"] == (
        payload,
        "qq_private",
        payload["metadata"],
        "display:10001",
        "display:20002",
    )
    assert calls["avatar"] == (payload, "qq_private", "display:10001")

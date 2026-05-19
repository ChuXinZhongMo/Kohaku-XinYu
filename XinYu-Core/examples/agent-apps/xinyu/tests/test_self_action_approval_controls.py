from __future__ import annotations

import json
from pathlib import Path

import pytest

from xinyu_core_bridge import XinYuBridgeRuntime
from xinyu_qq_gateway import GatewayConfig, NativeQQGateway
from xinyu_self_action_gateway import run_self_action_gateway
from xinyu_self_chosen_goal_ecology import run_self_chosen_goal_ecology


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _seed_self_code_candidate(root: Path) -> None:
    _write(root / "xinyu_self_chosen_goal_ecology.py", "def ok():\n    return 'goal'\n")
    _write(root / "xinyu_goal_outcome_observer.py", "def ok():\n    return 'observer'\n")
    _write(root / "xinyu_self_action_gateway.py", "def ok():\n    return 'action'\n")
    _write(root / "memory/context/recent_context.md", "Codex runtime pytest work remains active.")
    run_self_chosen_goal_ecology(root, checked_at="2026-05-16T10:00:00+08:00", trigger="test")
    run_self_action_gateway(root, checked_at="2026-05-16T10:01:00+08:00", trigger="test")


def _runtime(tmp_path: Path) -> XinYuBridgeRuntime:
    return XinYuBridgeRuntime(
        xinyu_dir=tmp_path,
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


@pytest.mark.asyncio
async def test_self_action_approval_request_pushes_to_owner_qq(tmp_path: Path) -> None:
    _write(tmp_path / "xinyu_qq_gateway.config.json", json.dumps({"owner_user_ids": ["42"]}))
    runtime = _runtime(tmp_path)
    try:
        notes = runtime._maybe_enqueue_self_action_approval_to_qq(
            {
                "approval_queue_items": [
                    {
                        "queued": True,
                        "queue_id": "selfaction-approval-test",
                        "goal_id": "continue_bounded_work",
                        "action_kind": "self_code_patch_request",
                        "reason": "needs a focused patch",
                        "params": {"approval_scope": "one_time_patch"},
                    }
                ]
            },
            checked_at="2026-05-16T10:01:00+08:00",
        )
    finally:
        await runtime.shutdown()

    queue = json.loads((tmp_path / "memory/context/qq_outbox_queue.json").read_text(encoding="utf-8"))
    item = queue["items"][0]
    metadata = item["metadata"]
    assert "self_action_qq_push:selfaction-approval-test/queued" in notes
    assert item["source"] == "self_action_approval_request"
    assert "我刚刚自己转了一圈" in item["message"]
    assert "小地方硌着" in item["message"]
    assert "递工单" in item["message"]
    assert "引用这条回「批准」" in item["message"]
    assert "我会碰哪里" not in item["message"]
    assert "你点头以后" not in item["message"]
    assert "任务" not in item["message"]
    assert "selfaction-approval-test" not in item["message"]
    assert metadata["qq_visible_control_plane_allowed"] is True
    assert metadata["self_action_queue_id"] == "selfaction-approval-test"
    assert metadata["self_action_authorize_existing"] is False


@pytest.mark.asyncio
async def test_self_action_prepared_patch_push_uses_human_readable_qq_text(tmp_path: Path) -> None:
    _write(tmp_path / "xinyu_qq_gateway.config.json", json.dumps({"owner_user_ids": ["42"]}))
    runtime = _runtime(tmp_path)
    try:
        notes = runtime._maybe_enqueue_self_action_prepared_patch_to_qq(
            {
                "status": "prepared",
                "action_kind": "self_code_patch_request",
                "queue_id": "selfaction-approval-test",
                "approval_id": "selfaction-decision-test",
                "task_id": "selfaction-patch-test",
                "goal_id": "continue_bounded_work",
                "approval_scope": "focused_xinyu_app_patch",
                "codex": {"status": "not_requested"},
            },
            checked_at="2026-05-16T10:02:00+08:00",
        )
    finally:
        await runtime.shutdown()

    queue = json.loads((tmp_path / "memory/context/qq_outbox_queue.json").read_text(encoding="utf-8"))
    item = queue["items"][0]
    metadata = item["metadata"]
    assert "self_action_prepared_qq_push:selfaction-approval-test/queued" in notes
    assert item["source"] == "self_action_prepared_patch_authorization"
    assert "我把刚才那个念头收住了" in item["message"]
    assert "一开口就像递工单" in item["message"]
    assert "不能自己批准自己" in item["message"]
    assert "引用这条回「批准」" in item["message"]
    assert "我会碰哪里" not in item["message"]
    assert "你点头以后" not in item["message"]
    assert "任务" not in item["message"]
    assert "selfaction-approval-test" not in item["message"]
    assert "selfaction-patch-test" not in item["message"]
    assert metadata["self_action_queue_id"] == "selfaction-approval-test"
    assert metadata["self_action_task_id"] == "selfaction-patch-test"
    assert metadata["self_action_authorize_existing"] is True


@pytest.mark.asyncio
async def test_desktop_self_action_approval_approves_and_prepares_patch_task(tmp_path: Path) -> None:
    _seed_self_code_candidate(tmp_path)
    runtime = XinYuBridgeRuntime(
        xinyu_dir=tmp_path,
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

    try:
        result = await runtime.desktop_self_action_approval(
            {"queueId": "latest", "decision": "approved", "execute": True, "decidedBy": "owner_desktop"}
        )
    finally:
        await runtime.shutdown()

    self_action = result["selfAction"]
    patch = self_action["patchExecutor"]
    assert result["accepted"] is True
    assert result["decision"] == "approved"
    assert result["execution"]["executed_count"] == 1
    assert result["patch_executor"]["status"] == "prepared"
    assert patch["status"] == "prepared"
    assert patch["codexStatus"] == "not_requested"
    assert patch["taskId"].startswith("selfaction-patch-")
    assert self_action["approvalQueue"]["pendingCount"] == 0
    assert "小改动收住了" in result["reply"]


@pytest.mark.asyncio
async def test_desktop_self_action_approval_can_authorize_codex_once(tmp_path: Path) -> None:
    _seed_self_code_candidate(tmp_path)
    runtime = XinYuBridgeRuntime(
        xinyu_dir=tmp_path,
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
    calls: dict[str, object] = {}

    async def fake_codex_execute(payload: dict[str, object]) -> dict[str, object]:
        calls["payload"] = payload
        return {
            "accepted": True,
            "reply": "Codex 已后台排队。",
            "request_path": "runtime/codex_delegate/requests/selfaction.md",
            "report_path": "runtime/codex_delegate/outbox/selfaction-report.md",
            "notes": ["codex_delegate_background:scheduled"],
        }

    runtime.codex_execute = fake_codex_execute  # type: ignore[method-assign]

    try:
        result = await runtime.desktop_self_action_approval(
            {
                "queueId": "latest",
                "decision": "approved",
                "execute": True,
                "authorizeCodex": True,
                "decidedBy": "owner_desktop",
            }
        )
    finally:
        await runtime.shutdown()

    payload = calls["payload"]
    assert isinstance(payload, dict)
    metadata = payload.get("metadata")
    assert isinstance(metadata, dict)
    assert result["accepted"] is True
    assert result["codex_execution_authorized"] is True
    assert result["patch_executor"]["status"] == "codex_scheduled"
    assert result["patch_executor"]["codex"]["status"] == "scheduled"
    assert "codex_payload" not in result["patch_executor"]
    assert result["codex_execution"]["accepted"] is True
    assert payload["background"] is True
    assert metadata["owner_local_write_approved"] is True
    assert metadata["self_action_patch_executor"] is True
    assert "用 Codex 执行" in str(payload["text"])
    assert "你点头了" in result["reply"]
    assert "这一小步" in result["reply"]
    assert "它动完" not in result["reply"]


@pytest.mark.asyncio
async def test_desktop_self_action_approval_can_authorize_existing_prepared_patch(tmp_path: Path) -> None:
    _seed_self_code_candidate(tmp_path)
    runtime = XinYuBridgeRuntime(
        xinyu_dir=tmp_path,
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
    calls: dict[str, object] = {}

    async def fake_codex_execute(payload: dict[str, object]) -> dict[str, object]:
        calls["payload"] = payload
        return {
            "accepted": True,
            "reply": "Codex 已后台排队。",
            "request_path": "runtime/codex_delegate/requests/selfaction.md",
            "report_path": "runtime/codex_delegate/outbox/selfaction-report.md",
            "notes": ["codex_delegate_background:scheduled"],
        }

    runtime.codex_execute = fake_codex_execute  # type: ignore[method-assign]

    try:
        prepared = await runtime.desktop_self_action_approval(
            {
                "queueId": "latest",
                "decision": "approved",
                "execute": True,
                "authorizeCodex": False,
                "decidedBy": "owner_desktop",
            }
        )
        scheduled = await runtime.desktop_self_action_approval(
            {
                "queueId": "latest",
                "decision": "approved",
                "execute": True,
                "authorizeCodex": True,
                "authorizeExisting": True,
                "decidedBy": "owner_desktop",
            }
        )
    finally:
        await runtime.shutdown()

    payload = calls["payload"]
    assert isinstance(payload, dict)
    assert prepared["patch_executor"]["status"] == "prepared"
    assert scheduled["accepted"] is True
    assert scheduled["status"] == "codex_scheduled"
    assert scheduled["patch_executor"]["codex"]["status"] == "scheduled"
    assert scheduled["codex_execution"]["accepted"] is True
    assert payload["background"] is True
    assert scheduled["selfAction"]["patchExecutor"]["codexStatus"] == "scheduled"


def test_qq_owner_private_self_action_approval_command_routes_to_control_plane(tmp_path: Path) -> None:
    gateway = NativeQQGateway(
        GatewayConfig(
            bridge_token="smoke-token",
            whitelist_user_ids=frozenset({"42"}),
            owner_user_ids=frozenset({"42"}),
            gateway_ack_spool_path=str(tmp_path / "ack_spool.jsonl"),
        )
    )
    event = {
        "post_type": "message",
        "message_type": "private",
        "user_id": 42,
        "message_id": 1001,
        "time": 1_762_000_000,
        "message": [{"type": "text", "data": {"text": "/sa approve selfaction-approval-test"}}],
        "raw_message": "/sa approve selfaction-approval-test",
    }

    prepared = gateway.prepare_message(event)

    assert prepared is not None
    assert prepared.route == "self_action_approval"
    assert prepared.payload["queueId"] == "selfaction-approval-test"
    assert prepared.payload["decision"] == "approved"
    assert prepared.payload["execute"] is True
    assert prepared.payload["authorizeCodex"] is True
    assert prepared.payload["authorizeExisting"] is True
    assert prepared.payload["decidedBy"] == "owner_qq"


def test_qq_owner_can_quote_pushed_self_action_message_to_approve(tmp_path: Path) -> None:
    gateway = NativeQQGateway(
        GatewayConfig(
            bridge_token="smoke-token",
            whitelist_user_ids=frozenset({"42"}),
            owner_user_ids=frozenset({"42"}),
            gateway_ack_spool_path=str(tmp_path / "ack_spool.jsonl"),
        )
    )
    gateway.xinyu_dir = tmp_path
    _write(
        tmp_path / "memory/context/qq_outbox_queue.json",
        json.dumps(
            {
                "items": [
                    {
                        "id": "qq-outbox-self-action",
                        "status": "sent",
                        "adapter_message_id": "9001",
                        "metadata": {
                            "self_action_approval_request": True,
                            "self_action_queue_id": "selfaction-approval-quoted",
                            "self_action_authorize_existing": True,
                        },
                    }
                ]
            }
        ),
    )
    event = {
        "post_type": "message",
        "message_type": "private",
        "user_id": 42,
        "message_id": 1003,
        "time": 1_762_000_000,
        "message": [
            {"type": "reply", "data": {"id": "9001"}},
            {"type": "text", "data": {"text": "批准"}},
        ],
        "raw_message": "[CQ:reply,id=9001]批准",
    }

    prepared = gateway.prepare_message(event)

    assert prepared is not None
    assert prepared.route == "self_action_approval"
    assert prepared.payload["queueId"] == "selfaction-approval-quoted"
    assert prepared.payload["decision"] == "approved"
    assert prepared.payload["authorizeCodex"] is True
    assert prepared.payload["authorizeExisting"] is True
    assert prepared.payload["reply_message_id"] == "9001"
    assert prepared.payload["metadata"]["quoted_self_action_message"] is True


def test_qq_non_owner_cannot_route_self_action_approval(tmp_path: Path) -> None:
    gateway = NativeQQGateway(
        GatewayConfig(
            bridge_token="smoke-token",
            whitelist_user_ids=frozenset({"43"}),
            owner_user_ids=frozenset({"42"}),
            gateway_ack_spool_path=str(tmp_path / "ack_spool.jsonl"),
        )
    )
    event = {
        "post_type": "message",
        "message_type": "private",
        "user_id": 43,
        "message_id": 1002,
        "time": 1_762_000_000,
        "message": [{"type": "text", "data": {"text": "/sa approve latest"}}],
        "raw_message": "/sa approve latest",
    }

    assert gateway.prepare_message(event) is None

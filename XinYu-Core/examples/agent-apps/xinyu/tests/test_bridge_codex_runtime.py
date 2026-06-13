from __future__ import annotations

import asyncio
import json
from datetime import datetime
from http import HTTPStatus
from pathlib import Path
from types import SimpleNamespace

import pytest

import xinyu_bridge_codex_runtime
from xinyu_bridge_errors import BridgeRequestError
from xinyu_dialogue_working_memory import save_dialogue_tail


class _Runtime:
    def __init__(self, xinyu_dir: Path) -> None:
        self.xinyu_dir = xinyu_dir


def test_codex_runtime_delegate_running_reports_lock_state() -> None:
    state = xinyu_bridge_codex_runtime.codex_delegate_running(
        Path("unused"),
        delegate_locked=True,
        window_title="Test codex",
    )

    assert state == {
        "running": True,
        "status": "running",
        "source": "lock",
        "visible_window_title": "Test codex",
    }


def test_codex_runtime_delegate_running_for_runtime_uses_lock_state(tmp_path: Path) -> None:
    runtime = _Runtime(tmp_path)
    runtime._codex_delegate_lock = SimpleNamespace(locked=lambda: True)

    state = xinyu_bridge_codex_runtime.codex_delegate_running_for_runtime(runtime)

    assert state["running"] is True
    assert state["source"] == "lock"
    assert state["visible_window_title"] == "Xinyu codex"


def test_codex_runtime_delegate_running_reads_presence_state(tmp_path: Path) -> None:
    path = tmp_path / "runtime/codex_presence_state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "status": "running",
                "job_id": "codex-qq-test",
                "visible_window_title": "Xinyu codex",
                "report_label": "codex-qq-test-report.md",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    state = xinyu_bridge_codex_runtime.codex_delegate_running(tmp_path, delegate_locked=False)

    assert state["running"] is True
    assert state["status"] == "running"
    assert state["job_id"] == "codex-qq-test"
    assert state["visible_window_title"] == "Xinyu codex"
    assert state["report_label"] == "codex-qq-test-report.md"
    assert state["stale"] is False


def test_codex_runtime_delegate_running_marks_stale_presence_not_running(tmp_path: Path) -> None:
    path = tmp_path / "runtime/codex_presence_state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"status": "running", "updated_at": "old", "job_id": "codex-old"}),
        encoding="utf-8",
    )

    state = xinyu_bridge_codex_runtime.codex_delegate_running(
        tmp_path,
        delegate_locked=False,
        timeout_seconds=100,
        seconds_since_iso_func=lambda value, default=0.0: 1001.0,
    )

    assert state["running"] is False
    assert state["status"] == "running"
    assert state["job_id"] == "codex-old"
    assert state["stale"] is True


def test_codex_runtime_busy_reply_includes_job_and_window() -> None:
    reply = xinyu_bridge_codex_runtime.codex_busy_reply(
        {"job_id": "codex-qq-test", "visible_window_title": "Test codex"},
    )

    assert "权限不是低" in reply
    assert "codex-qq-test" in reply
    assert "Test codex" in reply


def test_codex_runtime_busy_reply_default_uses_standard_window() -> None:
    reply = xinyu_bridge_codex_runtime.codex_busy_reply_default({"job_id": "codex-test"})

    assert "codex-test" in reply
    assert "Xinyu codex" in reply


def test_codex_runtime_extract_wait_to_think_task_builds_codex_task() -> None:
    task = xinyu_bridge_codex_runtime.extract_wait_to_think_task(
        "[WAIT_TO_THINK: verify exact behavior]",
        user_text="what exactly happens?",
        session_key="qq:private:owner",
    )

    assert "XinYu paused instead of faking certainty" in task
    assert "Owner message: what exactly happens?" in task
    assert "Session: qq:private:owner" in task
    assert "Specific uncertainty: verify exact behavior" in task


def test_codex_runtime_extract_wait_to_think_task_supports_default_and_legacy_marker() -> None:
    default_task = xinyu_bridge_codex_runtime.extract_wait_to_think_task(
        "[WAIT_TO_THINK]",
        user_text="not sure?",
        session_key="qq:private:owner",
    )
    legacy_task = xinyu_bridge_codex_runtime.extract_wait_to_think_task(
        "[[XINYU_WAIT_TO_THINK]]\ncheck   public docs\n[[/XINYU_WAIT_TO_THINK]]",
        user_text="look this up",
        session_key="qq:private:owner",
    )

    assert "Specific uncertainty: verify the uncertain owner request before answering" in default_task
    assert "Specific uncertainty: check public docs" in legacy_task
    assert xinyu_bridge_codex_runtime.extract_wait_to_think_task("plain reply", user_text="u", session_key="s") == ""


def test_codex_runtime_wait_to_think_execution_plan_classifies_read_only_and_write_risk() -> None:
    read_only = xinyu_bridge_codex_runtime.wait_to_think_execution_plan(
        "verify exact behavior from docs",
        user_text="what is the current behavior?",
    )
    high = xinyu_bridge_codex_runtime.wait_to_think_execution_plan(
        "prepare a patch",
        user_text="modify the bridge file",
    )

    assert "risk_level: read_only" in read_only
    assert "semi-structured read-only plan" in read_only
    assert "risk_level: high" in high
    assert "must not expand scope" in high
    assert "no destructive file operations" in high


def test_codex_runtime_owner_direct_codex_task_uses_default_marker_policy(monkeypatch) -> None:
    monkeypatch.setattr(xinyu_bridge_codex_runtime, "looks_like_codex_request", lambda text: True)
    runtime = SimpleNamespace(
        _can_model_delegate_codex=lambda payload: True,
        _compact_promise_text=lambda text: str(text).replace(" ", "").lower(),
    )

    task = xinyu_bridge_codex_runtime.owner_direct_codex_task(
        runtime,
        {"metadata": {"is_owner_user": True}},
        user_text="让 Codex 查一下这个问题",
        reply="要现在开始吗",
        session_key="qq:private:owner",
    )
    negative = xinyu_bridge_codex_runtime.owner_direct_codex_task(
        runtime,
        {"metadata": {"is_owner_user": True}},
        user_text="别用 Codex，先普通聊",
        reply="要现在开始吗",
        session_key="qq:private:owner",
    )

    assert "Owner explicitly asked XinYu to use Codex" in task
    assert "Owner message: 让 Codex 查一下这个问题" in task
    assert negative == ""


def test_codex_runtime_self_code_grant_defaults_include_readable_markers() -> None:
    runtime = SimpleNamespace()

    assert (
        xinyu_bridge_codex_runtime.owner_self_code_grant_in_text(
            runtime,
            "please improve your code modification ability",
        )
        is True
    )
    assert (
        xinyu_bridge_codex_runtime.owner_self_code_grant_in_text(
            runtime,
            "不要改代码 please improve your code modification ability",
        )
        is False
    )


def test_codex_runtime_prepare_self_code_watchdog_payload_appends_block(tmp_path: Path, monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_snapshot(root: Path, *, approval_id: str, reason: str) -> dict[str, str]:
        calls.append({"root": root, "approval_id": approval_id, "reason": reason})
        return {
            "snapshot_id": "snapshot-1",
            "manifest_path": r"D:\XinYu\runtime\self_code_watchdog\manifest.json",
        }

    monkeypatch.setattr(xinyu_bridge_codex_runtime, "create_self_code_snapshot", fake_snapshot)
    payload: dict[str, object] = {
        "text": "patch task",
        "raw_owner_task": "raw task",
        "metadata": {},
    }
    runtime = _Runtime(tmp_path)

    snapshot = xinyu_bridge_codex_runtime.prepare_self_code_watchdog_payload(
        runtime,
        payload,
        approval_id="approval-1",
    )

    assert snapshot["snapshot_id"] == "snapshot-1"
    assert calls == [
        {
            "root": tmp_path,
            "approval_id": "approval-1",
            "reason": "owner_self_code_iteration_before_codex_patch",
        }
    ]
    for key in ("text", "raw_owner_task"):
        value = str(payload[key])
        assert "Self-code watchdog:" in value
        assert "snapshot_id: snapshot-1" in value
        assert "-SelfCodeSnapshotPath" in value
        assert r"D:\XinYu\runtime\self_code_watchdog\manifest.json" in value
    assert payload["metadata"] == {
        "self_code_watchdog_snapshot_id": "snapshot-1",
        "self_code_watchdog_manifest_path": r"D:\XinYu\runtime\self_code_watchdog\manifest.json",
        "self_code_watchdog_restart_required": True,
    }


def test_codex_runtime_prepare_self_code_watchdog_payload_requires_manifest(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        xinyu_bridge_codex_runtime,
        "create_self_code_snapshot",
        lambda *args, **kwargs: {"snapshot_id": "", "manifest_path": ""},
    )

    with pytest.raises(RuntimeError, match="self-code watchdog snapshot"):
        xinyu_bridge_codex_runtime.prepare_self_code_watchdog_payload(
            _Runtime(tmp_path),
            {"metadata": {}},
            approval_id="approval-1",
        )


def test_codex_runtime_build_wait_to_think_codex_payload_adds_resume_and_plan() -> None:
    payload = {
        "platform": "qq",
        "adapter": "xinyu_native_qq_gateway",
        "message_type": "private_text",
        "user_id": "42",
        "timestamp": 456,
        "metadata": {"is_owner_user": True},
    }

    result = xinyu_bridge_codex_runtime.build_wait_to_think_codex_payload(
        payload,
        session_key="qq:private:owner",
        wait_task="verify exact behavior",
        resume_id="async-123",
        user_text="what exactly happens?",
        timeout_seconds=77,
        window_title="Wait codex",
    )

    assert result["session_id"] == "qq:private:owner"
    assert result["auto_study"] is False
    assert result["timeout_seconds"] == 77
    assert result["window_title"] == "Wait codex"
    assert result["metadata"]["delegated_by_model"] is True
    assert result["metadata"]["delegated_by_wait_to_think"] is True
    assert result["metadata"]["async_resume_id"] == "async-123"
    assert "Suspension resume_id: async-123" in result["raw_owner_task"]
    assert "Structured execution plan:" in result["raw_owner_task"]
    assert "risk_level: read_only" in result["raw_owner_task"]


def test_codex_runtime_transition_wait_to_think_reply_schedules_codex(tmp_path: Path, monkeypatch) -> None:
    captured: dict[str, object] = {}

    async def fake_codex_execute(payload: dict[str, object]) -> dict[str, object]:
        captured["codex_payload"] = payload
        return {"accepted": True}

    def fake_closure(root: Path, payload: dict[str, object], **kwargs: object) -> dict[str, object]:
        captured["closure"] = {"root": root, "payload": payload, **kwargs}
        return {
            "transition_message": "我去后台核对。",
            "resume_id": "wait-1",
            "notes": ["closure_note"],
        }

    monkeypatch.setattr(xinyu_bridge_codex_runtime, "create_async_exploration_closure", fake_closure)
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        codex_execute=fake_codex_execute,
        _wait_to_think_execution_plan=lambda task, *, user_text: "runtime-plan",
    )
    payload = {"platform": "qq", "metadata": {"is_owner_user": True}, "user_id": "owner-1"}

    transition, sidecar = asyncio.run(
        xinyu_bridge_codex_runtime.transition_wait_to_think_reply(
            runtime,
            payload,
            user_text="这是真的吗",
            draft_reply="[WAIT_TO_THINK]",
            wait_task="verify claim",
            session_key="qq:private:owner",
        )
    )

    assert transition == "我去后台核对。"
    assert sidecar == {"notes": ["wait_to_think_codex_scheduled", "closure_note"], "resume_id": "wait-1"}
    assert captured["closure"] == {
        "root": tmp_path,
        "payload": payload,
        "session_key": "qq:private:owner",
        "user_text": "这是真的吗",
        "draft_reply": "[WAIT_TO_THINK]",
        "task_text": "verify claim",
        "delegation_reason": "model_wait_to_think",
        "execution_plan": "runtime-plan",
    }
    codex_payload = captured["codex_payload"]
    assert codex_payload["metadata"]["delegated_by_wait_to_think"] is True
    assert codex_payload["metadata"]["async_resume_id"] == "wait-1"
    assert codex_payload["auto_study"] is False


def test_codex_runtime_transition_wait_to_think_reply_enqueues_failure(tmp_path: Path, monkeypatch) -> None:
    calls: dict[str, object] = {}

    async def fake_codex_execute(payload: dict[str, object]) -> dict[str, object]:
        calls["codex_payload"] = payload
        raise RuntimeError("codex down")

    def fake_update(root: Path, **kwargs: object) -> dict[str, object]:
        calls["update"] = {"root": root, **kwargs}
        return {"result_quality": "failed"}

    def fake_message(update: dict[str, object]) -> str:
        calls["message_update"] = update
        return "async failed"

    def fake_enqueue(root: Path, **kwargs: object) -> dict[str, object]:
        calls["enqueue"] = {"root": root, **kwargs}
        return {"queued": True}

    monkeypatch.setattr(
        xinyu_bridge_codex_runtime,
        "create_async_exploration_closure",
        lambda *args, **kwargs: {"transition_message": "", "resume_id": "wait-err", "notes": ["closure_note"]},
    )
    monkeypatch.setattr(xinyu_bridge_codex_runtime, "update_async_exploration_from_codex", fake_update)
    monkeypatch.setattr(xinyu_bridge_codex_runtime, "_async_exploration_outbox_message", fake_message)
    monkeypatch.setattr(xinyu_bridge_codex_runtime, "enqueue_qq_outbox_message", fake_enqueue)
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        codex_execute=fake_codex_execute,
        _owner_private_user_id=lambda: "owner-fallback",
    )

    transition, sidecar = asyncio.run(
        xinyu_bridge_codex_runtime.transition_wait_to_think_reply(
            runtime,
            {},
            user_text="查一下",
            draft_reply="[WAIT_TO_THINK]",
            wait_task="verify",
            session_key="qq:private:owner",
        )
    )

    assert transition == "我去后台验证一下，等结果出来再接着说。"
    assert sidecar == {"notes": ["wait_to_think_schedule_error", "closure_note"], "resume_id": "wait-err"}
    assert calls["update"] == {
        "root": tmp_path,
        "resume_id": "wait-err",
        "result": None,
        "error": "RuntimeError: codex down",
    }
    assert calls["message_update"] == {"result_quality": "failed"}
    assert calls["enqueue"] == {
        "root": tmp_path,
        "user_id": "owner-fallback",
        "message": "async failed",
        "source": "async_exploration_failure",
        "dedupe_key": "async_exploration_failure:wait-err",
        "metadata": {"resume_id": "wait-err", "has_error": True},
    }


def test_codex_runtime_apply_chat_delegates_wait_to_think_replaces_reply() -> None:
    calls: list[tuple[str, object]] = []
    agent = object()

    async def transition(payload, **kwargs):
        calls.append(("transition", {"payload": payload, **kwargs}))
        return "wait reply", {"notes": ["wait-note"], "resume_id": "wait-1"}

    runtime = SimpleNamespace(
        _transition_wait_to_think_reply=transition,
        _replace_last_assistant_message=lambda call_agent, reply: calls.append(
            ("replace", {"agent": call_agent, "reply": reply})
        ),
    )

    result = asyncio.run(
        xinyu_bridge_codex_runtime.apply_chat_codex_reply_delegates(
            runtime,
            SimpleNamespace(agent=agent),
            {"scope": "owner"},
            user_text="user",
            draft_reply="draft",
            session_key="qq:private:owner",
            self_code_task="",
            model_codex_task="",
            wait_to_think_task="verify",
        )
    )

    assert isinstance(result, xinyu_bridge_codex_runtime.ChatCodexReplyDelegateState)
    assert result == {
        "reply": "wait reply",
        "direct_codex_task": "",
        "wait_to_think_sidecar": {"notes": ["wait-note"], "resume_id": "wait-1"},
        "model_codex_delegate_note": "wait_to_think:scheduled",
    }
    assert calls == [
        (
            "transition",
            {
                "payload": {"scope": "owner"},
                "user_text": "user",
                "draft_reply": "draft",
                "wait_task": "verify",
                "session_key": "qq:private:owner",
            },
        ),
        ("replace", {"agent": agent, "reply": "wait reply"}),
    ]


def test_codex_runtime_apply_chat_delegates_self_code_busy_replaces_reply() -> None:
    calls: list[tuple[str, object]] = []
    agent = object()
    runtime = SimpleNamespace(
        _codex_delegate_running=lambda: calls.append(("running", None)) or {"running": True, "job_id": "job-1"},
        _codex_busy_reply=lambda state: calls.append(("busy", state)) or "busy reply",
        _replace_last_assistant_message=lambda call_agent, reply: calls.append(
            ("replace", {"agent": call_agent, "reply": reply})
        ),
    )

    result = asyncio.run(
        xinyu_bridge_codex_runtime.apply_chat_codex_reply_delegates(
            runtime,
            SimpleNamespace(agent=agent),
            {"scope": "owner"},
            user_text="user",
            draft_reply="draft",
            session_key="qq:private:owner",
            self_code_task="patch task",
            model_codex_task="",
            wait_to_think_task="",
        )
    )

    assert isinstance(result, xinyu_bridge_codex_runtime.ChatCodexReplyDelegateState)
    assert result == {
        "reply": "busy reply",
        "direct_codex_task": "",
        "wait_to_think_sidecar": {"notes": []},
        "model_codex_delegate_note": "owner_self_code_iteration:codex_busy",
    }
    assert calls == [
        ("running", None),
        ("busy", {"running": True, "job_id": "job-1"}),
        ("replace", {"agent": agent, "reply": "busy reply"}),
    ]


def test_codex_runtime_apply_chat_delegates_self_code_schedules_watchdog(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls: list[tuple[str, object]] = []
    agent = object()

    async def codex_execute(payload):
        calls.append(("codex_execute", payload))
        return {"request_path": "request-1"}

    def fake_mark(root, **kwargs):
        calls.append(("mark", {"root": root, **kwargs}))

    monkeypatch.setattr(xinyu_bridge_codex_runtime, "compose_codex_chat_scheduled_reply", lambda kind: f"scheduled:{kind}")
    monkeypatch.setattr(xinyu_bridge_codex_runtime, "mark_self_code_execution_scheduled", fake_mark)
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        _codex_delegate_running=lambda: calls.append(("running", None)) or {"running": False},
        _build_self_code_iteration_codex_payload=lambda payload, **kwargs: calls.append(
            ("build_self", {"payload": payload, **kwargs})
        )
        or {"payload": {"metadata": {}}, "approval_id": "approval-1"},
        _prepare_self_code_watchdog_payload=lambda codex_payload, **kwargs: calls.append(
            ("watchdog", {"codex_payload": codex_payload, **kwargs})
        )
        or {"snapshot_id": "snapshot-1", "manifest_path": "manifest-1"},
        codex_execute=codex_execute,
        _replace_last_assistant_message=lambda call_agent, reply: calls.append(
            ("replace", {"agent": call_agent, "reply": reply})
        ),
    )

    result = asyncio.run(
        xinyu_bridge_codex_runtime.apply_chat_codex_reply_delegates(
            runtime,
            SimpleNamespace(agent=agent),
            {"scope": "owner"},
            user_text="user",
            draft_reply="draft",
            session_key="qq:private:owner",
            self_code_task="patch task",
            model_codex_task="",
            wait_to_think_task="",
        )
    )

    assert isinstance(result, xinyu_bridge_codex_runtime.ChatCodexReplyDelegateState)
    assert result == {
        "reply": "scheduled:self_code",
        "direct_codex_task": "",
        "wait_to_think_sidecar": {"notes": []},
        "model_codex_delegate_note": "owner_self_code_iteration:scheduled",
    }
    assert calls == [
        ("running", None),
        ("build_self", {"payload": {"scope": "owner"}, "session_key": "qq:private:owner", "task_text": "patch task"}),
        ("watchdog", {"codex_payload": {"metadata": {}}, "approval_id": "approval-1"}),
        ("codex_execute", {"metadata": {}}),
        (
            "mark",
            {
                "root": tmp_path,
                "approval_id": "approval-1",
                "job_id": "request-1",
                "watchdog_snapshot_id": "snapshot-1",
                "watchdog_manifest_path": "manifest-1",
            },
        ),
        ("replace", {"agent": agent, "reply": "scheduled:self_code"}),
    ]


def test_codex_runtime_apply_chat_delegates_model_delegate_schedules(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []
    agent = object()

    async def codex_execute(payload):
        calls.append(("codex_execute", payload))
        return {"accepted": True}

    monkeypatch.setattr(xinyu_bridge_codex_runtime, "compose_codex_chat_scheduled_reply", lambda kind: f"scheduled:{kind}")
    runtime = SimpleNamespace(
        _can_model_delegate_codex=lambda payload, **kwargs: calls.append(
            ("can_model", {"payload": payload, **kwargs})
        )
        or True,
        _build_model_codex_payload=lambda payload, **kwargs: calls.append(
            ("build_model", {"payload": payload, **kwargs})
        )
        or {"metadata": {}},
        codex_execute=codex_execute,
        _replace_last_assistant_message=lambda call_agent, reply: calls.append(
            ("replace", {"agent": call_agent, "reply": reply})
        ),
    )

    result = asyncio.run(
        xinyu_bridge_codex_runtime.apply_chat_codex_reply_delegates(
            runtime,
            SimpleNamespace(agent=agent),
            {"scope": "owner"},
            user_text="user",
            draft_reply="draft",
            session_key="qq:private:owner",
            self_code_task="",
            model_codex_task="model task",
            wait_to_think_task="",
        )
    )

    assert isinstance(result, xinyu_bridge_codex_runtime.ChatCodexReplyDelegateState)
    assert result == {
        "reply": "scheduled:model_delegate",
        "direct_codex_task": "",
        "wait_to_think_sidecar": {"notes": []},
        "model_codex_delegate_note": "model_codex_delegate:scheduled",
    }
    assert calls == [
        ("can_model", {"payload": {"scope": "owner"}, "task_text": "model task"}),
        ("build_model", {"payload": {"scope": "owner"}, "session_key": "qq:private:owner", "task_text": "model task"}),
        ("codex_execute", {"metadata": {}}),
        ("replace", {"agent": agent, "reply": "scheduled:model_delegate"}),
    ]


def test_codex_runtime_apply_chat_delegates_owner_direct_marks_payload(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []
    agent = object()

    async def codex_execute(payload):
        calls.append(("codex_execute", payload.copy()))
        return {"accepted": True}

    monkeypatch.setattr(xinyu_bridge_codex_runtime, "compose_codex_chat_scheduled_reply", lambda kind: f"scheduled:{kind}")
    runtime = SimpleNamespace(
        _owner_direct_codex_task=lambda payload, **kwargs: calls.append(
            ("owner_direct", {"payload": payload, **kwargs})
        )
        or "direct task",
        _build_model_codex_payload=lambda payload, **kwargs: calls.append(
            ("build_model", {"payload": payload, **kwargs})
        )
        or {"metadata": {"existing": "kept"}},
        codex_execute=codex_execute,
        _replace_last_assistant_message=lambda call_agent, reply: calls.append(
            ("replace", {"agent": call_agent, "reply": reply})
        ),
    )

    result = asyncio.run(
        xinyu_bridge_codex_runtime.apply_chat_codex_reply_delegates(
            runtime,
            SimpleNamespace(agent=agent),
            {"scope": "owner"},
            user_text="user",
            draft_reply="draft",
            session_key="qq:private:owner",
            self_code_task="",
            model_codex_task="",
            wait_to_think_task="",
        )
    )

    assert isinstance(result, xinyu_bridge_codex_runtime.ChatCodexReplyDelegateState)
    assert result == {
        "reply": "scheduled:owner_direct",
        "direct_codex_task": "direct task",
        "wait_to_think_sidecar": {"notes": []},
        "model_codex_delegate_note": "owner_direct_codex_delegate:scheduled",
    }
    assert calls == [
        (
            "owner_direct",
            {"payload": {"scope": "owner"}, "user_text": "user", "reply": "draft", "session_key": "qq:private:owner"},
        ),
        ("build_model", {"payload": {"scope": "owner"}, "session_key": "qq:private:owner", "task_text": "direct task"}),
        ("codex_execute", {"metadata": {"existing": "kept", "delegated_by_owner_directive": True}}),
        ("replace", {"agent": agent, "reply": "scheduled:owner_direct"}),
    ]


def test_codex_runtime_background_success_trace_line_preserves_fields() -> None:
    result = SimpleNamespace(
        accepted=True,
        timed_out=False,
        exit_code=0,
        report_path="report.md",
    )

    line = xinyu_bridge_codex_runtime.codex_delegate_background_success_trace_line(
        result,
        started_at="start",
        text="task text",
        handoff_notes=["handoff"],
        report_material_id="material-1",
        report_material_notes=["ready", "quality"],
        action_experience_notes=["settled"],
        finished_at="finish",
    )

    assert line == (
        "finish ok started_at=start accepted=True timed_out=False exit=0 report=report.md "
        "dream_handoff=handoff report_material=material-1 report_material_notes=ready;quality "
        "action_experience=settled text='task text'\n"
    )


def test_codex_runtime_background_trace_lines_handle_defaults_and_errors() -> None:
    result = SimpleNamespace(
        accepted=False,
        timed_out=True,
        exit_code=None,
        report_path="",
    )

    success = xinyu_bridge_codex_runtime.codex_delegate_background_success_trace_line(
        result,
        started_at="start",
        text="x" * 140,
        handoff_notes=[],
        report_material_id="",
        report_material_notes=[],
        action_experience_notes=[],
        finished_at="finish",
    )
    error = xinyu_bridge_codex_runtime.codex_delegate_background_error_trace_line(
        RuntimeError("boom"),
        started_at="start",
        text="task",
        finished_at="finish",
    )

    assert "exit=timeout" in success
    assert "dream_handoff=none" in success
    assert "report_material=none" in success
    assert "action_experience=none" in success
    assert "x" * 120 in success
    assert "x" * 121 not in success
    assert error == "finish error started_at=start RuntimeError: boom text='task'\n"


def test_codex_runtime_append_background_trace_writes_line(tmp_path: Path) -> None:
    xinyu_bridge_codex_runtime.append_codex_delegate_background_trace(tmp_path, "trace line\n")

    trace = (tmp_path / "knowledge/codex_delegate_background_trace.log").read_text(encoding="utf-8")
    assert trace == "trace line\n"


def test_codex_runtime_delegate_background_runs_success_flow(tmp_path: Path) -> None:
    calls: list[tuple[str, object]] = []
    result = SimpleNamespace(accepted=True, timed_out=False, exit_code=0, report_path="report.md")

    async def run_background(payload: dict[str, object]) -> object:
        calls.append(("run", dict(payload)))
        return result

    async def settle(payload: dict[str, object], *, metadata: dict[str, object], result: object) -> list[str]:
        calls.append(("settle", {"metadata": metadata, "result": result}))
        return ["settled"]

    async def handoff(*, result: object, text: str) -> dict[str, object]:
        calls.append(("handoff", {"result": result, "text": text}))
        return {"notes": ["handoff"]}

    async def stage_report(**kwargs: object) -> dict[str, object]:
        calls.append(("stage", dict(kwargs)))
        return {"material_id": "material-1", "notes": ["ready", "quality", "", "ignored"]}

    def record_presence(*args: object, **kwargs: object) -> None:
        calls.append(("presence", {"args": args, "kwargs": kwargs}))

    def enqueue(payload: dict[str, object], **kwargs: object) -> None:
        calls.append(("enqueue", {"payload": dict(payload), "kwargs": kwargs}))

    def notify(payload: dict[str, object], **kwargs: object) -> None:
        calls.append(("notify", {"payload": dict(payload), "kwargs": kwargs}))

    traces: list[str] = []
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        memory_root=tmp_path,
        _prepare_codex_background_delegate_context=lambda payload: {
            "started_at": "start",
            "presence_paths": {"job_id": "codex-job"},
            "metadata": {"source": "test"},
            "async_resume_id": "resume-1",
            "owner_intervention": "owner-note",
        },
        _run_codex_background_delegate=run_background,
        _settle_codex_delegate_action_experience=settle,
        _handoff_codex_delegate_to_dream=handoff,
        _stage_codex_report_material_after_delegate=stage_report,
        _record_codex_delegate_presence_result=record_presence,
        _enqueue_codex_completion_if_needed=enqueue,
        _notify_async_exploration_codex_result=notify,
        _append_codex_delegate_background_trace=lambda memory_root, line: traces.append(line),
    )

    asyncio.run(
        xinyu_bridge_codex_runtime.runtime_codex_delegate_background(
            runtime,
            {"text": "run codex"},
            text="run codex",
            auto_study=True,
        )
    )

    assert [name for name, _ in calls] == ["run", "settle", "handoff", "stage", "presence", "enqueue", "notify"]
    assert calls[4][1]["kwargs"]["presence_paths"] == {"job_id": "codex-job"}  # type: ignore[index]
    assert calls[5][1]["kwargs"]["handoff_notes"] == ["handoff"]  # type: ignore[index]
    assert calls[6][1]["kwargs"]["async_resume_id"] == "resume-1"  # type: ignore[index]
    assert traces and "report_material=material-1" in traces[0]
    assert "action_experience=settled" in traces[0]


def test_codex_runtime_model_delegate_allows_owner_and_bounded_trusted_search() -> None:
    owner_payload = {"message_type": "private_text", "metadata": {"is_owner_user": True}}
    trusted_payload = {
        "message_type": "private_text",
        "metadata": {"is_owner_user": False, "is_trusted_user": True},
    }

    assert xinyu_bridge_codex_runtime.can_model_delegate_codex(owner_payload) is True
    assert xinyu_bridge_codex_runtime.can_model_delegate_codex({"message_type": "private_text", "metadata": {}}) is False
    assert (
        xinyu_bridge_codex_runtime.can_model_delegate_codex(
            {"message_type": "group_text", "group_id": "7", "metadata": {"is_owner_user": True}}
        )
        is False
    )
    assert xinyu_bridge_codex_runtime.can_model_delegate_codex(trusted_payload) is False
    assert (
        xinyu_bridge_codex_runtime.can_model_delegate_codex(
            trusted_payload,
            task_text="search public web sources for PyMuPDF docs",
        )
        is True
    )
    assert (
        xinyu_bridge_codex_runtime.can_model_delegate_codex(
            trusted_payload,
            task_text=r"search and read D:\XinYu\config.yaml",
        )
        is False
    )


def test_codex_runtime_build_model_payload_preserves_delegate_contract() -> None:
    payload = {
        "platform": "desktop",
        "adapter": "xinyu_desktop_shell",
        "message_type": "desktop_private",
        "session_id": "desktop:private:owner",
        "user_id": "desktop-owner",
        "message_id": "message-1",
        "timestamp": 123,
        "metadata": {
            "is_owner_user": True,
            "is_trusted_user": True,
            "owner_local_write_approved": True,
        },
    }

    result = xinyu_bridge_codex_runtime.build_model_codex_payload(
        payload,
        session_key="desktop:private:owner",
        task_text="inspect the desktop bridge",
        timeout_seconds=99,
        window_title="Test codex",
    )

    assert result["source"] == "qq_gateway_codex_execute_message"
    assert result["message_type"] == "private_codex_model_delegate"
    assert result["session_id"] == "desktop:private:owner"
    assert result["raw_owner_task"] == "inspect the desktop bridge"
    assert result["timeout_seconds"] == 99
    assert result["window_title"] == "Test codex"
    assert result["timestamp"] == 123
    assert result["metadata"]["delegated_by_model"] is True
    assert result["metadata"]["owner_local_write_approved"] is True
    assert result["metadata"]["trusted_public_search_task"] is False
    assert "owner-approved task" in result["text"]


def test_codex_runtime_build_model_payload_marks_trusted_public_search() -> None:
    payload = {
        "platform": "qq",
        "adapter": "xinyu_native_qq_gateway",
        "message_type": "private_text",
        "session_id": "qq:private:trusted",
        "user_id": "43",
        "metadata": {"is_owner_user": False, "is_trusted_user": True},
    }

    result = xinyu_bridge_codex_runtime.build_model_codex_payload(
        payload,
        session_key="qq:private:trusted",
        task_text="search public web sources for PyMuPDF docs",
    )

    assert result["metadata"]["is_owner_user"] is False
    assert result["metadata"]["is_trusted_user"] is True
    assert result["metadata"]["trusted_public_search_task"] is True
    assert "trusted public-source search task" in result["text"]


def test_codex_runtime_build_self_code_iteration_payload_marks_direct_owner_request() -> None:
    calls: list[dict[str, object]] = []

    def build_model_payload(payload: dict[str, object], **kwargs: object) -> dict[str, object]:
        calls.append({"payload": payload, **kwargs})
        return {
            "auto_study": True,
            "metadata": {"delegated_by_model": True, "existing": "kept"},
        }

    runtime = SimpleNamespace(
        _build_model_codex_payload=build_model_payload,
        _extract_self_code_approval_id=lambda task: "selfcode-direct-123",
    )
    payload = {"platform": "qq"}

    result = xinyu_bridge_codex_runtime.build_self_code_iteration_codex_payload(
        runtime,
        payload,
        session_key="qq:private:owner",
        task_text="approved direct self-code task",
    )

    codex_payload = result["payload"]
    assert result["approval_id"] == "selfcode-direct-123"
    assert calls == [
        {
            "payload": payload,
            "session_key": "qq:private:owner",
            "task_text": "approved direct self-code task",
        }
    ]
    assert codex_payload["auto_study"] is False
    assert codex_payload["metadata"] == {
        "delegated_by_model": False,
        "existing": "kept",
        "delegated_by_owner_self_code_iteration": True,
        "self_code_iteration": True,
        "approval_id": "selfcode-direct-123",
        "owner_intervention": "owner private direct self-code request",
    }


def test_codex_runtime_build_self_code_iteration_payload_marks_ticket_owner_request() -> None:
    runtime = SimpleNamespace(
        _build_model_codex_payload=lambda *args, **kwargs: {"metadata": None, "auto_study": True},
        _extract_self_code_approval_id=lambda task: "selfcode-ticket-456",
    )

    result = xinyu_bridge_codex_runtime.build_self_code_iteration_codex_payload(
        runtime,
        {"platform": "qq"},
        session_key="qq:private:owner",
        task_text="approved pending self-code task",
    )

    codex_payload = result["payload"]
    assert result["approval_id"] == "selfcode-ticket-456"
    assert codex_payload["auto_study"] is False
    assert codex_payload["metadata"]["delegated_by_model"] is False
    assert codex_payload["metadata"]["delegated_by_owner_self_code_iteration"] is True
    assert codex_payload["metadata"]["self_code_iteration"] is True
    assert codex_payload["metadata"]["approval_id"] == "selfcode-ticket-456"
    assert codex_payload["metadata"]["owner_intervention"] == "owner approved one-time self-code ticket through QQ"


def test_codex_runtime_augments_payload_with_recent_dialogue_context(tmp_path: Path) -> None:
    session_key = "qq:private:owner"
    assert save_dialogue_tail(
        tmp_path,
        session_key,
        [
            {"role": "user", "content": "Search for counterarguments to blindsight Watts."},
            {"role": "assistant", "content": "I can prepare a bounded search task."},
        ],
    )
    payload = {
        "source": "qq_gateway_codex_execute_message",
        "session_id": session_key,
        "raw_owner_task": "Try Codex search.",
        "metadata": {},
    }

    text = xinyu_bridge_codex_runtime.augment_codex_payload_with_dialogue_context(
        tmp_path,
        payload,
        "Use Codex for this task.",
        dialogue_prompt_tail_entries=4,
    )

    assert "Recent QQ context before this Codex request:" in text
    assert "counterarguments to blindsight Watts" in text
    assert "Current owner Codex task: Try Codex search." in text
    assert payload["text"] == text
    assert payload["codex_context_included"] is True
    assert payload["metadata"]["dialogue_context_included"] is True


def test_codex_runtime_augments_payload_with_runtime_settings(tmp_path: Path) -> None:
    session_key = "qq:private:owner"
    assert save_dialogue_tail(
        tmp_path,
        session_key,
        [
            {"role": "user", "content": "first context"},
            {"role": "assistant", "content": "second context"},
        ],
    )
    runtime = _Runtime(tmp_path)
    runtime.dialogue_prompt_tail_entries = 1
    payload = {
        "source": "qq_gateway_codex_execute_message",
        "session_id": session_key,
        "raw_owner_task": "Check one reference.",
        "metadata": {},
    }

    text = xinyu_bridge_codex_runtime.augment_runtime_codex_payload_with_dialogue_context(
        runtime,
        payload,
        "Use Codex.",
    )

    assert "Recent QQ context before this Codex request:" in text
    assert "second context" in text
    assert "first context" not in text
    assert payload["codex_context_included"] is True


def test_codex_runtime_format_runtime_dialogue_tail_uses_runtime_limit(tmp_path: Path) -> None:
    runtime = _Runtime(tmp_path)
    runtime.dialogue_prompt_tail_entries = 1

    text = xinyu_bridge_codex_runtime.format_runtime_dialogue_tail(
        runtime,
        [
            {"role": "user", "content": "first", "recorded_at": "2026-01-01T00:00:00+08:00"},
            {"role": "assistant", "content": "second", "recorded_at": "2026-01-01T00:01:00+08:00"},
        ],
    )

    assert "second" in text
    assert "first" not in text


def test_codex_runtime_completion_summary_delegates_with_runtime_root(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls: list[tuple[Path, object, int]] = []
    result = object()

    def fake_summary(root: Path, received: object, *, limit: int = 220) -> str:
        calls.append((root, received, limit))
        return "summary"

    monkeypatch.setattr(xinyu_bridge_codex_runtime, "_codex_completion_summary", fake_summary)

    assert xinyu_bridge_codex_runtime.codex_completion_summary(_Runtime(tmp_path), result, limit=12) == "summary"
    assert calls == [(tmp_path, result, 12)]


def test_codex_runtime_outbox_message_delegates_with_runtime_root(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls: list[tuple[Path, object, str, bool, list[str]]] = []
    result = object()

    def fake_outbox_message(
        root: Path,
        received: object,
        *,
        text: str,
        auto_study: bool,
        handoff_notes: list[str],
    ) -> str:
        calls.append((root, received, text, auto_study, handoff_notes))
        return "message"

    monkeypatch.setattr(xinyu_bridge_codex_runtime, "_codex_completion_outbox_message", fake_outbox_message)

    assert (
        xinyu_bridge_codex_runtime.codex_completion_outbox_message(
            _Runtime(tmp_path),
            result,
            text="task",
            auto_study=True,
            handoff_notes=["handoff"],
        )
        == "message"
    )
    assert calls == [(tmp_path, result, "task", True, ["handoff"])]


def test_codex_runtime_enqueue_completion_delegates_with_runtime_root(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls: list[tuple[Path, dict[str, object], object, str, bool, list[str], str]] = []
    payload: dict[str, object] = {"source": "qq_gateway_codex_execute_message"}
    result = object()

    def fake_enqueue(
        root: Path,
        received_payload: dict[str, object],
        *,
        result: object | None,
        text: str,
        auto_study: bool,
        handoff_notes: list[str],
        error: str = "",
    ) -> None:
        calls.append((root, received_payload, result, text, auto_study, handoff_notes, error))

    monkeypatch.setattr(xinyu_bridge_codex_runtime, "_enqueue_codex_completion_if_needed", fake_enqueue)

    xinyu_bridge_codex_runtime.enqueue_codex_completion_if_needed(
        _Runtime(tmp_path),
        payload,
        result=result,
        text="task",
        auto_study=False,
        handoff_notes=["handoff"],
        error="",
    )

    assert calls == [(tmp_path, payload, result, "task", False, ["handoff"], "")]


def test_codex_runtime_generated_images_delegate_with_runtime_root(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls: list[tuple[Path, object, str, int]] = []
    result = SimpleNamespace()
    image = tmp_path / "image.png"

    def fake_images(root: Path, received: object, *, task_text: str, limit: int = 3) -> list[Path]:
        calls.append((root, received, task_text, limit))
        return [image]

    monkeypatch.setattr(xinyu_bridge_codex_runtime, "_codex_generated_image_artifacts", fake_images)

    assert xinyu_bridge_codex_runtime.codex_generated_image_artifacts(
        _Runtime(tmp_path),
        result,
        task_text="generate image",
        limit=1,
    ) == [image]
    assert calls == [(tmp_path, result, "generate image", 1)]


def test_codex_runtime_codex_delegate_action_outcome_reports_success() -> None:
    result = SimpleNamespace(
        accepted=True,
        timed_out=False,
        exit_code=0,
        report_path="runtime/codex_delegate/outbox/report.md",
    )

    outcome = xinyu_bridge_codex_runtime.codex_delegate_action_outcome(result, summary="done")

    assert outcome["ok"] is True
    assert outcome["tool"] == "codex_delegate"
    assert outcome["summary"] == ["done"]
    assert outcome["report_path"] == "runtime/codex_delegate/outbox/report.md"
    assert outcome["risk"] == "delegated_local"
    assert outcome["result"] == "success"
    assert outcome["load"] == {"codex_exit_code": 0, "timeout": False, "scheduled": True}
    assert outcome["error_code"] == ""
    assert outcome["notes"] == ["codex_delegate_background_completion"]


def test_codex_runtime_codex_delegate_action_outcome_reports_incomplete_timeout() -> None:
    result = SimpleNamespace(
        accepted=True,
        timed_out=True,
        exit_code=None,
        report_path="runtime/codex_delegate/outbox/report.md",
    )

    outcome = xinyu_bridge_codex_runtime.codex_delegate_action_outcome(result, summary="timed out")

    assert outcome["ok"] is False
    assert outcome["result"] == "failure"
    assert outcome["load"] == {"codex_exit_code": None, "timeout": True, "scheduled": True}
    assert outcome["error_code"] == "codex_delegate_incomplete"


def test_codex_runtime_async_exploration_result_outbox_payload_reports_quality(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_message(update: dict[str, object]) -> str:
        calls.append(update)
        return "owner-visible async result"

    monkeypatch.setattr(xinyu_bridge_codex_runtime, "_async_exploration_outbox_message", fake_message)

    update = {"result_quality": "usable_partial"}
    payload = xinyu_bridge_codex_runtime.codex_async_exploration_result_outbox_payload(
        update,
        resume_id="wait-20260605-abcd1234",
        owner_intervention="owner narrowed scope",
    )

    assert payload == {
        "message": "owner-visible async result",
        "source": "async_exploration_result",
        "dedupe_key": "async_exploration_result:wait-20260605-abcd1234",
        "metadata": {
            "resume_id": "wait-20260605-abcd1234",
            "result_quality": "usable_partial",
            "owner_intervention": "owner narrowed scope",
        },
    }
    assert calls == [update]


def test_codex_runtime_async_exploration_result_outbox_payload_reports_error(monkeypatch) -> None:
    monkeypatch.setattr(
        xinyu_bridge_codex_runtime,
        "_async_exploration_outbox_message",
        lambda update: "owner-visible async error",
    )

    payload = xinyu_bridge_codex_runtime.codex_async_exploration_result_outbox_payload(
        {"result_quality": "failed"},
        resume_id="wait-20260605-deadbeef",
        owner_intervention="ignored on error",
        has_error=True,
    )

    assert payload == {
        "message": "owner-visible async error",
        "source": "async_exploration_result",
        "dedupe_key": "async_exploration_result:wait-20260605-deadbeef",
        "metadata": {"resume_id": "wait-20260605-deadbeef", "has_error": True},
    }


def test_codex_runtime_notify_async_exploration_result_enqueues_success(tmp_path: Path, monkeypatch) -> None:
    calls: list[tuple[str, object]] = []
    delegate_result = SimpleNamespace(accepted=True)

    def fake_update(root: Path, **kwargs: object) -> dict[str, object]:
        calls.append(("update", {"root": root, **kwargs}))
        return {"result_quality": "usable_partial"}

    def fake_enqueue(root: Path, *, user_id: str, **payload: object) -> None:
        calls.append(("enqueue", {"root": root, "user_id": user_id, **payload}))

    monkeypatch.setattr(xinyu_bridge_codex_runtime, "update_async_exploration_from_codex", fake_update)
    monkeypatch.setattr(xinyu_bridge_codex_runtime, "enqueue_qq_outbox_message", fake_enqueue)
    monkeypatch.setattr(
        xinyu_bridge_codex_runtime,
        "_async_exploration_outbox_message",
        lambda update: "owner-visible async result",
    )
    runtime = SimpleNamespace(xinyu_dir=tmp_path, _owner_private_user_id=lambda: "owner-fallback")

    xinyu_bridge_codex_runtime.notify_async_exploration_codex_result(
        runtime,
        {"user_id": "42"},
        async_resume_id="wait-1",
        owner_intervention="owner narrowed scope",
        result=delegate_result,
    )

    assert calls == [
        (
            "update",
            {
                "root": tmp_path,
                "resume_id": "wait-1",
                "result": delegate_result,
                "owner_intervention": "owner narrowed scope",
            },
        ),
        (
            "enqueue",
            {
                "root": tmp_path,
                "user_id": "42",
                "message": "owner-visible async result",
                "source": "async_exploration_result",
                "dedupe_key": "async_exploration_result:wait-1",
                "metadata": {
                    "resume_id": "wait-1",
                    "result_quality": "usable_partial",
                    "owner_intervention": "owner narrowed scope",
                },
            },
        ),
    ]


def test_codex_runtime_notify_async_exploration_result_enqueues_error_with_owner_fallback(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls: list[tuple[str, object]] = []

    def fake_update(root: Path, **kwargs: object) -> dict[str, object]:
        calls.append(("update", {"root": root, **kwargs}))
        return {"result_quality": "failed"}

    def fake_enqueue(root: Path, *, user_id: str, **payload: object) -> None:
        calls.append(("enqueue", {"root": root, "user_id": user_id, **payload}))

    monkeypatch.setattr(xinyu_bridge_codex_runtime, "update_async_exploration_from_codex", fake_update)
    monkeypatch.setattr(xinyu_bridge_codex_runtime, "enqueue_qq_outbox_message", fake_enqueue)
    monkeypatch.setattr(
        xinyu_bridge_codex_runtime,
        "_async_exploration_outbox_message",
        lambda update: "owner-visible async error",
    )
    runtime = SimpleNamespace(xinyu_dir=tmp_path, _owner_private_user_id=lambda: "owner-fallback")

    xinyu_bridge_codex_runtime.notify_async_exploration_codex_result(
        runtime,
        {},
        async_resume_id="wait-err",
        owner_intervention="owner narrowed scope",
        error="RuntimeError: boom",
    )

    assert calls == [
        (
            "update",
            {
                "root": tmp_path,
                "resume_id": "wait-err",
                "result": None,
                "error": "RuntimeError: boom",
                "owner_intervention": "owner narrowed scope",
            },
        ),
        (
            "enqueue",
            {
                "root": tmp_path,
                "user_id": "owner-fallback",
                "message": "owner-visible async error",
                "source": "async_exploration_result",
                "dedupe_key": "async_exploration_result:wait-err",
                "metadata": {"resume_id": "wait-err", "has_error": True},
            },
        ),
    ]


def test_codex_runtime_notify_async_exploration_result_skips_enqueue_without_user(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls: list[tuple[str, object]] = []

    def fake_update(root: Path, **kwargs: object) -> dict[str, object]:
        calls.append(("update", {"root": root, **kwargs}))
        return {"result_quality": "usable_partial"}

    def fake_enqueue(*args, **kwargs) -> None:
        calls.append(("enqueue", kwargs))

    monkeypatch.setattr(xinyu_bridge_codex_runtime, "update_async_exploration_from_codex", fake_update)
    monkeypatch.setattr(xinyu_bridge_codex_runtime, "enqueue_qq_outbox_message", fake_enqueue)
    runtime = SimpleNamespace(xinyu_dir=tmp_path, _owner_private_user_id=lambda: "")

    xinyu_bridge_codex_runtime.notify_async_exploration_codex_result(
        runtime,
        {},
        async_resume_id="wait-no-user",
        result=SimpleNamespace(accepted=True),
    )

    assert len(calls) == 1
    assert calls[0][0] == "update"


def test_codex_runtime_background_scheduled_response_preserves_contract() -> None:
    paths = {
        "job_id": "codex-qq-20260605T010203",
        "request_path": "runtime/codex/request.md",
        "workspace_path": "runtime/codex/workspace",
        "report_path": "runtime/codex/report.md",
        "last_message_path": "runtime/codex/last-message.txt",
    }

    response = xinyu_bridge_codex_runtime.codex_background_scheduled_response(
        paths,
        reply="started reply",
        auto_study=True,
        cleanup={"cleaned_sessions": 2},
        session_count=5,
    )

    assert response == {
        "accepted": True,
        "reply": "started reply",
        "memory_changed": False,
        "library_changed": False,
        "session_created": False,
        "sessions": 5,
        "request_path": "runtime/codex/request.md",
        "workspace_path": "runtime/codex/workspace",
        "report_path": "runtime/codex/report.md",
        "last_message_path": "runtime/codex/last-message.txt",
        "codex_exit_code": None,
        "codex_timed_out": False,
        "stdout_tail": "",
        "stderr_tail": "",
        "source_integration_gate": {},
        "learner_integration": {},
        "learning_quality": {},
        "integrated_materials": 0,
        "ready_materials": 0,
        "blocked_unreadable_materials": 0,
        "quality_grade": "background",
        "notes": [
            "codex_delegate",
            "codex_delegate_background:scheduled",
            "dream_handoff_on_timeout:armed",
            "job_id:codex-qq-20260605T010203",
            "learning_after_codex:scheduled_after_finish",
            "cleaned_idle_sessions:2",
        ],
    }


def test_codex_runtime_schedule_background_delegate_records_presence_and_task(tmp_path: Path, monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    async def cleanup() -> dict[str, int]:
        calls.append(("cleanup", "called"))
        return {"cleaned_sessions": 1}

    async def background(payload: dict[str, object], *, text: str, auto_study: bool) -> None:
        calls.append(("background", {"payload": payload, "text": text, "auto_study": auto_study}))

    def fake_create_task(coro, *, name: str):
        calls.append(("task", name))
        coro.close()
        return SimpleNamespace(name=name)

    def fake_presence(root: Path, **kwargs: object) -> None:
        calls.append(("presence", {"root": root, **kwargs}))

    monkeypatch.setattr(xinyu_bridge_codex_runtime.asyncio, "create_task", fake_create_task)
    monkeypatch.setattr(xinyu_bridge_codex_runtime, "record_codex_presence", fake_presence)
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        _sessions={"active": object(), "other": object()},
        _cleanup_idle_sessions=cleanup,
        _codex_delegate_background=background,
        _codex_status_reply=lambda status, **kwargs: calls.append(("reply", {"status": status, **kwargs}))
        or "started reply",
    )
    payload: dict[str, object] = {
        "job_id": "20260605T010203",
        "raw_owner_task": "raw owner task",
        "window_title": "Service Codex",
    }

    response = asyncio.run(
        xinyu_bridge_codex_runtime.schedule_codex_background_delegate(
            runtime,
            payload,
            text="delegate task",
            auto_study=True,
        )
    )

    assert response["accepted"] is True
    assert response["quality_grade"] == "background"
    assert response["sessions"] == 2
    assert response["reply"] == "started reply"
    assert response["notes"][-1] == "cleaned_idle_sessions:1"
    assert calls[0][0] == "presence"
    assert calls[0][1]["job_id"] == "codex-qq-20260605T010203"
    assert calls[0][1]["status"] == "running"
    assert calls[0][1]["visible_window_title"] == "Service Codex"
    assert calls[1] == ("cleanup", "called")
    assert calls[2] == ("task", "xinyu-codex-delegate-codex-qq-20260605T010203")
    assert calls[3][0] == "reply"
    assert calls[3][1]["status"] == "started"
    assert calls[3][1]["auto_study"] is True
    assert calls[3][1]["task_text"] == "raw owner task"


def test_codex_runtime_start_foreground_delegate_cleans_and_records_running(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls: list[tuple[str, object]] = []
    presence_paths = {
        "job_id": "codex-foreground",
        "request_path": "request.md",
        "report_path": "report.md",
    }

    async def cleanup() -> dict[str, int]:
        calls.append(("cleanup", "called"))
        return {"cleaned_sessions": 2}

    def fake_preview(root: Path, payload: dict[str, object]) -> dict[str, object]:
        calls.append(("preview", {"root": root, "payload": payload}))
        return presence_paths

    def fake_presence_state(
        root: Path,
        payload: dict[str, object],
        *,
        presence_paths: dict[str, object],
        status: str,
    ) -> None:
        calls.append(
            (
                "presence",
                {
                    "root": root,
                    "payload": payload,
                    "presence_paths": presence_paths,
                    "status": status,
                },
            )
        )

    monkeypatch.setattr(xinyu_bridge_codex_runtime, "preview_codex_delegate_paths", fake_preview)
    monkeypatch.setattr(xinyu_bridge_codex_runtime, "record_codex_delegate_presence_state", fake_presence_state)
    runtime = SimpleNamespace(xinyu_dir=tmp_path, _cleanup_idle_sessions=cleanup)
    payload = {"raw_owner_task": "foreground task"}

    result = asyncio.run(xinyu_bridge_codex_runtime.start_codex_foreground_delegate(runtime, payload))

    assert result == {"cleanup": {"cleaned_sessions": 2}, "presence_paths": presence_paths}
    assert calls == [
        ("cleanup", "called"),
        ("preview", {"root": tmp_path, "payload": payload}),
        (
            "presence",
            {
                "root": tmp_path,
                "payload": payload,
                "presence_paths": presence_paths,
                "status": "running",
            },
        ),
    ]


def test_codex_runtime_prepare_background_delegate_context_parses_resume_metadata(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls: list[dict[str, object]] = []
    presence_paths = {
        "job_id": "codex-background",
        "request_path": "request.md",
        "report_path": "report.md",
    }

    def fake_preview(root: Path, payload: dict[str, object]) -> dict[str, object]:
        calls.append({"root": root, "payload": payload})
        return presence_paths

    monkeypatch.setattr(xinyu_bridge_codex_runtime, "preview_codex_delegate_paths", fake_preview)
    payload = {
        "metadata": {
            "async_resume_id": " resume-1 ",
            "owner_intervention": " narrowed scope ",
        }
    }

    context = xinyu_bridge_codex_runtime.prepare_codex_background_delegate_context(
        SimpleNamespace(xinyu_dir=tmp_path),
        payload,
        started_at="start-time",
    )

    assert context == {
        "started_at": "start-time",
        "presence_paths": presence_paths,
        "metadata": payload["metadata"],
        "async_resume_id": "resume-1",
        "owner_intervention": "narrowed scope",
    }
    assert calls == [{"root": tmp_path, "payload": payload}]


def test_codex_runtime_prepare_background_delegate_context_handles_missing_metadata(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        xinyu_bridge_codex_runtime,
        "preview_codex_delegate_paths",
        lambda root, payload: {"job_id": "codex-background"},
    )

    context = xinyu_bridge_codex_runtime.prepare_codex_background_delegate_context(
        SimpleNamespace(xinyu_dir=tmp_path),
        {"metadata": "bad"},
        started_at="start-time",
    )

    assert context["metadata"] == {}
    assert context["async_resume_id"] == ""
    assert context["owner_intervention"] == ""
    assert context["presence_paths"] == {"job_id": "codex-background"}


def test_codex_runtime_execute_rejects_closed_runtime() -> None:
    with pytest.raises(BridgeRequestError) as caught:
        asyncio.run(xinyu_bridge_codex_runtime.runtime_codex_execute(SimpleNamespace(_closed=True), {}))

    assert caught.value.status == HTTPStatus.SERVICE_UNAVAILABLE
    assert caught.value.message == "bridge is shutting down"


def test_codex_runtime_execute_rejects_non_object_payload() -> None:
    runtime = SimpleNamespace(_closed=False)

    with pytest.raises(BridgeRequestError) as caught:
        asyncio.run(xinyu_bridge_codex_runtime.runtime_codex_execute(runtime, []))  # type: ignore[arg-type]

    assert caught.value.status == HTTPStatus.BAD_REQUEST
    assert caught.value.message == "request body must be a JSON object"


def test_codex_runtime_execute_rejects_ambiguous_text() -> None:
    runtime = SimpleNamespace(
        _closed=False,
        _payload_text=lambda payload: "plain chat",
    )

    with pytest.raises(BridgeRequestError) as caught:
        asyncio.run(xinyu_bridge_codex_runtime.runtime_codex_execute(runtime, {"text": "plain chat"}))

    assert caught.value.status == HTTPStatus.BAD_REQUEST
    assert caught.value.message == xinyu_bridge_codex_runtime.CODEX_AMBIGUOUS_REQUEST_MESSAGE


def test_codex_runtime_execute_schedules_background_delegate(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    def payload_text(payload: dict[str, object]) -> str:
        calls.append(("payload_text", dict(payload)))
        return "raw codex task"

    def augment(payload: dict[str, object], text: str) -> str:
        calls.append(("augment", {"payload": dict(payload), "text": text}))
        return f"{text} with dialogue context"

    async def schedule(payload: dict[str, object], *, text: str, auto_study: bool) -> dict[str, object]:
        calls.append(("schedule", {"payload": dict(payload), "text": text, "auto_study": auto_study}))
        return {"accepted": True, "job_id": payload["job_id"]}

    monkeypatch.setattr(
        xinyu_bridge_codex_runtime,
        "looks_like_codex_request",
        lambda text: text == "raw codex task",
    )
    payload: dict[str, object] = {"source": "qq_gateway_codex_execute_message", "text": "raw codex task"}
    runtime = SimpleNamespace(
        _closed=False,
        _payload_text=payload_text,
        _augment_codex_payload_with_dialogue_context=augment,
        _schedule_codex_background_delegate=schedule,
    )

    result = asyncio.run(
        xinyu_bridge_codex_runtime.runtime_codex_execute(
            runtime,
            payload,
            should_auto_study=lambda text: calls.append(("auto_study", text)) or True,
        )
    )

    assert result["accepted"] is True
    assert payload == {"source": "qq_gateway_codex_execute_message", "text": "raw codex task"}
    assert calls[0] == ("payload_text", payload)
    assert calls[1] == ("augment", {"payload": payload, "text": "raw codex task"})
    assert calls[2] == ("auto_study", "raw codex task with dialogue context")
    schedule_payload = calls[3][1]["payload"]  # type: ignore[index]
    assert schedule_payload["visible_window"] is True
    assert schedule_payload["window_title"] == "Xinyu codex"
    assert str(schedule_payload["job_id"]).startswith("codex-qq-")
    assert schedule_payload["timeout_seconds"] == 3600
    assert schedule_payload["network_access"] is True
    assert calls[3][1]["text"] == "raw codex task with dialogue context"  # type: ignore[index]
    assert calls[3][1]["auto_study"] is True  # type: ignore[index]


def test_codex_runtime_execute_runs_foreground_delegate(monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    async def start(payload: dict[str, object]) -> dict[str, object]:
        calls.append(("start", dict(payload)))
        return {"cleanup": {"removed": 1}, "presence_paths": {"job_id": "codex-fg"}}

    async def run(payload: dict[str, object], *, presence_paths: dict[str, object]) -> dict[str, object]:
        calls.append(("run", {"payload": dict(payload), "presence_paths": presence_paths}))
        return {"result": "delegate-result", "before_memory": {"before": 1}, "after_memory": {"after": 1}}

    async def finalize(payload: dict[str, object], **kwargs: object) -> dict[str, object]:
        calls.append(("finalize", {"payload": dict(payload), "kwargs": kwargs}))
        return {"accepted": True, "reply": "done"}

    monkeypatch.setattr(xinyu_bridge_codex_runtime, "looks_like_codex_request", lambda text: True)
    runtime = SimpleNamespace(
        _closed=False,
        _payload_text=lambda payload: "foreground codex task",
        _augment_codex_payload_with_dialogue_context=lambda payload, text: f"{text} with context",
        _start_codex_foreground_delegate=start,
        _run_codex_foreground_delegate=run,
        _finalize_codex_foreground_delegate_response=finalize,
    )
    payload: dict[str, object] = {"background": False, "auto_study": False, "text": "foreground codex task"}

    result = asyncio.run(
        xinyu_bridge_codex_runtime.runtime_codex_execute(
            runtime,
            payload,
            should_auto_study=lambda text: True,
        )
    )

    assert result == {"accepted": True, "reply": "done"}
    start_payload = calls[0][1]
    assert start_payload["visible_window"] is True  # type: ignore[index]
    assert start_payload["window_title"] == "Xinyu codex"  # type: ignore[index]
    assert "job_id" not in start_payload
    assert calls[1] == (
        "run",
        {"payload": start_payload, "presence_paths": {"job_id": "codex-fg"}},
    )
    final = calls[2][1]  # type: ignore[index]
    assert final["payload"] == start_payload
    assert final["kwargs"] == {
        "result": "delegate-result",
        "text": "foreground codex task with context",
        "auto_study": False,
        "cleanup": {"removed": 1},
        "before_memory": {"before": 1},
        "after_memory": {"after": 1},
        "presence_paths": {"job_id": "codex-fg"},
    }


def test_codex_runtime_prepare_codex_execute_payload_sets_background_defaults() -> None:
    payload: dict[str, object] = {"source": "qq_gateway_codex_execute_message"}
    calls: list[str] = []

    flags = xinyu_bridge_codex_runtime.prepare_codex_execute_payload(
        payload,
        text="run codex task",
        should_auto_study=lambda text: calls.append(text) or True,
        observed_at=datetime(2026, 6, 5, 1, 2, 3),
    )

    assert flags == {"auto_study": True, "background": True}
    assert calls == ["run codex task"]
    assert payload["visible_window"] is True
    assert payload["window_title"] == "Xinyu codex"
    assert payload["job_id"] == "codex-qq-20260605T010203"
    assert payload["timeout_seconds"] == 3600
    assert payload["network_access"] is True


def test_codex_runtime_prepare_codex_execute_payload_preserves_explicit_foreground_values() -> None:
    payload: dict[str, object] = {
        "auto_study": False,
        "background": False,
        "window_title": "Custom Codex",
    }

    flags = xinyu_bridge_codex_runtime.prepare_codex_execute_payload(
        payload,
        text="run codex task",
        should_auto_study=lambda text: True,
    )

    assert flags == {"auto_study": False, "background": False}
    assert payload["visible_window"] is True
    assert payload["window_title"] == "Custom Codex"
    assert "job_id" not in payload
    assert "network_access" not in payload


def test_codex_runtime_foreground_result_response_preserves_contract() -> None:
    result = SimpleNamespace(
        accepted=True,
        request_path="runtime/codex/request.md",
        workspace_path="runtime/codex/workspace",
        report_path="runtime/codex/report.md",
        last_message_path="runtime/codex/last-message.txt",
        exit_code=0,
        timed_out=False,
        stdout_tail="stdout",
        stderr_tail="stderr",
    )
    gate = {"status": "ok"}
    learner = {"newly_integrated_materials": 1}
    quality = {"quality_grade": "good"}
    notes = ["codex_delegate", "learning_after_codex:scheduled"]

    response = xinyu_bridge_codex_runtime.codex_foreground_result_response(
        result,
        reply="done reply",
        memory_changed=True,
        session_count=3,
        gate=gate,
        learner=learner,
        quality=quality,
        integrated=1,
        ready=2,
        blocked_unreadable=0,
        quality_grade="good",
        notes=notes,
    )

    assert response == {
        "accepted": True,
        "reply": "done reply",
        "memory_changed": True,
        "library_changed": True,
        "session_created": False,
        "sessions": 3,
        "request_path": "runtime/codex/request.md",
        "workspace_path": "runtime/codex/workspace",
        "report_path": "runtime/codex/report.md",
        "last_message_path": "runtime/codex/last-message.txt",
        "codex_exit_code": 0,
        "codex_timed_out": False,
        "stdout_tail": "stdout",
        "stderr_tail": "stderr",
        "source_integration_gate": gate,
        "learner_integration": learner,
        "learning_quality": quality,
        "integrated_materials": 1,
        "ready_materials": 2,
        "blocked_unreadable_materials": 0,
        "quality_grade": "good",
        "notes": notes,
    }


def test_codex_runtime_foreground_result_status_preserves_branches() -> None:
    assert xinyu_bridge_codex_runtime.codex_foreground_result_status(
        SimpleNamespace(accepted=True, timed_out=True)
    ) == "timeout_staged"
    assert xinyu_bridge_codex_runtime.codex_foreground_result_status(
        SimpleNamespace(accepted=False, timed_out=True)
    ) == "timeout"
    assert xinyu_bridge_codex_runtime.codex_foreground_result_status(
        SimpleNamespace(accepted=True, timed_out=False)
    ) == "done"
    assert xinyu_bridge_codex_runtime.codex_foreground_result_status(
        SimpleNamespace(accepted=False, timed_out=False)
    ) == "failed"


def test_codex_runtime_presence_status_from_result_preserves_branches() -> None:
    assert xinyu_bridge_codex_runtime.codex_presence_status_from_result(
        SimpleNamespace(accepted=True, timed_out=True)
    ) == "timed_out"
    assert xinyu_bridge_codex_runtime.codex_presence_status_from_result(
        SimpleNamespace(accepted=True, timed_out=False)
    ) == "finished"
    assert xinyu_bridge_codex_runtime.codex_presence_status_from_result(
        SimpleNamespace(accepted=False, timed_out=False)
    ) == "failed"


def test_codex_runtime_record_presence_state_uses_preview_paths_and_window(tmp_path: Path, monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_presence(root: Path, **kwargs: object) -> None:
        calls.append({"root": root, **kwargs})

    monkeypatch.setattr(xinyu_bridge_codex_runtime, "record_codex_presence", fake_presence)
    presence_paths = {
        "job_id": "codex-qq-test",
        "request_path": "request.md",
        "report_path": "report.md",
    }

    xinyu_bridge_codex_runtime.record_codex_delegate_presence_state(
        tmp_path,
        {"window_title": "Window A"},
        presence_paths=presence_paths,
        status="running",
    )

    assert calls == [
        {
            "root": tmp_path,
            "job_id": "codex-qq-test",
            "status": "running",
            "request_path": "request.md",
            "report_path": "report.md",
            "visible_window_title": "Window A",
        }
    ]


def test_codex_runtime_record_presence_result_uses_status_paths_and_window(tmp_path: Path, monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_presence(root: Path, **kwargs: object) -> None:
        calls.append({"root": root, **kwargs})

    monkeypatch.setattr(xinyu_bridge_codex_runtime, "record_codex_presence", fake_presence)
    presence_paths = {
        "job_id": "codex-qq-test",
        "request_path": "fallback-request.md",
        "report_path": "fallback-report.md",
    }

    xinyu_bridge_codex_runtime.record_codex_delegate_presence_result(
        tmp_path,
        {"window_title": "Window A"},
        result=SimpleNamespace(
            accepted=True,
            timed_out=False,
            request_path="result-request.md",
            report_path="result-report.md",
            exit_code=0,
        ),
        presence_paths=presence_paths,
    )
    xinyu_bridge_codex_runtime.record_codex_delegate_presence_result(
        tmp_path,
        {},
        result=SimpleNamespace(
            accepted=False,
            timed_out=True,
            request_path="",
            report_path="",
            exit_code=124,
        ),
        presence_paths=presence_paths,
    )

    assert calls == [
        {
            "root": tmp_path,
            "job_id": "codex-qq-test",
            "status": "finished",
            "request_path": "result-request.md",
            "report_path": "result-report.md",
            "exit_code": 0,
            "timed_out": False,
            "visible_window_title": "Window A",
        },
        {
            "root": tmp_path,
            "job_id": "codex-qq-test",
            "status": "timed_out",
            "request_path": "fallback-request.md",
            "report_path": "fallback-report.md",
            "exit_code": 124,
            "timed_out": True,
            "visible_window_title": "Xinyu codex",
        },
    ]


def test_codex_runtime_run_foreground_delegate_snapshots_and_runs_under_lock(tmp_path: Path, monkeypatch) -> None:
    calls: list[tuple[str, object]] = []
    snapshots: list[Path] = []

    class _Lock:
        async def __aenter__(self) -> None:
            calls.append(("lock", "enter"))

        async def __aexit__(self, exc_type, exc, tb) -> None:
            calls.append(("lock", "exit"))

    def fake_snapshot(root: Path) -> str:
        snapshots.append(root)
        calls.append(("snapshot", root))
        return f"snapshot-{len(snapshots)}"

    def fake_delegate(root: Path, payload: dict[str, object]) -> SimpleNamespace:
        calls.append(("delegate", {"root": root, "payload": dict(payload)}))
        return SimpleNamespace(accepted=True, timed_out=False)

    monkeypatch.setattr(xinyu_bridge_codex_runtime, "memory_snapshot", fake_snapshot)
    monkeypatch.setattr(xinyu_bridge_codex_runtime, "run_codex_delegate", fake_delegate)
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path / "repo",
        memory_root=tmp_path / "memory",
        _codex_delegate_lock=_Lock(),
    )

    result = asyncio.run(
        xinyu_bridge_codex_runtime.run_codex_foreground_delegate(
            runtime,
            {"task": "run codex"},
            presence_paths={"job_id": "codex-test", "request_path": "request.md", "report_path": "report.md"},
        )
    )

    assert result["result"].accepted is True
    assert result["before_memory"] == "snapshot-1"
    assert result["after_memory"] == "snapshot-2"
    assert calls == [
        ("lock", "enter"),
        ("snapshot", runtime.memory_root),
        ("delegate", {"root": runtime.xinyu_dir, "payload": {"task": "run codex"}}),
        ("snapshot", runtime.memory_root),
        ("lock", "exit"),
    ]


def test_codex_runtime_run_foreground_delegate_records_failed_presence_on_error(
    tmp_path: Path,
    monkeypatch,
) -> None:
    calls: list[tuple[str, object]] = []

    class _Lock:
        async def __aenter__(self) -> None:
            calls.append(("lock", "enter"))

        async def __aexit__(self, exc_type, exc, tb) -> None:
            calls.append(("lock", "exit"))

    def fake_snapshot(root: Path) -> str:
        calls.append(("snapshot", root))
        return "snapshot-before"

    def fake_delegate(root: Path, payload: dict[str, object]) -> SimpleNamespace:
        calls.append(("delegate", {"root": root, "payload": dict(payload)}))
        raise RuntimeError("boom")

    def fake_presence_state(
        root: Path,
        payload: dict[str, object],
        *,
        presence_paths: dict[str, object],
        status: str,
    ) -> None:
        calls.append(
            (
                "presence",
                {
                    "root": root,
                    "payload": dict(payload),
                    "presence_paths": dict(presence_paths),
                    "status": status,
                },
            )
        )

    monkeypatch.setattr(xinyu_bridge_codex_runtime, "memory_snapshot", fake_snapshot)
    monkeypatch.setattr(xinyu_bridge_codex_runtime, "run_codex_delegate", fake_delegate)
    monkeypatch.setattr(xinyu_bridge_codex_runtime, "record_codex_delegate_presence_state", fake_presence_state)
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path / "repo",
        memory_root=tmp_path / "memory",
        _codex_delegate_lock=_Lock(),
    )
    presence_paths = {"job_id": "codex-test", "request_path": "request.md", "report_path": "report.md"}

    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(
            xinyu_bridge_codex_runtime.run_codex_foreground_delegate(
                runtime,
                {"task": "run codex"},
                presence_paths=presence_paths,
            )
        )

    assert calls == [
        ("lock", "enter"),
        ("snapshot", runtime.memory_root),
        ("delegate", {"root": runtime.xinyu_dir, "payload": {"task": "run codex"}}),
        (
            "presence",
            {
                "root": runtime.xinyu_dir,
                "payload": {"task": "run codex"},
                "presence_paths": presence_paths,
                "status": "failed",
            },
        ),
        ("lock", "exit"),
    ]


def test_codex_runtime_run_background_delegate_runs_under_lock(tmp_path: Path, monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    class _Lock:
        async def __aenter__(self) -> None:
            calls.append(("lock", "enter"))

        async def __aexit__(self, exc_type, exc, tb) -> None:
            calls.append(("lock", "exit"))

    def fake_delegate(root: Path, payload: dict[str, object]) -> SimpleNamespace:
        calls.append(("delegate", {"root": root, "payload": dict(payload)}))
        return SimpleNamespace(accepted=True, timed_out=False)

    monkeypatch.setattr(xinyu_bridge_codex_runtime, "run_codex_delegate", fake_delegate)
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path / "repo",
        _codex_delegate_lock=_Lock(),
    )

    result = asyncio.run(
        xinyu_bridge_codex_runtime.run_codex_background_delegate(
            runtime,
            {"task": "background codex"},
        )
    )

    assert result.accepted is True
    assert calls == [
        ("lock", "enter"),
        ("delegate", {"root": runtime.xinyu_dir, "payload": {"task": "background codex"}}),
        ("lock", "exit"),
    ]


def test_codex_runtime_run_background_delegate_propagates_errors(tmp_path: Path, monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    class _Lock:
        async def __aenter__(self) -> None:
            calls.append(("lock", "enter"))

        async def __aexit__(self, exc_type, exc, tb) -> None:
            calls.append(("lock", "exit"))

    def fake_delegate(root: Path, payload: dict[str, object]) -> SimpleNamespace:
        calls.append(("delegate", {"root": root, "payload": dict(payload)}))
        raise RuntimeError("boom")

    monkeypatch.setattr(xinyu_bridge_codex_runtime, "run_codex_delegate", fake_delegate)
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path / "repo",
        _codex_delegate_lock=_Lock(),
    )

    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(
            xinyu_bridge_codex_runtime.run_codex_background_delegate(
                runtime,
                {"task": "background codex"},
            )
        )

    assert calls == [
        ("lock", "enter"),
        ("delegate", {"root": runtime.xinyu_dir, "payload": {"task": "background codex"}}),
        ("lock", "exit"),
    ]


def test_codex_runtime_stage_report_material_after_delegate_runs_stage_and_followup(tmp_path: Path, monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    class _Lock:
        async def __aenter__(self) -> None:
            calls.append(("lock", "enter"))

        async def __aexit__(self, exc_type, exc, tb) -> None:
            calls.append(("lock", "exit"))

    def fake_stage(root: Path, **kwargs: object) -> dict[str, object]:
        calls.append(("stage", {"root": root, **kwargs}))
        return {"material_id": "material-1", "notes": ["note-a", "", "note-b", "note-c", "note-d"]}

    async def followup(reason: str) -> None:
        calls.append(("followup", reason))

    def fake_create_task(coro, *, name: str | None = None):
        calls.append(("task", name))
        coro.close()
        return SimpleNamespace(name=name)

    monkeypatch.setattr(xinyu_bridge_codex_runtime, "stage_codex_report_material", fake_stage)
    monkeypatch.setattr(xinyu_bridge_codex_runtime.asyncio, "create_task", fake_create_task)
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        _global_turn_lock=_Lock(),
        _codex_learning_followup=followup,
    )

    result = asyncio.run(
        xinyu_bridge_codex_runtime.stage_codex_report_material_after_delegate(
            runtime,
            result=SimpleNamespace(accepted=True, report_path="report.md"),
            text="codex task",
            job_id="codex-qq-test",
            auto_study=True,
            followup_task_name="followup-task",
        )
    )

    assert result == {"material_id": "material-1", "notes": ["note-a", "note-b", "note-c"]}
    assert calls == [
        ("lock", "enter"),
        (
            "stage",
            {
                "root": tmp_path,
                "report_path": "report.md",
                "task_text": "codex task",
                "job_id": "codex-qq-test",
            },
        ),
        ("lock", "exit"),
        ("task", "followup-task"),
    ]


def test_codex_runtime_stage_report_material_after_delegate_skips_without_auto_study(tmp_path: Path, monkeypatch) -> None:
    def fail_stage(*args, **kwargs):
        raise AssertionError("stage should not run")

    monkeypatch.setattr(xinyu_bridge_codex_runtime, "stage_codex_report_material", fail_stage)
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        _global_turn_lock=object(),
        _codex_learning_followup=lambda reason: None,
    )

    result = asyncio.run(
        xinyu_bridge_codex_runtime.stage_codex_report_material_after_delegate(
            runtime,
            result=SimpleNamespace(accepted=True, report_path="report.md"),
            text="codex task",
            job_id="codex-qq-test",
            auto_study=False,
        )
    )

    assert result == {"material_id": "", "notes": []}


def test_codex_runtime_handoff_delegate_to_dream_skips_finished_result(tmp_path: Path, monkeypatch) -> None:
    def fail_handoff(*args, **kwargs):
        raise AssertionError("handoff should not run")

    monkeypatch.setattr(xinyu_bridge_codex_runtime, "handoff_codex_to_dream", fail_handoff)
    runtime = SimpleNamespace(xinyu_dir=tmp_path)

    result = asyncio.run(
        xinyu_bridge_codex_runtime.handoff_codex_delegate_to_dream(
            runtime,
            result=SimpleNamespace(accepted=True, timed_out=False),
            text="codex task",
        )
    )

    assert result == {"notes": [], "error_note": ""}


def test_codex_runtime_handoff_delegate_to_dream_runs_with_optional_lock(tmp_path: Path, monkeypatch) -> None:
    calls: list[tuple[str, object]] = []

    class _Lock:
        async def __aenter__(self) -> None:
            calls.append(("lock", "enter"))

        async def __aexit__(self, exc_type, exc, tb) -> None:
            calls.append(("lock", "exit"))

    def fake_handoff(root: Path, **kwargs: object) -> SimpleNamespace:
        calls.append(("handoff", {"root": root, **kwargs}))
        return SimpleNamespace(notes=["codex_dream_handoff"])

    monkeypatch.setattr(xinyu_bridge_codex_runtime, "handoff_codex_to_dream", fake_handoff)
    runtime = SimpleNamespace(xinyu_dir=tmp_path, _global_turn_lock=_Lock())
    delegate_result = SimpleNamespace(
        accepted=False,
        timed_out=True,
        report_path="report.md",
        request_path="request.md",
        workspace_path="workspace",
        exit_code=124,
    )

    result = asyncio.run(
        xinyu_bridge_codex_runtime.handoff_codex_delegate_to_dream(
            runtime,
            result=delegate_result,
            text="codex task",
            use_global_turn_lock=True,
        )
    )

    assert result == {"notes": ["codex_dream_handoff"], "error_note": ""}
    assert calls == [
        ("lock", "enter"),
        (
            "handoff",
            {
                "root": tmp_path,
                "task_text": "codex task",
                "report_path": "report.md",
                "request_path": "request.md",
                "workspace_path": "workspace",
                "timed_out": True,
                "exit_code": 124,
            },
        ),
        ("lock", "exit"),
    ]


def test_codex_runtime_handoff_delegate_to_dream_contains_errors(tmp_path: Path, monkeypatch) -> None:
    def fail_handoff(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(xinyu_bridge_codex_runtime, "handoff_codex_to_dream", fail_handoff)
    runtime = SimpleNamespace(xinyu_dir=tmp_path)
    delegate_result = SimpleNamespace(
        accepted=False,
        timed_out=False,
        report_path="report.md",
        request_path="request.md",
        workspace_path="workspace",
        exit_code=1,
    )

    result = asyncio.run(
        xinyu_bridge_codex_runtime.handoff_codex_delegate_to_dream(
            runtime,
            result=delegate_result,
            text="codex task",
            contain_errors=True,
        )
    )

    assert result == {"notes": [], "error_note": "codex_dream_handoff_failed:RuntimeError"}


def test_codex_runtime_settle_delegate_action_experience_returns_notes() -> None:
    calls: list[dict[str, object]] = []

    async def settle(payload: dict[str, object], *, request: dict[str, object], outcome: dict[str, object]):
        calls.append({"payload": payload, "request": request, "outcome": outcome})
        return {}, {}, ["action-note"]

    runtime = SimpleNamespace(
        _codex_completion_summary=lambda result: "codex summary",
        _settle_action_experience=settle,
    )
    result = SimpleNamespace(
        accepted=True,
        timed_out=False,
        exit_code=0,
        report_path="report.md",
    )

    notes = asyncio.run(
        xinyu_bridge_codex_runtime.settle_codex_delegate_action_experience(
            runtime,
            {"platform": "qq"},
            metadata={"action_layer_request": {"action": "inspect"}},
            result=result,
        )
    )

    assert notes == ["action-note"]
    assert calls[0]["payload"] == {"platform": "qq"}
    assert calls[0]["request"] == {"action": "inspect"}
    assert calls[0]["outcome"]["ok"] is True
    assert calls[0]["outcome"]["summary"] == ["codex summary"]
    assert calls[0]["outcome"]["load"] == {"codex_exit_code": 0, "timeout": False, "scheduled": True}


def test_codex_runtime_settle_delegate_action_experience_skips_without_request() -> None:
    runtime = SimpleNamespace(
        _codex_completion_summary=lambda result: "unexpected",
        _settle_action_experience=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("unexpected")),
    )

    notes = asyncio.run(
        xinyu_bridge_codex_runtime.settle_codex_delegate_action_experience(
            runtime,
            {"platform": "qq"},
            metadata={},
            result=SimpleNamespace(),
        )
    )

    assert notes == []


def test_codex_runtime_foreground_result_notes_preserves_order() -> None:
    notes = xinyu_bridge_codex_runtime.codex_foreground_result_notes(
        SimpleNamespace(accepted=True, notes=["delegate_note"]),
        report_material_id="material-1",
        report_material_notes=["material_note"],
        handoff_notes=["handoff_note"],
        handoff_error_note="",
        auto_study=True,
        cleanup={"cleaned_sessions": 1},
    )

    assert notes == [
        "delegate_note",
        "codex_report_material:material-1",
        "material_note",
        "handoff_note",
        "learning_after_codex:scheduled",
        "cleaned_idle_sessions:1",
    ]


def test_codex_runtime_foreground_result_notes_records_handoff_error_and_skip() -> None:
    notes = xinyu_bridge_codex_runtime.codex_foreground_result_notes(
        SimpleNamespace(accepted=False, notes=[]),
        report_material_id="",
        report_material_notes=[],
        handoff_notes=[],
        handoff_error_note="codex_dream_handoff_failed:RuntimeError",
        auto_study=True,
        cleanup={"cleaned_sessions": 0},
    )

    assert notes == [
        "codex_dream_handoff_failed:RuntimeError",
        "learning_after_codex:skipped",
    ]


def test_codex_runtime_finalize_foreground_response_stages_material_and_notes(tmp_path: Path) -> None:
    calls: list[dict[str, object]] = []

    def record_presence(root: Path, payload: dict[str, object], **kwargs: object) -> None:
        calls.append({"call": "presence", "root": root, "payload": payload, **kwargs})

    def status_reply(status: str, **kwargs: object) -> str:
        calls.append({"call": "status_reply", "status": status, **kwargs})
        return f"reply:{status}"

    async def stage_report(**kwargs: object) -> dict[str, object]:
        calls.append({"call": "stage", **kwargs})
        return {"material_id": "material-1", "notes": ["material-note", "", "material-note-2"]}

    async def handoff(**kwargs: object) -> dict[str, object]:
        calls.append({"call": "handoff", **kwargs})
        return {"notes": ["handoff-note"], "error_note": ""}

    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        _sessions={"s1": object(), "s2": object()},
        _record_codex_delegate_presence_result=record_presence,
        _codex_status_reply=status_reply,
        _stage_codex_report_material_after_delegate=stage_report,
        _handoff_codex_delegate_to_dream=handoff,
    )
    result = SimpleNamespace(
        accepted=True,
        timed_out=False,
        exit_code=0,
        request_path="request.md",
        workspace_path="workspace",
        report_path="report.md",
        last_message_path="last.txt",
        stdout_tail="stdout",
        stderr_tail="stderr",
        notes=["delegate-note"],
    )
    payload = {"raw_owner_task": "owner task"}
    presence_paths = {"job_id": "codex-job", "request_path": "request-preview.md", "report_path": "report-preview.md"}

    response = asyncio.run(
        xinyu_bridge_codex_runtime.finalize_codex_foreground_delegate_response(
            runtime,
            payload,
            result=result,
            text="fallback task",
            auto_study=True,
            cleanup={"cleaned_sessions": 1},
            before_memory={"same": True},
            after_memory={"same": True},
            presence_paths=presence_paths,
        )
    )

    assert response["accepted"] is True
    assert response["reply"] == "reply:done"
    assert response["memory_changed"] is True
    assert response["sessions"] == 2
    assert response["quality_grade"] == "scheduled"
    assert response["notes"] == [
        "delegate-note",
        "codex_report_material:material-1",
        "material-note",
        "material-note-2",
        "handoff-note",
        "learning_after_codex:scheduled",
        "cleaned_idle_sessions:1",
    ]
    assert calls == [
        {
            "call": "presence",
            "root": tmp_path,
            "payload": payload,
            "result": result,
            "presence_paths": presence_paths,
        },
        {
            "call": "status_reply",
            "status": "done",
            "paths": {
                "request_path": "request.md",
                "workspace_path": "workspace",
                "report_path": "report.md",
                "last_message_path": "last.txt",
            },
            "auto_study": True,
            "exit_code": 0,
            "task_text": "owner task",
        },
        {
            "call": "stage",
            "result": result,
            "text": "fallback task",
            "job_id": "codex-job",
            "auto_study": True,
        },
        {
            "call": "handoff",
            "result": result,
            "text": "fallback task",
            "use_global_turn_lock": True,
            "contain_errors": True,
        },
    ]


def test_codex_runtime_finalize_foreground_response_preserves_failed_status_and_handoff_error(tmp_path: Path) -> None:
    status_calls: list[str] = []

    async def no_material(**kwargs: object) -> dict[str, object]:
        del kwargs
        return {"material_id": "", "notes": []}

    async def failed_handoff(**kwargs: object) -> dict[str, object]:
        del kwargs
        return {"notes": [], "error_note": "codex_dream_handoff_failed:RuntimeError"}

    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        _sessions={},
        _record_codex_delegate_presence_result=lambda *args, **kwargs: None,
        _codex_status_reply=lambda status, **kwargs: status_calls.append(status) or f"reply:{status}",
        _stage_codex_report_material_after_delegate=no_material,
        _handoff_codex_delegate_to_dream=failed_handoff,
    )
    result = SimpleNamespace(
        accepted=False,
        timed_out=False,
        exit_code=1,
        request_path="request.md",
        workspace_path="workspace",
        report_path="report.md",
        last_message_path="last.txt",
        stdout_tail="",
        stderr_tail="error",
        notes=[],
    )

    response = asyncio.run(
        xinyu_bridge_codex_runtime.finalize_codex_foreground_delegate_response(
            runtime,
            {},
            result=result,
            text="fallback task",
            auto_study=True,
            cleanup={"cleaned_sessions": 0},
            before_memory={"before": True},
            after_memory={"after": True},
            presence_paths={"job_id": "codex-job"},
        )
    )

    assert status_calls == ["failed"]
    assert response["reply"] == "reply:failed"
    assert response["memory_changed"] is True
    assert response["quality_grade"] == "not_run"
    assert response["notes"] == [
        "codex_dream_handoff_failed:RuntimeError",
        "learning_after_codex:skipped",
    ]

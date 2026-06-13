from __future__ import annotations

from http import HTTPStatus
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import xinyu_bridge_external_plugin_routes as routes
from xinyu_bridge_errors import BridgeRequestError
from xinyu_external_plugins import TRANSPORT_MCP, TRANSPORT_NATIVE_BRIDGE


def _runtime(root: Path, **extra: Any) -> SimpleNamespace:
    values: dict[str, Any] = {
        "xinyu_dir": root,
        "_sessions": {"session-one": object()},
        "_closed": False,
    }
    values.update(extra)
    return SimpleNamespace(**values)


@pytest.mark.asyncio
async def test_external_plugin_manifest_reports_status_and_sessions(tmp_path: Path) -> None:
    result = await routes.external_plugin_manifest(_runtime(tmp_path), {})

    assert result["ok"] is True
    assert result["accepted"] is True
    assert result["sessions"] == 1
    assert result["memory_changed"] is False
    assert "external_plugin_manifest" in result["notes"]
    assert {item["plugin_id"] for item in result["plugins"]} >= {"codex", "kohaku_terrarium", "mcp_gateway"}


@pytest.mark.asyncio
async def test_external_plugin_routes_reject_non_object_payload(tmp_path: Path) -> None:
    with pytest.raises(BridgeRequestError) as exc:
        await routes.external_plugin_config(_runtime(tmp_path), ["bad"])  # type: ignore[arg-type]

    assert exc.value.status is HTTPStatus.BAD_REQUEST
    assert exc.value.message == "request body must be a JSON object"


@pytest.mark.asyncio
async def test_external_plugin_routes_reject_closed_runtime(tmp_path: Path) -> None:
    with pytest.raises(BridgeRequestError) as exc:
        await routes.external_plugin_manifest(_runtime(tmp_path, _closed=True), {})

    assert exc.value.status is HTTPStatus.SERVICE_UNAVAILABLE


@pytest.mark.asyncio
async def test_external_plugin_call_can_prepare_enabled_mcp_gateway(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    saved = await routes.external_plugin_config(
        runtime,
        {"plugin_id": "mcp_gateway", "enabled": True},
    )

    result = await routes.external_plugin_call(
        runtime,
        {
            "plugin_id": "mcp_gateway",
            "capability": "list_tools",
            "args": {"server": "local"},
            "execute": False,
            "context": {
                "source": "unit_test",
                "owner_private": True,
                "reason": "verify route extraction",
            },
        },
    )

    assert saved["accepted"] is True
    assert result["ok"] is True
    assert result["result"] == "prepared"
    assert result["prepared"]["request"]["transport"] == TRANSPORT_MCP
    assert result["prepared"]["request"]["operation"] == "list_tools"
    assert result["execution"] == {}
    assert result["sessions"] == 1
    assert "external_plugin_prepared" in result["notes"]


@pytest.mark.asyncio
async def test_external_plugin_native_bridge_call_preserves_owner_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    async def fake_codex_execute(payload: dict[str, Any]) -> dict[str, Any]:
        captured["payload"] = payload
        return {"accepted": True, "reply": "delegated", "memory_changed": False, "notes": ["fake_codex"]}

    def fake_allowed(root: Path, plugin_id: str, *, proactive: bool = False) -> tuple[bool, str, dict[str, Any]]:
        assert root == tmp_path
        assert plugin_id == "codex"
        assert proactive is True
        return True, "allowed", {"config": {}}

    class FakePrepared:
        def to_dict(self) -> dict[str, Any]:
            return {
                "decision": {"ok": True, "reason": "allowed", "notes": []},
                "request": {
                    "transport": TRANSPORT_NATIVE_BRIDGE,
                    "bridge_method": "codex_execute",
                    "payload": {"text": "inspect safely"},
                },
            }

    def fake_prepare(plugin_id: str, capability: str, args: dict[str, Any], context: Any) -> FakePrepared:
        assert plugin_id == "codex"
        assert capability == "delegate_task"
        assert args == {"task_text": "inspect safely"}
        assert context.owner_private is True
        assert context.proactive is True
        assert context.reason == "bounded inspection"
        return FakePrepared()

    monkeypatch.setattr(routes, "external_plugin_runtime_allowed", fake_allowed)
    monkeypatch.setattr(routes, "prepare_external_call", fake_prepare)

    result = await routes.external_plugin_call(
        _runtime(tmp_path, codex_execute=fake_codex_execute),
        {
            "plugin_id": "codex",
            "capability": "delegate_task",
            "args": {"task_text": "inspect safely"},
            "context": {
                "source": "unit_test",
                "owner_private": True,
                "proactive": True,
                "reason": "bounded inspection",
            },
        },
    )

    metadata = captured["payload"]["metadata"]
    assert result["ok"] is True
    assert result["accepted"] is True
    assert result["result"] == "success"
    assert metadata["is_owner_user"] is True
    assert metadata["external_plugin_call"] is True
    assert metadata["external_plugin_id"] == "codex"
    assert metadata["external_plugin_capability"] == "delegate_task"


def test_maybe_run_self_thought_external_plugin_skips_when_not_needed(tmp_path: Path, monkeypatch) -> None:
    def fail_allowed(*args: Any, **kwargs: Any) -> tuple[bool, str, dict[str, Any]]:
        raise AssertionError("runtime gate should not be called")

    monkeypatch.setattr(routes, "external_plugin_runtime_allowed", fail_allowed)

    assert (
        routes.maybe_run_self_thought_external_plugin(
            _runtime(tmp_path),
            thought={"research_needed": False},
            checked_at="2026-06-06T01:00:00+08:00",
        )
        == []
    )


def test_maybe_run_self_thought_external_plugin_prepares_executes_and_traces(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    class _Decision:
        ok = True
        reason = "allowed"

    class _Prepared:
        decision = _Decision()

    def fake_allowed(root: Path, plugin_id: str, *, proactive: bool = False) -> tuple[bool, str, dict[str, Any]]:
        captured["allowed"] = (root, plugin_id, proactive)
        return (
            True,
            "allowed",
            {
                "config": {
                    "base_url": "http://127.0.0.1:8123",
                    "session_id": "session-1",
                    "creature_id": "creature-1",
                }
            },
        )

    def fake_prepare(plugin_id: str, capability: str, args: dict[str, Any], context: Any) -> _Prepared:
        captured["prepare"] = (plugin_id, capability, args, context)
        return _Prepared()

    def fake_execute(prepared: _Prepared, *, timeout_seconds: int) -> dict[str, Any]:
        captured["execute"] = (prepared, timeout_seconds)
        return {
            "ok": True,
            "status_code": 200,
            "error_code": "",
            "text_preview": "observation",
        }

    (tmp_path / "memory/context").mkdir(parents=True)
    (tmp_path / "memory/context/self_thought_state.md").write_text(
        "- query: inspect source drift\n- target: local notes\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(routes, "external_plugin_runtime_allowed", fake_allowed)
    monkeypatch.setattr(routes, "prepare_external_call", fake_prepare)
    monkeypatch.setattr(routes, "execute_http_prepared_call", fake_execute)

    notes = routes.maybe_run_self_thought_external_plugin(
        _runtime(tmp_path),
        thought={
            "research_needed": True,
            "focus_label": "fallback query",
            "research_route": "external_runtime",
        },
        checked_at="2026-06-06T01:00:00+08:00",
    )

    assert notes == ["external_plugin:kohaku_terrarium/ok/"]
    assert captured["allowed"] == (tmp_path, "kohaku_terrarium", True)
    plugin_id, capability, args, context = captured["prepare"]
    assert (plugin_id, capability) == ("kohaku_terrarium", "chat_creature")
    assert args["base_url"] == "http://127.0.0.1:8123"
    assert args["session_id"] == "session-1"
    assert args["creature_id"] == "creature-1"
    assert "Route: external_runtime" in args["message"]
    assert "Target: local notes" in args["message"]
    assert "Query: inspect source drift" in args["message"]
    assert context.source == "self_thought_loop"
    assert context.owner_private is True
    assert context.proactive is True
    assert context.approved is False
    assert context.reason == "self_thought research handoff: external_runtime"
    assert captured["execute"][1] == 45

    trace = (tmp_path / "runtime/external_plugin_trace.jsonl").read_text(encoding="utf-8")
    assert '"plugin_id":"kohaku_terrarium"' in trace
    assert '"route":"external_runtime"' in trace
    assert '"target":"local notes"' in trace
    assert '"query":"inspect source drift"' in trace


def test_maybe_run_self_thought_external_plugin_reports_gate_and_prepare_blocks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        routes,
        "external_plugin_runtime_allowed",
        lambda root, plugin_id, *, proactive: (False, "not_installed", {}),
    )

    runtime = _runtime(tmp_path)
    thought = {"research_needed": True}
    assert routes.maybe_run_self_thought_external_plugin(
        runtime,
        thought=thought,
        checked_at="2026-06-06T01:00:00+08:00",
    ) == ["external_plugin:kohaku_terrarium/skipped/not_installed"]

    class _Decision:
        ok = False
        reason = "owner_private_required"

    class _Prepared:
        decision = _Decision()

    monkeypatch.setattr(
        routes,
        "external_plugin_runtime_allowed",
        lambda root, plugin_id, *, proactive: (
            True,
            "allowed",
            {"config": {"session_id": "session-1", "creature_id": "creature-1"}},
        ),
    )
    monkeypatch.setattr(routes, "prepare_external_call", lambda *args, **kwargs: _Prepared())

    assert routes.maybe_run_self_thought_external_plugin(
        runtime,
        thought=thought,
        checked_at="2026-06-06T01:00:00+08:00",
    ) == ["external_plugin:kohaku_terrarium/blocked/owner_private_required"]

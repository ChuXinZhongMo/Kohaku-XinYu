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

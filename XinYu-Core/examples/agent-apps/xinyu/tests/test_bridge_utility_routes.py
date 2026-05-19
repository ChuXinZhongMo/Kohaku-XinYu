from __future__ import annotations

import asyncio
from http import HTTPStatus
from pathlib import Path

import pytest

from xinyu_bridge_errors import BridgeRequestError
from xinyu_bridge_utility_routes import message_ack, probe


class FakeRuntime:
    def __init__(self, root: Path) -> None:
        self.xinyu_dir = root
        self._closed = False
        self._sessions = {"old": object()}
        self._review_admin_lock = asyncio.Lock()

    def _payload_text(self, payload: dict[str, object]) -> str:
        return str(payload.get("text") or "")

    async def _cleanup_idle_sessions(self) -> dict[str, int]:
        self._sessions.clear()
        return {"cleaned_sessions": 1}


@pytest.mark.asyncio
async def test_probe_stays_diagnostic_without_session_creation(tmp_path: Path) -> None:
    runtime = FakeRuntime(tmp_path)

    result = await probe(runtime, {"text": "hello"}, bridge_version="test-version")

    assert result["probe"] == "diagnostic_no_memory"
    assert result["version"] == "test-version"
    assert result["received_text_chars"] == 5
    assert result["memory_changed"] is False
    assert result["session_created"] is False
    assert result["cleaned_sessions"] == 1
    assert result["sessions"] == 0


@pytest.mark.asyncio
async def test_utility_routes_reject_non_object_payload(tmp_path: Path) -> None:
    runtime = FakeRuntime(tmp_path)

    with pytest.raises(BridgeRequestError) as exc:
        await message_ack(runtime, "bad")  # type: ignore[arg-type]

    assert exc.value.status is HTTPStatus.BAD_REQUEST


@pytest.mark.asyncio
async def test_utility_routes_reject_closed_runtime(tmp_path: Path) -> None:
    runtime = FakeRuntime(tmp_path)
    runtime._closed = True

    with pytest.raises(BridgeRequestError) as exc:
        await message_ack(runtime, {})

    assert exc.value.status is HTTPStatus.SERVICE_UNAVAILABLE

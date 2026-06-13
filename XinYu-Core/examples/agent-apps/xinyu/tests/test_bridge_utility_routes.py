from __future__ import annotations

import asyncio
from http import HTTPStatus
from pathlib import Path

import pytest

import xinyu_bridge_utility_routes
import xinyu_bridge_utility_probe
from xinyu_bridge_errors import BridgeRequestError
from xinyu_bridge_learning import LearningBridgeError
from xinyu_bridge_utility_routes import (
    learning_ingest,
    learning_observe,
    learning_study,
    message_ack,
    package_install,
    probe,
    runtime_probe,
    sticker_import,
)


class FakeLearningService:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def ingest(self, payload: dict[str, object]) -> dict[str, object]:
        self.calls.append(("ingest", payload))
        return {"route": "ingest", "payload": payload}

    async def study(self, payload: dict[str, object]) -> dict[str, object]:
        self.calls.append(("study", payload))
        return {"route": "study", "payload": payload}

    async def observe(self, payload: dict[str, object]) -> dict[str, object]:
        self.calls.append(("observe", payload))
        return {"route": "observe", "payload": payload}


class FakeRuntime:
    def __init__(self, root: Path) -> None:
        self.xinyu_dir = root
        self.bridge_version = "runtime-version"
        self._closed = False
        self._sessions = {"old": object()}
        self._review_admin_lock = asyncio.Lock()
        self._global_turn_lock = asyncio.Lock()
        self.learning_service = FakeLearningService()

    def _payload_text(self, payload: dict[str, object]) -> str:
        return str(payload.get("text") or "")

    async def _cleanup_idle_sessions(self) -> dict[str, int]:
        self._sessions.clear()
        return {"cleaned_sessions": 1}


def test_probe_stays_diagnostic_without_session_creation(tmp_path: Path) -> None:
    runtime = FakeRuntime(tmp_path)

    result = asyncio.run(probe(runtime, {"text": "hello"}, bridge_version="test-version"))

    assert result["probe"] == "diagnostic_no_memory"
    assert result["version"] == "test-version"
    assert result["received_text_chars"] == 5
    assert result["memory_changed"] is False
    assert result["session_created"] is False
    assert result["cleaned_sessions"] == 1
    assert result["sessions"] == 0


def test_runtime_probe_uses_runtime_bridge_version(tmp_path: Path) -> None:
    runtime = FakeRuntime(tmp_path)

    result = asyncio.run(runtime_probe(runtime, {"text": "hello"}))

    assert result["version"] == "runtime-version"
    assert result["received_text_chars"] == 5
    assert result["session_created"] is False


def test_probe_routes_delegate_to_health_diagnostics_service(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = FakeRuntime(tmp_path)
    payload = {"text": "hello"}
    calls: list[tuple[str, object, dict[str, object], str]] = []

    class Service:
        @staticmethod
        async def probe(
            received_runtime: object,
            received_payload: dict[str, object] | None = None,
            *,
            bridge_version: str,
            deps: object,
        ) -> dict[str, object]:
            calls.append(("probe", received_runtime, received_payload or {}, bridge_version))
            assert deps is not None
            return {"route": "service_probe"}

        @staticmethod
        async def runtime_probe(
            received_runtime: object,
            received_payload: dict[str, object] | None = None,
            *,
            deps: object,
        ) -> dict[str, object]:
            calls.append(("runtime_probe", received_runtime, received_payload or {}, "runtime"))
            assert deps is not None
            return {"route": "service_runtime_probe"}

    monkeypatch.setattr(xinyu_bridge_utility_probe, "HealthDiagnosticsService", Service)

    probe_result = asyncio.run(probe(runtime, payload, bridge_version="test-version"))
    runtime_probe_result = asyncio.run(runtime_probe(runtime, payload))

    assert probe_result == {"route": "service_probe"}
    assert runtime_probe_result == {"route": "service_runtime_probe"}
    assert calls == [
        ("probe", runtime, payload, "test-version"),
        ("runtime_probe", runtime, payload, "runtime"),
    ]


def test_utility_routes_reject_non_object_payload(tmp_path: Path) -> None:
    runtime = FakeRuntime(tmp_path)

    with pytest.raises(BridgeRequestError) as exc:
        asyncio.run(message_ack(runtime, "bad"))  # type: ignore[arg-type]

    assert exc.value.status is HTTPStatus.BAD_REQUEST


def test_utility_routes_reject_closed_runtime(tmp_path: Path) -> None:
    runtime = FakeRuntime(tmp_path)
    runtime._closed = True

    with pytest.raises(BridgeRequestError) as exc:
        asyncio.run(message_ack(runtime, {}))

    assert exc.value.status is HTTPStatus.SERVICE_UNAVAILABLE


def test_package_install_and_sticker_import_delegate_under_runtime_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = FakeRuntime(tmp_path)
    payload: dict[str, object] = {"text": "install pytest"}
    calls: list[tuple[str, Path, bool]] = []

    def fake_install(root: Path, received: dict[str, object]) -> dict[str, object]:
        calls.append(("package", root, received is payload))
        return {"accepted": True, "route": "package_install"}

    def fake_sticker(root: Path, received: dict[str, object]) -> dict[str, object]:
        calls.append(("sticker", root, received is payload))
        return {"accepted": True, "route": "sticker_import"}

    monkeypatch.setattr(xinyu_bridge_utility_routes, "install_python_packages", fake_install)
    monkeypatch.setattr(xinyu_bridge_utility_routes, "import_sticker_from_payload", fake_sticker)

    async def run_routes() -> tuple[dict[str, object], dict[str, object]]:
        package_result = await package_install(runtime, payload)
        sticker_result = await sticker_import(runtime, payload)
        return package_result, sticker_result

    package_result, sticker_result = asyncio.run(run_routes())

    assert package_result == {"accepted": True, "route": "package_install"}
    assert sticker_result == {"accepted": True, "route": "sticker_import"}
    assert calls == [("package", tmp_path, True), ("sticker", tmp_path, True)]


def test_learning_utility_routes_delegate_to_learning_service(tmp_path: Path) -> None:
    runtime = FakeRuntime(tmp_path)
    payload: dict[str, object] = {"file_path": "example.txt"}

    async def run_routes() -> tuple[dict[str, object], dict[str, object], dict[str, object]]:
        ingest_result = await learning_ingest(runtime, payload)
        study_result = await learning_study(runtime, payload)
        observe_result = await learning_observe(runtime, payload)
        return ingest_result, study_result, observe_result

    ingest_result, study_result, observe_result = asyncio.run(run_routes())

    assert ingest_result == {"route": "ingest", "payload": payload}
    assert study_result == {"route": "study", "payload": payload}
    assert observe_result == {"route": "observe", "payload": payload}
    assert runtime.learning_service.calls == [
        ("ingest", payload),
        ("study", payload),
        ("observe", payload),
    ]


def test_learning_ingest_maps_learning_bridge_error(tmp_path: Path) -> None:
    class FailingLearningService:
        async def ingest(self, payload: dict[str, object]) -> dict[str, object]:
            raise LearningBridgeError(HTTPStatus.FORBIDDEN, "outside allowed roots")

    runtime = FakeRuntime(tmp_path)
    runtime.learning_service = FailingLearningService()

    with pytest.raises(BridgeRequestError) as exc:
        asyncio.run(learning_ingest(runtime, {"file_path": "C:/secret.txt"}))

    assert exc.value.status is HTTPStatus.FORBIDDEN
    assert exc.value.message == "outside allowed roots"

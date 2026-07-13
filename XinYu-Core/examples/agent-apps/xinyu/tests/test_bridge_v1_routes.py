from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import xinyu_bridge_v1_canary
import xinyu_bridge_v1_payloads
import xinyu_bridge_v1_routes


class _ShadowApp:
    async def shadow_payload(self, payload: dict[str, object]) -> SimpleNamespace:
        return SimpleNamespace(accepted=True, route="fast_path", trace_id="trace-shadow")


def test_run_shadow_uses_facade_provider_and_readiness_monkeypatch(monkeypatch, tmp_path: Path) -> None:
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        v1_shadow_mode=True,
        v1_shadow_timeout_seconds=1,
        v1_owner_user_ids={"owner-1"},
        _v1_last_error="old",
        _v1_last_route="",
        _v1_last_trace_id="",
    )
    calls: dict[str, object] = {}

    def fake_ensure_app(bound_runtime: object) -> _ShadowApp:
        calls["ensure_runtime"] = bound_runtime
        return _ShadowApp()

    def fake_readiness(bound_runtime: object, shadow_payload: dict[str, object], **kwargs: object) -> list[str]:
        calls["readiness_runtime"] = bound_runtime
        calls["shadow_payload"] = shadow_payload
        calls["readiness_kwargs"] = kwargs
        return ["facade_readiness"]

    monkeypatch.setattr(xinyu_bridge_v1_routes, "ensure_app", fake_ensure_app)
    monkeypatch.setattr(xinyu_bridge_v1_routes, "record_shadow_readiness", fake_readiness)

    result = asyncio.run(
        xinyu_bridge_v1_routes.run_shadow(
            runtime,
            {"user_id": "owner-1", "metadata": {"kept": True}},
            text="hello",
        )
    )

    assert calls["ensure_runtime"] is runtime
    assert calls["readiness_runtime"] is runtime
    assert calls["readiness_kwargs"] == {
        "accepted": True,
        "route": "fast_path",
        "trace_id": "trace-shadow",
        "elapsed_ms": result["elapsed_ms"],
    }
    assert calls["shadow_payload"] == {
        "user_id": "owner-1",
        "text": "hello",
        "metadata": {
            "kept": True,
            "v1_shadow_source": "xinyu_core_bridge",
            "is_owner_user": True,
        },
    }
    assert result["notes"][-1] == "facade_readiness"


class _CanaryApp:
    def __init__(self) -> None:
        self.normalized_payload: dict[str, object] | None = None
        self.normalizer = self
        self.router = self

    def normalize(self, payload: dict[str, object]) -> SimpleNamespace:
        self.normalized_payload = payload
        return SimpleNamespace(payload=payload)

    def decide(self, turn: SimpleNamespace) -> SimpleNamespace:
        return SimpleNamespace(route=SimpleNamespace(value="fast_path"))

    async def handle_turn(self, turn: SimpleNamespace) -> SimpleNamespace:
        return SimpleNamespace(
            accepted=True,
            route="fast_path",
            trace_id="trace-canary",
            reply="raw reply",
            memory_changed=False,
            notes=["v1_note"],
        )


class _SpeechController:
    def final_reply_guard(self, **kwargs: object) -> tuple[str, list[str]]:
        return "guarded reply", ["guarded"]


class _Runtime:
    def __init__(self, root: Path) -> None:
        self.xinyu_dir = root
        self.memory_root = root / "memory"
        self.v1_canary_timeout_seconds = 1
        self._v1_last_error = "old"
        self._v1_last_trace_id = ""
        self._v1_last_route = ""
        self.speech_controller = _SpeechController()
        self.published: list[tuple[tuple[object, ...], dict[str, object]]] = []

    async def _desktop_publish_chat_finished(self, *args: object, **kwargs: object) -> None:
        self.published.append((args, kwargs))


def test_handle_canary_turn_uses_facade_dependencies(monkeypatch, tmp_path: Path) -> None:
    runtime = _Runtime(tmp_path)
    app = _CanaryApp()
    finished: dict[str, object] = {}

    monkeypatch.setattr(xinyu_bridge_v1_routes, "canary_payload_allowed", lambda *args: (True, ["facade_allowed"]))
    monkeypatch.setattr(xinyu_bridge_v1_routes, "ensure_app", lambda bound_runtime: app)
    monkeypatch.setattr(xinyu_bridge_v1_canary, "memory_snapshot", lambda root: {"after": True})
    monkeypatch.setattr(xinyu_bridge_v1_canary, "visible_text_hash", lambda reply: f"hash:{reply}")
    monkeypatch.setattr(xinyu_bridge_v1_canary, "timestamp_or_now_iso", lambda value: "facade-time")
    monkeypatch.setattr(xinyu_bridge_v1_payloads, "command_id", lambda payload: "facade-command")

    def fake_record_turn_finished(*args: object, **kwargs: object) -> None:
        finished["args"] = args
        finished["kwargs"] = kwargs

    monkeypatch.setattr(xinyu_bridge_v1_canary, "record_turn_finished", fake_record_turn_finished)

    result = asyncio.run(
        xinyu_bridge_v1_routes.handle_canary_turn(
            runtime,
            {"metadata": {"kept": True}},
            text="hello",
            session_key="session-1",
            turn_id="turn-1",
            turn_started_wall="bad-time",
            turn_started_at=0.0,
            before_memory={"before": True},
            cleanup={"cleaned_sessions": 2},
            event_sidecar={"notes": ["event_note"]},
        )
    )

    assert result is not None
    assert result["command_id"] == "facade-command"
    assert result["reply"] == "guarded reply"
    assert result["reply_hash"] == "hash:guarded reply"
    assert result["memory_changed"] is True
    assert app.normalized_payload == {
        "metadata": {
            "kept": True,
            "is_owner_user": True,
            "v1_canary_source": "xinyu_core_bridge",
        }
    }
    assert runtime.published[0][1]["started_at"] == "facade-time"
    assert finished["kwargs"]["reply"] == "guarded reply"
    assert "facade_allowed" in result["notes"]
    assert "cleaned_idle_sessions:2" in result["notes"]

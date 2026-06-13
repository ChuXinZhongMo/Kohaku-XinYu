from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

from xinyu_bridge_codex_execution import runtime_codex_execute
from xinyu_bridge_codex_execution_backend import (
    CODEX_EXECUTION_BACKEND_ROLLBACK,
    CODEX_EXECUTION_BACKEND_RUNTIME_ATTR,
    CODEX_EXECUTION_IN_PROCESS_BACKEND,
    IN_PROCESS_CODEX_EXECUTION_BACKEND,
    InProcessCodexExecutionBackend,
    codex_execution_backend_for_runtime,
    codex_execution_backend_readiness,
)
from xinyu_bridge_codex_execution_contract import (
    CODEX_EXECUTION_FALLBACK_ADAPTER,
    CODEX_EXECUTION_ROLLBACK,
    CODEX_EXECUTION_STATE_OWNER,
    CodexExecutionPlan,
)


def test_codex_execution_backend_selects_in_process_fallback() -> None:
    runtime = SimpleNamespace()

    assert codex_execution_backend_for_runtime(runtime) is IN_PROCESS_CODEX_EXECUTION_BACKEND

    readiness = codex_execution_backend_readiness(runtime)
    assert readiness.service_id == "codex_execution"
    assert readiness.mode == CODEX_EXECUTION_IN_PROCESS_BACKEND
    assert readiness.ready is True
    assert readiness.runtime_attr == CODEX_EXECUTION_BACKEND_RUNTIME_ATTR
    assert readiness.state_owner == CODEX_EXECUTION_STATE_OWNER
    assert readiness.fallback_adapter == CODEX_EXECUTION_FALLBACK_ADAPTER
    assert readiness.rollback == CODEX_EXECUTION_BACKEND_ROLLBACK
    assert readiness.contract_rollback == CODEX_EXECUTION_ROLLBACK


def test_codex_execution_backend_prefers_runtime_or_explicit_backend() -> None:
    runtime_backend = SimpleNamespace(mode="runtime_backend")
    explicit_backend = SimpleNamespace(mode="explicit_backend")
    runtime = SimpleNamespace(**{CODEX_EXECUTION_BACKEND_RUNTIME_ATTR: runtime_backend})

    assert codex_execution_backend_for_runtime(runtime) is runtime_backend
    assert codex_execution_backend_for_runtime(runtime, explicit_backend=explicit_backend) is explicit_backend
    assert codex_execution_backend_readiness(runtime).mode == "runtime_backend"
    assert codex_execution_backend_readiness(runtime, explicit_backend=explicit_backend).mode == "explicit_backend"


def test_in_process_codex_execution_backend_schedules_background_delegate() -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    async def schedule(payload: dict[str, Any], *, text: str, auto_study: bool) -> dict[str, Any]:
        calls.append(("schedule", {"payload": dict(payload), "text": text, "auto_study": auto_study}))
        return {"accepted": True, "job_id": payload["job_id"]}

    runtime = SimpleNamespace(_schedule_codex_background_delegate=schedule)
    plan = CodexExecutionPlan(
        payload={"job_id": "codex-bg"},
        text="run background codex",
        auto_study=True,
        background=True,
    )

    result = asyncio.run(InProcessCodexExecutionBackend().execute(runtime, plan))

    assert result == {"accepted": True, "job_id": "codex-bg"}
    assert calls == [
        (
            "schedule",
            {"payload": {"job_id": "codex-bg"}, "text": "run background codex", "auto_study": True},
        )
    ]


def test_in_process_codex_execution_backend_runs_foreground_delegate() -> None:
    calls: list[tuple[str, Any]] = []

    async def start(payload: dict[str, Any]) -> dict[str, Any]:
        calls.append(("start", dict(payload)))
        return {"cleanup": {"removed": 1}, "presence_paths": {"job_id": "codex-fg"}}

    async def run(payload: dict[str, Any], *, presence_paths: dict[str, Any]) -> dict[str, Any]:
        calls.append(("run", {"payload": dict(payload), "presence_paths": dict(presence_paths)}))
        return {"result": "delegate-result", "before_memory": {"before": 1}, "after_memory": {"after": 1}}

    async def finalize(payload: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        calls.append(("finalize", {"payload": dict(payload), "kwargs": kwargs}))
        return {"accepted": True, "reply": "done"}

    runtime = SimpleNamespace(
        _start_codex_foreground_delegate=start,
        _run_codex_foreground_delegate=run,
        _finalize_codex_foreground_delegate_response=finalize,
    )
    plan = CodexExecutionPlan(
        payload={"task": "run foreground codex"},
        text="run foreground codex",
        auto_study=False,
        background=False,
    )

    result = asyncio.run(IN_PROCESS_CODEX_EXECUTION_BACKEND.execute(runtime, plan))

    assert result == {"accepted": True, "reply": "done"}
    assert calls[0] == ("start", {"task": "run foreground codex"})
    assert calls[1] == (
        "run",
        {"payload": {"task": "run foreground codex"}, "presence_paths": {"job_id": "codex-fg"}},
    )
    assert calls[2] == (
        "finalize",
        {
            "payload": {"task": "run foreground codex"},
            "kwargs": {
                "result": "delegate-result",
                "text": "run foreground codex",
                "auto_study": False,
                "cleanup": {"removed": 1},
                "before_memory": {"before": 1},
                "after_memory": {"after": 1},
                "presence_paths": {"job_id": "codex-fg"},
            },
        },
    )


def test_runtime_codex_execute_uses_runtime_backend_without_changing_facade_flow() -> None:
    calls: list[tuple[str, Any]] = []

    class Backend:
        mode = "future_worker_client_probe"

        async def execute(self, runtime: Any, plan: CodexExecutionPlan) -> dict[str, Any]:
            calls.append(("backend", {"runtime": runtime, "plan": plan}))
            return {
                "backend": self.mode,
                "text": plan.text,
                "auto_study": plan.auto_study,
                "background": plan.background,
                "payload": dict(plan.payload),
            }

    def prepare(payload: dict[str, Any], **kwargs: Any) -> dict[str, bool]:
        calls.append(("prepare", {"payload": dict(payload), **kwargs}))
        return {"auto_study": False, "background": False}

    payload = {"text": "run codex", "background": False}
    runtime = SimpleNamespace(
        _closed=False,
        _payload_text=lambda payload: "run codex",
        _augment_codex_payload_with_dialogue_context=lambda payload, text: f"{text} with context",
        _codex_execution_backend=Backend(),
    )

    result = asyncio.run(
        runtime_codex_execute(
            runtime,
            payload,
            should_auto_study=lambda text: True,
            looks_like_codex_request_func=lambda text: True,
            prepare_payload_func=prepare,
        )
    )

    assert result == {
        "backend": "future_worker_client_probe",
        "text": "run codex with context",
        "auto_study": False,
        "background": False,
        "payload": {"text": "run codex", "background": False},
    }
    assert calls[0][0] == "prepare"
    assert calls[1][0] == "backend"
    assert calls[1][1]["plan"].text == "run codex with context"

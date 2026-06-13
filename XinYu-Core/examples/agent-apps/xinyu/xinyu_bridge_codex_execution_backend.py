from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from xinyu_bridge_codex_execution_contract import (
    CODEX_EXECUTION_FALLBACK_ADAPTER,
    CODEX_EXECUTION_ROLLBACK,
    CODEX_EXECUTION_SERVICE_ID,
    CODEX_EXECUTION_STATE_OWNER,
    CodexExecutionPlan,
)


CODEX_EXECUTION_BACKEND_RUNTIME_ATTR = "_codex_execution_backend"
CODEX_EXECUTION_IN_PROCESS_BACKEND = "in_process_runtime_delegate_backend"
CODEX_EXECUTION_BACKEND_ROLLBACK = "remove_runtime_backend_attr_to_use_in_process_fallback"


class CodexExecutionBackend(Protocol):
    mode: str

    async def execute(self, runtime: Any, plan: CodexExecutionPlan) -> dict[str, Any]:
        ...


@dataclass(frozen=True, slots=True)
class CodexExecutionBackendReadiness:
    service_id: str
    mode: str
    ready: bool
    runtime_attr: str
    state_owner: str
    fallback_adapter: str
    rollback: str
    contract_rollback: str
    notes: tuple[str, ...] = ()


class InProcessCodexExecutionBackend:
    mode = CODEX_EXECUTION_IN_PROCESS_BACKEND

    async def execute(self, runtime: Any, plan: CodexExecutionPlan) -> dict[str, Any]:
        if plan.background:
            return await runtime._schedule_codex_background_delegate(
                plan.payload,
                text=plan.text,
                auto_study=plan.auto_study,
            )

        delegate_start = await runtime._start_codex_foreground_delegate(plan.payload)
        presence_paths = delegate_start["presence_paths"]
        delegate_run = await runtime._run_codex_foreground_delegate(plan.payload, presence_paths=presence_paths)
        return await runtime._finalize_codex_foreground_delegate_response(
            plan.payload,
            result=delegate_run["result"],
            text=plan.text,
            auto_study=plan.auto_study,
            cleanup=delegate_start["cleanup"],
            before_memory=delegate_run["before_memory"],
            after_memory=delegate_run["after_memory"],
            presence_paths=presence_paths,
        )


IN_PROCESS_CODEX_EXECUTION_BACKEND = InProcessCodexExecutionBackend()


def codex_execution_backend_for_runtime(
    runtime: Any,
    *,
    explicit_backend: CodexExecutionBackend | None = None,
) -> CodexExecutionBackend:
    if explicit_backend is not None:
        return explicit_backend
    runtime_backend = getattr(runtime, CODEX_EXECUTION_BACKEND_RUNTIME_ATTR, None)
    if runtime_backend is not None:
        return runtime_backend
    return IN_PROCESS_CODEX_EXECUTION_BACKEND


def codex_execution_backend_readiness(
    runtime: Any,
    *,
    explicit_backend: CodexExecutionBackend | None = None,
) -> CodexExecutionBackendReadiness:
    backend = codex_execution_backend_for_runtime(runtime, explicit_backend=explicit_backend)
    return CodexExecutionBackendReadiness(
        service_id=CODEX_EXECUTION_SERVICE_ID,
        mode=getattr(backend, "mode", type(backend).__name__),
        ready=True,
        runtime_attr=CODEX_EXECUTION_BACKEND_RUNTIME_ATTR,
        state_owner=CODEX_EXECUTION_STATE_OWNER,
        fallback_adapter=CODEX_EXECUTION_FALLBACK_ADAPTER,
        rollback=CODEX_EXECUTION_BACKEND_ROLLBACK,
        contract_rollback=CODEX_EXECUTION_ROLLBACK,
        notes=(
            "runtime_facade_and_policy_remain_in_process",
            f"fallback_rollback={CODEX_EXECUTION_ROLLBACK}",
        ),
    )

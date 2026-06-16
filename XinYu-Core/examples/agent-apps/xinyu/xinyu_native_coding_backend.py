"""CodexExecutionBackend that runs XinYu's own native coding agent instead of the
external codex CLI.

Mirrors InProcessCodexExecutionBackend exactly except the execution step: the
``codex`` subprocess is replaced by ``run_native_coding_delegate`` (a real agentic
tool loop). All surrounding plumbing — presence paths, memory snapshots, the
finalize/outbox/learning path — is reused unchanged, so the result reaches the
owner through the same channel codex used.

Installed at bootstrap by setting ``runtime._codex_execution_backend``; controlled
by ``XINYU_NATIVE_CODING`` (default on). Set it to 0/false/no/off to fall back to
the in-process codex CLI backend.
"""

from __future__ import annotations

import asyncio
from typing import Any

from xinyu_bridge_codex_presence import record_codex_delegate_presence_state
from xinyu_bridge_memory_snapshot import memory_snapshot
from xinyu_native_coding import run_native_coding_delegate

NATIVE_CODING_BACKEND_MODE = "native_in_process_coding_backend"
DEFAULT_TIMEOUT_SECONDS = 900.0


class NativeCodingExecutionBackend:
    mode = NATIVE_CODING_BACKEND_MODE

    def __init__(
        self,
        *,
        model: str | None = None,
        tools: tuple[str, ...] | None = None,
        max_iterations: int = 40,
        delegate_func: Any = run_native_coding_delegate,
        memory_snapshot_func: Any = memory_snapshot,
    ) -> None:
        self._model = model
        self._tools = tools
        self._max_iterations = max_iterations
        self._delegate_func = delegate_func
        self._memory_snapshot_func = memory_snapshot_func

    def _timeout(self, plan: Any) -> float:
        try:
            return float(plan.payload.get("timeout_seconds") or DEFAULT_TIMEOUT_SECONDS)
        except (TypeError, ValueError):
            return DEFAULT_TIMEOUT_SECONDS

    async def _run_foreground(self, runtime: Any, plan: Any) -> dict[str, Any]:
        delegate_start = await runtime._start_codex_foreground_delegate(plan.payload)
        presence_paths = delegate_start["presence_paths"]
        cleanup = delegate_start["cleanup"]
        before_memory = self._memory_snapshot_func(runtime.memory_root)
        try:
            result = await self._delegate_func(
                runtime.xinyu_dir,
                plan.payload,
                task_text=plan.text,
                model=self._model,
                tools=self._tools,
                max_iterations=self._max_iterations,
                timeout=self._timeout(plan),
            )
        except Exception:
            record_codex_delegate_presence_state(
                runtime.xinyu_dir,
                plan.payload,
                presence_paths=presence_paths,
                status="failed",
            )
            raise
        after_memory = self._memory_snapshot_func(runtime.memory_root)
        return await runtime._finalize_codex_foreground_delegate_response(
            plan.payload,
            result=result,
            text=plan.text,
            auto_study=plan.auto_study,
            cleanup=cleanup,
            before_memory=before_memory,
            after_memory=after_memory,
            presence_paths=presence_paths,
        )

    async def execute(self, runtime: Any, plan: Any) -> dict[str, Any]:
        if plan.background:
            # Fire-and-forget: the long agent run must not block the chat turn; the
            # finalize step inside _run_foreground enqueues the outbox result when done.
            async def _runner() -> None:
                try:
                    await self._run_foreground(runtime, plan)
                except Exception as exc:  # never let a background failure escape
                    try:
                        runtime._trace_autonomous(f"native_coding_background_error={exc!r}")
                    except Exception:
                        pass

            asyncio.ensure_future(_runner())
            return {
                "accepted": True,
                "scheduled": True,
                "notes": ["native_coding_background_scheduled"],
            }
        return await self._run_foreground(runtime, plan)

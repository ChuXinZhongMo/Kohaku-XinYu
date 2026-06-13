from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
ROOT_TEXT = str(ROOT)
if ROOT_TEXT not in sys.path:
    sys.path.insert(0, ROOT_TEXT)

from xinyu_bridge_codex_execution import runtime_codex_execute
from xinyu_bridge_codex_execution_backend import (
    CODEX_EXECUTION_BACKEND_RUNTIME_ATTR,
    IN_PROCESS_CODEX_EXECUTION_BACKEND,
    codex_execution_backend_for_runtime,
)
from xinyu_bridge_codex_execution_response import codex_background_scheduled_response
from xinyu_bridge_codex_execution_worker_client import (
    CODEX_EXECUTION_WORKER_CLIENT_MODE,
    CODEX_EXECUTION_WORKER_RESPONSE_FIELDS,
    DryRunCodexExecutionWorkerClient,
)


IN_PROCESS_BACKGROUND_RESPONSE_FIELDS = (
    "accepted",
    "reply",
    "memory_changed",
    "library_changed",
    "session_created",
    "sessions",
    "request_path",
    "workspace_path",
    "report_path",
    "last_message_path",
    "codex_exit_code",
    "codex_timed_out",
    "stdout_tail",
    "stderr_tail",
    "source_integration_gate",
    "learner_integration",
    "learning_quality",
    "integrated_materials",
    "ready_materials",
    "blocked_unreadable_materials",
    "quality_grade",
    "notes",
)
WORKER_ONLY_RESPONSE_FIELDS = tuple(
    field for field in CODEX_EXECUTION_WORKER_RESPONSE_FIELDS if field != "accepted"
)


def _prepare_payload(payload: dict[str, Any], **kwargs: Any) -> dict[str, bool]:
    del kwargs
    return {"auto_study": False, "background": bool(payload.get("background"))}


def _execute(runtime: Any, payload: dict[str, Any]) -> dict[str, Any]:
    return asyncio.run(
        runtime_codex_execute(
            runtime,
            payload,
            should_auto_study=lambda text: False,
            looks_like_codex_request_func=lambda text: True,
            prepare_payload_func=_prepare_payload,
        )
    )


def _runtime_with_worker_backend(
    worker_backend: DryRunCodexExecutionWorkerClient,
) -> tuple[SimpleNamespace, list[dict[str, Any]]]:
    schedule_calls: list[dict[str, Any]] = []

    async def schedule_background_delegate(
        payload: dict[str, Any],
        *,
        text: str,
        auto_study: bool,
    ) -> dict[str, Any]:
        schedule_calls.append(
            {
                "payload": dict(payload),
                "text": text,
                "auto_study": auto_study,
                "backend_attr_present": hasattr(runtime, CODEX_EXECUTION_BACKEND_RUNTIME_ATTR),
            }
        )
        return codex_background_scheduled_response(
            {
                "job_id": payload["job_id"],
                "request_path": "request-preview.md",
                "workspace_path": "workspace",
                "report_path": "report-preview.md",
                "last_message_path": "last-message.txt",
            },
            reply="codex background delegate scheduled",
            auto_study=auto_study,
            cleanup={"cleaned_sessions": 0},
            session_count=0,
        )

    runtime = SimpleNamespace(
        _closed=False,
        _payload_text=lambda payload: str(payload.get("text", "")),
        _augment_codex_payload_with_dialogue_context=lambda payload, text: f"{text} with context",
        _schedule_codex_background_delegate=schedule_background_delegate,
        **{CODEX_EXECUTION_BACKEND_RUNTIME_ATTR: worker_backend},
    )
    return runtime, schedule_calls


def _run_smoke() -> None:
    worker_backend = DryRunCodexExecutionWorkerClient(enabled=True)
    runtime, schedule_calls = _runtime_with_worker_backend(worker_backend)

    assert codex_execution_backend_for_runtime(runtime) is worker_backend, "runtime attr backend was not selected"
    worker_result = _execute(
        runtime,
        {
            "job_id": "codex-worker-rollback-worker",
            "text": "run codex rollback smoke",
            "background": True,
            "timeout_seconds": 9,
        },
    )

    assert tuple(worker_result) == CODEX_EXECUTION_WORKER_RESPONSE_FIELDS, "worker response fields changed"
    assert worker_result["accepted"] is True, "worker dry-run did not accept the job"
    assert worker_result["mode"] == CODEX_EXECUTION_WORKER_CLIENT_MODE, "worker backend mode was not returned"
    assert worker_result["dry_run"] is True, "worker response is not marked dry-run"
    assert worker_result["request"]["job_id"] == "codex-worker-rollback-worker", "worker request job id changed"
    assert worker_result["request"]["text"] == "run codex rollback smoke with context", "facade text flow changed"
    assert schedule_calls == [], "in-process scheduler ran while worker runtime attr was set"

    delattr(runtime, CODEX_EXECUTION_BACKEND_RUNTIME_ATTR)
    assert not hasattr(runtime, CODEX_EXECUTION_BACKEND_RUNTIME_ATTR), "runtime backend attr was not removed"
    assert (
        codex_execution_backend_for_runtime(runtime) is IN_PROCESS_CODEX_EXECUTION_BACKEND
    ), "runtime attr removal did not restore in-process fallback"

    fallback_result = _execute(
        runtime,
        {
            "job_id": "codex-worker-rollback-in-process",
            "text": "run codex rollback smoke",
            "background": True,
            "timeout_seconds": 9,
        },
    )

    assert tuple(fallback_result) == IN_PROCESS_BACKGROUND_RESPONSE_FIELDS, "in-process public response shape changed"
    assert fallback_result["accepted"] is True, "in-process fallback did not accept the job"
    assert fallback_result["quality_grade"] == "background", "in-process background marker changed"
    assert "codex_delegate_background:scheduled" in fallback_result["notes"], "background schedule note missing"
    assert not (set(fallback_result) & set(WORKER_ONLY_RESPONSE_FIELDS)), (
        "in-process fallback response leaked worker response fields"
    )
    assert len(schedule_calls) == 1, "in-process scheduler was not called after rollback"
    assert schedule_calls[0]["backend_attr_present"] is False, "in-process fallback still depended on worker attr"
    assert schedule_calls[0]["text"] == "run codex rollback smoke with context", "rollback path changed facade text flow"


def test_rollback_unsets_runtime_backend_attr_smoke() -> None:
    _run_smoke()


def main() -> int:
    try:
        _run_smoke()
    except AssertionError as exc:
        print("rollback_unsets_runtime_backend_attr_smoke failed")
        if str(exc):
            print(f"- {exc}")
        return 1
    print("rollback_unsets_runtime_backend_attr_smoke: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[3]
ROOT_TEXT = str(ROOT)
if ROOT_TEXT not in sys.path:
    sys.path.insert(0, ROOT_TEXT)

from xinyu_bridge_codex_execution_contract import CodexExecutionPlan
from xinyu_bridge_codex_execution_worker_client import HttpCodexExecutionWorkerClient
from xinyu_bridge_codex_execution_worker_service import (
    CODEX_EXECUTION_WORKER_SERVICE_MODE,
    CodexExecutionWorkerService,
    codex_execution_worker_service_transport,
)


def _run_smoke() -> None:
    service = CodexExecutionWorkerService()
    health = service.handle_request("GET", "/health")
    assert health["ok"] is True, "worker service health is not ready"
    assert health["mode"] == CODEX_EXECUTION_WORKER_SERVICE_MODE, "worker service mode changed"
    assert health["executes_runtime"] is False, "dry-run worker service must not execute runtime Codex"

    client = HttpCodexExecutionWorkerClient(
        endpoint="http://127.0.0.1:8787",
        enabled=True,
        healthy=True,
        transport=codex_execution_worker_service_transport(service),
    )
    result = asyncio.run(
        client.execute(
            SimpleNamespace(),
            CodexExecutionPlan(
                payload={"job_id": "codex-worker-service-smoke", "timeout_seconds": 5},
                text="run codex service smoke",
                auto_study=False,
                background=True,
            ),
        )
    )

    assert result["accepted"] is True, "HTTP worker client did not accept worker service response"
    assert result["job_id"] == "codex-worker-service-smoke", "worker service changed job id"
    assert result["request"]["text"] == "run codex service smoke", "worker service changed request text"

    cancel = service.handle_request(
        "POST",
        "/codex/cancel",
        {"job_id": "codex-worker-service-smoke", "reason": "smoke"},
    )
    assert cancel["cancel_requested"] is True, "worker service cancel did not request cancellation"
    assert cancel["cancel_reason"] == "smoke", "worker service cancel reason changed"


def test_codex_execution_worker_service_smoke() -> None:
    _run_smoke()


def main() -> int:
    try:
        _run_smoke()
    except AssertionError as exc:
        print("codex_execution_worker_service_smoke failed")
        if str(exc):
            print(f"- {exc}")
        return 1
    print("codex_execution_worker_service_smoke: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

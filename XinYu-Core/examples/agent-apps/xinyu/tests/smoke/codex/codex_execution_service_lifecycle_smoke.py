from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

SMOKE_DIR = Path(__file__).resolve().parent
if str(SMOKE_DIR) not in sys.path:
    sys.path.insert(0, str(SMOKE_DIR))

from _bootstrap import ensure_project_root_on_path

ensure_project_root_on_path()

from xinyu_bridge_codex_execution_backend import (
    CODEX_EXECUTION_BACKEND_RUNTIME_ATTR,
    CODEX_EXECUTION_IN_PROCESS_BACKEND,
    codex_execution_backend_for_runtime,
)
from xinyu_bridge_codex_execution_service import (
    CODEX_EXECUTION_SERVICE_MODE_WORKER_CLIENT,
    CodexExecutionServiceConfig,
    build_codex_execution_service_handle,
)
from xinyu_bridge_codex_execution_worker_client import CODEX_EXECUTION_WORKER_CLIENT_MODE


def _check(failures: list[str], condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)


def _run_smoke() -> None:
    failures: list[str] = []

    default_runtime = SimpleNamespace()
    default_handle = build_codex_execution_service_handle()
    default_ready = default_handle.start(default_runtime)
    _check(failures, default_ready.ready is True, "default service handle is not ready")
    _check(
        failures,
        default_ready.backend_mode == CODEX_EXECUTION_IN_PROCESS_BACKEND,
        "default service handle no longer uses in-process backend",
    )
    _check(
        failures,
        not hasattr(default_runtime, CODEX_EXECUTION_BACKEND_RUNTIME_ATTR),
        "default service handle injected a runtime backend",
    )
    _check(failures, "no_external_worker_started" in default_ready.notes, "default service handle may start a worker")

    worker_runtime = SimpleNamespace()
    worker_handle = build_codex_execution_service_handle(
        CodexExecutionServiceConfig(
            mode=CODEX_EXECUTION_SERVICE_MODE_WORKER_CLIENT,
            worker_enabled=True,
            worker_healthy=True,
        )
    )
    worker_ready = worker_handle.start(worker_runtime)
    _check(failures, worker_ready.ready is True, "healthy worker service handle is not ready")
    _check(failures, worker_ready.backend_mode == CODEX_EXECUTION_WORKER_CLIENT_MODE, "worker backend mode changed")
    _check(failures, worker_ready.injected_runtime_backend is True, "healthy worker was not injected")
    _check(
        failures,
        codex_execution_backend_for_runtime(worker_runtime).mode == CODEX_EXECUTION_WORKER_CLIENT_MODE,
        "runtime backend selection did not pick the injected worker",
    )
    closed = worker_handle.close(worker_runtime)
    _check(failures, closed.started is False, "service handle did not close")
    _check(
        failures,
        codex_execution_backend_for_runtime(worker_runtime).mode == CODEX_EXECUTION_IN_PROCESS_BACKEND,
        "service close did not roll back to in-process backend",
    )

    unhealthy_runtime = SimpleNamespace()
    unhealthy_handle = build_codex_execution_service_handle(
        CodexExecutionServiceConfig(
            mode=CODEX_EXECUTION_SERVICE_MODE_WORKER_CLIENT,
            worker_enabled=True,
            worker_healthy=False,
            fallback_on_unhealthy=True,
        )
    )
    unhealthy_ready = unhealthy_handle.start(unhealthy_runtime)
    _check(failures, unhealthy_ready.ready is True, "unhealthy worker did not fall back ready")
    _check(
        failures,
        unhealthy_ready.backend_mode == CODEX_EXECUTION_IN_PROCESS_BACKEND,
        "unhealthy worker did not report in-process fallback",
    )
    _check(
        failures,
        not hasattr(unhealthy_runtime, CODEX_EXECUTION_BACKEND_RUNTIME_ATTR),
        "unhealthy worker injected a runtime backend",
    )

    if failures:
        raise AssertionError("\n".join(failures))


def test_codex_execution_service_lifecycle_smoke() -> None:
    _run_smoke()


def main() -> int:
    try:
        _run_smoke()
    except AssertionError as exc:
        print("codex_execution_service_lifecycle_smoke failed")
        for failure in str(exc).splitlines():
            print(f"- {failure}")
        return 1
    print("codex_execution_service_lifecycle_smoke: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

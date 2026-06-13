from __future__ import annotations

import asyncio
from copy import deepcopy
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

SMOKE_DIR = Path(__file__).resolve().parent
if str(SMOKE_DIR) not in sys.path:
    sys.path.insert(0, str(SMOKE_DIR))

from _bootstrap import ensure_project_root_on_path

ensure_project_root_on_path()

from xinyu_bridge_codex_execution import CODEX_VISIBLE_WINDOW_TITLE, runtime_codex_execute
from xinyu_bridge_codex_execution_backend import (
    CODEX_EXECUTION_BACKEND_RUNTIME_ATTR,
    CODEX_EXECUTION_IN_PROCESS_BACKEND,
)
from xinyu_bridge_codex_execution_timeout import CODEX_DEFAULT_TIMEOUT_SECONDS
from xinyu_bridge_codex_execution_worker_client import (
    CODEX_EXECUTION_WORKER_CLIENT_MODE,
    DryRunCodexExecutionWorkerClient,
)


def _payload_text(payload: dict[str, Any]) -> str:
    return str(payload.get("text") or payload.get("raw_message") or "").strip()


def _augment_codex_payload_with_dialogue_context(payload: dict[str, Any], text: str) -> str:
    del payload
    return f"{text}\n\n[dialogue_context]\nfacade payload smoke context"


def _check(condition: bool, failures: list[str], message: str) -> None:
    if not condition:
        failures.append(message)


async def _run_facade_payload_probe() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[str]]:
    client = DryRunCodexExecutionWorkerClient(enabled=True)
    runtime = SimpleNamespace(
        _closed=False,
        _payload_text=_payload_text,
        _augment_codex_payload_with_dialogue_context=_augment_codex_payload_with_dialogue_context,
        **{CODEX_EXECUTION_BACKEND_RUNTIME_ATTR: client},
    )
    payload: dict[str, Any] = {
        "source": "qq_gateway_codex_execute_message",
        "text": "run codex facade payload smoke",
        "background": True,
        "auto_study": False,
        "metadata": {"route": "/codex/execute", "smoke": "facade_payload"},
    }
    original_payload = deepcopy(payload)
    auto_study_inputs: list[str] = []

    result = await runtime_codex_execute(
        runtime,
        payload,
        should_auto_study=lambda text: auto_study_inputs.append(text) or True,
        looks_like_codex_request_func=lambda text: text.startswith("run codex"),
    )
    return result, payload, original_payload, auto_study_inputs


def _run_smoke() -> None:
    failures: list[str] = []
    result, payload, original_payload, auto_study_inputs = asyncio.run(_run_facade_payload_probe())
    request = result.get("request")
    request_payload = request.get("payload") if isinstance(request, dict) else None

    _check(payload == original_payload, failures, "input payload was mutated by runtime_codex_execute")
    _check(result.get("accepted") is True, failures, "worker dry-run did not accept the facade request")
    _check(result.get("mode") == CODEX_EXECUTION_WORKER_CLIENT_MODE, failures, "worker mode changed")
    _check(result.get("dry_run") is True, failures, "worker response lost dry_run marker")
    _check(result.get("fallback") == CODEX_EXECUTION_IN_PROCESS_BACKEND, failures, "worker fallback marker changed")
    _check(result.get("status") == "queued", failures, "worker status changed")
    _check(isinstance(request, dict), failures, "worker response missing request object")

    if isinstance(request, dict) and isinstance(request_payload, dict):
        job_id = str(request.get("job_id") or "")
        expected_text = auto_study_inputs[0] if auto_study_inputs else ""
        request_text = str(request.get("text") or "")
        _check(job_id.startswith("codex-qq-"), failures, "background facade job_id no longer uses codex-qq prefix")
        _check(bool(expected_text), failures, "should_auto_study was not called with facade text")
        _check(request_text == expected_text, failures, "request text no longer uses augmented text")
        _check(request_text.startswith(original_payload["text"]), failures, "request text lost original task text")
        _check(request.get("background") is True, failures, "request background flag changed")
        _check(request.get("auto_study") is False, failures, "request auto_study flag changed")
        _check(
            request.get("timeout_seconds") == CODEX_DEFAULT_TIMEOUT_SECONDS,
            failures,
            "request timeout_seconds default changed",
        )

        _check(request_payload.get("source") == original_payload["source"], failures, "payload source changed")
        _check(request_payload.get("text") == original_payload["text"], failures, "payload text changed")
        _check(request_payload.get("background") is True, failures, "payload background changed")
        _check(request_payload.get("auto_study") is False, failures, "payload auto_study changed")
        _check(request_payload.get("metadata") == original_payload["metadata"], failures, "payload metadata changed")
        _check(request_payload.get("visible_window") is True, failures, "payload visible_window default changed")
        _check(
            request_payload.get("window_title") == CODEX_VISIBLE_WINDOW_TITLE,
            failures,
            "payload window_title default changed",
        )
        _check(request_payload.get("job_id") == job_id, failures, "payload job_id and request job_id diverged")
        _check(
            request_payload.get("timeout_seconds") == CODEX_DEFAULT_TIMEOUT_SECONDS,
            failures,
            "payload timeout_seconds default changed",
        )
        _check(request_payload.get("network_access") is True, failures, "payload network_access default changed")
    elif isinstance(request, dict):
        failures.append("worker request missing payload object")

    if failures:
        raise AssertionError("\n".join(failures))


def test_facade_route_payload_contract_unchanged_smoke() -> None:
    _run_smoke()


def main() -> int:
    try:
        _run_smoke()
    except AssertionError as exc:
        print("codex_execution_facade_payload_smoke failed")
        for failure in str(exc).splitlines():
            print(f"- {failure}")
        return 1

    print("codex_execution_facade_payload_smoke: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

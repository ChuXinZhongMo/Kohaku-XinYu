from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace


import xinyu_native_coding as nc
from xinyu_codex_delegate import CodexDelegateResult
from xinyu_native_coding import run_native_coding_delegate
from xinyu_native_coding_backend import NativeCodingExecutionBackend


def test_enabled_default_on_with_off_escape(monkeypatch) -> None:
    monkeypatch.delenv("XINYU_NATIVE_CODING", raising=False)
    assert nc.native_coding_enabled() is True
    for off in ("0", "false", "no", "off"):
        monkeypatch.setenv("XINYU_NATIVE_CODING", off)
        assert nc.native_coding_enabled() is False


def test_coding_model_env_override(monkeypatch) -> None:
    monkeypatch.delenv("XINYU_CODING_MODEL", raising=False)
    assert nc.coding_model() == "mimo-v2.5-pro"
    monkeypatch.setenv("XINYU_CODING_MODEL", "some-stronger-model")
    assert nc.coding_model() == "some-stronger-model"


async def test_delegate_writes_result_files_and_shapes_result(tmp_path: Path) -> None:
    async def fake_runner(root, text, *, model, tools, max_iterations, timeout):
        return ("我已运行 echo 并得到 hello", False)

    result = await run_native_coding_delegate(
        tmp_path, {"text": "run echo hello"}, runner=fake_runner
    )
    assert isinstance(result, CodexDelegateResult)
    assert result.accepted is True
    assert result.exit_code == 0
    assert "hello" in result.reply
    # the summary/outbox path reads these files, so they must exist with the output
    assert Path(result.last_message_path).exists()
    assert Path(result.report_path).exists()
    assert "hello" in Path(result.last_message_path).read_text(encoding="utf-8")


async def test_delegate_handles_runner_failure(tmp_path: Path) -> None:
    async def boom(root, text, *, model, tools, max_iterations, timeout):
        raise RuntimeError("model exploded")

    result = await run_native_coding_delegate(tmp_path, {"text": "x"}, runner=boom)
    assert result.accepted is False
    assert result.exit_code == 1
    assert "native_coding_error" in result.notes


async def test_delegate_marks_timeout(tmp_path: Path) -> None:
    async def slow(root, text, *, model, tools, max_iterations, timeout):
        return ("partial", True)

    result = await run_native_coding_delegate(tmp_path, {"text": "x"}, runner=slow)
    assert result.timed_out is True
    assert result.exit_code is None
    assert "native_coding_timeout" in result.notes


class _FakeRuntime:
    def __init__(self, tmp_path: Path) -> None:
        self.xinyu_dir = tmp_path
        self.memory_root = tmp_path / "memory"
        self.calls: list[str] = []

    async def _start_codex_foreground_delegate(self, payload):
        self.calls.append("start")
        return {"presence_paths": {"p": "x"}, "cleanup": {"c": "y"}}

    async def _finalize_codex_foreground_delegate_response(self, payload, *, result, **kw):
        self.calls.append("finalize")
        self.finalized_result = result
        return {"accepted": True, "reply": "scheduled-canned", "notes": ["finalized"]}


async def test_backend_foreground_reuses_start_and_finalize(tmp_path: Path) -> None:
    runtime = _FakeRuntime(tmp_path)

    async def fake_delegate(root, payload, *, task_text, model, tools, max_iterations, timeout):
        return CodexDelegateResult(
            accepted=True, reply="done", request_path="", workspace_path=str(root),
            report_path="r", last_message_path="l", exit_code=0, timed_out=False,
            stdout_tail="done", stderr_tail="", notes=["native_coding_delegate"],
        )

    backend = NativeCodingExecutionBackend(
        delegate_func=fake_delegate, memory_snapshot_func=lambda root: "snap"
    )
    plan = SimpleNamespace(payload={"text": "task"}, text="task", auto_study=False, background=False)
    out = await backend.execute(runtime, plan)
    assert runtime.calls == ["start", "finalize"]
    assert runtime.finalized_result.reply == "done"
    assert out["notes"] == ["finalized"]


async def test_backend_background_schedules_and_returns_immediately(tmp_path: Path) -> None:
    import asyncio

    runtime = _FakeRuntime(tmp_path)
    ran = asyncio.Event()

    async def fake_delegate(root, payload, *, task_text, model, tools, max_iterations, timeout):
        ran.set()
        return CodexDelegateResult(
            accepted=True, reply="bg", request_path="", workspace_path=str(root),
            report_path="r", last_message_path="l", exit_code=0, timed_out=False,
            stdout_tail="bg", stderr_tail="", notes=[],
        )

    backend = NativeCodingExecutionBackend(
        delegate_func=fake_delegate, memory_snapshot_func=lambda root: "snap"
    )
    plan = SimpleNamespace(payload={"text": "task"}, text="task", auto_study=False, background=True)
    out = await backend.execute(runtime, plan)
    assert out.get("scheduled") is True
    await asyncio.wait_for(ran.wait(), timeout=2.0)  # the background task did run
    assert "finalize" in runtime.calls

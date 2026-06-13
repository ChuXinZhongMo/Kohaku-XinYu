from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import xinyu_bridge_learning_sidecars


class _Lock:
    def __init__(self, calls: list[object]) -> None:
        self._calls = calls

    async def __aenter__(self) -> None:
        self._calls.append("enter")

    async def __aexit__(self, exc_type, exc, tb) -> None:
        self._calls.append("exit")


def test_codex_learning_followup_writes_success_trace(tmp_path: Path, monkeypatch) -> None:
    calls: list[object] = []

    def fake_chain(root: Path, mode: str) -> dict[str, object]:
        calls.append((root, mode))
        return {
            "learner_integration": {"newly_integrated_materials": "3"},
            "learning_quality": {"quality_grade": "A"},
        }

    monkeypatch.setattr(xinyu_bridge_learning_sidecars, "run_learning_study_chain", fake_chain)
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        memory_root=tmp_path / "memory",
        _global_turn_lock=_Lock(calls),
    )

    asyncio.run(xinyu_bridge_learning_sidecars.codex_learning_followup(runtime, "codex_delegate_async"))

    assert calls == ["enter", (tmp_path, "codex_delegate_async"), "exit"]
    trace = (tmp_path / "memory/knowledge/codex_learning_followup_trace.log").read_text(encoding="utf-8")
    assert " ok " in trace
    assert "integrated=3" in trace
    assert "quality=A" in trace


def test_codex_learning_followup_writes_error_trace(tmp_path: Path, monkeypatch) -> None:
    calls: list[object] = []

    def fail_chain(root: Path, mode: str) -> dict[str, object]:
        raise RuntimeError("boom")

    monkeypatch.setattr(xinyu_bridge_learning_sidecars, "run_learning_study_chain", fail_chain)
    runtime = SimpleNamespace(
        xinyu_dir=tmp_path,
        memory_root=tmp_path / "memory",
        _global_turn_lock=_Lock(calls),
    )

    asyncio.run(xinyu_bridge_learning_sidecars.codex_learning_followup(runtime, "codex_delegate_async"))

    assert calls == ["enter", "exit"]
    trace = (tmp_path / "memory/knowledge/codex_learning_followup_trace.log").read_text(encoding="utf-8")
    assert " error " in trace
    assert "RuntimeError: boom" in trace

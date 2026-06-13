from __future__ import annotations

import asyncio
from pathlib import Path

import xinyu_bridge_observation
from xinyu_bridge_observation import observe


def test_learning_observe_writes_under_memory_root(tmp_path) -> None:
    root = tmp_path
    memory_root = root / "memory"

    async def cleanup_idle_sessions() -> dict[str, int]:
        return {"cleaned_sessions": 0}

    payload = {
        "text": "这是一条带有 https://example.com/doc 的群观察材料",
        "group_id": "10001",
        "user_id": "20002",
        "message_id": "30003",
        "priority_learning_group": True,
    }

    result = asyncio.run(
        observe(
            xinyu_dir=root,
            memory_root=memory_root,
            payload=payload,
            cleanup_idle_sessions=cleanup_idle_sessions,
            session_count=lambda: 0,
            lock=asyncio.Lock(),
        )
    )

    assert result["accepted"] is True
    assert (memory_root / "knowledge/group_learning_observations.md").exists()
    assert (memory_root / "context/real_life_input_events.md").exists()
    assert not (memory_root / "memory").exists()


def test_learning_observe_keeps_facade_sidecar_monkeypatch(tmp_path, monkeypatch) -> None:
    calls: list[tuple[Path, dict[str, object], str]] = []

    async def cleanup_idle_sessions() -> dict[str, int]:
        return {"cleaned_sessions": 0}

    def fake_record(root: Path, payload: dict[str, object], *, text: str) -> dict[str, object]:
        calls.append((root, payload, text))
        return {"notes": ["sidecar_patched"]}

    payload: dict[str, object] = {
        "text": "https://example.com/doc",
        "group_id": "10001",
        "user_id": "20002",
        "message_id": "30003",
    }
    monkeypatch.setattr(xinyu_bridge_observation, "record_learning_observe_event", fake_record)

    result = asyncio.run(
        observe(
            xinyu_dir=tmp_path,
            memory_root=tmp_path / "memory",
            payload=payload,
            cleanup_idle_sessions=cleanup_idle_sessions,
            session_count=lambda: 0,
            lock=asyncio.Lock(),
        )
    )

    assert calls == [(tmp_path, payload, "https://example.com/doc")]
    assert "sidecar_patched" in result["notes"]
